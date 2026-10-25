# astrbot_plugin_deepseek_sing

适用于 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 的 AI 唱歌插件：点一首歌，AI 用指定音色翻唱并回传音频。

插件本身只是一个**轻量网关客户端**——歌曲搜索、下载、RVC 推理全部在网关侧完成，你的 AstrBot 服务器**不需要**安装 torch / ffmpeg / yt-dlp，也不需要 GPU。插件本身可以任意移植给你的平台（dsh、openclaw均可）

```
QQ ──► AstrBot（默认） ──► 本插件 ──HTTP──► sing-song 网关 ──► 音乐搜索下载 + Replicate RVC 翻唱
                          │                ├── FlowBee（免部署，按次计费）
                          │                └── 或你自托管的 sing-gateway（用自己的 Replicate Token）
                          └── 音色白名单：FlowBee 用平台名单 / 自托管可自己配
```

## 演示

<video src="https://github.com/user-attachments/assets/21c6961b-bd65-49d2-885f-51c1ac7ab6fd" controls width="640"></video>

## 功能

- `/点歌 歌名 [音色名]` —— 网易云曲库搜歌 + AI 翻唱，直接发语音（VIP 歌曲自动解锁：完整曲目或约 45 秒试听段）
- `/音色` —— 拉取当前可选音色列表，插件配置项也可选择。
- 指定音色 —— 在插件配置「演唱默认参数 → 音色」里填一次，点歌就不用每次指定音色
- LLM 工具调用 —— 直接对机器人说「唱一首《歌名》」即可
- 两种模式一键切换：FlowBee 免部署按次计费 / 自托管网关用你自己的 Replicate Token
- 音色自定义: Flowbee模式音色可联系我为你添加；自托管模式支持在插件配置页直接编辑音色白名单 JSON，改完即时生效
- QQ 语音发送失败时自动降级为文件附件，再失败附音频直链

### 目前进度、反馈与联系方式

