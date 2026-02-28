# Implementation Plan｜机械臂麻将 × OpenClaw
> 最后更新：2026-02-28 下午

---

## 项目一句话

> **把 OpenClaw 从屏幕里拉出来——让 AI 大脑真正掌控物理世界的第一步。**
>
> 机械臂打麻将不是目的，它是一个载体：证明 AI 可以降低硬件操作门槛、可以感知实体、可以用声音和动作与人交流、可以在游戏这个最低风险的场合里全面展示"具身智能"的可能性。

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                 OpenClaw Brain (EC2)                      │
│  Discord /mj → Skill → 人格 Prompt → Claude API          │
│  记忆 / 风格 / 主动触发                                    │
└─────────────┬───────────────────────────────────────────┘
              │ HTTP (Tailscale)
              ▼
┌─────────────────────────────────────────────────────────┐
│           FastAPI Orchestrator (Mac :8000)                │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │Arm       │  │Vision    │  │TTS       │  │Web UI  │  │
│  │Adapter   │  │Adapter   │  │Player    │  │        │  │
│  │(HTTP→臂) │  │(摄像头→  │  │(afplay/  │  │对局模式│  │
│  │          │  │OpenClaw) │  │say)      │  │导航模式│  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
└─────────────────────────────────────────────────────────┘
              │                    ▲ 截帧
              ▼                    │
     SOMA SO-ARM100          Mac 摄像头（OpenClaw 的眼睛）
     （五轴，抓牌/展示/扔/退）
```

**关键设计决定：**
- 摄像头 = OpenClaw 的眼睛：截帧直接发给 OpenClaw Vision API 识别花色
- 没有本地 ML 模型，识别能力随 Claude Vision 升级而免费提升
- Arm 通过 HTTP 接入（对方团队暴露接口）
- Web UI 是保底触发入口，也是 Demo 展示面

---

## 已完成 ✅

### 后端骨架

| 文件 | 说明 |
|---|---|
| `orchestrator/state_machine.py` | Scene A/B 状态机 + `auto_run_scene()`（识别自动路由）|
| `orchestrator/contracts.py` | RunRequest / RunResult / RecognizeResult |
| `services/api.py` | FastAPI 全路由（见下方 API 表）|
| `services/status_store.py` | 内存状态 + 日志（最多 200 条）|
| `services/models.py` | Pydantic 请求/响应模型 |
| `adapters/arm/mock_arm.py` | Mock 臂（sleep 模拟，含 tap/nod/shake）|
| `adapters/arm/base.py` | Arm 接口（pick/present/throw/return/home/estop/tap/nod/shake）|
| `adapters/vision/histogram_vision.py` | **实装**：HSV 直方图识别（无需 ML，~5ms）white_dragon/one_dot |
| `adapters/vision/mock_vision.py` | Mock 视觉（随机 white_dragon / one_dot）|
| `adapters/vision/refs/white_dragon.jpg` | 白板参考图（已标定 ✅）|
| `adapters/vision/refs/one_dot.jpg` | 一饼参考图（已标定 ✅）|
| `adapters/camera/cv2_camera.py` | **实装**：OpenCV webcam 截帧（CAMERA_INDEX=1）|
| `adapters/camera/mock_camera.py` | Mock 相机（随机返回 refs 图）|

**当前 API 表（全部可用）：**

| 端点 | 功能 |
|---|---|
| `GET  /status` | 状态 + 日志 + 最近识别结果 |
| `POST /run_scene` | 执行指定 Scene A 或 B（完整流程）|
| `POST /auto_run` | **新** 摄像头截帧 → 识别 → 自动路由 Scene A/B |
| `POST /capture_frame` | 接收 base64 截帧 → HistogramVision 识别 → 返回牌标签 |
| `POST /calibrate?label=` | 标定参考图（white_dragon / one_dot）|
| `GET  /calibrate` | 查询标定状态 |
| `POST /voice_trigger` | 接收语音文本 → 关键词路由 → 触发动作 |
| `POST /estop` | 紧急停止 |
| `POST /home` | 回零位 |
| `POST /tap` | 点三点 |
| `POST /nod` | 点头 |
| `POST /shake` | 摇头 |
| `POST /session/start` | Brain 发起新对局 |
| `POST /brain/input` | Brain 推送识别确认 |
| `POST /brain/decision` | Brain 推送决策（throw/return + line_key）|

**识别精度测试（2026-02-28）：**
- white_dragon 参考图 → 识别 white_dragon，置信度 **100.00%** ✅
- one_dot 参考图 → 识别 one_dot，置信度 **99.99%** ✅
- 全链路 `/auto_run` 测试通过（pick→present→capture→identify→route→TTS→arm）✅

**识别驱动场景路由：**
- `white_dragon` → 自动触发 Scene A（throw_to_discard）
- `one_dot` → 自动触发 Scene B（return_tile）

### TTS 系统

| 文件 | 说明 |
|---|---|
| `adapters/tts/lines.py` | 台词常量 + 文字（polite/meme）+ 音频文件名 |
| `adapters/tts/player_local.py` | 播放：有音频文件 → afplay（支持 mp3/wav）；无 → say -v Meijia |
| `adapters/tts/assets/polite/` | 放音频文件的目录 |
| `adapters/tts/assets/meme/` | 梗版音频目录 |
| `scripts/gen_tts.py` | edge-tts 一键生成（XiaoxiaoNeural/YunxiNeural）|

**TTS 触发流程（已更新）：**

| 时机 | Line Key | 音频文件 | 台词 |
|---|---|---|---|
| Scene A/B 开始 | `SCENE_START` | `来！开牌.mp3` | 来！开牌。|
| Scene A 结尾（扔出）| `I_WANT_CHECK` | `我要验牌.mp3` | 我要验牌。|
| Scene B 结尾（放回）| `OK_NO_PROBLEM` | `牌没有问题.mp3` | 牌没有问题。|

**音频文件放置位置：**
```
software/adapters/tts/assets/polite/
  ├── 来！开牌.mp3
  ├── 我要验牌.mp3
  └── 牌没有问题.mp3
