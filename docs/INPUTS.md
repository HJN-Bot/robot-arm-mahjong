# Inputs / 配置清单（开工前必须填）｜Robot Arm Mahjong

> 目的：把“需要的输入”一次性列清楚，避免现场靠口头对接。

---

## 1) Discord / OpenClaw（Brain）

### 1.1 新建频道（建议）
- `#mahjong-brain`（或你命名的频道）

### 1.2 需要填写的值
- Discord **Guild ID**：`1467170598529794317` ✅
- Discord **Channel ID**（mahjong-brain）：`1476944737931100221` ✅
- 是否 requireMention：`false`（Hackathon 期间直接响应）

### 1.3 OpenClaw 绑定策略 ✅ 已确认
- ~~方案 A：复用现有 agent~~
- **方案 B：新建 agentId `mahjong`**（隔离记忆与提示词，已选定）

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

### 3.1 接口形态 ✅ 已确认
- [x] **HTTP**（明天拿 URL）

### 3.2 若是 HTTP（推荐），至少提供这些 endpoint（建议）
- `POST /pick_tile`
- `POST /present_to_camera`
- `POST /throw_to_discard`
- `POST /return_tile`
- `POST /home`
- `POST /estop`
- `GET  /status`

需要填写：
- `ARM_HTTP_BASE_URL = http://<arm-host>:<port>`（明天确认）

> 如果对方不是 HTTP：请他们在同 WiFi 内包一层 HTTP 给你们（最省对接成本）。

---

## 4) Vision（两阶段：Marker 定位 + 正面花色识别）✅ 方案已确认

### 4.1 两阶段说明
```
阶段 1 — 抓取定位（marker 在牌背面）
  牌面朝下放桌上 → 背面朝上 → marker 朝摄像头
  OpenCV ArUco 检测 → 输出 target_pose (x, y, theta)
  → 机械臂知道去哪里抓

阶段 2 — 花色识别（正面朝摄像头）
  机械臂抓起后 present_to_camera
  牌正面（花色/图案）朝摄像头
  图像识别 → 输出 label（white_dragon / one_dot / ...）
```

### 4.2 摄像头 ✅ 已确认
- [x] **电脑自带摄像头**（Mac 内置）
- `CAMERA_INDEX = 0`

### 4.3 阶段 1：Marker 定位（背面）
- 推荐：**ArUco marker**（OpenCV 原生，无额外依赖）
  - 打印后贴在牌背面
  - marker 只需要传递位置，不需要区分牌种（ID 可以全部用同一个）
- 输出：`target_pose = (x, y, theta)`

待确认：
- [ ] marker 类型：ArUco / AprilTag / 二维码？（建议 ArUco）
- [ ] 是否明天打印并贴好？

### 4.4 阶段 2：正面花色识别
- 输入：机械臂举牌后拍一帧正面图像
- 识别方案（按稳定性排序，Hackathon 选其一）：
  - **方案 A（最快）**：调用 Claude Vision API / GPT-4V，发图直接问"这是什么麻将牌"
  - **方案 B（本地）**：OpenCV 颜色/形状模板匹配（白板=空白多，一饼=一个圆）
  - **方案 C（备选）**：简单 CNN，需要提前准备训练数据
- 待确认：选哪个方案？（建议先试方案 A，速度快且准）

### 4.5 输出契约（orchestrator 需要，不变）
- `label`：`white_dragon | one_dot`
- `confidence`：0-1

### 4.6 防抖策略
- 连续 3 帧一致才输出最终结果
- 单帧超时 2s → confidence=0，orchestrator 记录失败

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

✅ 已确认：
- 牌面贴 marker，摆放位置相对灵活（marker 提供位置信息）
- 摄像头：Mac 内置摄像头固定俯拍/侧拍桌面

仍需现场确认：
- 相机安装高度与角度（marker 检测需保证 marker 正面朝摄像头）
- 光照：避免 marker 表面反光（哑光打印 / 遮光）

> 本项目不接受”抓取失败就推/拨”保底：抓取必须稳定。
