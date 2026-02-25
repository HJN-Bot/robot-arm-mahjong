# Requirements｜机械臂麻将（Robot Arm Mahjong）

## 1) 功能需求（按优先级）

### P0（必须实现：Scene1 MVP）
- 摄像头识别桌面并输出目标位姿 `target_pose`
- 机械臂动作序列：抓牌 → 微微收回看牌姿态 → 放置/扔到中央区域
- TTS 输出："我要验牌"
- Discord（或按钮）触发 Scene1
- 安全：急停、限速、限位、工作区边界

### P1（建议实现：至少 2 个增强动作）
- 点 3 点（tap3）
- 点头（nod）
- 摇头（shake）
- 台词风格切换：礼貌版/梗版

### P2（可选：更“像智能体”）
- `/status` 输出指标（最近一次 scene、成功率、耗时、失败原因计数）
- 失败回 home + 二次尝试
- 视觉从“定位”升级到“识别牌面/区域分类”（不作为 MVP 硬依赖）

---

## 2) 非功能需求（Hackathon 成败关键）

- **稳定性**：连续 10 次演示成功率 ≥ 80%
- **安全**：任何情况下不越界、不撞人
- **可观测**：失败原因可定位（vision? arm? grasp? timeout?）
- **演示节奏**：Scene1 全程 ≤ 10 秒（建议 6-8 秒）
- **可降级**：抓取失败 → 允许 push/拨牌到中央；vision 不稳 → 手动点选取点

---

## 3) 多层“最小成功”定义（从 Demo 到产品化）

### Level A（Hackathon 必过：可演示闭环）
- Scene1：定位（可手点选）→ 动作库（固定轨迹）→ TTS

### Level B（可复现工程化）
- vision 自动输出 target_pose + 多次稳定执行
- orchestrator 有重试/超时/失败回 home

### Level C（Brain 具备“偏好与人格”）
- 台词库（礼貌/梗） + 动作节奏参数化
- OpenClaw 记住偏好：默认风格、安全等级

### Level D（受控的“自我改编程/自我验证”）
- OpenClaw 允许修改“参数”（速度、幅度、目标偏移）
- 执行前必须通过：guard（限速/限位）+ dry-run（空中走轨迹）+ 必要时 human-confirm

---

## 4) 待确认：SOMA 机械臂控制接口

我们需要从厂商确认至少一项：
- Python SDK？（推荐）
- ROS/ROS2？
- HTTP/WebSocket API？
- 串口/Modbus？

拿到接口后，在 `arm_adapter/` 内做一次性适配，让 orchestrator 不被 SDK 绑死。