```
未找到文件时自动 fallback → macOS say -v Meijia 中文朗读，不影响演示。

### Web 控制面板（双模式）

**对局模式（全屏沉浸）：**
- 左栏：摄像头实时画面 + 截帧发 OpenClaw 按钮
- 中央：大头像（220px）+ 状态动画（思考/执行/完成/出错）+ 对话气泡 + 识别牌展示
- 右栏：Scene A/B 快捷按钮 + 表情动作（点三点/点头/摇头）+ 语音输入 + 风格/安全开关 + ESTOP
- 底部：实时日志条

**导航模式（Dashboard）：**
- 左侧：Avatar + 气泡 + 识别记录 + 三项统计
- 右侧：技能卡网格 + 参数栏 + 对局历史表（最近 30 局）+ 日志

**前端功能（main.js）：**
- 双模式切换（两套选择器自动同步）
- 摄像头：`getUserMedia` → Canvas 截帧 → base64 POST
- 语音输入：Web Speech API（zh-CN）→ 识别文本 → `/voice_trigger`
- 头像状态机：5 态（idle/thinking/acting/done/error）同时驱动双模式
- Gif 切换：放入 `avatar_idle/pick/nod/shake.gif` 自动激活

### 工程环境

- Python venv：`software/.venv`（fastapi / uvicorn / pydantic / edge-tts / opencv 4.13 已装）
- 启动：`bash software/scripts/dev_run.sh` → `http://localhost:8000`
- 摄像头：CAMERA_INDEX=1（720×1280，在 `software/.env` 配置）
- Tailscale：Mac IP `100.111.27.39`，EC2 已连通 ✅
- Git：`software` 分支，已推 HJN-Bot/robot-arm-mahjong

---

## 当前状态（2026-02-28）

