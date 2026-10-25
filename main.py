"""AstrBot plugin for the deepseek-sing gateway.

Thin client only — every generation happens on an OpenAI-compatible
``sing-song`` endpoint: either the hosted FlowBee gateway (per-call billing on
the user's own key) or a self-hosted sing-gateway (own Replicate token, own
voice whitelist file). No local audio stack is required.

Voice lists are pulled from ``GET /v1/voices`` (direct gateway) or via the
free ``sing-voices`` chat model when relayed behind new-api.
"""

from __future__ import annotations

import json
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.message.components import File, Record

SING_MODEL = "sing-song"
VOICES_MODEL = "sing-voices"
REQUEST_TIMEOUT = 360.0  # cold starts can take 2-4 minutes
VOICE_CACHE_TTL = 600.0  # seconds; /音色 always force-refreshes
PITCH_MODES = ("no-change", "male-to-female", "female-to-male")
FLOWBEE_KEY_URL = "https://flowbee.top"

# Config keys grouped into cards in _conf_schema.json (nested dicts since v0.2.0).
_CONFIG_GROUPS = {
    "flowbee_base_url": "flowbee",
    "flowbee_api_key": "flowbee",
    "gateway_base_url": "selfhosted",
    "gateway_token": "selfhosted",
    "voices": "selfhosted",
    "voices_file": "selfhosted",
    "voice": "singing",
    "duration": "singing",
    "start": "singing",
    "pitch": "singing",
    "pitch_mode": "singing",
}

USAGE_HINT = (
    "用法：/点歌 歌名 [音色名]　·　/音色 查看可选音色　·　/点歌帮助\n"
    "音色名可省略：未指定时使用插件配置的默认音色，未配置则用网关默认。"
)


def _clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _command_arg(event: AstrMessageEvent, command: str) -> str:
    """Strip the leading command token (with or without ``/``) from the text."""
    text = (event.message_str or "").strip()
    for prefix in (f"/{command}", command):
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


