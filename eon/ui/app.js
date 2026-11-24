/* EON v0.4.1 — same-origin client. No external APIs or analytics. */
'use strict';
const el = id => document.getElementById(id);
let csrfToken = '';
const hashParams = new URLSearchParams(location.hash.slice(1));
const launchAccess = hashParams.get('access');
const launchBoot = hashParams.get('boot');
let sessionAccess = launchAccess || '';
try {
  if (launchAccess) sessionStorage.setItem('eon-access', launchAccess);
  else if (!launchBoot) sessionAccess = sessionStorage.getItem('eon-access') || '';
} catch {}
if (launchAccess || launchBoot) history.replaceState(null, '', location.pathname);
let state = null;
let installedModels = [];
let apps = [];
let appsHaveIcons = false;
let busy = false;
let editId = '';
let isCustom = false;
let toastTimeout = null;
let disconnected = false;

function toast(message) {
  const opened = document.querySelector('dialog[open]');
  if (opened) {
    let feedback = opened.querySelector('[role=status]');
    if (!feedback) { feedback = document.createElement('p'); feedback.setAttribute('role','status'); opened.append(feedback); }
    feedback.textContent = String(message);
    return;
  }
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
    options.headers = {...options.headers, 'X-EON-Access':sessionAccess};
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
      throw new Error('EON terminalindeki tam başlatma bağlantısını kullan.');
    }
    throw new Error(result.error || 'İşlem tamamlanamadı.');
  }
  return result;
}

