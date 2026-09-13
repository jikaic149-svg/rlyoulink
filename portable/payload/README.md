# rlyoulink Windows 便携版

完整解压文件夹，双击 **rlyoulink.exe**。程序自动打开浏览器，右下角托盘提供“打开上位机 / 打开日志文件夹 / 退出”。关闭浏览器不会退出后端。重复启动会打开已有实例。

支持 Windows 10/11 x64。包含 Python 3.13 运行环境、OpenOCD、esptool 和签名工具，无需安装 Python、ESP-IDF 或 GCC。保留整个文件夹结构，不要单独移动 EXE。目录必须可写；程序资源都按 EXE 所在目录定位，不依赖启动时的工作目录。优先使用本机 8765 端口，被占用时自动使用 8766–8795，不停止其他软件。

## 连接与使用

1. USB：用数据线接入已运行 rlyoulink 固件的 XIAO ESP32-S3。单台探针自动选中，多台时选择序列号。首次接入电脑须允许 Windows 安装设备驱动；若 CMSIS-DAP 接口未绑定 WinUSB，需安装/修复该接口的驱动，便携包不自动修改系统驱动。
2. Wi-Fi：电脑连接设备的 `rlyoulink-` 热点，打开设备管理页配置 2.4 GHz 路由器；随后电脑与探针连接同一局域网。默认热点、管理和升级密码为 `12345678`。路由器密码以实际网络为准。广播发现不可用时可填写设备实际 IP。
3. 接目标：D3/GPIO4 → SWCLK，D4/GPIO5 → SWDIO，D2/GPIO3 → NRST，必须共地并正确供电。GPIO6/D5 不再用作 NRST。
4. 点击连接目标，自动识别支持的 STM32 F1、F4、G4、常见 H7。未知型号会明确拒绝；C5、H7R/S、H7 双核同时调试不支持。新增系列尚未逐板实测。
5. STM32 烧录选择目标程序的 BIN/HEX/ELF；BIN 需填正确地址，常用内部 Flash 起点为 `0x08000000`。独立整片擦除不需要文件，完成后目标保持暂停。
6. 调试页可暂停、继续、单步、读内核寄存器和设置断点。当前“复位运行”通过 SWD 的 SYSRESETREQ，不是物理 NRST 脉冲。

连接状态分别展示 PC ↔ ESP32 与 ESP32 ↔ STM32；探针在线不等于目标已连接。烧录进度显示实际阶段，某阶段到 100% 不等于最终成功，需等校验和启动确认。

## ESP32 更新

在上位机升级页选择 `firmware/*.amphipkg`，先校验再升级。先结束 STM32 调试会话。USB 升级自动进入下载模式；Wi-Fi 升级需设备 IP 和密码。写入非运行 OTA 槽，完成后切换并确认启动，保留网络配置。当前包内 ESP32 固件版本为 3.0.0，上位机便携发行版本为 3.0.1。

此升级流程要求设备已经安装支持维护接口的 rlyoulink 固件，**不用于空白 ESP32 首次安装或未知分区布局救砖**。没有附带针对旧板的固定序列号迁移脚本。

## 固件签名发布

按项目所有者要求，本便携包包含现有私钥 `publisher/keys/rlyoulink-private.pem`、对应公钥及签名工具。持有本包的人也拥有发布该设备可接受固件的签名能力。日常 `.amphipkg` 本身仍不包含私钥。

从本目录运行（路径包含空格时加引号）：

```bat
rlyoulink-worker.exe --task release pack application.bin --version 3.0.0 --output release.amphipkg
rlyoulink-worker.exe --task release verify release.amphipkg
rlyoulink-worker.exe --task self-test
rlyoulink-worker.exe --task usb-info
```

版本必须与固件内部描述符一致。发布时复用已有密钥，不为每个固件重新生成密钥。验签、硬件型号、分区布局及固件哈希检查均保留。USB 多探针维护命令可增加 `--serial 十二位序列号`。

## 文件与故障排查

- `_internal/`：共享 Python 运行库、页面资源、维护脚本，必须保留。
- `tools/openocd/`：有线/无线 OpenOCD 及 DLL、目标配置。
- `firmware/`：ESP32 升级包；`examples/`：STM32 示例。
- `publisher/keys/`：发布密钥；`assets/`：程序图标。
- `data/`、`logs/`：运行后生成的实例信息和日志。连接 IP 仍由浏览器本地存储保存。
- `source/`：便携封装源码、构建说明和离线测试；`licenses/`：第三方许可、OpenOCD 源码与补丁。

无法启动时先确认已完整解压，并查看 `logs/application.log`；设备不可见时检查供电、数据线、WinUSB 驱动。此 Windows EXE 未作代码签名；它与设备固件的 RSA 签名是两件不同的事。

图标来自用户指定的 Bilibili《勇者肋骨：女神表情包》系列：
https://www.bilibili.com/opus/1215891802555416584
仅品牌头像使用该图片，前五个功能导航保留原功能图标。图片权利归原权利人。
