/* EON v0.0.2 — same-origin client. No external APIs or analytics. */
'use strict';
const el = id => document.getElementById(id);
let csrfToken = '';
let state = null;
let installedModels = [];
let apps = [];
let busy = false;
let editId = '';
let isCustom = false;
let toastTimeout = null;

function toast(message) {
  const box = el('toast');
  box.textContent = String(message);
  box.classList.remove('hidden');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => box.classList.add('hidden'), 4800);
}

async function request(path, body) {
  const options = body === undefined ? {} : {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-EON-Token': csrfToken},
    body: JSON.stringify(body)
  };
  const response = await fetch(path, options);
  let result;
  try { result = await response.json(); } catch { throw new Error('Yerel sunucudan yanıt alınamadı.'); }
  if (!response.ok) throw new Error(result.error || 'İşlem tamamlanamadı.');
  return result;
}

function svgIcon(id) {
  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', '#' + id);
  icon.appendChild(use);
  return icon;
}

function setBusy(value, description='') {
  busy = value;
  el('sendButton').disabled = value;
  el('summaryButton').disabled = value;
  el('messageInput').disabled = value;
  el('busyMessage').textContent = value ? description || 'EON düşünüyor...' : '';
}

function showPage(name) {
  document.querySelectorAll('.page').forEach(page => page.classList.toggle('active-page', page.id === 'view-' + name));
  document.querySelectorAll('.nav-button').forEach(btn => btn.classList.toggle('selected', btn.dataset.view === name));
  if (name === 'history') renderHistory();
  if (name === 'settings') renderStats();
  if (name === 'apps') renderApps();
  if (name === 'chat') el('messageInput').focus();
}

function renderState(newState) {
  state = newState;
  renderChat();
  renderStats();
  document.querySelectorAll('[data-style]').forEach(btn => btn.classList.toggle('selected', btn.dataset.style === state.style));
  ['modelSelect', 'settingsModelSelect'].forEach(id => {
    const select = el(id);
    if (Array.from(select.options).some(opt => opt.value === state.model)) select.value = state.model;
  });
}

function renderChat() {
  if (!state) return;
  const history = state.history || [];
  el('welcome').classList.toggle('hidden', history.length > 0);
  const log = el('chatLog');
  log.replaceChildren();
  history.forEach((entry, index) => {
    const msg = document.createElement('div');
    msg.className = 'msg ' + (entry.role === 'user' ? 'user' : 'assistant');
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = entry.content;
    msg.appendChild(bubble);
    if (entry.role === 'assistant' && index === history.length - 1) {
      const actions = document.createElement('div');
      actions.className = 'reply-actions';
      const again = document.createElement('button');
      again.type = 'button';
      again.textContent = 'Yanıtı yenile';
      again.disabled = busy;
      again.addEventListener('click', regenerate);
      actions.appendChild(again);
      msg.appendChild(actions);
    }
    log.appendChild(msg);
  });
  log.scrollTop = log.scrollHeight;
}

function renderHistory() {
  const root = el('historyList');
  root.replaceChildren();
  const history = state?.history || [];
  if (!history.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-hint';
    empty.textContent = 'Henüz bir konuşma yok. Sohbet ekranından başlayabilirsin.';
    root.appendChild(empty);
    return;
  }
  history.forEach(entry => {
    const card = document.createElement('div');
    card.className = 'history-entry';
    const label = document.createElement('small');
    label.textContent = entry.role === 'user' ? 'SEN' : 'EON';
    const content = document.createElement('div');
    content.textContent = entry.content;
    card.append(label, content);
    root.appendChild(card);
  });
}

function renderStats() {
  if (!state) return;
  const s = state.stats;
  el('countMessages').textContent = String(s.messages);
  el('countRetries').textContent = String(s.regenerated);
  el('countSummaries').textContent = String(s.summaries);
  el('countMinutes').textContent = String(s.minutes);
}

function modelOptions(select, models, current) {
  select.replaceChildren();
  if (!models.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'Model yok';
    select.appendChild(option);
    select.disabled = true;
    return;
  }
  select.disabled = false;
  models.forEach(name => {
    const option = document.createElement('option');
    option.value = name;
    option.textContent = name;
    select.appendChild(option);
  });
  select.value = models.includes(current) ? current : models[0];
}

