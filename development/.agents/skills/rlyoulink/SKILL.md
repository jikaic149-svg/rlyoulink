---
name: rlyoulink
description: 使用和维护 rlyoulink XIAO ESP32-S3 烧录器及其 Windows 上位机，包括 STM32 F1/F4/G4/H7 自动识别与 SWD 调试、配网、ESP32 签名升级和固件发布。用于该项目的实际连接与维护任务。
---

# rlyoulink 使用技能

这是项目本地技能，仅在本项目范围内使用，不复制或安装到全局 skills 目录。

## 定位项目

优先使用用户指定目录；本开发包通常位于 `C:/Users/rlyoulo/Desktop/rlyoulink`。确认同时存在 `AmphiLink_UI/server.py` 和 `AmphiLink_flash/rlyou_release.py`。不要因内部旧名称另找历史固件。先读取项目根目录 README.md 中与当前操作有关的章节，依赖路径以实际文件为准。

## 启动与连接

- 运行根目录 `启动上位机.cmd`，服务地址 `http://127.0.0.1:8765/`。直接打开 HTML 不会提供真实烧录后端。
- 先检查端口归属；启动器可能复用旧目录的服务。仅对已确认属于该项目、且用户任务需要停止的进程进行管理，不批量杀 Python/OpenOCD。
- PC ↔ ESP32 和 ESP32 ↔ STM32 是两条不同连接，分别查看实际状态。USB 枚举或 HTTP 在线不能证明 SWD 已接通。
- Wi-Fi 配网：电脑连接设备 `rlyoulink-` AP，在管理页面扫描并配置 2.4 GHz 路由器，再让电脑回到同一局域网。使用当前 IP，不沿用历史地址。默认 AP/管理/升级密码 `12345678`，不擅改已保存的路由器密码。
- HTTP `/api/v1/health` 可检查固件、版本、running_slot、ota_confirmed。发现广播可能受网络限制，允许填实际 IP。

## STM32 调试约束

- 独立 `/api/erase` 不接收或要求固件文件，擦除完成后保持目标 halted；不调用 write_image、resume 或 reset run。它与 flash 接口的 erase=all（先全擦再烧录）不同。功能验证优先离线测试，未经实板擦除授权不点击执行。
- 连接时 flash info 会自动 probe，不再前置重复 flash probe；Tcl 连接等 OpenOCD 就绪事件。性能报告使用实际测量样本，不承诺固定连接时间。

- 烧录接口 erase 只接受 covered 或 all。all 通过 `flash erase_sector <主Flash bank索引> 0 last` 擦除所有主 Flash Bank；先解析镜像和校验全部 Bank，跳过 OTP，不操作选项字节、不自动解除保护。完成全擦后 write_image 不再附带 erase。修改此功能本身不构成执行实板全擦授权。

- 身份读取期间短暂停核，并在 finally 中恢复原先运行状态；Flash 容量通过对齐的 32 位访问提取对应 16 位字段，不能假设运行态半字读取可靠。枚举 flash list 时只探测普通应用 Flash，排除脚本注册的 OTP Bank（如 G4 的 0x1FFF7000），但不要扩大普通 Flash 的允许地址范围。

- 目标不手选系列。`AmphiLink_UI/targets.py` 通过 CPUID、DBGMCU_IDCODE 和容量自动匹配 F1/F4/G4/常见 H7；具体芯片组见 README。未知 ID 不猜测驱动；识别到芯片组不代表确定完整料号。
- 连接初期先开只用于身份读取的 Cortex-M 会话，再加载对应系列配置；暂停、继续、单步等动作仍复用后续调试会话。目标实例来自匹配结果，不写死 stm32g4x.cpu；H7 使用 stm32h7x.cpu0。
- Flash 范围取自实际扇区表并核对总容量，不能简单用 Flash 起点加容量代替 H7/G4 的非连续 Bank 布局。C5、H7R/S、外部 Flash 和 H7 双核同时调试未加入；H7 仅 M7。新增系列未完成实板验证时明确说明。
- XIAO D3/GPIO4→SWCLK，D4/GPIO5→SWDIO，D2/GPIO3→NRST；共地，目标正确供电。GPIO6/D5 已停用。
- NRST 默认开漏释放。不得在连接目标时随意改成推挽高电平。当前 UI 复位运行走 SWD SYSRESETREQ（reset_config none），不能称为 NRST 硬复位。
- 调试动作使用同一 OpenOCD 会话。检查真实错误与耗时，不用每次重启/重连掩盖超时。当前 cmsis-dap quirk disable；有线和无线均使用随包 OpenOCD。
- 读探针信息优先用无目标副作用的接口。连接调试会话可能短暂停住目标；擦写、复位和执行程序应符合用户当前授权，不为验证 UI 自动烧写 STM32。
- USB 序列号及升级 MAC 固定为当前探针，换设备需要明确适配，不能直接删除身份检查以绕过错误。

## ESP32 升级和发布

- 日常升级用上位机选择 `.amphipkg`。停止调试会话后选择 USB/Wi-Fi；Wi-Fi 需要实际 IP 和管理密码。
- 包中只有 manifest.json、manifest.sig、application.bin。RSA-3072/PKCS#1 v1.5 + SHA-256 验证清单，再验证固件哈希与硬件兼容。
- 日常 USB 命令：使用 README 指定的 ESP-IDF Python 运行 `AmphiLink_flash/rlyou_usb_upgrade.py <包路径>`。只读 USB 信息使用工作站 Python 运行 `AmphiLink_flash/rlyou_usb_info.py`。
- 写非运行 OTA 槽，成功后提交启动选择。两个槽大小均 2 MiB，地址 0x20000 和 0x220000；otadata 为 0x1d000 / 0x2000。保留 NVS，不整片擦除，不额外建 USB 分区。
- `bootstrap-rlyou.py <COM口>` 仅用于符合其检查条件的旧版迁移，会写 bootloader；不可作为通用日常升级或未知板救砖命令。失败后先确认写到哪个阶段、当前槽和端口，不能盲目重跑。
- “数据写入成功”与“新固件启动成功”分开报告；新版本/新槽及 ota_confirmed 或 USB OTA VALID 状态得到确认后才能报告升级完成。回滚配置开启不等于故障注入测试已通过。
- 发布时沿用 `.release-keys/rlyoulink-private.pem`，不打印密钥内容、不放进用户升级包。公钥位于固件 tcp/inc/release_public.pem。密钥迁移不属于普通版本升级。
- 编译和打包命令见 README。保持固件版本、签名清单版本和发布文件名一致。管理网页嵌入 ESP32 应用；电脑上位机 HTML/JS 不随 ESP32 OTA 更新。

## 报告结果

烧录进度由独立 `/api/progress` 提供，不能放在长耗时操作的 LOCK 后等待。ESP32 USB 百分比来自实时 esptool 输出；Wi-Fi 百分比仅表示 HTTP 发送量；STM32 当前只提供真实阶段进度。上传或某阶段到 100% 不代表整体成功，必须等校验/运行或 OTA 启动确认。页面“未选择文件”时升级按钮禁用正常，不直接诊断为卡死。

按实际证据说明：探针在线、目标识别、命令完成、写入校验、启动确认分别是否通过。不要用模拟状态冒充连接或成功。交付目录不保留历史 process、测试截图和日志；运行产生的新日志用于故障定位，不代表打包遗漏。
