# rlyoulink

基于 XIAO ESP32-S3 的 USB / Wi-Fi 双模式 STM32 烧录与调试工具，配套 Windows 便携上位机。

本项目由 [AmphiLink](https://github.com/danjinghaoeggggg/AmphiLink--A-Dual-Mode-Wired-Wireless-Debugger) 适配扩展而来，保留相关第三方许可。适配硬件为 XIAO ESP32-S3（8 MiB Flash），NRST 使用 D2 / GPIO3。

## 下载和启动

前往本仓库 **Releases** 下载 `rlyoulink-portable-win64.zip`，完整解压后双击 `rlyoulink.exe`。支持 Windows 10/11 x64，不需要额外安装 Python、OpenOCD、ESP-IDF 或 GCC。USB 驱动仍需由 Windows 正常安装；若设备不可见，检查数据线与 CMSIS-DAP 接口的 WinUSB 驱动。

请不要直接打开 HTML，也不要仅从压缩包中拖出一个 EXE。程序资源按 EXE 所在目录定位；重复启动复用本目录实例，8765 被占用时自动使用 8766–8795。托盘菜单提供打开页面、查看日志与退出。

## 功能

- PC ↔ ESP32 与 ESP32 ↔ STM32 分别显示连接状态。
- USB / Wi-Fi 烧录调试，STM32 F1/F4/G4/常见 H7 自动识别，无需手选系列。
- BIN / HEX / ELF 写入与校验，支持独立整片擦除，无需选择烧录文件。
- 暂停、继续、单步、内核寄存器读取及断点，复用 OpenOCD 调试会话。
- ESP32 AP/STA 配网：扫描并配置 2.4 GHz Wi-Fi，再与电脑连接同一局域网。
- ESP32 USB / Wi-Fi 签名包升级，写入非运行 OTA 槽并确认新固件启动。
- 烧录显示真实阶段进度；上传到 100% 不等于最终升级完成。

## 硬件连接

| XIAO ESP32-S3 | STM32 |
|---|---|
| D3 / GPIO4 | SWCLK |
| D4 / GPIO5 | SWDIO |
| D2 / GPIO3 | NRST，开漏释放 |
| GND | GND |

目标独立正确供电，信号使用 3.3 V 电平。D5 / GPIO6 已停用。当前“复位运行”经 SWD 发出 SYSRESETREQ，并非 NRST 硬复位。

热点、管理与升级默认密码为 `12345678`；路由器密码以实际网络为准。

## 目录与版本

| 目录 | 内容 |
|---|---|
| `development/` | 当前原始开发文件夹：ESP32 固件、旧开发启动器、上位机、工具与示例 |
| `portable/` | 便携发行版封装源码、资源、构建脚本与离线测试 |
| `portable/payload/firmware/` | ESP32 3.0.0 正式 `.amphipkg` 升级包 |
| `portable/payload/licenses/` | 第三方许可、定制 OpenOCD 对应源码和补丁 |

便携上位机发行版本为 **3.0.1**，随附 ESP32 固件仍为 **3.0.0**。制作 EXE 不等于重新烧录 ESP32。

日常使用推荐 Releases 里的便携 APP。`development/` 保留原开发现场，其旧启动器与部分维护脚本仍具有开发机路径、固定探针身份等限制；不能将该目录的直接运行能力与便携版混为一谈。便携版已移除固定探针序列号，单台 USB 探针自动选择，多台时显式选择。

## 构建与维护

便携构建见 [portable/BUILD.md](portable/BUILD.md)。需要 Windows x64 Python 3.13，安装 `portable/requirements-build.txt` 中依赖；运行 PyInstaller 并将 payload 合并到发行目录。运行时不需要编译工具链。

固件开发与型号覆盖详情见 [development/README.md](development/README.md)。日常 ESP32 更新使用 `.amphipkg`；当前维护流程要求设备已安装匹配布局和升级接口的 rlyoulink 固件，不用于空白板首次安装或未知布局救砖。

## 已验证与限制

- 24 项离线测试通过，覆盖芯片识别、Flash Bank 范围、擦除保护、进度和会话复用。
- 便携 EXE 的内置运行库、OpenOCD、esptool、签名打包及验签通过检查；篡改镜像与错误签名被拒绝。
- 含中文与空格的路径、清空开发工具 PATH、重复启动、端口冲突和浏览器脚本检查通过。
- 通过 USB 读到现有探针固件 3.0.0、8 MiB Flash 及有效 OTA 状态；本次发布未执行实板擦写。
- 未在另一台全新 Windows 电脑完成验证。F1/F4/H7 未逐板实测；C5、H7R/S、H7 双核同时调试未支持。

## 密钥与素材备注

**此仓库按项目所有者要求设为私有，并包含现有固件签名私钥、公钥与发布工具。** 拥有仓库或完整 APP 包的人也拥有签名发布能力。升级包本身仍只有清单、签名、应用镜像；版本更新复用现有密钥，不为每份文件重新生成。

Windows EXE 本身没有代码签名，与 ESP32 固件 RSA 验签不同。

品牌图标采用用户指定的 [Bilibili《勇者肋骨：女神表情包》](https://www.bilibili.com/opus/1215891802555416584)，图片权利归原权利人。前五个功能导航保留普通功能图标。项目本地 skill 保留在对应项目目录，不安装为全局 skill。