- ****✅ Done****　beewith Bot 平台开发 · AstrBot 插件移植 · 自定义声音
  ****🚧 In Progress****　DSH 插件移植 · 可选伴奏混频 · 本地模型兼容 · 音色与算法优化

  💬 **反馈**  Bug / 想法 / 建议 → 欢迎提 [Issue](https://github.com/leicanxi/astrbot_plugin_deepseek_sing/issues)

  📮 **联系**
  - 抖音（可以关注一下，我目标是打造一整套开箱即用的ai生态）　
  - `5- 长按复制此条消息，打开抖音搜索，查看TA的更多作品。 https://v.douyin.com/pVt-TXIBWE0/ 8@4.com :8pm`
  - QQ 群等 见主页链接 

## 快速开始（FlowBee，30 秒）

你需要有一个服务器并且运行astrbot，
如果你没有服务器或不想自己部署，可以依赖后续flowbee的beewith项目，
服务器都会由flowbee建好，你无需承担完整的服务器费用，可能每个月几块钱足够。
如果你需要一台自己的服务器，直接[【腾讯云】4核4G3M79元/年](https://curl.qcloud.com/VKDxR8f7)

下面是步骤:

1. 安装插件（AstrBot 插件目录下）：

   ```bash
   cd AstrBot/data/plugins
   git clone https://github.com/leicanxi/astrbot_plugin_deepseek_sing.git astrbot_plugin_deepseek_sing
   ```

   在 AstrBot 网页后台启用插件（首次会自动安装依赖）。

2. 打开插件配置页，只需填一项：**FlowBee API Key**（在 [FlowBee](https://flowbee.top) 获取，生成按次计费到你的 FlowBee 账户，免部署免服务器）。“演唱默认参数”可按需配置。
   'RECOMMEND':不用折腾visa卡和注册replicate。

4. 群里/私聊开唱：

   ```
   /点歌 雨爱
   /点歌 雨爱 cirno
   /音色
   “唱一首《雨爱》”
   ```

   > FlowBee 的曲库是网易云（机房 IP 也能用、无需账号）。VIP / 数字专辑歌曲会通过社区解锁接口尽力获取——可能是完整曲目，也可能是约 45 秒的试听段（唱短片段完全够用）；解锁能力依赖社区维护、可能随网易封堵失效，失效时 VIP 歌会提示换一首免费的。

## 自托管网关（用自己的 Replicate Token）

不想走按次计费？在你自己的服务器（和 AstrBot 同机即可）跑一个 sing-gateway，插件的生成就只花你自己 Replicate 账户的钱。

<details>
<summary>什么是 Replicate？为什么用它？</summary>

Replicate 是一家美国的开源 AI 模型托管云平台，面向开发者，通过简单 API 即可运行、微调或部署开源模型，无需自建基础设施。国内暂无更好的替代平台，主流模型商均无部署，显卡租赁按小时计费不划算。

> 使用前提：GitHub 登录 + 可扣费的 Visa 卡；没有的话推荐直接用 Flowbee。（非广告）

</details>

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
   export SING_NCM_API=http://127.0.0.1:3010   # 可选：搭配 ncm-api sidecar 解锁 VIP 曲库，见 sing-gateway.md
   octop-sing-gateway --host 127.0.0.1 --port 9001
   ```

   Docker 网络、systemd、开机自启等部署细节见 [docs/sing-gateway.md](https://github.com/leicanxi/Octop/blob/main/docs/sing-gateway.md)。

3. 插件配置页切换模式并填写：

   | 配置项   | 值                                                      |
   | -------- | ------------------------------------------------------- |
   | 运行模式 | `self-hosted`                                           |
   | 网关地址 | `http://127.0.0.1:9001/v1`（与 AstrBot 同机时保持默认） |
   | 网关令牌 | 第 2 步设置的 `SING_GATEWAY_TOKEN`                      |

   注意：`REPLICATE_API_TOKEN` 配在**网关侧**（第 2 步的环境变量），不填在插件里。

## 音色管理

| 模式        | 谁能加音色     | 怎么加                                                                                                                                                                      |
| ----------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FlowBee     | 平台白名单制   | 想加新音色请联系站长；群里 `/音色` 看到的即当前名单                                                                                                                         |
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

### 固定默认音色

在插件配置「演唱默认参数 → 音色」里填音色名（群里发 `/音色` 可查看当前列表），点歌时不指定音色就用它；留空则用网关默认。优先级：**消息里指定的音色 > 配置的默认音色 > 网关默认**。

想新增自定义音色：FlowBee 模式为平台白名单制，请联系站长；自托管模式按上表自己加即可。

> ⚠️ **安全须知**：`.pth` 模型文件是不可信数据（pickle 格式，加载即执行），且任意 URL 会由你的 Replicate 账户拉取。只添加你信任来源的模型地址。

## 配置项参考

配置页按「FlowBee / 自托管 / 演唱默认参数」三个分组卡片展示，只需关注你所用模式的分组。

| 分组         | 配置项           | 默认值                      | 说明                                                        |
| ------------ | ---------------- | --------------------------- | ----------------------------------------------------------- |
| —            | 运行模式         | `flowbee`                   | `flowbee`（免部署按次计费）或 `self-hosted`（自托管网关）   |
| FlowBee      | FlowBee API 地址 | `https://flowbee.top/v1`    | 一般保持默认；自建 new-api 网关时改这里                     |
| FlowBee      | FlowBee API Key  | 空                          | [FlowBee](https://flowbee.top) 获取                         |
| 自托管       | 网关地址         | `http://127.0.0.1:9001/v1`  | 仅 self-hosted 模式                                         |
| 自托管       | 网关令牌         | 空                          | 仅 self-hosted 模式，即 `SING_GATEWAY_TOKEN`                |
| 自托管       | 音色白名单 JSON  | 见上                        | 仅 self-hosted 模式                                         |
| 自托管       | 音色文件路径     | `~/.octop/sing-voices.json` | 仅 self-hosted 模式，需与网关一致                           |
| 演唱默认参数 | 音色（默认音色） | 空                          | 点歌未指定音色时使用；留空用网关默认，发 `/音色` 查看列表   |
| 演唱默认参数 | 片段长度（秒）   | `25`                        | 范围 5~30                                                   |
| 演唱默认参数 | 截取起点（秒）   | `60`                        | 从歌曲第几秒开始截取                                        |
| 演唱默认参数 | 音高（半音）     | `2`                         | 整体升降调                                                  |
| 演唱默认参数 | 人声音域         | `no-change`                 | 下拉选择：`no-change` / `male-to-female` / `female-to-male` |

> 从 v0.1.0 升级：配置页改为分组卡片，旧版本保存的配置仍然生效（代码会兼容读取）；在配置页重新保存一次即迁移到新结构。

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
- 用户自定义音色与本项目无利益关系，纯属个人教育学习使用。
- 本项目仅供学习与技术研究使用，请勿将生成内容用于侵权、诈骗或其他违法违规用途；由此产生的一切责任由使用者自行承担。
- 使用 FlowBee 或 Replicate 等第三方服务时，请同时遵守对应服务的条款。

## 协议（网关接口简述）

插件与网关之间是 OpenAI 兼容协议：

- 生成：`POST {base}/chat/completions`，`model=sing-song`，user content 为 JSON：`{"song": "歌名", "voice": "音色名", "start": 60, "duration": 25, "pitch": 2, "pitch_mode": "no-change"}`（`song` 可换成 `url` 直传歌曲链接，支持网易云 / B 站）。返回的 assistant content 是 JSON 音频块 `{"type": "audio", "source": {"url": "..."}}`。
- 拉音色：直连网关用 `GET {base}/voices`；经 new-api 中转时用 `POST {base}/chat/completions`、`model=sing-voices`（免费），返回 `{"type": "voices", "voices": [...]}`。

## 与类似项目的关系、致谢

思路类似，代码有借鉴。大多数已有插件均依赖本地部署，本插件实现了云端方案，且借助网关分离的策略便于在多种agent平台间迁移。在这里感谢相关开源仓库，本仓库或多或少有你们的影子，因此本仓库也选择开源。

## License

MIT
