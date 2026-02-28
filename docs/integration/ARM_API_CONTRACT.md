# 机械臂 HTTP API 合约

> 面向：机械臂硬件团队
>
> Mac Hub 通过 `HttpArm` 适配器调用机械臂服务。
> 机械臂团队需在指定地址启动 HTTP 服务，实现以下接口。

**交付约定**：硬件同学按本文的**请求/响应格式**实现并部署服务后，请把**服务地址（IP:端口）**提供给 Mac 端（例如 `192.168.x.x:9000`），用于在 `software/.env` 中配置 `ARM_HTTP_BASE_URL`。默认端口建议为 `9000`，若使用其他端口一并告知即可。

---

## 基本约定

- **协议**：HTTP/1.1
- **Content-Type**：`application/json`
- **默认端口**：`9000`（可在 Mac 的 `.env` 中通过 `ARM_HTTP_BASE_URL` 修改）
- **超时**：所有请求 Mac 端设置 30s 超时

### 统一响应格式

```json
// 成功
{ "ok": true }

// 失败
{ "ok": false, "error": "错误描述" }
```

---

## 接口列表

### POST /pick_tile
抓取牌堆顶部一张牌。

**请求体**
```json
{ "safe": true }
```
- `safe`：`true` = 安全模式（较慢但稳定），`false` = 快速模式

**响应**
```json
{ "ok": true }
```

**预期耗时**：~0.5s

---

### POST /present_to_camera
将当前持有的牌举至摄像头前，等待视觉识别。

**请求体**
```json
{ "safe": true }
```

**响应**
```json
{ "ok": true }
```

**预期耗时**：~1.0s
> 此接口返回后，Mac 端会立即开始采帧识别，臂需保持静止约 1-2s。

---

### POST /throw_to_discard
将牌扔入弃牌区（Scene A · 白板决策）。

**请求体**
```json
{ "safe": true }
```

**响应**
```json
{ "ok": true }
```

**预期耗时**：~2.0s

---

### POST /return_tile
将牌退回原位（Scene B · 一筒决策）。

**请求体**
```json
{ "safe": true }
```

**响应**
```json
{ "ok": true }
```

**预期耗时**：~2.0s

---

### POST /home
回归零位/初始位置。

**请求体**
```json
{}
```

**响应**
```json
{ "ok": true }
```

---

### POST /estop
紧急停止，立即停止所有运动。

**请求体**
```json
{}
```

**响应**
```json
{ "ok": true }
```

> **优先级最高**，任何状态下必须立即响应。

---

### POST /tap
末端执行器点击动作（表示"我要验牌"）。

**请求体**
```json
{ "times": 3 }
```

**响应**
```json
{ "ok": true }
```

---

### POST /nod
点头动作（表示同意/OK）。

**请求体**
```json
{}
```

**响应**
```json
{ "ok": true }
```

---

### POST /shake
摇头动作（表示不同意/拒绝）。

**请求体**
```json
{}
```

**响应**
```json
{ "ok": true }
```

---

### GET /status
查询机械臂当前状态。

**响应**
```json
{
  "ready": true,
  "position": "home",
  "error": null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ready` | bool | 是否就绪（可接受新指令） |
| `position` | string | 当前位置描述（`home` / `picking` / `presenting` 等） |
| `error` | string\|null | 错误信息，无错误则为 `null` |

---

## Mac 端配置

机械臂服务地址通过环境变量配置，在 `software/.env` 文件中设置：

```env
ARM_ADAPTER=http
ARM_HTTP_BASE_URL=http://<机械臂IP>:9000
```

**验证联通性**：
```bash
curl http://<机械臂IP>:9000/status
# 预期: {"ready": true, "position": "home", "error": null}
```

也可通过 Mac Hub 的健康检查端点验证：
```bash
curl http://100.111.27.39:8000/health
# 返回中会包含 arm 的连通状态
```

---

## 调用顺序（完整一局）

```
Scene A（白板 → 扔出）:
  POST /pick_tile        → 抓牌
  POST /present_to_camera → 举至摄像头（Mac 识别）
  POST /throw_to_discard  → 扔出

Scene B（一筒 → 退回）:
  POST /pick_tile
  POST /present_to_camera
  POST /return_tile       → 退回

结束后:
  POST /home              → 回零位（可选）
```

---

## 错误处理建议

- 所有动作失败时返回 `{ "ok": false, "error": "描述" }`
- Mac 端收到 `ok: false` 会立即中断流程并上报错误
- 网络超时（30s）Mac 端会自动标记为失败
- 建议：每个动作执行前检查 `GET /status` 中 `ready: true`
