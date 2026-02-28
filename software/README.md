# software (local)

本目录是 **机械臂麻将**的软件端主工程：
- 本地（Mac）跑：Orchestrator + Web 面板 + Vision 最小分类 + 离线 TTS + Arm Adapter（可插拔）
- OpenClaw（EC2）跑：Discord Skill（触发 scene + 个性化/人设/偏好）

## 今日目标（Hackathon Day 0/1）
1) 先用 MockArm + MockVision 把端到端流程跑通（UI/状态机/语音）
2) 再替换 Vision 为 webcam + 二分类（白板 vs 一饼）
3) 最后对接机械臂团队接口（HTTP/ROS 任选其一，优先 HTTP）

## API（本地服务）
- `POST /run_scene`  { "scene": "A"|"B", "style": "polite"|"meme", "safe": true|false }
- `GET  /status`
- `POST /stop`
- `POST /estop`

## Scenes
- Scene A：抓牌 → 送到电脑前摄像头 → 识别 → TTS → 扔出去
- Scene B：抓牌 → 送到电脑前摄像头 → 识别 → TTS → 拿回来/放回

## 识别状态与准确度
- **「识别成功」与后端一致**：仅当置信度 ≥ 0.65 时 UI 显示「识别成功」✅，否则显示「置信度不足」；`/status`、`/capture_frame`、`/run_scene`、`/execute_scene` 均返回 `recognition_ok` 供前端同步。
- **无结果时清空**：新一轮开牌（如 `/arm/start_scene`）后若尚未识别，会清空上次的识别展示，避免一直显示旧的成功。
- **牌面与画面不一致时**：当前为 HistogramVision（白板/一筒二分类）。需用 **同一摄像头、相近角度与光线** 对 `white_dragon` / `one_dot` 做标定（`POST /calibrate?label=...`），并把牌放在画面**居中**区域；未标定或光线差异大会用 Mock 或置信度偏低，UI 会显示「置信度不足」而非「识别成功」。

## Dev Quickstart（占位）
> 明天补齐依赖与启动脚本。

