# 机械臂分步调用手册

> 机械臂团队跑在 `localhost:9000`，Mac Hub 通过 HttpArm 适配器调用。
> 本文件是逐步调用的 curl 验证命令和完整两条路径。

---

## 环境配置（software/.env）

```env
ARM_ADAPTER=http
ARM_HTTP_BASE_URL=http://127.0.0.1:9000
```

重启 dev_run.sh 后生效。

---

## 连通性验证

```bash
# 1. 确认机械臂服务在线
curl http://localhost:9000/status
# 预期: {"ok": true, "state": "idle"}

# 2. 确认 Mac Hub 已切换到 HttpArm
curl http://localhost:8000/health
# 预期: { "arm": "ok", ... }
```

---

## 完整执行路径：Scene A（白板 → 扔出）

按顺序执行，每步等待上一步返回 `{"ok": true}` 后再执行下一步：

```bash
# Step 1：抓牌
curl -X POST http://localhost:9000/pick_tile \
  -H "Content-Type: application/json" \
  -d '{"safe": true}'
# 预期: {"ok": true}   耗时 ~0.5s

# Step 2：举至摄像头前（展示给视觉识别）
curl -X POST http://localhost:9000/present_to_camera \
  -H "Content-Type: application/json" \
  -d '{"safe": true}'
# 预期: {"ok": true}   耗时 ~1.0s
# → 此时 Mac 前端会连拍 4 帧做识别

# Step 3A：扔出（Scene A · 白板决策）
curl -X POST http://localhost:9000/throw_to_discard \
  -H "Content-Type: application/json" \
  -d '{"safe": true}'
# 预期: {"ok": true}   耗时 ~2.0s
```

---

## 完整执行路径：Scene B（一筒 → 退回）

```bash
# Step 1：抓牌
curl -X POST http://localhost:9000/pick_tile \
  -H "Content-Type: application/json" \
  -d '{"safe": true}'

# Step 2：举至摄像头前
curl -X POST http://localhost:9000/present_to_camera \
  -H "Content-Type: application/json" \
  -d '{"safe": true}'

# Step 3B：退回（Scene B · 一筒决策）
curl -X POST http://localhost:9000/return_tile \
  -H "Content-Type: application/json" \
  -d '{"safe": true}'
# 预期: {"ok": true}   耗时 ~2.0s
```

---

## 收尾 / 工具指令

```bash
# 回零位（每局结束后）
curl -X POST http://localhost:9000/home \
  -H "Content-Type: application/json" \
  -d '{}'

# 紧急停止（任何时候）
curl -X POST http://localhost:9000/estop \
  -H "Content-Type: application/json" \
  -d '{}'

# 点头（表示 OK）
curl -X POST http://localhost:9000/nod \
  -H "Content-Type: application/json" \
  -d '{}'

# 摇头（表示拒绝）
curl -X POST http://localhost:9000/shake \
  -H "Content-Type: application/json" \
  -d '{}'

# 点三点（表示"我要验牌"）
curl -X POST http://localhost:9000/tap \
  -H "Content-Type: application/json" \
  -d '{"times": 3}'
```

---

## 通过 Mac Hub 触发完整流程（推荐验证方式）

不需要直接打 :9000，让 Mac Hub 驱动整个流程：

```bash
# 触发一次完整开牌（arm/start_scene + capture_frame × 4 + execute_scene 全自动）
curl -X POST "http://localhost:8000/trigger?style=polite&safe=true"
# 预期: {"ok": true, "queued": true}

# 等 ~6s 后查结果
curl http://localhost:8000/status | python3 -m json.tool
# 看 recognized.label 和 last_scene
```

---

## 快速一键冒烟测试（bash 脚本）

```bash
#!/bin/bash
BASE="http://localhost:9000"

echo "=== 机械臂冒烟测试 ==="

echo "1. status..."
curl -s $BASE/status && echo

echo "2. pick_tile..."
curl -s -X POST $BASE/pick_tile -H "Content-Type: application/json" -d '{"safe":true}' && echo

echo "3. present_to_camera..."
curl -s -X POST $BASE/present_to_camera -H "Content-Type: application/json" -d '{"safe":true}' && echo

echo "4. throw_to_discard (Scene A)..."
curl -s -X POST $BASE/throw_to_discard -H "Content-Type: application/json" -d '{"safe":true}' && echo

echo "5. home..."
curl -s -X POST $BASE/home -H "Content-Type: application/json" -d '{}' && echo

echo "=== 全部通过 ==="
```

保存为 `software/scripts/test_arm.sh`，运行：
```bash
bash software/scripts/test_arm.sh
```
