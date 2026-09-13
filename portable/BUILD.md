# 构建便携版

使用 Windows x64 Python 3.13 创建 `.venv`，安装 `requirements-build.txt`，运行：

```powershell
.venv/Scripts/python.exe -m PyInstaller --noconfirm rlyoulink.spec
Copy-Item payload/* dist/rlyoulink-portable-win64 -Recurse -Force
```

发行目录内的 `source/src` 与本文件保存便携层源码；重建时放入工作目录的 `src`，把现有发行目录中的 tools、firmware、publisher、assets、examples、licenses 放入 `payload`，并准备上述根目录说明文件。不要把 `_internal`、日志、虚拟环境再次放进 payload。

`rlyoulink.exe` 与 `rlyoulink-worker.exe` 共用 `_internal`。GUI 运行本机 HTTP 服务，工作进程执行签名校验和 USB 升级，所有运行资源从 EXE 位置解析。HTTP 仅绑定 127.0.0.1；修改操作仍保留 Host、Origin、会话令牌和操作锁校验。

测试：设置 PYTHONPATH 为 src 的路径，再运行 `python -m unittest discover -s src/ui/tests`。运行 `rlyoulink-worker.exe --task self-test` 检查内置依赖及随包固件。实板擦写不属于离线测试。

OpenOCD 对应源码在 licenses：解压 openocd 与 jimtcl 源码，将 jimtcl 放入 OpenOCD 的 jimtcl 子目录，再应用 cmsis-dap-tcp-fix.patch，使用 MSYS2 UCRT64 和 build-openocd.sh 构建。工具链和编译依赖由开发者安装，不包含在运行包中。
