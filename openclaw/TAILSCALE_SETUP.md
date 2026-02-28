# Tailscale 配置指南

> 目标：让 EC2 上的 OpenClaw 能通过 Tailscale 访问 Mac 的 FastAPI（:8000）

---

## 1. Mac 端（本地 Hub）

### 安装 Tailscale

```bash
brew install tailscale
```

或者直接下载：https://tailscale.com/download/mac

### 启动并登录

```bash
# 启动
sudo tailscaled

# 在新终端登录（会弹出浏览器）
tailscale up

# 查看自己的 Tailscale IP（记下来，给 EC2 用）
tailscale ip -4
# 例如：100.64.x.x
```

### 验证服务可达

```bash
# 先启动 FastAPI（另一个终端）
cd /Users/eva/Desktop/majong/software
bash scripts/dev_run.sh

# 验证本地能访问
curl http://localhost:8000/status
# → {"busy": false, "logs": [...]}
```

---

## 2. EC2 端（OpenClaw Brain）

> 如果 EC2 已经装了 Tailscale 就跳过安装

### 安装（Amazon Linux 2 / Ubuntu）

```bash
# Ubuntu
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# 查看 EC2 的 Tailscale IP
tailscale ip -4
```

### 测试连通性

```bash
# 把 100.64.x.x 替换成上面 Mac 的 Tailscale IP
curl http://100.64.x.x:8000/status

# 期望结果：
# {"busy":false,"last_scene":null,"last_error":null,"recognized":null,"logs":[]}
```

---

## 3. 配置 OpenClaw Skill

在 EC2 的 skill 脚本 / 环境变量里设置：

```bash
# 在 EC2 上
export MAC_HUB_URL=http://100.64.x.x:8000

# 验证所有关键端点
curl -X POST $MAC_HUB_URL/home
curl $MAC_HUB_URL/status
curl -X POST $MAC_HUB_URL/tap
```

---

## 4. 防火墙检查

Mac 上需要确保防火墙允许来自 Tailscale 接口的流量：

```bash
# 检查 Mac 防火墙状态
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# 如果是 enabled，临时允许 Python（运行 uvicorn 的进程）：
# 系统偏好设置 → 安全性与隐私 → 防火墙 → 防火墙选项
# 把 Python 加入允许列表
# 或者直接关掉防火墙（hackathon 期间）
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off
```

---

## 5. 网络验证清单

在开始接入之前，逐项确认：

```
[ ] Mac 的 Tailscale 已登录（tailscale status 显示 connected）
[ ] EC2 的 Tailscale 已登录
[ ] 两台机器在同一个 Tailscale 账号下（或同一 tailnet）
[ ] Mac FastAPI 用 --host 0.0.0.0 启动（dev_run.sh 已修复）
[ ] EC2 能 curl http://<mac-ts-ip>:8000/status 返回 200
[ ] MAC_HUB_URL 环境变量已配置到 EC2 的 OpenClaw skill
```

---

## 6. 调试技巧

```bash
# 在 Mac 上监控请求（确认 EC2 在调用）
cd /Users/eva/Desktop/majong/software
bash scripts/dev_run.sh
# uvicorn 会打印每一条请求日志

# 如果 curl 超时，检查 Tailscale 连通性：
ping <mac-ts-ip>      # 在 EC2 上执行

# 如果 ping 通但 curl 不通，是防火墙问题：
# → 检查 Mac 防火墙设置
```

---

## 关键参数（已确认）

| 参数 | 值 |
|---|---|
| FastAPI 端口 | 8000 |
| uvicorn 绑定 | 0.0.0.0（已设置）|
| **Mac Tailscale IP** | **100.111.27.39** ✅ |
| **MAC_HUB_URL** | **http://100.111.27.39:8000** ✅ |
| Guild ID | 1467170598529794317 |
| Channel ID | 1476944737931100221 |
| Agent ID | mahjong |

> **连通性已验证** — `curl http://100.111.27.39:8000/status` 返回 200 ✅
