---
name: rlyoulink
description: 使用本项目便携版 rlyoulink 连接 ESP32 探针、调试 STM32、更新探针固件和签名发布；仅作为项目技能。
---

# rlyoulink 便携版使用

先读取项目根目录 README.md。通过当前目录的 rlyoulink.exe 启动，实际 URL 从 data/runtime.json 读取并核对 /api/health 的 instance；不要写死 8765、磁盘路径、探针 IP 或序列号。不要另启一个 OpenOCD 抢占现有调试会话。

所有维护命令用随包 rlyoulink-worker.exe，帮助及任务参数见 README。USB 多设备时选定真实序列号；进入 ROM 后仍核对同一设备 MAC，不取消身份校验。不要把启动上位机当成实板擦除或升级授权。

PC ↔ ESP32 与 ESP32 ↔ STM32 分别判断。目标支持 F1/F4/G4/常见 H7 自动识别，未知型号拒绝，不能编造连接或完整料号。调试动作复用现有 OpenOCD 会话，复位运行走 SWD SYSRESETREQ。NRST 是 XIAO D2/GPIO3，SWCLK D3/GPIO4，SWDIO D4/GPIO5，GPIO6 已停用。

独立整片擦除不需要文件，跳过 OTP 和选项字节，完成保持暂停。BIN 地址由真实目标与镜像决定，不能只靠默认值推断。只在实际操作获授权时调用擦写、复位和执行接口。

ESP32 日常升级选择 firmware 内 .amphipkg，先验签、型号、布局和哈希，再写非运行 OTA 槽，启动确认后才报告成功。此便携版不包含空白板首次安装或旧布局迁移流程。管理和升级默认密码 12345678，不覆盖用户路由器密码。

按用户明确要求，发行文件夹包含 publisher/keys 中现有私钥和公钥，发布复用这一对密钥；不打印私钥，不为每个版本生成新密钥。.amphipkg 内只包含清单、签名、应用镜像。不要擅自删除发行目录中的密钥。

源码与构建说明在 source 中。离线测试与实板验证分开报告；不要把依赖自检等同于无线升级或全部 STM32 实测。运行日志位于 logs，不把历史过程文件加入下一份发行包。本技能只保留在项目内，不安装到全局。