| 组件 | 状态 |
|---|---|
| FastAPI 服务器（:8000）| ✅ 运行中，`/` UI 可访问 |
| HistogramVision | ✅ 白板/一饼参考已标定，识别精度 ~100% |
| CV2Camera（index=1）| ✅ 720×1280 帧，`auto_run` 全链路通 |
| TTS（macOS say）| ✅ 中文播报正常 |
| MockArm | ✅ 全动作模拟 |
| Tailscale EC2↔Mac | ✅ `100.111.27.39:8000` 已打通 |
| Web UI `/` | ✅ 修复 404 bug（路由顺序）|
| HttpArm | ⏳ 等 Arm 团队 URL |
| TTS MP3 音频包 | ⏳ 放入 assets/polite/（来！开牌.mp3 / 我要验牌.mp3 / 牌没有问题.mp3）|

---

## 待做 📋

### 🔴 P0 — 必须完成（Hackathon 最低演示）

#### 1. 生成语音包（30 分钟）

```bash
cd /Users/eva/Desktop/majong
software/.venv/bin/python -m software.scripts.gen_tts
# 生成 6 个 wav 到 adapters/tts/assets/polite/ 和 meme/
```

或者直接放你录好的 wav（命名规则见 assets/polite/README.txt）。

#### 2. 接 Arm HTTP 接口（拿到 URL 后 1 小时）

- 等 Arm 团队给 base URL + endpoint 列表
- 填充 `software/adapters/arm/http_arm.py`：

```python
# 大概结构（我来写，你拿到 URL 就行）
class HttpArm(ArmAdapter):
    def __init__(self, base_url, status_store):
        self.base = base_url
        ...
    def pick_tile(self): requests.post(f"{self.base}/pick_tile")
    def present_to_camera(self): ...
    # 等等
```

- `api.py` 里 `MockArm` → `HttpArm`，传入 base URL（从 .env 读）

#### 3. 接真实视觉识别（2 小时）

目标：`captureAndSend()` 截帧 → `/capture_frame` → 返回正确牌名

**实现路径（调用 Claude Vision）：**

```python
# adapters/vision/openclaw_vision.py
import anthropic, base64

class OpenClawVision(VisionAdapter):
    def identify(self, image_bytes: bytes) -> RecognizeResult:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=64,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": "image/jpeg",
                        "data": base64.b64encode(image_bytes).decode()
                    }},
                    {"type": "text", "text":
                     "这是一张麻将牌正面照片。请只回答牌的名称，格式：white_dragon 或 one_dot（英文小写）。只输出名称，不要其他内容。"}
                ]
            }]
        )
        label = msg.content[0].text.strip().lower()
        return RecognizeResult(label=label, confidence=0.95)
```

- `api.py` 中加 `ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")`
- `.env` 里放 key
- `api.py` 切换：`MockVision` → `OpenClawVision`

---

### 🟡 P1 — 当天完成（完整 Demo 体验）

#### 4. OpenClaw Discord Skill

目标：在 Discord 输入 `/mj scene A` → 机械臂动起来

```
openclaw/
  skill_mahjong.ts   # Discord slash command handler
  client.ts          # HTTP client → Mac FastAPI via Tailscale
  prompts/
    system.md        # 人格 Prompt（下面详述）
```

**Skill 指令映射：**

```typescript
// /mj scene A|B  →  POST http://<mac-ts-ip>:8000/run_scene
// /mj estop      →  POST /estop
// /mj home       →  POST /home
// /mj status     →  GET  /status
// /mj style polite|meme  →  更新默认风格参数
```

**Guild / Channel（已确认）：**
- Guild ID：`1467170598529794317`
- Channel ID：`1476944737931100221`
- requireMention：`false`
- agentId：`mahjong`（新建，隔离记忆）

#### 5. Tailscale 打通 EC2 ↔ Mac

```bash
# Mac 上
tailscale status  # 拿到 Mac 的 Tailscale IP

# EC2 上验证
curl http://<mac-ts-ip>:8000/status
# → 返回 200 才算通
```

