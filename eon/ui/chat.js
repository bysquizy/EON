'use strict';

let activeStream = null;
let pendingVisionImages = [];

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
  const lines = text.split('\n');
  for (let i=0; i<lines.length; i++) {
    const line=lines[i];
    if (!code && line.includes('|') && /^\s*\|?\s*:?-{3,}/.test(lines[i+1] || '')) {
      const table = document.createElement('table');
      const headers = line.trim().replace(/^\||\|$/g,'').split('|');
      const addRow = (values,tag) => {
        const row=table.insertRow();
        for(const value of values.slice(0,24)) {
          const cell=document.createElement(tag); cell.textContent=value.trim();row.append(cell);
        }
      };
      addRow(headers,'th'); i++;
      while(lines[i+1]?.includes('|')) addRow(lines[++i].trim().replace(/^\||\|$/g,'').split('|'),'td');
      const wrap=document.createElement('div');wrap.className='table-scroll';wrap.append(table);root.append(wrap);
      list=null;continue;
    }
    const fence = /^\s*```([A-Za-z0-9_+#.-]{0,24})/.exec(line);
    if (fence) {
      if (code) code = null;
      else {
        const lang = (fence[1] || 'code').toLowerCase();
        const header = document.createElement('div');
        header.className = 'code-header';
        const badge = document.createElement('span');
        badge.className = 'code-lang';
        badge.textContent = lang;
        const pre = document.createElement('pre');
        code = document.createElement('code');
        const block = code;
        header.append(badge, action('Kodu kopyala', () => {
          navigator.clipboard.writeText(block.textContent.replace(/\n$/, ''));
          toast('Kod panoya kopyalandı.');
        }));
        pre.append(code);
        root.append(header, pre);
      }
      list = null;
      continue;
    }
    if (code) {
      for(const token of line.split(/(\b(?:def|class|return|if|else|elif|for|while|function|const|let|var|async|await|import|from|export|try|catch|finally|True|False|None|null|undefined|SELECT|FROM|WHERE)\b)/g)) {
        if (/^(def|class|return|if|else|elif|for|while|function|const|let|var|async|await|import|from|export|try|catch|finally|True|False|None|null|undefined|SELECT|FROM|WHERE)$/.test(token)) {
          const mark=document.createElement('span');mark.className='code-keyword';mark.textContent=token;code.append(mark);
        } else code.append(token);
      }
      code.append('\n');continue;
    }
    const bullet = /^(?:[-*]|\d+\.) (.*)/.exec(line);
    const ordered = /^\d+\. /.test(line);
    const quote = /^> ?(.*)/.exec(line);
    const heading = /^(#{1,6}) (.*)/.exec(line);
    const node = document.createElement(bullet ? 'li' : heading ? 'h4' : quote ? 'blockquote' : 'div');
    if (bullet) {
      if (!list || list.tagName !== (ordered ? 'OL' : 'UL')) { list = document.createElement(ordered ? 'ol' : 'ul'); root.append(list); }
      list.append(node);
    } else { list = null; root.append(node); }
    for (const part of (bullet?.[1] ?? heading?.[2] ?? quote?.[1] ?? line).split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]{1,200}\]\([^\s)]{1,1024}\)|\$[^$]{1,200}\$)/g)) {
      const link=/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/i.exec(part);
      if(link) {
        let url; try {url=new URL(link[2]);} catch {}
        if (url && !url.username && !url.password && (url.protocol==='https:' || url.protocol==='http:')) {
          const anchor=document.createElement('a');anchor.href=url.href;anchor.target='_blank';
          anchor.rel='noopener noreferrer';anchor.textContent=link[1];node.append(anchor);continue;
        }
      }
      if(part.startsWith('$') && part.endsWith('$') && part.length>2) {
        const math=document.createElement('span');math.className='math-inline';
        math.textContent=part.slice(1,-1).replaceAll('\\times','×').replaceAll('\\cdot','·').replaceAll('\\pm','±');
        node.append(math);continue;
      }
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
  let queuedText = '', frame = 0, first = true;
  function flush() {
    frame = 0;
    if (!queuedText || !status.isConnected) { queuedText = ''; return; }
    const log = el('chatLog');
    const follow = log.scrollHeight - log.scrollTop - log.clientHeight < 120;
    if (first) { status.replaceChildren(); first = false; }
    status.append(queuedText);
    queuedText = '';
    if (follow) log.scrollTop = log.scrollHeight;
  }
  try {
    const research = el('researchToggle')?.getAttribute('aria-pressed') === 'true';
    const profile = el('profileSelect')?.value || 'balanced';
    const imagesToSend = pendingVisionImages.map(img => ({mime: img.mime, data: img.data}));
    pendingVisionImages = [];
    if (typeof renderVisionBar === 'function') renderVisionBar();
    const response = await fetch('/api/stream', {method:'POST',
      headers:{'Content-Type':'application/json','X-EON-Token':csrfToken,'X-EON-Access':sessionAccess},
      body:JSON.stringify({key, id, text, index, destination:state.cloud_model || "ollama",
        images: imagesToSend.length ? imagesToSend : undefined, research, profile})});
    if (!response.ok) throw new Error('Sohbet bağlantısı kurulamadı. Yeniden bağlanmayı dene.');
    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    let pending = '';

    try {
      let sentenceBuf = '';
      const liveVoice = el('liveVoiceToggle')?.getAttribute('aria-pressed') === 'true';
      if (liveVoice && typeof stopVoicePlayback === 'function') stopVoicePlayback();
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
            queuedText += event.delta;
            if (!frame) frame = requestAnimationFrame(flush);
            if (liveVoice && typeof enqueueLiveSentence === 'function') {
              sentenceBuf += event.delta;
              const match = /^([\s\S]{18,}?[.!?…]+(?:\s+|\n|$))([\s\S]*)$/.exec(sentenceBuf);
              if (match) {
                enqueueLiveSentence(match[1].trim());
                sentenceBuf = match[2];
              }
            }
          }
          if (event.state) {
            completed = true;
            if (liveVoice && sentenceBuf.trim() && typeof enqueueLiveSentence === 'function') {
              enqueueLiveSentence(sentenceBuf.trim());
              sentenceBuf = '';
            }
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
    cancelAnimationFrame(frame);
    activeStream = null;
    el('stop').classList.add('hidden');
    setBusy(false);
    const log = el('chatLog');
    const top = log.scrollTop;
    const preserve = log.scrollHeight - top - log.clientHeight > 120;
    renderChat();
    if (preserve) log.scrollTop = top;
  }
}

function fillPreferences() {
  el('instructions').value = state.instructions;
  el('contextLimit').value = state.context;
  el('outputLimit').value = state.output;
}
function renderNotes() {
  const root = el('notes');
  if (!root) return;
  root.replaceChildren();
  const scopeSelect = el('memoryProjectScope');
  if (scopeSelect) {
    const prev = scopeSelect.value;
    scopeSelect.replaceChildren(new Option('Genel (Projesiz)', ''), ...Object.entries(state.projects || {}).map(([k, v]) => new Option(v.name, k)));
    if ([...scopeSelect.options].some(o => o.value === prev)) scopeSelect.value = prev;
  }
  const metaMap = state.memory_meta || {};
  for (const [id,value] of Object.entries(state.memory)) {
    const m = metaMap[id] || {};
    const searchVal = el('memorySearch')?.value.trim().toLocaleLowerCase('tr') || '';
    const searchable = (value + ' ' + (m.category || '') + ' ' + (state.projects?.[m.project]?.name || '')).toLocaleLowerCase('tr');
    if (searchVal && !searchable.includes(searchVal)) continue;
    const row = document.createElement('div');
    row.className = 'note-row';
    const body = document.createElement('div');
    body.className = 'note-body';
    const txt = document.createElement('span');
    txt.textContent = value;
    const badgeWrap = document.createElement('small');
    badgeWrap.className = 'note-meta-badges';
    const projName = m.project && state.projects?.[m.project] ? state.projects[m.project].name : 'Genel';
    const createdStr = m.created_at ? new Date(m.created_at * 1000).toLocaleDateString() : '';
    const usedStr = m.last_used_at ? ' · Son kullanım: ' + new Date(m.last_used_at * 1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : '';
    badgeWrap.textContent = `[${m.category || 'genel'} · ${projName} · Kaynak: ${m.source || 'kullanıcı'}${createdStr ? ' · ' + createdStr : ''}${usedStr}]`;
    body.append(txt, badgeWrap);
    row.append(body, action('Düzenle', async () => {
      const changed = prompt('Hafıza kaydını düzenle', value);
      if (changed?.trim()) renderState(await request('/api/memory', {id, value:changed, category:m.category, project:m.project}));
    }), action('Sil', async () => {
      if (confirm('Hafıza kaydı silinsin mi?')) renderState(await request('/api/memory', {id, value:null}));
    }));
    root.append(row);
  }
}

function showMemoryConflict(conflictData) {
  const box = el('memoryConflictBox');
  if (!box) return;
  box.replaceChildren();
  box.classList.remove('hidden');
  const title = document.createElement('strong');
  title.textContent = 'Çelişen veya benzer hafıza kaydı tespit edildi:';
  box.append(title);
  for (const item of conflictData.conflicts) {
    const p = document.createElement('p');
    p.textContent = `Mevcut: "${item.value}" (${item.reason}) ↔ Yeni: "${conflictData.proposed}"`;
    const replaceBtn = action('Mevcut kaydı bununla değiştir', async () => {
      box.classList.add('hidden');
      renderState(await request('/api/memory', {
        value: conflictData.proposed,
        category: conflictData.category,
        source: conflictData.source,
        project: conflictData.project,
        replace_id: item.id,
        force: true,
      }));
      el('newNote').value = '';
      toast('Hafıza kaydı güncellendi.');
    });
    box.append(p, replaceBtn);
  }
  const keepBoth = action('Her ikisini de ayrı kayıt olarak tut', async () => {
    box.classList.add('hidden');
    renderState(await request('/api/memory', {
      value: conflictData.proposed,
      category: conflictData.category,
      source: conflictData.source,
      project: conflictData.project,
      force: true,
    }));
    el('newNote').value = '';
    toast('Yeni hafıza kaydı eklendi.');
  });
  const cancelBtn = action('İptal (Mevcut kaydı koru)', () => box.classList.add('hidden'));
  box.append(keepBoth, cancelBtn);
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
    const category = el('memoryCategory')?.value || 'genel';
    const project = el('memoryProjectScope')?.value || '';
    const res = await request('/api/memory', {value:el('newNote').value, category, project, source:'kullanıcı'});
    renderState(res);
    if (res.memory_conflict) {
      showMemoryConflict(res.memory_conflict);
    } else {
      el('memoryConflictBox')?.classList.add('hidden');
      el('newNote').value = '';
    }
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
    if (e.key === 'Escape' && activeStream && !document.querySelector('dialog[open]')) el('stop').click();
  });
}
