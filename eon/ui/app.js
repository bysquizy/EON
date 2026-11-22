/* EON v0.1.0 — same-origin client. No external APIs or analytics. */
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
let disconnected = false;

function toast(message) {
  const box = el('toast');
  box.textContent = String(message);
  box.classList.remove('hidden');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => box.classList.add('hidden'), 4800);
}

function setConnectionLost(lost) {
  disconnected = Boolean(lost);
  el('serverError').classList.toggle('hidden', !disconnected);
  el('connection').classList.toggle('connected', !disconnected && installedModels.length > 0);
  if (disconnected) el('connectionText').textContent = 'Yerel EON sunucusuna ulaşılamıyor';
}

async function request(path, body) {
  const options = body === undefined ? {cache: 'no-store'} : {
    method: 'POST', cache: 'no-store',
    headers: {'Content-Type': 'application/json', 'X-EON-Token': csrfToken},
    body: JSON.stringify(body)
  };
  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    setConnectionLost(true);
    throw new Error('EON sunucusuna ulaşılamıyor. Terminali kapattıysan EON’u yeniden başlat ve açılan yeni sekmeyi kullan.');
  }
  let result;
  try { result = await response.json(); } catch {
    throw new Error('Yerel sunucudan okunabilir yanıt alınamadı.');
  }
  if (!response.ok) {
    if (response.status === 403) {
      setConnectionLost(true);
      throw new Error('Oturum doğrulaması değişti. Yeniden bağlanmayı dene.');
    }
    throw new Error(result.error || 'İşlem tamamlanamadı.');
  }
  return result;
}

async function reconnect() {
  try {
    const boot = await request('/api/bootstrap');
    csrfToken = boot.token;
    state = boot.state;
    apps = boot.apps || [];
    installedModels = boot.models.models || [];
    renderState(state);
    renderApps();
    for (const id of ['modelSelect', 'settingsModelSelect']) {
      modelOptions(el(id), installedModels, boot.models.selected);
    }
    setConnectionLost(false);
    el('connectionText').textContent = boot.models.connected && installedModels.length
      ? 'Yerel model hazır' : boot.models.connected ? 'Yerel model bulunamadı' : 'Ollama bağlantısı yok';
    toast('EON yerel sunucusuna yeniden bağlandı.');
  } catch (error) {
    toast(error.message);
  }
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
  if (name === 'settings' && state) { renderStats(); fillPreferences(); }
  if (name === 'apps') renderApps();
  if (name === 'chat') el('messageInput').focus();
}

function renderState(newState) {
  state = newState;
  document.querySelectorAll('.storageStatus').forEach(node => node.textContent = state.storage);
  renderNotes();
  if (!el('view-settings').classList.contains('active-page')) fillPreferences();
  if (!activeStream || el("chatLog").dataset.chat !== state.active_chat_id) renderChat();
  renderHistory();
  renderStats();
  document.querySelectorAll('[data-style]').forEach(btn => btn.classList.toggle('selected', btn.dataset.style === state.style));
  ['modelSelect', 'settingsModelSelect'].forEach(id => {
    const select = el(id);
    if (Array.from(select.options).some(opt => opt.value === state.model)) select.value = state.model;
  });
}

