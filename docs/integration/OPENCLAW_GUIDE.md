# OpenClaw 调用指南

> 面向：OpenClaw EC2 团队
>
> OpenClaw 通过 Tailscale 访问 Mac Hub，是系统的**决策层**。
> Mac Hub 是**执行层**，负责摄像头、机械臂、TTS。

---

## 网络配置

```
Mac Hub 地址（Tailscale）: http://100.111.27.39:8000
Mac Tailscale hostname:   evamacbook-air
```

**连通性验证**：
```bash
curl http://100.111.27.39:8000/health
# 预期: { "api": "ok", "arm": "ok", "vision": "ok", ... }
```

---

## 标准对局流程

### Step 1：激活前端（Session 开始时调用一次）

```http
POST http://100.111.27.39:8000/activate
Content-Type: application/json

{}
```

**作用**：浏览器检测到后自动开启摄像头并启动 AutoLoop（Watch Mode）。
**何时调用**：每次新对局开始时。如果操作员已手动点击了「开始自动识别」，可跳过。

---

### Step 2：触发开牌

```http
POST http://100.111.27.39:8000/trigger?style=polite&safe=true
```

| 参数 | 可选值 | 说明 |
|------|--------|------|
| `style` | `polite` / `meme` | TTS 台词风格 |
| `safe` | `true` / `false` | 安全模式（true=慢稳，false=快速） |

**响应**：
```json
{ "ok": true }
```

**作用**：设置 `trigger_pending = true`，浏览器 Watch Mode 检测后自动执行：
```
机械臂抓牌 → 举牌展示 → 摄像头识别 × 4帧 → 自动执行 Scene A/B → TTS
```

**注意**：如果 `busy = true`，触发无效，需等待当前动作完成。

---

### Step 3：等待并轮询结果

触发后约 **4-8 秒**轮询结果：

```http
GET http://100.111.27.39:8000/status
```

**响应示例**：
```json
{
  "busy": false,
  "last_scene": "A",
  "recognized": {
    "label": "white_dragon",
    "confidence": 0.97
  },
  "recognition_ok": true,
  "trigger_pending": false,
  "logs": ["..."]
}
```

**判断逻辑**：
```python
if status["busy"] == False and status["recognized"]:
    label = status["recognized"]["label"]
    scene = status["last_scene"]   # "A" or "B"
    conf  = status["recognized"]["confidence"]
    # 发送 Discord 解说
```

---

### Step 4：发送 Discord 解说

根据识别结果和 `last_scene` 生成解说：

| `label` | `scene` | 解说示例（polite） |
|---------|---------|-----------------|
| `white_dragon` | `A` | "看到白板，扔了，字牌孤张价值低。" |
| `one_dot` | `B` | "一筒留着，序数牌有搭子潜力。" |

---

## 玩家 Override 指令

当玩家不认同自动决策时：

```http
# 强制扔出
POST http://100.111.27.39:8000/run_scene
{ "scene": "A", "style": "polite", "safe": true }

# 强制留下
POST http://100.111.27.39:8000/run_scene
{ "scene": "B", "style": "polite", "safe": true }
```

**注意**：先检查 `GET /status` 确认 `busy: false` 再调用。

---

## 其他控制指令

```http
# 紧急停止
POST http://100.111.27.39:8000/estop

# 回零位
POST http://100.111.27.39:8000/home

# 点头（表示OK）
POST http://100.111.27.39:8000/nod

# 摇头（表示拒绝）
POST http://100.111.27.39:8000/shake
```

---

## Discord 指令 → API 映射

| 用户说 | OpenClaw 调用 |
|--------|-------------|
| `/mj start` / "开始打麻将吧" | `POST /activate` → `POST /trigger` |
| `/mj scene A` / "扔了" | `POST /run_scene {"scene":"A"}` |
| `/mj scene B` / "留着" | `POST /run_scene {"scene":"B"}` |
| `/mj estop` / "急停" | `POST /estop` |
| `/mj stop` / "停止" / "回零" | `POST /home` |
| `/mj status` | `GET /status` |
| `/mj style meme` / "梗一点" | 本地更新 `style=meme`，下次调用携带 |

---

## 完整 Python 调用示例

```python
import httpx
import time

HUB = "http://100.111.27.39:8000"

def start_round(style="polite", safe=True):
    # 1. 激活前端
    httpx.post(f"{HUB}/activate")

    # 2. 触发开牌
    r = httpx.post(f"{HUB}/trigger", params={"style": style, "safe": safe})
    assert r.json()["ok"], "触发失败（可能 busy）"

    # 3. 等待结果（最多 15s）
    for _ in range(20):
        time.sleep(0.8)
        s = httpx.get(f"{HUB}/status").json()
        if not s["busy"] and s.get("recognized"):
            return s["recognized"], s["last_scene"]

    raise TimeoutError("识别超时")

# 使用示例
recognized, scene = start_round()
label = recognized["label"]   # "white_dragon" | "one_dot"
conf  = recognized["confidence"]
print(f"识别: {label} ({conf:.0%}) → Scene {scene}")
```

---

## 错误处理

| 情况 | 表现 | 处理 |
|------|------|------|
| `busy: true` 时触发 | `POST /trigger` 返回 `ok: false` | 等待 `busy: false` 后重试 |
| 识别失败 | `recognized: null` | 重新触发或提示玩家 |
| 网络不通 | 连接超时 | 检查 Tailscale 连接状态 |
| 机械臂故障 | `status.last_error` 有值 | 调用 `POST /estop` + `POST /home` |
