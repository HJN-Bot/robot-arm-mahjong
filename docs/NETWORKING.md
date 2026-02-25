# Networking｜EC2(OpenClaw) ↔ Mac(Arm Host)

> 结论：同一 WiFi + 翻墙/VPN 状态下，**不要依赖公网直接互打端口**。
> 推荐用 **Tailscale** 建立稳定内网。

## 方案 A（推荐）：Tailscale

### 1) 在 Mac（机械臂主机）
1. 安装 Tailscale（GUI 即可）并登录同一账号
2. 打开后获得一个 Tailscale IP（形如 `100.x.y.z`）
3. 运行你的 arm orchestrator：监听 `0.0.0.0:8000`

### 2) 在 EC2（OpenClaw 主机）
1. 安装并登录同一 Tailscale 账号
2. 确认 EC2 能 ping 通 Mac 的 Tailscale IP
3. 在 OpenClaw skill 配置：
   - `ARM_ORCH_URL=http://<mac-tailscale-ip>:8000`

### 3) 最小 API（建议）
- `POST /run_scene` `{scene, style, safe}`
- `GET /status`
- `POST /estop`

## 测试
在 EC2 上：
- `curl http://<mac-tailscale-ip>:8000/status`

---

## 注意事项
- 如果你们现场网络很差：Mac 可以开热点，EC2 通过其它方式上网；但 Tailscale 仍然能在“有网”的情况下建立连接。
- 语音（TTS）建议在 Mac 本地执行，减少网络依赖。