function renderChat() {
  if (!state) return;
  el("chatLog").dataset.chat = state.active_chat_id;
  const history = state.history || [];
  el('welcome').classList.toggle('hidden', history.length > 0);
  const log = el('chatLog');
  log.replaceChildren();
  history.forEach((entry, index) => {
    const msg = document.createElement('div');
    msg.className = 'msg ' + (entry.role === 'user' ? 'user' : 'assistant');
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    if (entry.role === 'assistant') markdown(bubble, entry.content);
    else bubble.textContent = entry.content;
    msg.appendChild(bubble);
    const tools = document.createElement('div');
    tools.className = 'reply-actions';
    tools.append(action('Kopyala', () => navigator.clipboard.writeText(entry.content)));
    if (entry.role === 'user') tools.append(action('Düzenle', async () => {
      if (busy) return;
      const value = prompt('Bu mesajdan sonraki yanıtlar yeniden oluşturulacak.', entry.content);
      if (value?.trim()) await streamAnswer(value.trim(), index);
    }));
    msg.append(tools);
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
  const query = el('chatSearch').value.trim().toLocaleLowerCase('tr');
  const conversations = (state?.conversations || []).filter(c => c.title.toLocaleLowerCase('tr').includes(query));
  if (!conversations.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-hint';
    empty.textContent = 'Henüz bir sohbet yok.';
    root.appendChild(empty);
    return;
  }
  conversations.forEach(chat => {
    const row = document.createElement('div');
    row.className = 'conversation-row' + (chat.id === state.active_chat_id ? ' active-chat' : '');
    const open = document.createElement('button');
    open.type = 'button';
    open.className = 'conversation-open';
    const name = document.createElement('strong');
    name.textContent = chat.title;
    const meta = document.createElement('small');
    meta.textContent = chat.message_count ? chat.message_count + ' mesaj' : 'Boş sohbet';
    open.append(name, meta);
    open.addEventListener('click', () => openChat(chat.id));
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'conversation-delete';
    remove.textContent = 'Sil';
    remove.setAttribute('aria-label', chat.title + ' sohbetini sil');
    remove.addEventListener('click', () => deleteChat(chat.id));
    row.append(open, action('Adlandır', async () => {
      const title = prompt('Sohbet adı', chat.title);
      if (title?.trim()) renderState(await request('/api/chats/rename', {id: chat.id, title}));
    }), remove);
    root.appendChild(row);
  });
}

async function newChat() {
  if (busy && !activeStream) return toast('İşlem tamamlanıyor.');
  try {
    renderState(await request('/api/chats/new', {}));
    el('summaryPanel').classList.add('hidden');
    showPage('chat');
  } catch (error) { toast(error.message); }
}

async function openChat(id) {
  if (busy && !activeStream) return toast('İşlem tamamlanıyor.');
  try {
    renderState(await request('/api/chats/open', {id}));
    el('summaryPanel').classList.add('hidden');
    showPage('chat');
  } catch (error) { toast(error.message); }
}

async function deleteChat(id) {
  if (busy && !activeStream) return toast('İşlem tamamlanıyor.');
  if (!confirm('Bu sohbeti silmek istiyor musun?')) return;
  try {
    renderState(await request('/api/chats/delete', {id}));
    el('summaryPanel').classList.add('hidden');
    renderHistory();
  } catch (error) { toast(error.message); }
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
  if (!name) return;
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

function showPendingMessage(text) {
  const log = el('chatLog');
  el('welcome').classList.add('hidden');
  const user = document.createElement('div');
  user.className = 'msg user';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  user.appendChild(bubble);
  const assistant = document.createElement('div');
  assistant.className = 'msg assistant pending-answer';
  const status = document.createElement('div');
  status.className = 'bubble';
  status.textContent = 'EON yanıt hazırlıyor…';
  assistant.appendChild(status);
  log.append(user, assistant);
  log.scrollTop = log.scrollHeight;
  return status;
}

async function send() {
  const input = el('messageInput');
  const text = input.value.trim();
  if (!text || busy) return;
  const isCommand = text.startsWith('/');
  // Clear immediately, not after a slow local model call.
  input.value = '';
  if (!isCommand) return streamAnswer(text);
  const status = null;
  setBusy(true, 'EON yanıt hazırlıyor...');
  try {
    const result = await request('/api/message', {text});
    renderState(result.state);
    if (isCommand) {
      if (result.summary) showSummary(result.summary);
      else if (text.startsWith('/gecmis') || text.startsWith('/geçmiş')) showPage('history');
      else if (text.startsWith('/istatistik') || text.startsWith('/durum')) showPage('settings');
      else if (text.startsWith('/yeniden') || text.startsWith('/yenisohbet')) showPage('chat');
      else toast(result.message);
    }
  } catch (error) {
    // A transport failure does not mean the server did not receive the message.
    // Preserve it visually, without claiming it was successfully sent.
    if (status) {
      status.textContent = 'Yanıt alınamadı. Bağlantıyı kontrol et. Mesajın işlenip işlenmediği belirsiz; tekrar göndermeden önce kontrol et.';
      status.parentElement.classList.add('failed-answer');
    }
    if (!input.value) input.value = text;
    toast(error.message);
  } finally {
    setBusy(false);
    input.focus();
  }
}

async function regenerate() {
  if (busy) return;
  await streamAnswer(null);
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
  el('removeApp').classList.toggle('hidden', !app);
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
  if (!confirm('Uygulama listeden kaldırılsın mı?')) return;
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
  el('newChatButton').addEventListener('click', newChat);
  el('newChatInHistory').addEventListener('click', newChat);
  el('retryConnection').addEventListener('click', reconnect);
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
  el('restoreApps').onclick = async () => {
    try { apps = (await request('/api/apps/restore', {})).apps; renderApps(); }
    catch (error) { toast(error.message); }
  };
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
  wireLibrary();
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
    setConnectionLost(false);
    el('connectionText').textContent = !boot.models.connected ? 'Ollama bağlantısı yok' : installedModels.length ? 'Yerel model hazır' : 'Yerel model bulunamadı';
  } catch (error) { toast('EON yerel sunucusu hazır değil: ' + error.message); }
}
initialize();