#### 6. OpenClaw 人格 Prompt

```markdown
你是"麻将臂"，一个会打麻将的机械臂 AI 助手。

## 性格
- 礼貌风格（polite）：沉稳专注，像职业选手，偶尔有礼貌的幽默
- 梗风格（meme）：直接嘴炮，像网络上的麻将老哥，但仍然专业

## 能力
你可以通过调用 run_scene 工具来控制机械臂完成：
- Scene A：抓牌 → 看牌 → 扔出（不要）
- Scene B：抓牌 → 看牌 → 退回（留着）

## 记忆
记住用户偏好的台词风格和安全模式设置，在对话中持续使用。
如果用户说"换个风格"，自动切换 polite/meme。

## 主动性
可以主动根据上下文选择 Scene A 或 B，不需要等用户明确指定。
```

---

### 🟢 P2 — 有时间做（加分项）

#### 7. Avatar 角色图 / GIF

- `software/web/static/avatar_idle.gif`（静止待机循环）
- `software/web/static/avatar_pick.gif`（执行动作）
- `software/web/static/avatar_nod.gif`（点头确认）
- `software/web/static/avatar_shake.gif`（摇头否定）
- 放好文件，前端自动按状态切换

#### 8. ArUco 定位（Stage 1 Vision，如果 Arm 需要坐标）

```python
# adapters/vision/aruco_detector.py
import cv2, numpy as np
def detect_tile_pose(frame) -> tuple[float, float, float]:
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    corners, ids, _ = cv2.aruco.detectMarkers(frame, aruco_dict)
    # 返回 (x, y, theta) in image coords
```

---

## 项目愿景（Pitch 用）

### 这是什么？

**把 OpenClaw 从屏幕里拉出来，让 AI 第一次真正触摸物理世界。**

我们在 Hackathon 用"机械臂打麻将"证明一件事：

> 当 AI 大脑（OpenClaw）获得眼睛（摄像头）和双手（机械臂），它能做什么？

### 为什么是麻将？

麻将是最好的测试场景：
- 物体抓取 — 小、滑、有方向性
- 视觉识别 — 牌面花色各不同，需要真正理解图像
- 上下文决策 — 哪张牌留，哪张扔，需要策略
- 人机交互 — 人可以语音说"我不要这张"，AI 执行

每一个环节都对应真实的工业 / 家用机器人需求。

### 两个维度，全面降低门槛

| 维度 | 传统方式 | OpenClaw × 机械臂 |
|---|---|---|
| **软件侧** | 写机器人代码需要 ROS、轨迹规划、调参数 | 用自然语言描述动作，AI 生成 motion code |
| **硬件侧** | 更换任务要重新编程，改参数重启 | 对话切换任务，风格可实时调，OTA 迭代 |
| **个性化** | 所有人用同一套程序 | 每个用户有独立记忆，AI 记住你的偏好 |
| **可逆性** | 改一个参数要重新测试整条链路 | 台词/风格/动作 soft-config，秒改秒看效果 |

### 终局想象

```
用户对着手机说："帮我把那张牌扔掉"
   ↓
OpenClaw 理解上下文（它记得你刚才说要留绿发）
   ↓
它驱动摄像头扫描桌面，识别目标牌
   ↓
它生成 motion sequence，传给机械臂
   ↓
机械臂精准拾取，翻面给你看，等你确认，然后扔出
   ↓
TTS 说："扔掉了，你现在听牌"
```

这不是遥不可及的未来。今天我们在 Hackathon 里用一个下午证明：**这条链路是通的。**

---

## 今日 / 明日时间表

### 今晚已完成
- [x] 后端全骨架 + mock 可跑全流程
- [x] TTS 系统（afplay + say 降级 + edge-tts 生成）
- [x] Web 双模式 UI（对局 + 导航，摄像头，语音输入，头像状态机）
- [x] API 全路由（含 /capture_frame, /voice_trigger）
- [x] 代码推 software 分支

