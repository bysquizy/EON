'use strict';

const drafts = new Map();
let displayedChat = '';
let searchTimer, searchVersion = 0;

function switchDraft(next) {
  if (next.active_chat_id === displayedChat) return;
  const input = el('messageInput');
  if (displayedChat && input.value) drafts.set(displayedChat, input.value);
  else drafts.delete(displayedChat);
  const valid = new Set(next.conversations.map(chat => chat.id));
  for (const key of drafts.keys()) if (!valid.has(key)) drafts.delete(key);
  displayedChat = next.active_chat_id;
  input.value = drafts.get(displayedChat) || '';
}

function options(select, entries, selected) {
  select.replaceChildren(...entries.map(([id,name]) => new Option(name,id)));
  select.value = selected;
  if (select.selectedIndex < 0) select.selectedIndex = 0;
}
function renderWorkspace() {
  const root = document.documentElement;
  for (const [key,value] of Object.entries(state.look)) {
    root.dataset[key] = String(value);
    if (typeof value === 'boolean') el(key).checked = value;
    else el(key).value = value;
  }
  const filter = el('projectFilter');
  options(filter, [['*','Tüm projeler'],['','Projesiz'], ...named(state.projects)], filter.options.length ? filter.value : '*');
  const chat = currentChat();
  el('chatOptions').textContent = [state.projects[chat.project]?.name, state.modes[chat.mode]?.name].filter(Boolean).join(' · ') + ' ▾';
}
function currentChat() { return state.conversations.find(chat => chat.id === state.active_chat_id); }
function named(records) { return Object.entries(records).map(([key,value]) => [key,value.name]); }
async function library(kind, data) { renderState(await request('/api/library/' + kind, data)); }

function cancelSearch() {
  clearTimeout(searchTimer);
  searchVersion++;
}
function scheduleSearch(query, selected) {
  cancelSearch();
  const version = searchVersion;
  const favorites = el('favoritesOnly').checked;
  searchTimer = setTimeout(async () => {
    try {
      const {results} = await request('/api/search', {query, project:selected === '*' ? null : selected, favorites});
      if (version !== searchVersion) return;
      const root = el('historyList');
      root.replaceChildren();
      for (const hit of results) {
        const button = action((hit.pinned ? '★ ' : '') + hit.title, async () => {
          await openChat(hit.id);
          if (state.active_chat_id === hit.id && hit.index !== null) {
            const message = el('chatLog').querySelector('[data-index="' + hit.index + '"]');
            message?.scrollIntoView({block:'center'});
          }
        });
        button.className = 'search-hit';
        if (hit.index !== null) {
          const snippet = document.createElement('small');
          snippet.textContent = hit.snippet;
          button.append(snippet);
        }
        root.append(button);
      }
      if (!results.length) root.textContent = 'Eşleşme bulunamadı.';
      if (results.length === 100) root.append('İlk 100 sonuç gösteriliyor. Aramayı daraltabilirsin.');
    } catch (error) { if (version === searchVersion) toast(error.message); }
  }, 170);
}