@register(
    "astrbot_plugin_deepseek_sing",
    "leicanxi",
    "AI 唱歌：B站点歌 + RVC 翻唱，走 sing-song 网关（FlowBee 免部署或自托管），音色白名单可自配",
    "0.2.0",
    "https://github.com/leicanxi/astrbot_plugin_deepseek_sing",
)
class DeepSeekSingPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self._voices_cache: list[dict[str, str]] = []
        self._voices_cache_at = 0.0
        self._voice_checked = False
        self._sync_voices_file()

    # ---- configuration -----------------------------------------------------

    def _get(self, key: str, default: Any = None) -> Any:
        """Read the grouped (v0.2.0 nested) config first, then legacy flat keys.

        Flattening the schema orphans values saved by older plugin versions;
        falling back keeps pre-upgrade configs working until re-saved.
        """
        group = _CONFIG_GROUPS.get(key)
        if group:
            sub = self.config.get(group)
            if isinstance(sub, dict):
                value = sub.get(key)
                if value not in (None, ""):
                    return value
        return self.config.get(key, default)

    @property
    def default_voice(self) -> str:
        return str(self._get("voice") or "").strip()

    @property
    def mode(self) -> str:
        return str(self.config.get("mode") or "flowbee").strip().lower()

    @property
    def base_url(self) -> str:
        key = "gateway_base_url" if self.mode == "self-hosted" else "flowbee_base_url"
        return str(self._get(key) or "").strip().rstrip("/")

    @property
    def api_key(self) -> str:
        key = "gateway_token" if self.mode == "self-hosted" else "flowbee_api_key"
        return str(self._get(key) or "").strip()

    def _require_key(self) -> str:
        key = self.api_key
        if key:
            return key
        if self.mode == "self-hosted":
            raise RuntimeError("未配置网关令牌，请在插件配置里填写 gateway_token（即网关的 SING_GATEWAY_TOKEN）")
        raise RuntimeError(f"未配置 FlowBee API Key，请在插件配置里填写（{FLOWBEE_KEY_URL} 获取）")

    def _gen_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "duration": _clamp_int(self._get("duration"), 25, 5, 30),
            "start": _clamp_int(self._get("start"), 60, 0, 3600),
            "pitch": _clamp_int(self._get("pitch"), 2, -24, 24),
        }
        pitch_mode = str(self._get("pitch_mode") or "no-change").strip()
        if pitch_mode in PITCH_MODES:
            params["pitch_mode"] = pitch_mode
        return params

    # ---- gateway client ----------------------------------------------------

    async def _chat(self, model: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.base_url:
            raise RuntimeError("未配置网关地址")
        key = self._require_key()
        request = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
            ],
        }
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json=request,
            )
        if response.status_code >= 400:
            raise RuntimeError(f"网关请求失败：HTTP {response.status_code} {self._error_detail(response)}")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("网关返回格式不正确") from exc
        if isinstance(content, str):
            try:
                block = json.loads(content)
            except ValueError as exc:
                raise RuntimeError("网关返回内容不是 JSON") from exc
        else:
            block = content
        if not isinstance(block, dict):
            raise RuntimeError("网关返回内容格式不正确")
        return block

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return response.text[:300]
        if isinstance(data, dict):
            detail = data.get("detail") or data.get("error")
            if isinstance(detail, dict):
                detail = detail.get("message")
            if detail:
                return str(detail)[:300]
        return response.text[:300]

    async def _fetch_voices(self, *, force: bool = False) -> list[dict[str, str]]:
        """Return the whitelist: direct GET first, then the sing-voices model."""
        now = time.monotonic()
        if not force and self._voices_cache and now - self._voices_cache_at < VOICE_CACHE_TTL:
            return self._voices_cache
        voices: list[dict[str, str]] = []
        # Tier 1: GET /v1/voices — works against a directly reachable gateway.
        try:
            key = self._require_key()
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers={"Authorization": f"Bearer {key}"},
                )
            if response.status_code == 200:
                for item in response.json().get("data") or []:
                    name = str(item.get("id") or "").strip()
                    if name:
                        voices.append({"name": name, "label": str(item.get("label") or name)})
        except Exception:
            logger.debug("[deepseek-sing] GET /voices failed", exc_info=True)
        # Tier 2: POST model=sing-voices — works behind new-api relays.
        if not voices:
            try:
                block = await self._chat(VOICES_MODEL, {})
                if block.get("type") == "voices":
                    for item in block.get("voices") or []:
                        name = str(item.get("name") or "").strip()
                        if name:
                            voices.append(
                                {"name": name, "label": str(item.get("label") or name)}
                            )
            except Exception as exc:
                logger.debug("[deepseek-sing] sing-voices pull failed: %s", exc)
        if voices:
            self._voices_cache = voices
            self._voices_cache_at = now
            self._check_default_voice(voices)
        return voices or self._voices_cache

    def _check_default_voice(self, voices: list[dict[str, str]]) -> None:
        """Warn once when the configured default voice is not in the whitelist."""
        if self._voice_checked:
            return
        self._voice_checked = True
        configured = self.default_voice
        if configured and not any(v["name"].casefold() == configured.casefold() for v in voices):
            logger.warning(
                "[deepseek-sing] 配置的默认音色 %r 不在当前白名单里，点歌将回退网关默认；发 /音色 查看可用列表",
                configured,
            )

    # ---- voices file sync (self-hosted) ------------------------------------

    def _sync_voices_file(self) -> None:
        """Write the configured voices JSON into the gateway voices file."""
        if self.mode != "self-hosted":
            return
        raw = self._get("voices")
        if not isinstance(raw, dict) or not raw:
            return
        text = json.dumps(raw, ensure_ascii=False, indent=2) + "\n"
        target = Path(
            str(self._get("voices_file") or "~/.octop/sing-voices.json")
        ).expanduser()
        try:
            if target.exists() and target.read_text(encoding="utf-8") == text:
                return
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            logger.info(f"[deepseek-sing] 已同步音色白名单到 {target}")
        except OSError:
            logger.warning(f"[deepseek-sing] 音色白名单同步失败：{target}", exc_info=True)

    # ---- generation ---------------------------------------------------------

    async def _sing(self, song: str, voice: str = "") -> dict[str, Any]:
        payload: dict[str, Any] = dict(self._gen_params())
        if song.startswith(("http://", "https://")):
            payload["url"] = song
        else:
            payload["song"] = song
        voice = (voice or "").strip() or self.default_voice
        if voice:
            payload["voice"] = voice
        block = await self._chat(SING_MODEL, payload)
        source = block.get("source")
        if block.get("type") != "audio" or not isinstance(source, dict) or not source.get("url"):
            raise RuntimeError(str(block.get("error") or "网关没有返回音频"))
        return block

    async def _download_audio(self, url: str) -> Path:
        path = Path(tempfile.gettempdir()) / f"deepseek_sing_{uuid.uuid4().hex}.mp3"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            path.write_bytes(response.content)
        return path

    async def _send_audio(self, event: AstrMessageEvent, url: str) -> None:
        try:
            await event.send(event.chain_result([Record(file=url)]))
            return
        except Exception:
            logger.warning("[deepseek-sing] 语音（URL）发送失败，尝试本地文件", exc_info=True)
        path: Path | None = None
        try:
            path = await self._download_audio(url)
            try:
                await event.send(event.chain_result([Record(file=str(path))]))
                return
            except Exception:
                logger.warning("[deepseek-sing] 语音（文件）发送失败，改发文件附件", exc_info=True)
            await event.send(
                event.chain_result([File(name=f"deepseek_sing_{int(time.time())}.mp3", file=str(path))])
            )
        except Exception:
            logger.warning("[deepseek-sing] 音频发送全部失败", exc_info=True)
            await event.send(event.plain_result(f"⚠️ 语音发送失败，音频链接：{url}"))
        finally:
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass

    # ---- commands -----------------------------------------------------------

    @filter.command("点歌")
    async def diange(self, event: AstrMessageEvent):
        """点一首歌让 AI 唱：/点歌 歌名 [音色名]"""
        args = _command_arg(event, "点歌")
        if not args:
            await event.send(event.plain_result(USAGE_HINT))
            return
        self._sync_voices_file()
        voices = await self._fetch_voices()
        song, voice = args, ""
        parts = args.rsplit(maxsplit=1)
        if len(parts) == 2:
            tail = parts[1].strip().casefold()
            if any(v["name"].casefold() == tail for v in voices):
                song, voice = parts[0].strip(), tail
        await event.send(event.plain_result("🎤 正在生成，请稍候（冷启动最长约 4 分钟）..."))
        try:
            block = await self._sing(song, voice)
        except Exception as exc:
            logger.warning("[deepseek-sing] 点歌失败：%s", exc)
            await event.send(event.plain_result(f"❌ 点歌失败：{exc}"))
            return
        await self._send_audio(event, str(block["source"]["url"]))

    @filter.command("音色")
    async def list_voices(self, event: AstrMessageEvent):
        """列出可选音色：/音色"""
        self._sync_voices_file()
        voices = await self._fetch_voices(force=True)
        if not voices:
            note = (
                "自托管模式：请检查网关地址与令牌是否正确。"
                if self.mode == "self-hosted"
                else f"FlowBee 模式：请检查 API Key（{FLOWBEE_KEY_URL}）。"
            )
            await event.send(
                event.plain_result(f"⚠️ 暂时拉不到音色列表，点歌将使用网关默认音色。\n{note}")
            )
            return
        lines = [
            f"- {v['label']}（音色名：{v['name']}）" if v["label"] != v["name"] else f"- {v['name']}"
            for v in voices
        ]
        configured = self.default_voice
        head = (
            f"🎵 可选音色（当前默认：{configured}）："
            if configured
            else "🎵 可选音色（未设置默认，将使用网关默认）："
        )
        custom = (
            "自托管模式：编辑音色白名单（配置页「音色白名单 JSON」或网关音色文件）即可。"
            if self.mode == "self-hosted"
            else "FlowBee 模式为平台白名单制，想新增自定义音色请联系管理员。"
        )
        await event.send(
            event.plain_result(
                head
                + "\n"
                + "\n".join(lines)
                + "\n用法：/点歌 歌名 音色名（音色名可省略，用默认）"
                + "\n💡 想固定音色？在插件配置「演唱默认参数 → 音色」里填音色名，点歌就不用每次带上。"
                + f"\n🎤 自定义音色：{custom}"
            )
        )

    @filter.command("点歌帮助")
    async def sing_help(self, event: AstrMessageEvent):
        """查看点歌帮助"""
        await event.send(
            event.plain_result(
                "🎤 DeepSeek 唱歌\n"
                "/点歌 歌名 [音色名]　AI 唱歌（音色名可省略）\n"
                "/音色　查看可选音色\n\n"
                "音色省略时使用插件配置的默认音色，未配置则用网关默认；自定义音色需管理员添加，详见 /音色。\n"
                "也可以直接对 LLM 说「唱一首《歌名》」，LLM 会自动调用工具。\n"
                "生成按次计费或由你的 Replicate Token 承担，详见插件 README。"
            )
        )

    # ---- LLM tool -----------------------------------------------------------

    @filter.llm_tool(name="sing_song")
    async def sing_song_tool(self, event: AstrMessageEvent, song: str, voice: str = "") -> str:
        '''唱一首歌（AI 翻唱），会直接把音频发到当前会话。

        Args:
            song(string): 歌曲名；用户明确确认过的 B 站歌曲链接也可以直接传。
            voice(string, optional): 音色名（白名单内），可先调用 list_sing_voices 查看。
        Returns:
            成功时返回"已发送"，失败时返回错误信息。
        '''
        self._sync_voices_file()
        try:
            block = await self._sing((song or "").strip(), (voice or "").strip())
        except Exception as exc:
            logger.warning("[deepseek-sing] LLM 工具点歌失败：%s", exc)
            return f"点歌失败：{exc}"
        url = str(block["source"]["url"])
        await self._send_audio(event, url)
        return f"已生成并发送：{url}"

    @filter.llm_tool(name="list_sing_voices")
    async def list_voices_tool(self, event: AstrMessageEvent) -> str:
        '''列出当前可选的唱歌音色及使用说明。

        Returns:
            音色名列表；选择音色时只传音色名，不能传自定义链接。
        '''
        voices = await self._fetch_voices()
        if not voices:
            return "暂时拉不到音色列表，可让唱歌曲目使用默认音色。"
        names = ", ".join(v["name"] for v in voices)
        return (
            f"可选音色：{names}。用户未指定音色时插件会自动使用配置的默认音色；"
            "选择时只传音色名，不能传自定义链接。"
        )
