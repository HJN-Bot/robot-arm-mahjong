# 麻将臂 · 系统集成总览

> 本文档面向：OpenClaw 团队 / 机械臂硬件团队 / 前端调试
>
> 最后更新：2026-02-28

---

## 一、网络拓扑

```
Discord 用户
    │  Discord 消息 / 斜杠指令
    ▼
OpenClaw（EC2 云服务器）
    │  HTTP over Tailscale
    │  调用地址：http://100.111.27.39:8000
    ▼
Mac Hub（evamacbook-air · Tailscale IP: 100.111.27.39）
    │  uvicorn 监听 0.0.0.0:8000  ← dev_run.sh 启动
    ├─── 浏览器前端（localhost:8000，本地操作员界面）
    └─── 机械臂服务（ARM_HTTP_BASE_URL:9000，对接后生效）
```

**前提条件**：
- Mac 上 Tailscale 保持在线（`evamacbook-air` / `100.111.27.39`）
- Mac 上 `./software/scripts/dev_run.sh` 正在运行
- 浏览器已打开 `http://localhost:8000`

---

## 二、完整执行信号链

```
Discord 用户: "开始打麻将吧"
    │
    ▼
OpenClaw（EC2）
    ├─ 1. POST /activate              ← 远程激活前端摄像头 + AutoLoop
    ├─ 2. POST /trigger?style=polite  ← 触发一次完整开牌流程
    └─ 3. (等待 ~6s) GET /status      ← 轮询结果，获取识别结果

Mac Hub（100.111.27.39:8000）
    ├─ /activate → 设置 activate_pending = true
    ├─ /trigger  → 设置 trigger_pending = true
    └─ /status   → 返回 recognized / last_scene / busy

浏览器前端（getStatus 每 800ms 轮询）
    ├─ 检测到 activate_pending → 自动开摄像头 + 启动 AutoLoop
    └─ 检测到 trigger_pending  → 触发 autoLoopTick()

autoLoopTick() 内部流程：
    ├─ Step 1: POST /arm/start_scene  → 机械臂抓牌 + 举牌展示
    ├─ Step 2+3: 连续采帧 POST /capture_frame × 4 → 识别牌面
    └─ Step 4: POST /execute_scene    → 机械臂执行 Scene A/B

机械臂（:9000）
    ├─ /pick_tile         → 抓牌
    ├─ /present_to_camera → 举至摄像头
    ├─ /throw_to_discard  → 扔出（Scene A · 白板）
    └─ /return_tile       → 退回（Scene B · 一筒）

最终输出：
    ├─ 前端：播放 sceneA.mp4 / sceneB.mp4 + TTS 语音
    └─ OpenClaw → Discord：解说文字（"看到白板，扔了！"）
```

---

## 三、Mac Hub 端点速查

| 端点 | 方法 | 调用方 | 说明 |
|------|------|--------|------|
| `POST /activate` | `{}` | OpenClaw | 远程激活前端摄像头和 AutoLoop |
| `POST /trigger` | query: `style` `safe` | OpenClaw | 触发一次完整开牌流程 |
| `GET /status` | — | OpenClaw | 查询状态、识别结果、busy 标志 |
| `POST /run_scene` | `{scene, style, safe}` | OpenClaw | 手动指定场景执行（override） |
| `POST /arm/start_scene` | query: `style` `safe` | 前端 | Step1：TTS+抓牌+举牌 |
| `POST /capture_frame` | `{image: base64}` | 前端 | 识别摄像头帧 |
| `POST /execute_scene` | `{scene, recognized_label, ...}` | 前端 | Step4：执行场景动作 |
| `POST /estop` | `{}` | OpenClaw/前端 | 紧急停止 |
| `POST /home` | `{}` | OpenClaw/前端 | 回零位 |
| `GET /health` | — | 任何 | 全系统健康检查 |

---

## 四、子文档索引

| 文档 | 面向 | 内容 |
|------|------|------|
| [ARM_API_CONTRACT.md](ARM_API_CONTRACT.md) | 机械臂团队 | 需实现的 HTTP 接口合约 |
| [OPENCLAW_GUIDE.md](OPENCLAW_GUIDE.md) | OpenClaw 团队 | 调用顺序、示例代码、错误处理 |
