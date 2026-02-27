# 待决策清单（逐项展开用）｜机械臂麻将 Robot Arm Mahjong

> 用法：每一项都要落到 **一个明确选择** + **Owner** + **截止时间** + **验收口径**。

---

## A. 场景（Scenes）

### A1. 本次必须交付的核心场景（Scene1）
- [ ] Scene1 的“看牌”动作定义：
  - 方案A：固定观测位 + 停顿（不加新摄像头）
  - 方案B：加顶视摄像头（桌面定位）+ 手背相机（近看确认）
  - 方案C：结构件（定位槽/导轨/滑滑梯）辅助稳定牌姿态
- [ ] Scene1 的输入是“自动定位”还是“手动点选取点”作为保底？
- [ ] Scene1 的验收：10连成功率阈值（建议≥80%）与单次耗时（建议≤10s）

### A2. 2日内最大成功（Scene2/3/4）
- [ ] 选择至少 2 个增强动作：tap3 / nod / shake
- [ ] 台词风格：polite vs meme（梗版是否默认关闭）
- [ ] “陪伴感”节奏：停顿时长、语速、动作幅度（参数范围）

### A3. 桌游拓展（Brain 学习内容）
- [ ] cron 学什么：桌游梗 / 麻将技巧 / 玩法变体（每天1条？）
- [ ] 产物格式：卡片 schema（标题/规则一句话/2句台词/可绑定动作/注意事项）

---

## B. 接口定义（Interfaces）

### B1. OpenClaw ↔ Mac（Arm Host）网络方案
- [ ] Tailscale 组网（你已选 A）：Mac 与 EC2 同一 tailnet；谁来装/谁来验证 ping
- [ ] API 基线（必须实现）：
  - `POST /run_scene` {scene, style, safe}
  - `GET /status`
  - `POST /estop`

### B2. Vision ↔ Orchestrator
- [ ] `target_pose` 坐标系定义（table_frame）与标定方式（AprilTag vs 四角标定）
- [ ] 失败策略：vision 不稳允许手动点选（抓取必须成功）

### B3. TTS 触发协议
- [ ] TTS 在哪跑：建议 Mac 本地离线播放
- [ ] 触发方式：传 line_key（推荐）还是直接传文本

---

## C. 两日规划（2-day Plan）

### C1. Day1 必达成（只做一件大事）
- [ ] 抓取稳定：至少“抓起一张牌”重复 20 次（记录失败原因与参数）
- [ ] Scene1 端到端闭环（即使 vision 先手动点选）：抓→看→扔→TTS

### C2. Day2 输出打包
- [ ] Scene2/3/4（至少2个）+ `/style` `/safe` + `/status`
- [ ] Demo 视频（2分钟）+ PPT deck（6页）+ README 更新

---

## D. 分工定义（Owners）

> 目标：每个人都有“可验收交付物”，避免口头任务。

- [ ] 机械臂主机 Owner（Python + LeRobot + Orchestrator + 本地TTS）
- [ ] OpenClaw Owner（EC2 部署 + skill 编排 + Discord 指令）
- [ ] Vision Owner（标定 + target_pose 输出；可先点选）
- [ ] 包装 Owner（台词库 + 陪伴节奏参数 + 海报/架构图）
- [ ] PPT Deck Owner（演讲叙事：Body/Brain/陪伴意义/技术平权）
- [ ] Demo Video Owner（分镜/拍摄/剪辑/字幕）
- [ ] 3D 外壳 Owner（optional：不影响动作范围）

---

## E. 每人输出交付（Deliverables）

- [ ] 机械臂主机：
  - 可运行服务 + API 可用
  - Scene1 稳定抓取/动作序列
- [ ] OpenClaw：
  - 指令集 `/scene` `/status` `/style` `/safe` `/estop`
  - 与 Mac API 连通
- [ ] Vision：
  - 标定与 target_pose 输出（或点选工具）
- [ ] 包装：
  - 台词两套（polite/meme）+ 禁用词列表
  - 30秒/2分钟现场脚本
- [ ] PPT：
  - 6页 deck + 30秒 pitch
- [ ] 视频：
  - 2分钟成片（Scene1为主，增强场景点缀）

---

## F. 采购清单（已有机械臂；补齐周边）

### F1. 必备（强烈建议开工前到位）
- [ ] 麻将牌（建议≥40张）
- [ ] 桌面标定物（AprilTag 打印纸/贴纸）+ 胶带
- [ ] 桌面定位辅助（定位槽/夹具/防滑垫/胶带框）
- [ ] USB Hub（Mac）+ Type-C 线若干 + 插排/延长线
- [ ] 小音箱（可选但强烈建议，提升陪伴感）

### F2. 待决策（影响方案走向）
- [ ] 是否加顶视 USB 摄像头（建议加；若不加需强化定位槽方案）
- [ ] 俯拍支架/桌夹（若加顶视相机必买）
- [ ] 是否做 3D 外壳（可选）

---

## G. 需要补齐的信息（开工前）
- [ ] SOMA 官方：串口参数（baudrate）/关节ID/校准流程/示例代码（最好 LeRobot 适配说明）
- [ ] 现场桌面尺寸与弃牌区定义（矩形区域坐标）
- [ ] 目标牌“标准摆放姿态”（固定朝向/固定位置/固定光照）
