"""Build the editable v2 source with the local ESP-IDF/Ninja/GCC toolchain."""
from pathlib import Path
import os, runpy, subprocess, sys

root = Path(__file__).resolve().parent
runpy.run_path(str(root / 'sync-v2-build.py'))
build_source = Path(os.environ['TEMP']) / 'rlyoulink-build'
env = os.environ.copy()
env.update(IDF_PATH='D:/ESP32/ESP-IDF-v5.3.2',
           IDF_TOOLS_PATH='D:/ESP32/.espressif',
           IDF_PYTHON_ENV_PATH='D:/ESP32/.espressif/python_env/idf5.3_py3.13_env')
env['PATH'] = ';'.join([
    'D:/ESP32/.espressif/tools/xtensa-esp-elf/esp-13.2.0_20240530/xtensa-esp-elf/bin',
    'D:/ESP32/.espressif/python_env/idf5.3_py3.13_env/Scripts',
    'D:/CMAKE/bin', 'D:/Ninja', 'D:/Git/cmd', env['PATH']])
commands = [
    ['D:/CMAKE/bin/cmake.exe', '-S', str(build_source), '-B', str(build_source/'build'),
     '-G', 'Ninja', '-DIDF_TARGET=esp32s3',
     '-DPYTHON=D:/ESP32/.espressif/python_env/idf5.3_py3.13_env/Scripts/python.exe'],
    ['D:/Ninja/ninja.exe', '-C', str(build_source/'build'), '-j', '8'],
]
with (root/'build-v2.log').open('w', encoding='utf-8') as log:
    for command in commands:
        result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        log.write(f'\nProcess exit code: {result.returncode}\n'); log.flush()
        if result.returncode:
            print('Build failed; see AmphiLink_flash/build-v2.log')
            sys.exit(result.returncode)
print('CMake + Ninja + GCC: PASS (exit 0). Log: AmphiLink_flash/build-v2.log')
