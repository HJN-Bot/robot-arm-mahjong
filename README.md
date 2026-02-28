# 机械臂麻将（Robot Arm Mahjong）

一个 **OpenClaw × 机械臂 × 桌面麻将** 的可现场演示 Demo。

## 一句话
机械臂“看见桌面 → 抓牌 → 收回看牌动作 → 扔牌到中央 → 语音说「我要验牌」”，并在后续场景里做点头/摇头/挑衅话术的拟人交互。

## Demo 场景（v0）

### Scene 1（MVP）：抓牌 → 看牌 → 扔牌 → 语音「我要验牌」
- 摄像头识别当前桌面与目标牌位
- 机械臂抓取指定牌
- 手臂轻微回收（模拟“看牌”动作）
- 扔/放置到中央弃牌区
- TTS 输出：**“我要验牌。”**

### Scene 2：点头（牌没问题）
- 机械臂上下轻微摆动（点头）
- TTS：**“牌没有问题。”**
- 机械臂转向观众/玩家方向
- 末端执行器在桌面/空中点 1-2 次

### Scene 3：摇头 + 梗（嘲讽）
- 机械臂横向摆动（摇头）
- TTS：**“还得练啊”**（可替换为更安全/更通用的台词）

---

## System Architecture (Who controls what?)

### Participants
- **Discord**: input (commands)
- **OpenClaw Brain (EC2)**: *decision owner* (persona/prefs/scene routing)
- **Mac Local Hub (FastAPI + Orchestrator + Vision + Local Audio)**: *I/O owner* (camera, web UI, TTS/SFX)
- **Arm Team Service (HTTP, same Wi‑Fi)**: actuator primitives only (pick/present/throw/return/home/estop/status)

### Control Ownership (very important)
- **OpenClaw (EC2) ALWAYS owns decisions**: what scene to run, what to say, what to do next.
- **Mac Local Hub owns I/O**: camera access, web rendering, audio playback, local logging.
- **Arm service owns motion execution only**: no product logic.

### High-level Data Flow
1) User triggers from **Discord** (`/mj start`, `/mj scene A|B`) or from **Web Panel** (buttons)
2) **OpenClaw Brain (EC2)** calls **Mac Local Hub** via HTTP (Tailscale)
3) Mac Hub calls **Arm Team HTTP** → `pick` → `present_to_camera`
4) Mac Hub runs **Vision** (minimal class: `white_dragon` vs `one_dot`)
5) Brain returns a **Decision Packet** (`action` + `line_key` + `ui_text` + `sfx`)
6) Mac Hub executes throw/return + plays TTS/SFX + updates UI

> Full sequence diagram + API list: `software/docs/ARCH_FLOW.md`

---

## 2 日 Hackathon 计划（简版）
- Day 1：硬件打通 + 视觉识别最小闭环 + 机械臂动作库 v0 + Scene1 端到端通
- Day 2：加入 Scene2/3/4 + OpenClaw skill/Discord 体验 + 调参稳定性 + Demo 视频 + Presentation

更详细见：
- `docs/PROJECT_DRAFT.md`（两日工期 + 最大成功）
- `docs/ARCHITECTURE.md`（技术架构图 + 协议 + Brain“有灵魂”的落地方式）
- `docs/REQUIREMENTS.md`（需求 + 多层最小成功）
- `docs/SCENES_BRAINSTORM.md`（脑爆场景拓展）
- `docs/NETWORKING.md`（Tailscale：EC2 ↔ Mac）
- `docs/HARDWARE_CHECKLIST.md`（硬件/线材/桌面布置清单）
