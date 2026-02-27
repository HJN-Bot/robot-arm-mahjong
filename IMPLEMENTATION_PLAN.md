# Implementation Plan｜机械臂麻将 × OpenClaw

> 更新：2026-02-27 晚

---

## 系统架构总览

```
Discord 指令
    ↓
OpenClaw Brain（EC2）— skill.ts / prompt
    ↓ HTTP
FastAPI 后端（Mac 本地，port 8000）
    ├── Orchestrator 状态机
    ├── Arm Adapter（SOMA SO-ARM100 via LeRobot / HTTP）
    ├── Vision Adapter（USB 摄像头 → 牌识别）
    └── TTS Player（afplay wav → macOS say 降级）
    ↓
Web 控制面板（localhost:8000）
    ├── 人物 Avatar（动画状态 + 对话气泡）
    └── Skill Navigator Dashboard（历史记录 + 参数）
```

---

## 已完成 ✅

### 后端骨架（可用 mock 跑全流程）

| 文件 | 说明 |
|---|---|
| `software/orchestrator/state_machine.py` | Scene A/B 状态机：pick→present→recognize→TTS→throw/return |
| `software/orchestrator/contracts.py` | RunRequest / RunResult / RecognizeResult dataclass |
| `software/services/api.py` | FastAPI：`/run_scene` `/status` `/estop` `/stop` `/home` `/tap` `/nod` `/shake` |
| `software/services/status_store.py` | 内存状态 + 日志（最多 200 条） |
| `software/adapters/arm/mock_arm.py` | Mock 机械臂（sleep 模拟，含 tap/nod/shake）|
| `software/adapters/vision/mock_vision.py` | Mock 视觉（随机返回 white_dragon / one_dot）|
| `software/adapters/arm/base.py` | Arm 接口定义（pick/present/throw/return/home/estop/tap/nod/shake）|

### TTS 系统

| 文件 | 说明 |
|---|---|
| `software/adapters/tts/lines.py` | 台词常量 + 文字内容（polite/meme 两套）+ wav 文件名映射 |
| `software/adapters/tts/player_local.py` | 播放逻辑：有 wav → afplay；无 wav → macOS say -v Meijia |
| `software/adapters/tts/assets/polite/` | **放预录 wav 文件的目录**（look_done / i_want_check / ok_no_problem）|
| `software/adapters/tts/assets/meme/` | 梗版 wav 目录 |
| `software/scripts/gen_tts.py` | 一键用 edge-tts 生成全套语音包（XiaoxiaoNeural / YunxiNeural）|

### Web 控制面板（深色 Dashboard）

| 区域 | 内容 |
|---|---|
| 左侧 Avatar 面板 | 圆形人物头像（放 `static/avatar.png` 即换图）+ 状态动画（待机/思考/执行/完成/报错）+ 对话气泡 + 识别牌结果 + 三项统计（总局/成功率/均耗时）|
| 右侧 Skill Navigator | Scene A、Scene B、点三点、点头、摇头、回零位 六个技能卡 |
| 参数栏 | 台词风格（polite/meme）、安全模式（on/off）、ESTOP |
| 对局记录 | 最近 30 局表格：场景/结果/识别牌/耗时/风格 |
| 日志 | 实时滚动，800ms 轮询 |

### 环境

- Python venv：`software/.venv`
- 依赖：fastapi / uvicorn / pydantic / edge-tts（全部已装）
- 启动：`bash software/scripts/dev_run.sh` → `http://localhost:8000`

---

## 明天待做 📋

### 优先级 P0（必须完成）

#### 1. 放入 / 生成语音包
```bash
# 方案 A：把你的预录 wav 放进去
# 命名规则：
#   software/adapters/tts/assets/polite/look_done.wav       "好，我看好了。"
#   software/adapters/tts/assets/polite/i_want_check.wav    "我要验牌。"
#   software/adapters/tts/assets/polite/ok_no_problem.wav   "牌没有问题。"
#   software/adapters/tts/assets/meme/（同上，梗版台词）

# 方案 B：自动生成（需联网）
cd /Users/eva/Desktop/majong
software/.venv/bin/python -m software.scripts.gen_tts
```

#### 2. 把 OpenClaw 脚本放进来
- 新建 `openclaw/` 目录，放入你的 EC2 上的 skill 脚本
- 我看完后：写 Discord slash command handler + system prompt + Brain 人格 prompt

#### 3. 确认 arm 团队 HTTP 接口
- 拿到他们的 base URL + endpoints
- 我填充 `software/adapters/arm/http_arm.py`

---

### 优先级 P1（当天完成）

#### 4. 真实 Arm Adapter（两条路，选其一）

**路径 A：HTTP Adapter（对接另一个团队的服务）**
```
software/adapters/arm/http_arm.py
# 填充 base_url + 各动作的 POST 请求
```

**路径 B：LeRobot Adapter（直接控 SOMA SO-ARM100）**
```
software/adapters/arm/lerobot_arm.py
# pip install lerobot
# 配置串口、关节 ID、动作原语
```

