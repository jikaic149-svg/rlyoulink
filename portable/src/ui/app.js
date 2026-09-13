'use strict';
const $ = id => document.getElementById(id);
const pages = {
  overview: ['工作台', '调试，从连接开始。', '连接探针，发现目标，让每一次烧录与调试都有迹可循。'],
  network: ['网络与配网', '让探针，无线连接。', '通过 ESP32 管理页扫描和配网，再切回同一局域网调试。'],
  flash: ['固件烧录', '把想法，写进芯片。', '选择目标固件，完成擦除、写入、校验与运行。'],
  debug: ['调试器', '看清程序的每一步。', '控制目标运行，查看寄存器、内存和地址断点。'],
  settings: ['设备与设置', '适合你的调试环境。', '管理探针参数、复位接线和 ESP32 固件维护。']
};
const state = { connected: false, transport: 'usb', halted: false, file: null, flashing: false, page: 'overview', logs: [] };
let toastTimer;
function toast(message) { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 4200); }
function log(message, level = 'info') {
  state.logs.push({ time: new Date().toLocaleTimeString('zh-CN', { hour12: false }), level, message });
  state.logs = state.logs.slice(-200); renderLogs();
}
function renderLogs() {
  $('logs').replaceChildren();
  for (const row of state.logs) {
    const div = document.createElement('div'); div.className = `log-row ${row.level}`;
    const time = document.createElement('time'); time.textContent = row.time;
    const level = document.createElement('span'); level.className = 'log-level'; level.textContent = row.level.toUpperCase();
    const text = document.createElement('span'); text.textContent = row.message;
    div.append(time, level, text); $('logs').append(div);
  }
  $('log-count').textContent = state.logs.length; $('logs').scrollTop = $('logs').scrollHeight;
}
function go(page) {
  if (!pages[page]) page = 'overview';
  state.page = page;
  document.querySelectorAll('.page').forEach(el => el.hidden = el.id !== `page-${page}`);
  document.querySelectorAll('nav button').forEach(el => el.classList.toggle('active', el.dataset.page === page));
  [$('crumb').textContent, $('page-title').textContent, $('page-subtitle').textContent] = pages[page];
  $('page-code').textContent = page.toUpperCase();
  history.replaceState(null, '', `#${page}`);
}
function validIP(value) { const parts = value.split('.'); return parts.length === 4 && parts.every(x => /^\d{1,3}$/.test(x) && +x <= 255); }
function validAddress(value) { return /^0x[\da-f]{1,8}$/i.test(value.trim()); }
function setTransport(kind) {
  if (state.connected) return toast('请先断开当前连接，再切换连接方式。');
  state.transport = kind;
  document.querySelectorAll('[data-transport]').forEach(el => el.classList.toggle('selected', el.dataset.transport === kind));
  $('usb-fields').hidden = kind !== 'usb'; $('wifi-fields').hidden = kind !== 'wifi';
  $('link-label').textContent = kind === 'usb' ? 'USB CMSIS-DAP' : 'TCP / LOCAL NETWORK';
  $('connect-hint').textContent = kind === 'usb' ? '首次使用建议选择 USB。有线连接也是配网和维护的入口。' : '电脑和探针需要网络互通。此前的 IP 地址可能因 DHCP 变化。';
}
function selectFile(file) {
  if (!file) return;
  if (!/\.(bin|elf|hex)$/i.test(file.name)) return toast('请选择 BIN、ELF 或 HEX 文件。');
  if (!file.size) return toast('不能使用空文件。');
  if (state.flashing) return toast('烧录进行中，暂时不能更换固件。');
  state.file = file; $('file-name').textContent = file.name; $('file-size').textContent = `${(file.size / 1024).toFixed(1)} KiB · 仅本地选择，未上传`;
  const bin = /\.bin$/i.test(file.name); $('flash-address').disabled = !bin;
  $('flash-address').value = bin ? '0x08000000' : '由镜像决定';
  $('flash-stage').textContent = '固件已选择'; log(`已选择固件 ${file.name}，尚未解析或写入设备。`);
  renderFlashActions();
}
document.querySelectorAll('[data-page]').forEach(el => el.onclick = () => go(el.dataset.page));
document.querySelectorAll('[data-go]').forEach(el => el.onclick = () => go(el.dataset.go));
document.querySelectorAll('[data-transport]').forEach(el => el.onclick = () => setTransport(el.dataset.transport));
$('firmware-file').onchange = event => selectFile(event.target.files[0]);
$('dropzone').ondragover = event => { event.preventDefault(); $('dropzone').classList.add('dragover'); };
$('dropzone').ondragleave = () => $('dropzone').classList.remove('dragover');
$('dropzone').ondrop = event => { event.preventDefault(); $('dropzone').classList.remove('dragover'); selectFile(event.dataTransfer.files[0]); };
$('upgrade-probe').onclick = () => { toast('升级脚本尚未接入 UI，此操作不会重启 ESP32。'); log('未执行探针升级：需要接入本地维护服务。', 'warn'); };
$('clear-log').onclick = () => { state.logs = []; renderLogs(); };
$('toggle-log').onclick = () => { $('logs').hidden = !$('logs').hidden; $('toggle-log').textContent = $('logs').hidden ? '展开 ⌄' : '收起 ⌃'; $('toggle-log').setAttribute('aria-expanded', String(!$('logs').hidden)); };
$('export-log').onclick = () => { const url = URL.createObjectURL(new Blob([JSON.stringify({ mode: 'live', entries: state.logs }, null, 2)], { type: 'application/json' })); const a = document.createElement('a'); a.href = url; a.download = 'rlyoulink-ui-log.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); };
$('help').onclick = () => $('info-dialog').showModal(); $('close-dialog').onclick = $('dialog-confirm').onclick = () => $('info-dialog').close();
window.addEventListener('hashchange', () => go(location.hash.slice(1)));
go(location.hash.slice(1) || 'overview'); log('界面已加载，等待本地服务状态。');