async function loadModels() {
  const result = await request('/api/models');
  installedModels = result.models || [];
  state.model = result.selected;
  for (const id of ['modelSelect', 'settingsModelSelect']) modelOptions(el(id), installedModels, state.model);
  el('connection').classList.toggle('connected', Boolean(result.connected && installedModels.length));
  el('connectionText').textContent = !result.connected ? 'Ollama bağlantısı yok' : installedModels.length ? 'Yerel model hazır' : 'Yerel model bulunamadı';
}

async function changeModel(name) {
  if (!name || busy) return;
  try {
    const updated = await request('/api/model', {model: name});
    renderState(updated);
    toast('Model değiştirildi: ' + name);
  } catch (error) {
    toast(error.message);
    if (state) ['modelSelect', 'settingsModelSelect'].forEach(id => {
      if (installedModels.includes(state.model)) el(id).value = state.model;
    });
  }
}

async function send() {
  const input = el('messageInput');
  const text = input.value.trim();
  if (!text || busy) return;
  setBusy(true, 'EON yanıt hazırlıyor...');
  try {
    const result = await request('/api/message', {text});
    input.value = '';
    renderState(result.state);
    if (text.startsWith('/')) {
      if (result.summary) showSummary(result.summary);
      else if (text.startsWith('/gecmis') || text.startsWith('/geçmiş')) showPage('history');
      else if (text.startsWith('/istatistik') || text.startsWith('/durum')) showPage('settings');
      else if (text.startsWith('/yeniden')) showPage('chat');
      else toast(result.message);
    }
  } catch (error) {
    toast(error.message);
  } finally {
    setBusy(false);
    renderChat();
    input.focus();
  }
}

async function regenerate() {
  if (busy) return;
  setBusy(true, 'Yanıt yenileniyor...');
  try {
    const result = await request('/api/regenerate', {});
    renderState(result.state);
    showPage('chat');
  } catch (error) { toast(error.message); }
  finally { setBusy(false); renderChat(); }
}

function showSummary(content) {
  el('summaryText').textContent = content;
  el('summaryPanel').classList.remove('hidden');
}

async function summarize() {
  if (busy) return;
  setBusy(true, 'Sohbet özetleniyor...');
  try {
    const result = await request('/api/summary', {});
    renderState(result.state);
    showSummary(result.summary);
    showPage('chat');
  } catch (error) { toast(error.message); }
  finally { setBusy(false); renderChat(); }
}

async function changeLength(style) {
  if (busy) return;
  try {
    renderState(await request('/api/length', {style}));
    toast('Yanıt modu güncellendi.');
  } catch (error) { toast(error.message); }
}

function renderApps() {
  const root = el('appList');
  root.replaceChildren();
  apps.forEach(app => {
    const card = document.createElement('div');
    card.className = 'app-card';
    const icon = document.createElement('div');
    icon.className = 'app-icon';
    icon.textContent = (app.name || '?').slice(0, 2).toUpperCase();
    const meta = document.createElement('div');
    meta.className = 'app-meta';
    const title = document.createElement('strong');
    title.textContent = app.name;
    const status = document.createElement('small');
    status.textContent = app.ready ? app.source === 'saved' ? 'Kaydedildi · Hazır' : 'Otomatik bulundu · Hazır' : 'Yol eklenmedi';
    meta.append(title, status);
    const buttons = document.createElement('div');
    buttons.className = 'app-buttons';
    const open = document.createElement('button');
    open.type = 'button';
    open.textContent = 'Aç';
    open.disabled = !app.ready;
    open.addEventListener('click', () => launchApp(app.id));
    const edit = document.createElement('button');
    edit.type = 'button';
    edit.textContent = app.ready ? 'Yol' : 'Ekle';
    edit.addEventListener('click', () => openAppModal(app));
    buttons.append(open, edit);
    card.append(icon, meta, buttons);
    root.appendChild(card);
  });
}

async function refreshApps() {
  try {
    const result = await request('/api/apps/refresh', {});
    apps = result.apps || [];
    renderApps();
    toast('Uygulama yolları yeniden tarandı.');
  } catch (error) { toast(error.message); }
}

async function launchApp(id) {
  // The only launch path is a direct click on the selected entry's Aç button.
  try {
    await request('/api/apps/launch', {id});
    const app = apps.find(item => item.id === id);
    toast((app?.name || 'Uygulama') + ' başlatma isteği Windows’a gönderildi.');
  } catch (error) { toast(error.message); }
}

