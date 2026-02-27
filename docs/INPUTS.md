# Inputs / 配置清单（开工前必须填）｜Robot Arm Mahjong

> 目的：把“需要的输入”一次性列清楚，避免现场靠口头对接。

---

## 1) Discord / OpenClaw（Brain）

### 1.1 新建频道（建议）
- `#mahjong-brain`（或你命名的频道）

### 1.2 需要填写的值
- Discord **Guild ID**：`__________`
- Discord **Channel ID**（mahjong-brain）：`__________`
- 是否 requireMention：`true/false`（建议 Hackathon 期间 false）

### 1.3 OpenClaw 绑定策略（二选一）
- 方案 A：复用现有 agent（andrew/rex 等）+ 新 channel binding
- 方案 B：新建 agentId：`mahjong`（推荐，隔离记忆与提示词）

### 1.4 Skill 指令协议（Brain 侧）
- `/mj scene A|B`
- `/mj style polite|meme`
- `/mj safe on|off`
- `/mj status`
- `/mj stop`
- `/mj estop`

> Skill 只做编排与调用本地 orchestrator：**不要直接耦合机械臂控制细节**。

---

## 2) 联网（EC2 ↔ Mac 本地 orchestrator）

> 你已选：Tailscale

需要填写：
- EC2 Tailscale IP：`100.___.___.___`
- Mac Tailscale IP：`100.___.___.___`
- 本地 orchestrator 端口：默认 `8000`

最终基地址（OpenClaw 调用）：
- `ORCH_BASE_URL = http://<mac-tailscale-ip>:8000`

必测：
- EC2 上 `curl http://<mac-tailscale-ip>:8000/status` 返回 200

---

## 3) 机械臂团队接口（Arm Adapter）

### 3.1 接口形态（必须确认）
- [ ] HTTP
- [ ] ROS/ROS2
- [ ] 其他：__________

### 3.2 若是 HTTP（推荐），至少提供这些 endpoint（建议）
- `POST /pick_tile`
- `POST /present_to_camera`
- `POST /throw_to_discard`
- `POST /return_tile`
- `POST /home`
- `POST /estop`
- `GET  /status`

需要填写：
- `ARM_HTTP_BASE_URL = http://<arm-host>:<port>`

> 如果对方不是 HTTP：请他们在同 WiFi 内包一层 HTTP 给你们（最省对接成本）。

---

## 4) Vision（电脑前摄像头最小识别）

目标：明天只做最小分类（甚至只认两张牌）
- A（扔出去）= 白板（white_dragon）
- B（拿回来）= 一饼（one_dot）

需要填写：
- 摄像头来源：
  - [ ] 电脑自带摄像头
  - [ ] 外接 USB 摄像头
- Mac 摄像头 index：`CAMERA_INDEX=0/1/...`
- 识别策略：
  - [ ] 单帧
  - [ ] 多帧取最大置信度（建议 5-10 帧）

输出契约（orchestrator 需要）：
- `label`：`white_dragon | one_dot`
- `confidence`：0-1

---

## 5) TTS（离线语音包）

你已决定：**本地离线**。

需要填写：
- 语音素材格式：wav / mp3：`_____`
- 语音素材路径（或生成脚本输出路径）：`software/adapters/tts/assets/...`
- 台词风格：`polite` / `meme`

最小 line_key（必须有 2 句就够演示）：
- `LOOK_DONE`（看牌结束/我看完了）
- `I_WANT_CHECK`（我要验牌）

可选加分：
- `OK_NO_PROBLEM`（牌没问题）

---

## 6) Web 面板（本地 UI）

需要填写：
- Web 面板访问地址：`http://localhost:8000/`
- UI 是否暴露 style/safe 开关：`yes/no`（建议 yes）

---

## 7) 桌面布置（抓取成功率的核心输入）

必须明确：
- 牌的“标准摆放姿态”：位置、朝向、间距
- 相机与牌的相对位置：固定距离、固定角度
- 光照：避免强反光

> 本项目不接受“抓取失败就推/拨”保底：抓取必须稳定。
