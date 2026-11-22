'use strict';

let activeStream = null;
function action(label, handler) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'text-button';
  button.textContent = label;
  button.onclick = async () => {
    try { await handler(); } catch (error) { toast(error.message); }
  };
  return button;
}

// Model output is rendered exclusively through text nodes and fixed elements.
function markdown(root, text) {
  let code = null;
  let list = null;
  for (const line of text.split('\n')) {
    if (/^\s*```/.test(line)) {
      if (code) code = null;
      else {
        const pre = document.createElement('pre');
        code = document.createElement('code');
        pre.append(code);
        root.append(pre);
      }
      list = null;
      continue;
    }
    if (code) { code.append(line + '\n'); continue; }
    const bullet = /^[-*] (.*)/.exec(line);
    const heading = /^(#{1,6}) (.*)/.exec(line);
    const node = document.createElement(bullet ? 'li' : heading ? 'h4' : 'div');
    if (bullet) {
      if (!list) { list = document.createElement('ul'); root.append(list); }
      list.append(node);
    } else { list = null; root.append(node); }
    for (const part of (bullet?.[1] ?? heading?.[2] ?? line).split(/(\*\*[^*]+\*\*|`[^`]+`)/g)) {
      if (part.startsWith('**') && part.endsWith('**')) {
        const strong = document.createElement('strong');
        strong.textContent = part.slice(2,-2);
        node.append(strong);
      } else if (part.startsWith('`') && part.endsWith('`') && part.length > 1) {
        const inline = document.createElement('code');
        inline.textContent = part.slice(1,-1);
        node.append(inline);
      } else node.append(part);
    }
    if (!line) node.append(document.createElement('br'));
  }
}

async function streamAnswer(text, index = null) {
  if (busy) return;
  const id = state.active_chat_id;
  const key = crypto.randomUUID();
  const status = showPendingMessage(text ?? state.history.at(-2)?.content ?? '');
  activeStream = key;
  setBusy(true, 'Yanıt hazırlanıyor…');
  let completed = false;
  try {
    const response = await fetch('/api/stream', {method:'POST',
      headers:{'Content-Type':'application/json','X-EON-Token':csrfToken},
      body:JSON.stringify({key, id, text, index})});
    if (!response.ok) throw new Error('Sohbet bağlantısı kurulamadı. Yeniden bağlanmayı dene.');
    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    let pending = '';
    let first = true;
    try {
      while (true) {
        const {value, done} = await reader.read();
        if (done) break;
        pending += value;
        const lines = pending.split('\n');
        pending = lines.pop();
        for (const line of lines) {
          const event = JSON.parse(line);
          if (event.ready) el('stop').classList.remove('hidden');
          if (event.error) throw new Error(event.error);
          if (event.delta) {
            if (first) { status.replaceChildren(); first = false; }
            status.append(event.delta);
            const log = el('chatLog');
            if (log.scrollHeight - log.scrollTop - log.clientHeight < 120) log.scrollTop = log.scrollHeight;
          }
          if (event.state) {
            completed = true;
            if (state.active_chat_id === id && event.state.active_chat_id === id) renderState(event.state);
          }
        }
      }
    } finally { reader.releaseLock(); }
    if (!completed) throw new Error('Yanıt akışı kesildi. Sohbeti yeniden açıp kontrol et.');
  } catch (error) {
    if (text && state.active_chat_id === id && !el('messageInput').value) el('messageInput').value = text;
    if (error instanceof TypeError) setConnectionLost(true);
    toast(error instanceof TypeError ? 'Yerel sunucuya ulaşılamadı. Yeniden bağlanmayı dene.' : error.message);
  } finally {
    activeStream = null;
    el('stop').classList.add('hidden');
    setBusy(false);
    renderChat();
  }
}

function fillPreferences() {
  el('instructions').value = state.instructions;
  el('contextLimit').value = state.context;
  el('outputLimit').value = state.output;
}
function renderNotes() {
  const root = el('notes');
  root.replaceChildren();
  for (const [id,value] of Object.entries(state.memory)) {
    const row = document.createElement('div');
    row.className = 'note-row';
    const body = document.createElement('span');
    body.textContent = value;
    row.append(body, action('Düzenle', async () => {
      const changed = prompt('Hafıza kaydını düzenle', value);
      if (changed?.trim()) renderState(await request('/api/memory', {id,value:changed}));
    }), action('Sil', async () => {
      if (confirm('Hafıza kaydı silinsin mi?')) renderState(await request('/api/memory', {id,value:null}));
    }));
    root.append(row);
  }
}

function wireLibrary() {
  const bind = (id, fn) => el(id).onclick = async () => {
    try { await fn(); } catch (error) { toast(error.message); }
  };
  el('chatSearch').oninput = renderHistory;
  bind('stop', () => request('/api/stop', {key:activeStream}));
  bind('savePrefs', async () => {
    renderState(await request('/api/preferences', {instructions:el('instructions').value,
      context:el('contextLimit').valueAsNumber, output:el('outputLimit').valueAsNumber}));
    toast('Model tercihleri güncellendi.');
  });
  bind('addNote', async () => {
    renderState(await request('/api/memory', {value:el('newNote').value}));
    el('newNote').value = '';
  });
  const format = new Intl.DateTimeFormat(undefined, {day:'numeric', month:'short',hour:'2-digit',minute:'2-digit'});
  let timer;
  function tick() {
    clearTimeout(timer);
    if (document.hidden) return;
    el('clock').textContent = format.format(new Date());
    timer = setTimeout(tick, 60000 - Date.now() % 60000);
  }
  tick();
  document.addEventListener('visibilitychange', () => { tick(); if (!document.hidden && disconnected) reconnect(); });
  window.addEventListener('online', () => { if (disconnected) reconnect(); });
  document.addEventListener('keydown', e => {
    if (e.ctrlKey && e.altKey && e.code === 'KeyN') { e.preventDefault(); newChat(); }
    if (e.key === 'Escape' && activeStream) el('stop').click();
  });
  let weatherVersion = 0;
  el('weatherConsent').onchange = () => {
    weatherVersion++;
    el('weatherRead').disabled = !el('weatherConsent').checked;
    el('forecast').textContent = el('weatherConsent').checked ? 'Hava verisi bekleniyor' : 'Hava durumu kapalı';
  };
  bind('weatherRead', async () => {
    const version = ++weatherVersion;
    const report = await request('/api/weather', {consent:el('weatherConsent').checked,
      lat:el('lat').valueAsNumber, lon:el('lon').valueAsNumber});
    if (version === weatherVersion) el('forecast').textContent = report.label;
  });
}
