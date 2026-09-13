# STM32G474 RGB 循环

仅适用于当前 X Pulse STM32G474VET6 板：PC2 红、PC1 绿、PC0 蓝，低电平点亮。

运行现象：红 → 绿 → 蓝，每项约 0.8 秒，循环持续 2.4 秒。使用默认 HSI16 时钟和 SysTick，不操作其他外设。

上位机选择 `rgb_cycle.bin`，起始地址 `0x08000000`，启用写入校验和完成后运行。会替换目标原应用的起始 Flash 页面。也可以选择 ELF，由文件携带地址。

烧录随附 BIN/ELF 不需要编译环境。重新编译源码时自行安装 CMake、Ninja、ARM GCC，并将 ARM GCC 的 bin 目录加入 PATH，再运行 `cmake -S . -B build -G Ninja` 和 `cmake --build build`。构建脚本通过程序名查找工具链，没有固定磁盘路径。
