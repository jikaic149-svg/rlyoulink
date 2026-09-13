'use strict';
$('open-probe-form').onsubmit = event => {
  event.preventDefault();
  const ip = $('management-ip').value.trim();
  if (!validIP(ip) || ip === '0.0.0.0' || ip === '255.255.255.255') {
    $('management-result').textContent = '请输入有效的 ESP32 IPv4 地址。';
    return;
  }
  window.open(`http://${ip}/`, '_blank', 'noopener');
  if(!liveState.session_active)$('host-input').value = ip;
  $('management-result').textContent = `已打开 ${ip} 的 Wi-Fi 管理入口，用于搜索、保存和切换网络。`;
  log(`打开 ESP32 Wi-Fi 管理入口 ${ip}。`);
};