async function reconnect() {
  try {
    const bootUrl = launchBoot ? `/api/bootstrap?boot=${encodeURIComponent(launchBoot)}` : '/api/bootstrap';
    const boot = await request(bootUrl);
    if (boot.access) {
      sessionAccess = boot.access;
      try { sessionStorage.setItem('eon-access', sessionAccess); } catch {}
    }
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
  if (name === 'projects' && typeof renderProjectsPage === 'function') renderProjectsPage();
  if (name === 'kb' && typeof renderKbPage === 'function') renderKbPage();
  if (name === 'studio' && typeof renderStudioPage === 'function') renderStudioPage();
  if (name === 'actions' && typeof renderActionsPage === 'function') renderActionsPage();
  if (name === 'tasks' && typeof renderTasksPage === 'function') renderTasksPage();
  if (name === 'health' && typeof renderHealthPage === 'function') renderHealthPage();
  if (name === 'apps') {
    renderApps();
    if (!appsHaveIcons) request('/api/apps').then(result=>{
      appsHaveIcons=true;apps=result.apps;renderApps();
    }).catch(error=>toast(error.message));
  }
  if (name === 'chat') el('messageInput').focus();
}

function renderState(newState) {
  switchDraft(newState);
  state = newState;
  renderWorkspace();
  renderHybrid();
  el("undoChat").hidden = !state.undo_available;
  document.querySelectorAll('.storageStatus').forEach(node => node.textContent = state.storage);
  renderNotes();
  if (typeof renderProjectsPage === 'function' && el('view-projects')?.classList.contains('active-page')) renderProjectsPage();
  if (typeof renderKbPage === 'function' && el('view-kb')?.classList.contains('active-page')) renderKbPage();
  if (typeof renderStudioPage === 'function' && el('view-studio')?.classList.contains('active-page')) renderStudioPage();
  if (typeof renderActionsPage === 'function' && el('view-actions')?.classList.contains('active-page')) renderActionsPage();
  if (typeof renderTasksPage === 'function' && el('view-tasks')?.classList.contains('active-page')) renderTasksPage();
  if (!el('view-settings').classList.contains('active-page')) fillPreferences();
  if (!activeStream || el("chatLog").dataset.chat !== state.active_chat_id) renderChat();
  renderHistory();
  renderStats();
  document.querySelectorAll('[data-style]').forEach(btn => btn.classList.toggle('selected', btn.dataset.style === state.style));
  ['settingsModelSelect'].forEach(id => {
    const select = el(id);
    if (select && Array.from(select.options).some(opt => opt.value === state.model)) select.value = state.model;
  });
  if (typeof syncUnifiedModelSelect === 'function') syncUnifiedModelSelect();
  if (typeof renderHardwareAndSetupBanner === 'function') renderHardwareAndSetupBanner();
}

function renderChat() {
  if (!state) return;
  const sameChat = el("chatLog").dataset.chat === state.active_chat_id;
  el("chatLog").dataset.chat = state.active_chat_id;
  const history = state.history || [];
  el('welcome').classList.toggle('hidden', history.length > 0);
  const log = el('chatLog');
  const top = log.scrollTop;
  const follow = !sameChat || log.scrollHeight - top - log.clientHeight < 120;
  const old = [...log.children];
  let keep = 0;
  while (sameChat && keep < history.length && old[keep]?.messageText === history[keep].content &&
         old[keep]?.messageStar === state.stars.includes(keep) && !old[keep]?.isLast) keep++;
  while (log.children.length > keep) log.lastElementChild.remove();
  history.forEach((entry, index) => {
    if (index < keep) return;
    const msg = document.createElement('div');
    msg.messageText = entry.content;
    msg.messageStar = state.stars.includes(index);
    msg.isLast = index === history.length - 1;
    msg.dataset.index = index;
    msg.className = 'msg ' + (entry.role === 'user' ? 'user' : 'assistant');
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    if (entry.role === 'assistant') markdown(bubble, entry.content);
    else bubble.textContent = entry.content;
    msg.appendChild(bubble);
    const sourcesForMsg = state.chat_sources?.[String(index)];
    if (entry.role === 'assistant' && Array.isArray(sourcesForMsg) && sourcesForMsg.length) {
      const srcBox = document.createElement('div');
      srcBox.className = 'citations-bar';
      const head = document.createElement('small');
      head.textContent = 'Kaynaklar: ';
      srcBox.appendChild(head);
      sourcesForMsg.forEach(src => {
        if (src.kind === 'web' && src.uri) {
          const a = document.createElement('a');
          a.href = src.uri;
          a.target = '_blank';
          a.rel = 'noopener noreferrer';
          a.className = 'citation-chip web';
          a.textContent = src.title || src.uri;
          srcBox.appendChild(a);
        } else {
          const chip = document.createElement('button');
          chip.type = 'button';
          chip.className = 'citation-chip doc';
          const loc = src.page ? `Sayfa ${src.page}` : (src.section || '');
          chip.textContent = `${src.title}${loc ? ' · ' + loc : ''}`;
          chip.title = 'Belge kaynağını ve tam metin bölümünü görüntüle';
          chip.onclick = () => {
            if (typeof inspectKnowledgeCitation === 'function' && src.doc_id) inspectKnowledgeCitation(src.doc_id, src.chunk_index || 0);
            else showPage('kb');
          };
          srcBox.appendChild(chip);
        }
      });
      msg.appendChild(srcBox);
    }
    const actionCard = state.chat_action_cards?.[String(index)];
    if (entry.role === 'assistant' && actionCard && actionCard.token) {
      const card = document.createElement('div');
      card.className = 'pending-confirm-box inline-action-card';
      const title = document.createElement('strong');
      title.textContent = `Önerilen Eylem Planı: ${actionCard.title} (${actionCard.risk.toUpperCase()})`;
      const desc = document.createElement('p');
      desc.textContent = actionCard.change_summary;
      card.append(title, desc);
      const steps = Array.isArray(actionCard.steps) && actionCard.steps.length ? actionCard.steps : [actionCard];
      const approve = action(steps.length > 1 ? `Tüm Planı Onayla ve Uygula (${steps.length} Adım)` : 'Onayla ve Uygula', async () => {
        let lastState = state;
        for (const st of steps) {
          const res = await request('/api/actions', {action:'confirm', token:st.token, approve:true});
          lastState = res.state;
        }
        delete lastState.chat_action_cards[String(index)];
        renderState(lastState);
        toast('Ajan eylem planı onaylandı ve sırayla uygulandı.');
      });
      const cancel = action('İptal', async () => {
        let lastState = state;
        for (const st of steps) {
          const res = await request('/api/actions', {action:'confirm', token:st.token, approve:false});
          lastState = res.state;
        }
        delete lastState.chat_action_cards[String(index)];
        renderState(lastState);
        toast('Eylem planı iptal edildi.');
      });
      card.append(approve, cancel);
      msg.appendChild(card);
    }
    const tools = document.createElement('div');
    tools.className = 'reply-actions';
    const starred = state.stars.includes(index);
    const chatId = state.active_chat_id;
    if (entry.role === 'assistant') {
      tools.append(action('Seslendir',()=>speakText(entry.content)));
      tools.append(action('Kopyala', () => navigator.clipboard.writeText(entry.content)));
      if (entry.content.length > 180 || entry.content.includes('```')) {
        tools.append(action('Canvas', () => typeof openCanvasDrawer === 'function' ? openCanvasDrawer(entry.content, currentChat()?.title || 'Canvas') : openInStudio(entry.content)));
      }
      tools.append(action('Stüdyo',()=>openInStudio(entry.content)));
    } else {
      tools.append(action('Kopyala', () => navigator.clipboard.writeText(entry.content)));
      tools.append(action('Düzenle', async () => {
        if (busy) return;
        const value = prompt('Bu mesajdan sonraki yanıtlar yeniden oluşturulacak.', entry.content);
        if (value?.trim()) await streamAnswer(value.trim(), index);
      }));
    }
    tools.append(action(starred ? '★' : '☆', () =>
      library('star', {id:chatId, index, revision:state.revision, on:!starred})));
    tools.append(action('Sil', async()=>{
      if (confirm('Bu mesaj ve eşleşen yanıt silinsin mi?')) await extra({kind:'delete_message',id:chatId,index,revision:state.revision});
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
  log.scrollTop = follow ? log.scrollHeight : top;
}

function renderHistory() {
  const query = el('chatSearch').value.trim();
  const selected = el('projectFilter').value;
  if (query || el('favoritesOnly').checked || selected !== '*') {
    scheduleSearch(query, selected);
    return;
  }
  cancelSearch();
  const root = el('historyList');
  root.replaceChildren();
  const conversations = [...(state?.conversations || [])].sort((a,b) => Number(b.pinned)-Number(a.pinned));
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
    name.textContent = (chat.pinned ? '★ ' : '') + chat.title;
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
    row.append(open, action(chat.pinned ? 'Sabitlemeyi kaldır' : 'Sabitle',
      () => library('pin', {id:chat.id, on:!chat.pinned})), action('Adlandır', async () => {
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
  modelOptions(el('settingsModelSelect'), installedModels, state.model);
  if (typeof syncUnifiedModelSelect === 'function') syncUnifiedModelSelect();
  const hasCloud = Boolean(state.cloud_model && state.cloud_allowed);
  el('connection').classList.toggle('connected', Boolean(hasCloud || (result.connected && installedModels.length)));
  if (!hasCloud) {
    el('connectionText').textContent = !result.connected ? 'Hazır' : installedModels.length ? 'Yerel model hazır' : 'Hazır';
  }
}

async function changeModel(name) {
  if (!name) return;
  try {
    if (name.startsWith('models/gemini-')) {
      if (!state?.gemini_configured && !state?.gemini_models_ready && !state?.cloud_model) {
        showPage('settings');
        el('directApiKeyInput')?.focus();
        if (typeof syncUnifiedModelSelect === 'function') syncUnifiedModelSelect();
        toast('Gemini modelini kullanmak için Google Gemini API anahtarını kaydet.');
        return;
      }
      const updated = await request('/api/cloud/new', {
        id: (state.cloud_model || !state.history?.length) ? state.active_chat_id : null,
        model: name,
        consent: true,
      });
      renderState(updated);
      toast('Model seçildi: ' + (typeof formatGeminiModelLabel === 'function' ? formatGeminiModelLabel(name) : name.replace('models/', '')));
      return;
    }
    const updated = await request('/api/model', {model: name});
    renderState(updated);
    toast('Yerel model seçildi: ' + name);
  } catch (error) {
    toast(error.message);
    if (typeof syncUnifiedModelSelect === 'function') syncUnifiedModelSelect();
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
    const result = await request('/api/summary', {id:state.active_chat_id, destination:state.cloud_model || 'ollama'});
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
  const favorites = state?.extras.favorite_apps || [];
  const query = el('appSearch').value.trim().toLocaleLowerCase('tr');
  [...apps].sort((a,b)=>Number(favorites.includes(b.id))-Number(favorites.includes(a.id))).filter(
    app=>app.name.toLocaleLowerCase('tr').includes(query)).forEach(app => {
    const card = document.createElement('div');
    card.className = 'app-card';
    card.dataset.id = app.id;
    const icon = document.createElement('div');
    icon.className = 'app-icon';
    drawAppIcon(icon, app);
    const meta = document.createElement('div');
    meta.className = 'app-meta';
    const title = document.createElement('strong');
    title.textContent = app.name;
    const status = document.createElement('small');
    status.textContent = app.ready ? app.source === 'saved' ? 'Kaydedildi · Hazır' : 'Otomatik bulundu · Hazır' : 'Yol eklenmedi';
    meta.append(title, status);
    if (app.path) { const path = document.createElement("small"); path.textContent = app.path; path.className = "launch-path"; meta.append(path); }
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
    buttons.append(action(favorites.includes(app.id) ? '★' : '☆',async()=>{
      await extra({kind:'app_favorite',id:app.id});renderApps();
    }),open, edit);
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
    const {target} = await request('/api/apps/target', {id});
    if (!confirm('Bu uygulama açılsın mı?\n'+target)) return;
    await request('/api/apps/launch', {id,target});
    const app = apps.find(item => item.id === id);
    toast((app?.name || 'Uygulama') + ' başlatma isteği Windows’a gönderildi.');
  } catch (error) { toast(error.message); }
}

function openAppModal(app) {
  el('iconChoices').hidden = !app;
  el('iconFile').value = '';
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
    if (btn.dataset.action === 'livevoice') {
      if (typeof openLiveVoiceOverlay === 'function') openLiveVoiceOverlay();
      return;
    }
    if (btn.dataset.action === 'apps') return showPage('apps');
    if (btn.dataset.action === 'kb') return showPage('kb');
    if (btn.dataset.action === 'studio') return showPage('studio');
    showPage('chat');
    el('messageInput').value = btn.dataset.action === 'math' ? '/hesap ' : 'Python ile şu konuda kod yaz: ';
    el('messageInput').dispatchEvent(new Event('input'));
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
  wireHybrid();
  wireStudio();
  wireWorkspace();
  try {
    const bootUrl = launchBoot ? `/api/bootstrap?boot=${encodeURIComponent(launchBoot)}` : '/api/bootstrap';
    const boot = await request(bootUrl);
    if (boot.access) {
      sessionAccess = boot.access;
      try { sessionStorage.setItem('eon-access', sessionAccess); } catch {}
    }
    csrfToken = boot.token;
    state = boot.state;
    apps = boot.apps || [];
    renderState(state);
    renderApps();
    installedModels = boot.models.models || [];
    modelOptions(el('settingsModelSelect'), installedModels, boot.models.selected);
    if (typeof syncUnifiedModelSelect === 'function') syncUnifiedModelSelect();
    el('connection').classList.toggle('connected', Boolean(state.cloud_model || (boot.models.connected && installedModels.length)));
    setConnectionLost(false);
    el('connectionText').textContent = state.cloud_model
      ? (typeof formatGeminiModelLabel === 'function' ? formatGeminiModelLabel(state.cloud_model) : 'Gemini hazır')
      : 'Hazır';
    // Non-blocking background discovery of local Ollama models so UI startup is instant
    setTimeout(() => { loadModels().catch(() => {}); }, 80);
  } catch (error) { toast('EON yerel sunucusu hazır değil: ' + error.message); }
}
initialize();