#### 5. 视觉识别
```
software/adapters/vision/classifier_min2.py
# 选其一实现：
# A. USB 摄像头截图 + AprilTag / 颜色/形状模板匹配（最快）
# B. 手动点击画面取点（保底降级）
```

#### 6. 在 FastAPI 中切换到真实 Adapter
```python
# software/services/api.py 顶部
# 把 MockArm → HttpArm 或 LeRobotArm
# 把 MockVision → 真实 Vision
```

---

### 优先级 P2（有时间做）

#### 7. OpenClaw Discord Skill
```
openclaw/
  skill.ts          Discord slash command: /scene /status /style /estop /home
  client.ts         HTTP client → Mac FastAPI (通过 Tailscale IP)
  prompts/
    system.md       Brain 人格（捣蛋/思考/语气）
    scene_router.md 场景路由逻辑
```

#### 8. 语音输入（ASR）接口预留
```
POST /voice_trigger  { "text": "验牌" }
→ Orchestrator 关键词匹配 → 路由 scene
```
> 具体触发方式（麦克风 / 蓝牙 / 手机端）等场景确认后接入。

#### 9. Avatar 人物图
- 把捏的角色图放进 `software/web/static/avatar.png`（自动显示）
- 进阶：多状态图（idle/thinking/acting）分开，前端按状态切换

---

## Day 1 / Day 2 时间表

### Day 1（让它跑起来）

| 时段 | 任务 |
|---|---|
| 09:30 – 10:00 | 放语音包 + 测试 TTS 出声 |
| 10:00 – 11:00 | 确认 arm HTTP 接口 → 填 http_arm.py |
| 11:00 – 12:30 | 接真实机械臂：home / estop / pick / place |
| 13:30 – 15:00 | 摄像头标定 + vision 输出 target_pose |
| 15:00 – 17:00 | Scene A 端到端跑通（vision → arm → TTS）|
| 19:30 – 21:30 | 连续 10 次压测 + 调参 + 失败回 home |

**Day 1 交付物**
- Scene A 可演示（即使 vision 手动取点）
- /status 能返回成功率 / 失败原因
- TTS 能出声

### Day 2（让它好看 + 能讲）

| 时段 | 任务 |
|---|---|
| 09:30 – 10:00 | 台词定稿（polite / meme 两套）|
| 10:00 – 12:00 | Scene B + 点三点 + 点头 + 摇头 加入真实 arm |
| 13:30 – 14:30 | OpenClaw Discord skill 联调 |
| 14:30 – 16:00 | Avatar 人物图 + 动画优化 |
| 16:00 – 17:00 | Demo 视频录制 |
| 17:00 – 18:00 | Presentation slide |

**Day 2 最小交付（必过）**
- Scene A 稳定 ≥ 80%（10 次）
- TTS 出声 + 台词两套可切

**Day 2 最大交付**
- Scene A + B + 至少 2 个增强动作
- OpenClaw Discord 可触发
- Demo 视频 + Slide + Avatar 界面

---

## 风险与保底

| 风险 | 保底策略 |
|---|---|
| 抓取不稳 | 先固定位置 + 固定牌姿态，反复调夹爪摩擦 |
| 视觉不稳 | 降级为手动点击画面取点（但抓取必须成功）|
| arm SDK 不兼容 | 先手动录制关节角度序列作为固定轨迹 |
| TTS 无语音包 | macOS say 自动降级，不影响演示 |
| OpenClaw 接入不了 | Web 控制面板作为保底触发入口 |

---

## 文件结构速查

```
majong/
├── IMPLEMENTATION_PLAN.md     ← 本文件
├── docs/                      ← 项目文档（架构/需求/硬件）
└── software/
    ├── .venv/                 ← Python 环境（已建好）
    ├── requirements.txt       ← fastapi + uvicorn + pydantic + edge-tts
    ├── scripts/
    │   ├── dev_run.sh         ← 一键启动服务
    │   └── gen_tts.py         ← 生成语音包
    ├── orchestrator/
    │   ├── state_machine.py   ← 核心状态机
    │   └── contracts.py       ← 数据结构
    ├── adapters/
    │   ├── arm/
    │   │   ├── base.py        ← 接口定义
    │   │   ├── mock_arm.py    ← Mock（可用）
    │   │   └── http_arm.py    ← TODO：等 arm 团队接口
    │   ├── vision/
    │   │   ├── mock_vision.py ← Mock（可用）
    │   │   └── classifier_min2.py ← TODO：真实识别
    │   └── tts/
    │       ├── lines.py       ← 台词常量 + 文字
    │       ├── player_local.py← 播放器（afplay/say）
    │       └── assets/        ← 放语音包 wav 文件
    ├── services/
    │   └── api.py             ← FastAPI 路由
    └── web/
        ├── templates/index.html  ← Dashboard UI
        └── static/
            ├── style.css      ← 深色主题样式
            ├── main.js        ← 状态机 + 对局历史
            └── avatar.png     ← 放人物图片（可选）
```
