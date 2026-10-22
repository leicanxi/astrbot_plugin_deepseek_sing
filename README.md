# astrbot_plugin_deepseek_sing

适用于 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 的 AI 唱歌插件：群里点一首歌，AI 用指定音色翻唱并回传音频。

插件本身只是一个**轻量网关客户端**——歌曲搜索、下载、RVC 推理全部在网关侧完成，你的 AstrBot 服务器**不需要**安装 torch / ffmpeg / yt-dlp，也不需要 GPU。

```
QQ ──► AstrBot ──► 本插件 ──HTTP──► sing-song 网关 ──► 音乐搜索下载 + Replicate RVC 翻唱
                          │                ├── FlowBee（免部署，按次计费）
                          │                └── 或你自托管的 sing-gateway（用自己的 Replicate Token）
                          └── 音色白名单：FlowBee 用平台名单 / 自托管可自己配
```





## 演示

<video src="https://github.com/user-attachments/assets/21c6961b-bd65-49d2-885f-51c1ac7ab6fd" controls width="640"></video>

## 功能

- `/点歌 歌名 [音色名]` —— 网易云免费曲库搜歌 + AI 翻唱，直接发语音
- `/音色` —— 拉取当前可选音色列表
- LLM 工具调用 —— 直接对机器人说「唱一首《歌名》」即可
- 两种模式一键切换：FlowBee 免部署按次计费 / 自托管网关用你自己的 Replicate Token
- 自托管模式支持在插件配置页直接编辑音色白名单 JSON，改完即时生效
- QQ 语音发送失败时自动降级为文件附件，再失败附音频直链

### 目前进度
- beewith自有bot平台开发 done√
- astrbot插件移植 done√
- dsh插件移植  onlist
- 插件优化：可选伴奏混频 onlist
- 本地模型运行兼容 onlist
- 算法和音色优化 onlist
- 如果有bug、想法或建议欢迎提issue
- 欢迎抖音关注  ```5- 长按复制此条消息，打开抖音搜索，查看TA的更多作品。 https://v.douyin.com/pVt-TXIBWE0/ 8@4.com :8pm```
更多联系方式（qq群等）见主页链接