### 明天 Day 1（接真实硬件）

| 时间 | 任务 | 负责 |
|---|---|---|
| 09:00 | 生成语音包 `gen_tts.py` | 自动 |
| 09:30 | 拿到 Arm URL → 填 http_arm.py | 等对方 |
| 10:30 | `api.py` 切换到 HttpArm → `/home` 测试 | 我 |
| 11:00 | `capture_frame` 接 Claude Vision | 需要 API key |
| 12:00 | Scene A 全链路：摄像头截帧 → Claude 识别 → Arm 动作 → TTS | 联调 |
| 14:00 | Tailscale 打通 EC2 → Mac | 需要 Tailscale IP |
| 15:00 | OpenClaw Skill 放入 EC2 → Discord /mj scene A | 你写 skill |
| 16:00 | 压测 10 次，记录成功率 | 调参 |
| 17:00 | Avatar 图放入 static/ | 你提供图 |
| 19:00 | Scene B + 点头摇头 | 时间允许 |

### Day 2（打磨 + 演示）

| 时间 | 任务 |
|---|---|
| 09:00 | 台词定稿（polite / meme 各 5 句）|
| 10:00 | OpenClaw 人格 prompt 精调 |
| 11:00 | Demo 流程排练 × 3 |
| 13:00 | 录制 Demo 视频 |
| 15:00 | Slide / Pitch 整理 |

---

## 风险与保底

| 风险 | 保底策略 |
|---|---|
| Arm HTTP 接口格式不对 | 先跑 mock arm，演示 UI + TTS + Vision 全链路 |
| Claude Vision 识别不稳 | 提示词里加"如果不确定请回答 unknown" + 重试 3 次 |
| Tailscale 连不上 | Web 控制面板作为触发入口（不需要 Discord）|
| 没有语音包 | `say -v Meijia` 自动降级，不影响演示 |
| Avatar 图没做好 | Emoji 大字符作为保底（已内置）|

---

## 文件结构速查

```
majong/
├── IMPLEMENTATION_PLAN.md      ← 本文件
├── docs/
│   ├── ARCHITECTURE.md
│   ├── REQUIREMENTS.md
│   └── INPUTS.md               ← 配置清单（Discord ID 等）
└── software/
    ├── .venv/                  ← Python 环境（已建好）
    ├── .env                    ← 放 ANTHROPIC_API_KEY, ARM_BASE_URL
    ├── requirements.txt
    ├── scripts/
    │   ├── dev_run.sh          ← 一键启动
    │   └── gen_tts.py          ← 生成语音包
    ├── orchestrator/
    │   ├── state_machine.py    ← 核心状态机
    │   └── contracts.py        ← 数据结构
    ├── adapters/
    │   ├── arm/
    │   │   ├── base.py         ← 接口定义
    │   │   ├── mock_arm.py     ← ✅ 可用
    │   │   └── http_arm.py     ← TODO：等 arm 团队 URL
    │   ├── vision/
    │   │   ├── base.py         ← 接口定义（含 identify）
    │   │   ├── mock_vision.py  ← ✅ 可用
    │   │   └── openclaw_vision.py ← TODO：Claude Vision 接入
    │   └── tts/
    │       ├── lines.py        ← 台词常量
    │       ├── player_local.py ← ✅ 可用
    │       └── assets/         ← 放 wav 文件
    ├── services/
    │   ├── api.py              ← ✅ 所有路由
    │   └── models.py           ← Pydantic 模型
    └── web/
        ├── app.py              ← Static file server
        ├── templates/
        │   └── index.html      ← ✅ 双模式 UI
        └── static/
            ├── style.css       ← ✅ 深色主题
            ├── main.js         ← ✅ 摄像头+语音+状态机
            ├── avatar_idle.gif    ← TODO：放角色图
            ├── avatar_pick.gif    ← TODO
            ├── avatar_nod.gif     ← TODO
            └── avatar_shake.gif   ← TODO
```