function dialog(title) {
  el('libraryTitle').textContent = title;
  const body = el('libraryBody');
  body.replaceChildren();
  el('libraryDialog').querySelector('[role=status]')?.remove();
  if (!el('libraryDialog').open) el('libraryDialog').showModal();
  return body;
}
function field(body, label, tag) {
  const wrap = document.createElement('label');
  wrap.textContent = label;
  const node = document.createElement(tag);
  node.className = 'field';
  wrap.append(node);
  body.append(wrap);
  return node;
}
function manage(kind) {
  const project = kind === 'project';
  const records = project ? state.projects : Object.fromEntries(Object.entries(state.modes)
    .filter(([key]) => !['general','code','study','write'].includes(key)));
  const body = dialog(project ? 'Projeleri yönet' : 'Özel modları yönet');
  const select = field(body, project ? 'Proje' : 'Mod', 'select');
  options(select, [['','Yeni oluştur'], ...named(records)], '');
  const name = field(body,'Ad','input');
  name.maxLength = 64;
  const instructions = field(body,'Yönergeler','textarea');
  instructions.maxLength = 480;
  const remove = action('Sil', async () => {
    const message = project ? 'Proje silinsin mi? Sohbetleri Projesiz altında kalacak.' : 'Mod silinsin mi? Bağlı sohbetler Genel Asistan moduna dönecek.';
    if (confirm(message)) { await library(kind,{id:select.value, delete:true}); manage(kind); }
  });
  remove.disabled = true;
  select.onchange = () => {
    const record = records[select.value];
    name.value = record?.name || '';
    instructions.value = record?.instructions || '';
    remove.disabled = !record;
  };
  body.append(action('Kaydet', async () => {
    await library(kind, {id:select.value, name:name.value, instructions:instructions.value});
    el('libraryDialog').close();
  }), remove);
  if (kind==='project') body.append(action('Proje modeli ve hafızası',()=>projectOptions(select.value)));
}
function chatOptions() {
  const chat = currentChat();
  const body = dialog('Sohbet seçenekleri');
  const project = field(body,'Proje','select');
  options(project, [['','Projesiz'], ...named(state.projects)], chat.project);
  const mode = field(body,'Mod','select');
  options(mode,named(state.modes),chat.mode);
  const local = field(body,'Sohbetin yerel modeli','select');
  const profile = field(body,'Çalışma profili','select');
  const length = field(body,'Yanıt uzunluğu','select');
  const opts=state.extras.chat_options[chat.id] || {};
  options(local,[['','Proje veya genel seçim'],...installedModels.map(name=>[name,name])],opts.model||'');
  options(profile,[['balanced','Dengeli'],['fast','Hızlı'],['deep','Derin Düşünme']],opts.profile||'balanced');
  options(length,[['','Genel ayar'],['kisa','Kısa'],['normal','Normal'],['detayli','Detaylı']],opts.style||'');
  body.append(action('Uygula', async () => {
    await library('configure',{id:chat.id, project:project.value, mode:mode.value});
    await extra({kind:'chat',id:chat.id,model:local.value,style:length.value,profile:profile.value});
    el('libraryDialog').close();
  }), action('Studio ile DOCX/PDF/XLSX üret', () => {
    el('libraryDialog').close();
    const lastReply = [...(state.history || [])].reverse().find(m => m.role === 'assistant');
    if (typeof openInStudio === 'function') openInStudio(lastReply?.content || '', chat.title);
    else showPage('studio');
  }), action('Pano yardımcısı', clipboardDialog), action('Markdown indir',()=>downloadChat('md')),
      action('Metin indir',()=>downloadChat('txt')));
}
function downloadChat(ext) {
  if (!confirm('Sohbet şifrelenmemiş bir dosya olarak bu cihaza indirilecek. Devam edilsin mi?')) return;
  const title = currentChat().title;
  const lines = [ext === 'md' ? '# ' + title : title, ''];
  for (const entry of state.history) {
    const name = entry.role === 'user' ? 'Sen' : 'EON';
    lines.push(ext === 'md' ? '## ' + name : name, '', entry.content, '');
  }
  const url = URL.createObjectURL(new Blob([lines.join('\n')], {type:'text/plain;charset=utf-8'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'EON-' + title.replace(/[^\p{L}\p{N} _-]/gu,'').trim().slice(0,64) + '.' + ext;
  link.click();
  setTimeout(()=>URL.revokeObjectURL(url), 1000);
}
function clipboardDialog() {
  const body = dialog('Pano yardımcısı');
  const task = field(body,'İşlem','select');
  options(task,[['Özetle','Özetle'],['Düzelt','Düzelt'],['Açıkla','Açıkla'],['Çevir','Çevir']], 'Özetle');
  const language = field(body,'Hedef dil','input');
  language.value = 'Türkçe';
  language.maxLength = 40;
  language.parentElement.hidden = true;
  task.onchange = () => { language.parentElement.hidden = task.value !== 'Çevir'; };
  body.append(action('Panoyu oku ve taslağa al', async () => {
    const prompt = task.value === 'Çevir' ? 'Şu dile çevir: ' + language.value.trim() : task.value;
    if (task.value === 'Çevir' && !language.value.trim()) throw new Error('Hedef dili gir.');
    const id = state.active_chat_id;
    let text;
    try { text = await navigator.clipboard.readText(); }
    catch { throw new Error('Pano okunamadı. Tarayıcı iznini kontrol et veya metni mesaj alanına yapıştır.'); }
    if (!text.trim()) throw new Error('Panoda metin bulunamadı.');
    const draft = prompt + '\n\n' + text;
    if (draft.length > el('messageInput').maxLength) throw new Error('Metin mesaj sınırını aşıyor. Daha kısa bir bölüm seç.');
    if (!task.isConnected || !el('libraryDialog').open || state.active_chat_id !== id) return;
    if (el('messageInput').value && !confirm('Mevcut taslak pano metniyle değiştirilsin mi?')) return;
    el('messageInput').value = draft;
    el('libraryDialog').close();
    showPage('chat');
  }));
}

function commandPalette() {
  if (!state) return;
  const modal = el('commandDialog');
  const query = el('commandQuery');
  const root = el('commandResults');
  const commands = [
    ['Yeni sohbet', newChat], ['Projeler çalışma alanı',()=>showPage('projects')],
    ['Bilgi Tabanı (Belgeler & RAG)',()=>showPage('kb')], ['EON Studio (DOCX/PDF/XLSX üret)',()=>showPage('studio')],
    ['EON Actions (Güvenli Araçlar)',()=>showPage('actions')], ['Görevler ve Odak (Pomodoro)',()=>showPage('tasks')],
    ['Sistem Sağlığı (Command Center)',()=>showPage('health')], ['Sohbet geçmişi',()=>showPage('history')],
    ['Favoriler',()=>{el('favoritesOnly').checked=true; el('chatSearch').value=''; el('projectFilter').value='*'; showPage('history');}],
    ['Sohbet seçenekleri',chatOptions], ['Projeleri yönet',()=>manage('project')], ['Modları yönet',()=>manage('mode')],
    ['Pano yardımcısı',clipboardDialog], ['Ayarlar',()=>showPage('settings')], ['Hafıza',()=>showPage('memory')],
    ...named(state.projects).map(([id,name])=>['Proje · '+name,()=>{
      el('projectFilter').value=id; el('chatSearch').value='';el('favoritesOnly').checked=false;showPage('history');
    }]),
    ...(state.knowledge_docs || []).map(d=>['Belge · '+d.name,()=>showPage('kb')]),
    ...Object.values(state.extras.prompts).map(p=>['Şablon · '+p.name,()=>applyPrompt(p.text)]),
    ...state.conversations.map(c=>['Sohbet · '+c.title,()=>openChat(c.id)]),
    ...installedModels.map(name=>['Model · '+name,()=>changeModel(name)]),
    ...apps.map(app=>['Uygulama · '+app.name,()=>{
      showPage('apps');
      const card = [...el('appList').children].find(node=>node.dataset.id===app.id);
      card?.scrollIntoView({block:'center'}); card?.querySelector('button:not(:disabled)')?.focus();
    }])
  ];
  function render() {
    root.replaceChildren();
    const normalize = value => value.toLocaleLowerCase('tr').replaceAll('ı','i');
    const needle = normalize(query.value.trim());
    for (const [title,run] of commands.filter(([title])=>normalize(title).includes(needle))) {
      root.append(action(title,async()=>{modal.close();await run();}));
    }
    if (!root.children.length) root.textContent = 'Komut bulunamadı.';
  }
  modal.querySelector('[role=status]')?.remove();
  query.value = '';
  query.oninput = render;
  modal.onkeydown = event => {
    const buttons = [...root.children];
    const index = buttons.indexOf(document.activeElement);
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const next = event.key === 'ArrowDown' ? index+1 : index<0 ? buttons.length-1 : index-1;
      buttons[(next+buttons.length)%buttons.length]?.focus();
    }
    if (event.key === 'Enter' && document.activeElement === query) {
      event.preventDefault(); buttons[0]?.click();
    }
  };
  render();
  if (!modal.open) modal.showModal();
  query.focus();
}
function wireWorkspace() {
  el('commandOpen').onclick = commandPalette;
  el('chatOptions').onclick = chatOptions;
  if (el('manageProjects')) el('manageProjects').onclick = ()=>manage('project');
  if (el('manageModes')) el('manageModes').onclick = ()=>manage('mode');
  for (const id of ['favoritesOnly','projectFilter']) el(id).onchange = renderHistory;
  for (const id of ['theme','accent','compact','reduced']) el(id).onchange = async () => {
    try {
      await library('look',{theme:el('theme').value,accent:el('accent').value,
        compact:el('compact').checked,reduced:el('reduced').checked});
    } catch(error) { renderWorkspace(); toast(error.message); }
  };
  document.querySelectorAll('[data-close]').forEach(button=>button.onclick=()=>button.closest('dialog').close());
  document.addEventListener('keydown', event=>{
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase()==='k') {
      event.preventDefault();
      if (el('libraryDialog').open) el('libraryDialog').close();
      commandPalette();
    }
  });
}