## 快速开始（FlowBee，30 秒）
你需要有一个服务器并且运行astrbot，
如果你没有服务器或不想自己部署，可以依赖后续flowbee的beewith项目，
服务器都会由flowbee建好，你无需承担完整的服务器费用，可能每个月几块钱足够。
如果你需要一台自己的服务器，直接[【腾讯云】4核4G3M79元/年](https://curl.qcloud.com/VKDxR8f7)，

下面是步骤:
1. 安装插件（AstrBot 插件目录下）：

   ```bash
   cd AstrBot/data/plugins
   git clone https://github.com/leicanxi/deepseek-sing-astrbot.git astrbot_plugin_deepseek_sing
   ```

   在 AstrBot 网页后台启用插件（首次会自动安装依赖）。

2. 打开插件配置页，只需填一项：**FlowBee API Key**（在 [FlowBee](https://flowbee.top) 获取，生成按次计费到你的 FlowBee 账户，免部署免服务器）。其余保持默认即可。
   'RECOMMEND':不用折腾visa卡和注册replicate。
4. 群里开唱：

   ```
   /点歌 雨爱
   /点歌 雨爱 cirno
   /音色
   ```

   > FlowBee 的曲库是网易云免费曲库（机房 IP 也能用、无需账号）；VIP / 数字专辑歌曲拿不到音频，机器人会提示换一首免费的。

## 自托管网关（用自己的 Replicate Token）

不想走按次计费？在你自己的服务器（和 AstrBot 同机即可）跑一个 sing-gateway，插件的生成就只花你自己 Replicate 账户的钱。
“Replicate”是一家美国的开源人工智能模型托管云平台，主要面向开发者，目的是让人无需深入掌握机器学习或自建基础设施，就能通过简单的 API 运行、微调或部署各种开源 AI 模型。国内目前暂未找到更好的平台，主流模型商均无部署，显卡租赁方案按小时计费，不划算，没收广告费。你需要github登录并有可扣费的visa卡，若没有推荐直接使用flowbee

1. 安装网关及运行时依赖：

   ```bash
   pip install octop
   pip install "yt-dlp>=2025.1.1" "imageio-ffmpeg>=0.5"
   ```

2. 启动网关：

   ```bash
   export SING_GATEWAY_TOKEN='choose-a-long-random-secret'
   export REPLICATE_API_TOKEN='r8_...'
   export SING_MUSIC_SOURCE=netease   # 可选：海外服务器建议（B站对机房 IP 有 412 风控）；默认 bilibili
   octop-sing-gateway --host 127.0.0.1 --port 9001
   ```

   Docker 网络、systemd、开机自启等部署细节见 [docs/sing-gateway.md](https://github.com/leicanxi/Octop/blob/main/docs/sing-gateway.md)。

3. 插件配置页切换模式并填写：

   | 配置项 | 值 |
   |--------|-----|
   | 运行模式 | `self-hosted` |
   | 网关地址 | `http://127.0.0.1:9001/v1`（与 AstrBot 同机时保持默认） |
   | 网关令牌 | 第 2 步设置的 `SING_GATEWAY_TOKEN` |

   注意：`REPLICATE_API_TOKEN` 配在**网关侧**（第 2 步的环境变量），不填在插件里。

## 音色管理

| 模式 | 谁能加音色 | 怎么加 |
|------|-----------|--------|
| FlowBee | 平台白名单制 | 想加新音色请联系站长；群里 `/音色` 看到的即当前名单 |
| self-hosted | 你自己，随时加 | 插件配置页「音色白名单 JSON」直接编辑，保存并重载插件后写入音色文件，网关即时生效；或直接编辑服务器上的 `~/.octop/sing-voices.json`（与网关的 `SING_VOICES_FILE` 保持一致） |

音色 JSON 格式：

```json
{
  "keine": "https://huggingface.co/leicanxi/rvc-models/resolve/main/keine_genso_flat.zip",
  "cirno": {
    "label": "Cirno",
    "url": "https://huggingface.co/.../cirno.zip"
  }
}
```

值可以是 zip URL 字符串，也可以是 `{"label": 显示名, "url": zip地址}`。zip 内是 RVC 模型文件（`.pth` + 可选 `.index`）。

> ⚠️ **安全须知**：`.pth` 模型文件是不可信数据（pickle 格式，加载即执行），且任意 URL 会由你的 Replicate 账户拉取。只添加你信任来源的模型地址。

## 配置项参考

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 运行模式 | `flowbee` | `flowbee`（免部署按次计费）或 `self-hosted`（自托管网关） |
| FlowBee API 地址 | `https://flowbee.top/v1` | 一般保持默认；自建 new-api 网关时改这里 |
| FlowBee API Key | 空 | [FlowBee](https://flowbee.top) 获取 |
| 网关地址 | `http://127.0.0.1:9001/v1` | 仅 self-hosted 模式 |
| 网关令牌 | 空 | 仅 self-hosted 模式，即 `SING_GATEWAY_TOKEN` |
| 音色白名单 JSON | 见上 | 仅 self-hosted 模式 |
| 音色文件路径 | `~/.octop/sing-voices.json` | 仅 self-hosted 模式，需与网关一致 |
| 片段长度（秒） | `25` | 范围 5~30 |
| 截取起点（秒） | `60` | 从歌曲第几秒开始截取 |
| 音高（半音） | `2` | 整体升降调 |
| 人声音域 | `no-change` | `no-change` / `male-to-female` / `female-to-male` |

## 计费说明

- **FlowBee 模式**：每次生成按 FlowBee 上 `sing-song` 模型的定价扣费（以 [FlowBee](https://flowbee.top) 页面标价为准），拉音色列表不计费，生成失败（网关报错）不扣费。
- **self-hosted 模式**：只花你自己 Replicate 账户的钱，单次真实成本典型 $0.016–0.054（约 0.12–0.39 元），最坏情况（冷启动）约 $0.08（约 0.58 元）。

### 缓存是怎么回事？

网关按「源歌曲 + 截取起点/长度 + 音色 + 模型参数」生成指纹，把生成结果缓存在网关磁盘上（默认保留 7 天、最多 50 条，同一网关的所有用户共享）：

- **命中**：7 天内用**完全相同的参数**对同一首歌再次生成 → 直接返回缓存，不再跑 Replicate，网关侧成本近似为零。
- **不命中**：新歌第一次唱、搜索落到不同的歌曲源、更换音色或截取参数、超过 7 天或被容量挤出 → 正常全价渲染。

两点需要知悉：

- **FlowBee 模式下**：new-api 按调用次数计费，感知不到网关内部是否命中缓存（平台计费机制所致）且平台visa支付会有汇损，服务器还需存储成本。后续如果flowbee使用人数增多，flowbee会按照实际情况调整价格，不留盈利空间。
- **冷启动耗时**：网关空闲较久后的第一次生成需要加载模型容器，可能需要 2~4 分钟，之后的生成约 1 分钟；单次真实成本也以此时最高（约 0.58 元）。

## 音色来源与免责声明

- 本插件自带及示例中的 RVC 音色模型来自 [voice-models](https://voice-models.com/)，我仅将部分模型上传至 HuggingFace 的 voice-model 仓库（如 [leicanxi/rvc-models](https://huggingface.co/leicanxi/rvc-models) 等），**版权归原训练者所有**，本项目不主张任何权利，与 voice-models 无利益关系。
- 本项目仅供学习与技术研究使用，请勿将生成内容用于侵权、诈骗或其他违法违规用途；由此产生的一切责任由使用者自行承担。
- 使用 FlowBee 或 Replicate 等第三方服务时，请同时遵守对应服务的条款。

## 协议（网关接口简述）

插件与网关之间是 OpenAI 兼容协议：

- 生成：`POST {base}/chat/completions`，`model=sing-song`，user content 为 JSON：`{"song": "歌名", "voice": "音色名", "start": 60, "duration": 25, "pitch": 2, "pitch_mode": "no-change"}`（`song` 可换成 `url` 直传歌曲链接，支持网易云 / B 站）。返回的 assistant content 是 JSON 音频块 `{"type": "audio", "source": {"url": "..."}}`。
- 拉音色：直连网关用 `GET {base}/voices`；经 new-api 中转时用 `POST {base}/chat/completions`、`model=sing-voices`（免费），返回 `{"type": "voices", "voices": [...]}`。

## License

MIT