function openAppModal(app) {
  editId = app?.id || 'custom_' + Math.random().toString(36).slice(2, 10);
  isCustom = !app;
  el('modalTitle').textContent = app ? app.name + ' · Uygulama yolu' : 'Uygulama ekle';
  el('appName').value = app?.name || '';
  el('appName').readOnly = Boolean(app && ['chrome','spotify','notion','obs','solidworks','antigravity'].includes(app.id));
  el('appPath').value = app?.path || '';
  el('removeApp').classList.toggle('hidden', !app || app.source !== 'saved');
  el('appModal').classList.remove('hidden');
  el('appName').focus();
}
function closeAppModal() { el('appModal').classList.add('hidden'); }

async function saveApp() {
  const name = el('appName').value.trim();
  const path = el('appPath').value.trim();
  if (!name || !path) return toast('Uygulama adı ve yolunu gir.');
  try {
    await request('/api/apps/save', {id: editId, name, path});
    const data = await request('/api/apps');
    apps = data.apps || [];
    renderApps();
    closeAppModal();
    toast('Uygulama yolu kaydedildi.');
  } catch (error) { toast(error.message); }
}

async function removeApp() {
  if (!confirm('Kaydedilen uygulama yolunu silmek istiyor musun?')) return;
  try {
    const result = await request('/api/apps/remove', {id: editId});
    apps = result.apps || [];
    renderApps();
    closeAppModal();
    toast('Kayıt silindi.');
  } catch (error) { toast(error.message); }
}

async function pickApp() {
  try {
    const result = await request('/api/apps/pick', {});
    if (result.path) el('appPath').value = result.path;
  } catch (error) { toast(error.message + ' Dosya yolunu elle yazabilirsin.'); }
}

function wireEvents() {
  document.querySelectorAll('.nav-button').forEach(btn => btn.addEventListener('click', () => showPage(btn.dataset.view)));
  document.querySelectorAll('[data-style]').forEach(btn => btn.addEventListener('click', () => changeLength(btn.dataset.style)));
  document.querySelectorAll('[data-action]').forEach(btn => btn.addEventListener('click', () => {
    if (btn.dataset.action === 'apps') return showPage('apps');
    showPage('chat');
    el('messageInput').value = btn.dataset.action === 'math' ? '/hesap ' : 'Python ile şu konuda kod yaz: ';
    el('messageInput').focus();
  }));
  el('sendButton').addEventListener('click', send);
  el('messageInput').addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      send();
    }
  });
  el('summaryButton').addEventListener('click', summarize);
  el('dismissSummary').addEventListener('click', () => el('summaryPanel').classList.add('hidden'));
  el('clearButton').addEventListener('click', async () => {
    if (!state?.history?.length) return;
    if (!confirm('Bu oturumun sohbet geçmişi temizlensin mi?')) return;
    try { renderState(await request('/api/clear', {})); el('summaryPanel').classList.add('hidden'); toast('Sohbet temizlendi.'); }
    catch (error) { toast(error.message); }
  });
  ['modelSelect','settingsModelSelect'].forEach(id => el(id).addEventListener('change', evt => changeModel(evt.target.value)));
  el('reloadModels').addEventListener('click', async () => { try { await loadModels(); toast('Model listesi güncellendi.'); } catch (error) { toast(error.message); } });
  el('refreshApps').addEventListener('click', refreshApps);
  el('addApp').addEventListener('click', () => openAppModal(null));
  el('closeAppModal').addEventListener('click', closeAppModal);
  el('cancelApp').addEventListener('click', closeAppModal);
  el('appModal').addEventListener('click', e => { if (e.target === el('appModal')) closeAppModal(); });
  el('saveApp').addEventListener('click', saveApp);
  el('removeApp').addEventListener('click', removeApp);
  el('browseApp').addEventListener('click', pickApp);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') {closeAppModal(); el('summaryPanel').classList.add('hidden');} });
}

async function initialize() {
  wireEvents();
  try {
    const boot = await request('/api/bootstrap');
    csrfToken = boot.token;
    state = boot.state;
    apps = boot.apps || [];
    renderState(state);
    renderApps();
    installedModels = boot.models.models || [];
    for (const id of ['modelSelect','settingsModelSelect']) modelOptions(el(id), installedModels, boot.models.selected);
    el('connection').classList.toggle('connected', Boolean(boot.models.connected && installedModels.length));
    el('connectionText').textContent = !boot.models.connected ? 'Ollama bağlantısı yok' : installedModels.length ? 'Yerel model hazır' : 'Yerel model bulunamadı';
  } catch (error) { toast('EON yerel sunucusu hazır değil: ' + error.message); }
}
initialize();
