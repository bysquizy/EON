'use strict';

async function extra(data) { renderState(await request('/api/extras',data)); }

function applyPrompt(text) {
  const input=el('messageInput');
  if(input.value && !confirm('Mevcut taslak değiştirilsin mi?')) return;
  input.value=text;
  input.dispatchEvent(new Event('input'));
  if(el('libraryDialog').open) el('libraryDialog').close();
  showPage('chat');
}
function promptLibrary() {
  const body=dialog('Prompt kütüphanesi');
  const list=field(body,'Şablon','select'), name=field(body,'Ad','input'), text=field(body,'İstem','textarea');
  name.maxLength=64; text.maxLength=2500;
  options(list,[['','Yeni şablon'],...named(state.extras.prompts)],'');
  list.onchange=()=>{
    const item=state.extras.prompts[list.value];
    name.value=item?.name || ''; text.value=item?.text || '';
  };
  body.append(action('Kaydet',async()=>{await extra({kind:'prompt',id:list.value,name:name.value,text:text.value});promptLibrary();}),
    action('Taslağa al',()=>applyPrompt(text.value)),action('Sil',async()=>{
      if(list.value && confirm('Şablon silinsin mi?')) {await extra({kind:'prompt',id:list.value,delete:true});promptLibrary();}
    }));
}
function projectOptions(id) {
  if(!id) throw new Error('Önce bir proje seç.');
  const body=dialog('Proje modeli ve hafızası');
  const model=field(body,'Yerel model','select'), mode=field(body,'Varsayılan mod','select');
  const config=state.extras.projects[id] || {};
  options(model,[['','Genel seçim'],...installedModels.map(m=>[m,m])],config.model || '');
  options(mode,[['','Sohbet seçimi'],...named(state.modes)],config.mode || '');
  const heading=document.createElement('p');
  heading.textContent='Bu projede kullanılabilecek hafıza kayıtları';
  body.append(heading);
  const notes=Object.entries(state.memory).map(([key,value])=>{
    const label=document.createElement('label'), check=document.createElement('input');
    check.type='checkbox';check.value=key;check.checked=(config.notes || []).includes(key);
    label.append(check,' '+value);body.append(label);return check;
  });
  body.append(action('Uygula',async()=>{
    await extra({kind:'project',id,model:model.value,mode:mode.value,notes:notes.filter(c=>c.checked).map(c=>c.value)});
    el('libraryDialog').close();
  }));
}
function saveMemoryCandidate(content) {
  const body=dialog('Hafıza önerisini düzenle');
  const note=field(body,'Kaydedilecek not','textarea');note.maxLength=400;note.value=content.slice(0,400);
  const cat=field(body,'Kategori','select');
  options(cat,[['genel','Genel'],['tercih','Tercih'],['proje','Proje'],['kisilik','Profil']],'genel');
  const proj=field(body,'Proje Kapsamı','select');
  const activeProj=currentChat()?.project || '';
  options(proj,[['','Genel (Projesiz)'],...named(state.projects)],activeProj);
  body.append(action('Onayla ve kaydet',async()=>{
    const res=await request('/api/memory',{value:note.value,category:cat.value,project:proj.value,source:'sohbet-önerisi'});
    renderState(res);
    el('libraryDialog').close();
    if(res.memory_conflict) { showPage('memory'); showMemoryConflict(res.memory_conflict); }
    else toast('Hafıza kaydı onaylanarak eklendi.');
  }));
}
function proposeTaskFromMessage(content) {
  const body=dialog('Sohbetten Görev Önerisi');
  const firstLine=content.split('\n').find(l=>l.trim())?.replace(/^[-*#\d.]+\s*/,'').trim() || content;
  const title=field(body,'Görev Başlığı','input');title.maxLength=200;title.value=firstLine.slice(0,180);
  const due=field(body,'Bitiş Tarihi (İsteğe bağlı)','input');due.type='date';
  const proj=field(body,'Proje','select');
  options(proj,[['','Projesiz'],...named(state.projects)],currentChat()?.project || '');
  body.append(action('Onayla ve Görevlere Ekle',async()=>{
    const res=await request('/api/productivity',{action:'add_task',title:title.value,due:due.value,project:proj.value,source:'sohbet'});
    renderState(res.state);
    el('libraryDialog').close();
    toast('Görev onaylanarak listeye eklendi.');
  }));
}
function findInChat() {
  const body=dialog('Bu sohbette ara');
  const search=field(body,'Kelime veya ifade','input'), results=document.createElement('div');
  body.append(results); search.focus();
  search.oninput=()=>{
    results.replaceChildren();
    const query=search.value.trim().toLocaleLowerCase('tr');
    if(!query) return;
    let count=0;
    for(const [index,message] of state.history.entries()) {
      const match=message.content.toLocaleLowerCase('tr').indexOf(query);
      if(match<0) continue;
      results.append(action(message.content.slice(Math.max(0,match-25),match+75),()=>{
        el('libraryDialog').close();el('chatLog').querySelector('[data-index="'+index+'"]')?.scrollIntoView({block:'center'});
      }));
      if(++count===50) break;
    }
    if(!count) results.textContent='Eşleşme yok.';
  };
}

let focusDeadline=0, focusInterval=0, focusTargetMins=25;
function focusMode() {
  showPage('tasks');
  el('tasksFocusMinutes')?.focus();
}

const signature=new TextEncoder().encode('EONBK01');
const backupLimit=24*1024*1024;
async function backupKey(password,salt) {
  if(password.length<12 || password.length>256) throw new Error('12–256 karakterlik bir parola kullan.');
  const material=await crypto.subtle.importKey('raw',new TextEncoder().encode(password),'PBKDF2',false,['deriveKey']);
  return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations:600000,hash:'SHA-256'},material,
    {name:'AES-GCM',length:256},false,['encrypt','decrypt']);
}
function backupTools() {
  const body=dialog('Şifreli EON Kasa Yedeği (.eonbackup)');
  const advice=document.createElement('p');advice.textContent='Şifreli yedek tüm sohbetleri, projeleri, bilgi tabanını, görevleri ve EON tercihlerini AES-256-GCM ile korur. Normal belge dışa aktarımı (Studio) değildir. API anahtarını ve Windows uygulama yollarını yeniden girmen gerekir.';
  body.append(advice);
  const pass=field(body,'Yedek parolası (en az 12 karakter)','input');pass.type='password';pass.autocomplete='new-password';
  const file=field(body,'Geri yüklenecek .eonbackup dosyası','input');file.type='file';file.accept='.eonbackup';
  body.append(action('Şifrele ve indir',async()=>{
    const salt=crypto.getRandomValues(new Uint8Array(16)), iv=crypto.getRandomValues(new Uint8Array(12));
    const key=await backupKey(pass.value,salt);
    const raw=new TextEncoder().encode(JSON.stringify(await request('/api/backup/export',{})));
    if(raw.length>backupLimit-64) throw new Error('Kasa bu yedek biçimi için çok büyük.');
    const encrypted=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:signature},key,raw);
    const url=URL.createObjectURL(new Blob([signature,salt,iv,encrypted]));
    const a=document.createElement('a');a.href=url;a.download='EON.eonbackup';a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);pass.value='';
  }),action('Doğrula ve geri yükle',async()=>{
    const selected=file.files[0];
    if(!selected || selected.size<51 || selected.size>backupLimit) throw new Error('Geçerli bir EON yedeği seç.');
    const bytes=new Uint8Array(await selected.arrayBuffer());
    if(!signature.every((value,i)=>bytes[i]===value)) throw new Error('Yedek biçimi desteklenmiyor.');
    const key=await backupKey(pass.value,bytes.slice(7,23));
    let plain;
    try {plain=await crypto.subtle.decrypt({name:'AES-GCM',iv:bytes.slice(23,35),additionalData:signature},key,bytes.slice(35));}
    catch {throw new Error('Parola yanlış veya yedek bozuk.');}
    const data=JSON.parse(new TextDecoder().decode(plain));
    if(!confirm('Mevcut sohbet ve ayarlar yedekteki kayıtlarla değiştirilsin mi?')) return;
    renderState(await request('/api/backup/restore',data));pass.value='';el('libraryDialog').close();toast('Yedek geri yüklendi.');
  }));
}

/* --- A. EON Projects 2.0 Workspace Page --- */
function renderProjectsPage() {
  if (!state) return;
  const sel = el('wsProjectSelect');
  const currentVal = sel.value;
  const entries = [['', '+ Yeni Proje Oluştur'], ...named(state.projects)];
  const activeProj = currentChat()?.project || '';
  const targetId = entries.some(([k]) => k === currentVal) && currentVal ? currentVal : activeProj;
  options(sel, entries, targetId);
  fillProjectForm(sel.value);
}

function fillProjectForm(pid) {
  const proj = state.projects[pid];
  const ext = state.extras.projects[pid] || {};
  el('wsProjectName').value = proj?.name || '';
  el('wsProjectInstructions').value = proj?.instructions || '';
  el('wsProjectNotes').value = ext.workspace_notes || '';
  el('wsProjectDelete').disabled = !proj;
  el('wsProjectActivate').disabled = !proj;
  options(el('wsProjectModel'), [['', 'Genel Model Seçimi'], ...installedModels.map(m => [m, m])], ext.model || '');
  options(el('wsProjectMode'), [['', 'Sohbet Modu Seçimi'], ...named(state.modes)], ext.mode || '');
  el('wsProjectProfile').value = ext.profile || 'balanced';
  el('wsProjectShareDocs').checked = Boolean(ext.share_docs);

  const memBox = el('wsProjectMemoryList');
  memBox.replaceChildren();
  const selectedNotes = ext.notes || [];
  const memEntries = Object.entries(state.memory);
  if (!memEntries.length) {
    memBox.textContent = 'Henüz hafıza kaydı yok.';
  } else {
    for (const [k, v] of memEntries) {
      const lbl = document.createElement('label');
      const chk = document.createElement('input');
      chk.type = 'checkbox';
      chk.value = k;
      chk.checked = selectedNotes.includes(k);
      lbl.append(chk, ' ' + v);
      memBox.append(lbl);
    }
  }
  const sumBox = el('wsProjectSummary');
  if (!proj) {
    sumBox.textContent = 'Yeni bir proje oluşturmak için ad ve yönerge girip Kaydet düğmesine basın.';
  } else {
    const pChats = (state.conversations || []).filter(c => c.project === pid).length;
    const pDocs = (state.knowledge_docs || []).filter(d => d.project === pid).length;
    sumBox.textContent = `${proj.name}: ${pChats} bağlı sohbet · ${pDocs} bilgi tabanı belgesi · ${selectedNotes.length} seçili hafıza kaydı.`;
  }
}

/* --- A. EON Knowledge Base Page --- */
let kbAbortController = null;
function renderKbPage() {
  if (!state) return;
  const pSel = el('kbProjectSelect');
  const prev = pSel.value;
  const activeProj = currentChat()?.project || '';
  options(pSel, [['', 'Genel (Projesiz)'], ...named(state.projects)], prev || activeProj);

  const root = el('kbDocList');
  root.replaceChildren();
  const docs = state.knowledge_docs || [];
  if (!docs.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-hint';
    empty.textContent = 'Henüz içe aktarılmış bir belge yok. Yukarıdan TXT, MD, PDF, DOCX, CSV veya XLSX ekleyebilirsin.';
    root.append(empty);
    return;
  }
  for (const doc of docs) {
    const row = document.createElement('div');
    row.className = 'conversation-row';
    const info = document.createElement('div');
    info.className = 'conversation-open';
    const title = document.createElement('strong');
    title.textContent = doc.name;
    const meta = document.createElement('small');
    const pName = doc.project && state.projects[doc.project] ? state.projects[doc.project].name : 'Genel';
    const kb = Math.max(1, Math.round(doc.size / 1024));
    meta.textContent = `Proje: ${pName} · ${doc.chunk_count} bölüm · ${kb} KiB${doc.has_embeddings ? ' · Vektör indeksli' : ' · FTS5 indeksli'}`;
    info.append(title, meta);
    const delBtn = action('Kaldır', async () => {
      if (!confirm(`"${doc.name}" bilgi tabanından kaldırılsın mı? (Kaynak dosyanıza dokunulmaz)`)) return;
      const res = await request('/api/knowledge', {action:'delete', id:doc.id});
      renderState(res.state);
      renderKbPage();
      toast('Belge bilgi tabanından kaldırıldı.');
    });
    row.append(info, delBtn);
    root.append(row);
  }
}

/* --- C. EON Studio Page --- */
let lastStudioPreview = null;
function renderStudioPage() {
  if (!state) return;
  const fSel = el('studioFolderSelect');
  const prev = fSel.value;
  const folders = state.actions_state?.allowed_folders || [];
  options(fSel, [['', 'Tarayıcı üzerinden indir'], ...folders.map(f => [f, 'Klasöre kaydet: ' + f])], prev);
}

function openInStudio(content, title = '') {
  showPage('studio');
  el('studioTitle').value = title || currentChat()?.title || 'EON Raporu';
  el('studioContent').value = content || '';
  el('studioGenerateBtn').disabled = true;
  el('studioPreviewBox').textContent = 'İçerik aktarıldı. Çıktı türünü seçip "Önizle" düğmesine basın.';
}

function drawStudioChartIfTable(rows) {
  const canvas = el('studioChartCanvas');
  if (!canvas) return;
  if (!Array.isArray(rows) || rows.length < 2) {
    canvas.classList.add('hidden');
    return;
  }
  const pairs = [];
  for (const r of rows.slice(1, 10)) {
    if (r.length >= 2) {
      const num = parseFloat(String(r[1]).replace(',', '.').replace(/[^0-9.-]/g, ''));
      if (Number.isFinite(num)) pairs.push([String(r[0]).slice(0, 14), num]);
    }
  }
  if (!pairs.length) {
    canvas.classList.add('hidden');
    return;
  }
  canvas.classList.remove('hidden');
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const maxVal = Math.max(...pairs.map(p => Math.abs(p[1])), 1);
  const barW = Math.floor((canvas.width - 60) / pairs.length) - 10;
  ctx.fillStyle = '#9fd5f4';
  ctx.font = '11px Inter, sans-serif';
  pairs.forEach(([label, val], idx) => {
    const x = 35 + idx * (barW + 10);
    const h = Math.max(4, Math.round((Math.abs(val) / maxVal) * 130));
    const y = 165 - h;
    ctx.fillStyle = '#5a75d9';
    ctx.fillRect(x, y, Math.max(14, barW), h);
    ctx.fillStyle = '#e9ecff';
    ctx.fillText(String(val), x, y - 5);
    ctx.fillStyle = '#a3adce';
    ctx.fillText(label, x, 184);
  });
}

/* --- B. EON Actions Page --- */
function renderActionsPage() {
  if (!state) return;
  const act = state.actions_state || {allowed_folders:[], skills:[], audit_log:[], rollback_available:false};
  el('actionRollbackBtn').disabled = !act.rollback_available;

  const fList = el('allowedFoldersList');
  fList.replaceChildren();
  if (!act.allowed_folders.length) {
    fList.textContent = 'Henüz izinli çalışma klasörü eklenmedi.';
  } else {
    for (const folder of act.allowed_folders) {
      const row = document.createElement('div');
      row.className = 'folder-item';
      const sp = document.createElement('span');
      sp.textContent = folder;
      row.append(sp, action('İzni Kaldır', async () => {
        const res = await request('/api/actions', {action:'remove_folder', path:folder});
        renderState(res.state);
        renderActionsPage();
      }));
      fList.append(row);
    }
  }

  const sSel = el('actionSkillSelect');
  if (!sSel.options.length && act.skills.length) {
    options(sSel, act.skills.map(s => [s.name, `${s.title} (${s.risk.toUpperCase()})`]), act.skills[0].name);
    updateSkillForm();
  }

  const aList = el('actionAuditList');
  aList.replaceChildren();
  if (!act.audit_log.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-hint';
    empty.textContent = 'Henüz çalıştırılmış bir eylem kaydı yok.';
    aList.append(empty);
  } else {
    for (const log of act.audit_log) {
      const row = document.createElement('div');
      row.className = 'conversation-row';
      const info = document.createElement('div');
      info.className = 'conversation-open';
      const head = document.createElement('strong');
      head.textContent = `${log.skill} · ${log.status.toUpperCase()} ${log.approved ? '(Onaylı)' : ''}`;
      const sub = document.createElement('small');
      const dt = log.time ? new Date(log.time * 1000).toLocaleTimeString() : '';
      sub.textContent = `${dt} · Hedef: ${log.target} · ${log.detail}`;
      info.append(head, sub);
      row.append(info);
      aList.append(row);
    }
  }
}

function updateSkillForm() {
  const act = state?.actions_state;
  if (!act) return;
  const skillName = el('actionSkillSelect').value;
  const spec = act.skills.find(s => s.name === skillName);
  el('actionSkillDesc').textContent = spec ? `${spec.description} · İzin kapsamı: ${spec.scope}` : '';
  const contentLbl = el('actionContentLabel');
  if (skillName === 'write_text_file') {
    contentLbl.classList.remove('hidden');
    contentLbl.firstChild.textContent = 'Yazılacak Metin İçeriği ';
  } else if (skillName === 'rename_file') {
    contentLbl.classList.remove('hidden');
    contentLbl.firstChild.textContent = 'Yeni Dosya Adı ';
  } else {
    contentLbl.classList.add('hidden');
  }
}

/* --- H. EON Focus & Tasks Page --- */
function renderTasksPage() {
  if (!state) return;
  const prod = state.productivity || {tasks:[], total_tasks:0, completed_tasks:0, pending_tasks:0, today_focus_minutes:0, total_focus_minutes:0};
  el('tasksDailySummary').textContent = `Günlük Çalışma Özeti: Bugün ${prod.today_focus_minutes} dk odaklanıldı (Toplam ${prod.total_focus_minutes} dk) · ${prod.completed_tasks}/${prod.total_tasks} görev tamamlandı.`;

  const list = el('taskListContainer');
  list.replaceChildren();
  if (!prod.tasks.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-hint';
    empty.textContent = 'Henüz görev eklenmedi.';
    list.append(empty);
    return;
  }
  for (const task of prod.tasks) {
    const row = document.createElement('div');
    row.className = 'conversation-row';
    const chk = document.createElement('input');
    chk.type = 'checkbox';
    chk.checked = task.done;
    chk.onchange = async () => {
      const res = await request('/api/productivity', {action:'update_task', id:task.id, done:chk.checked});
      renderState(res.state);
    };
    const info = document.createElement('div');
    info.className = 'conversation-open';
    const title = document.createElement('strong');
    title.textContent = task.title;
    if (task.done) title.style.textDecoration = 'line-through';
    const meta = document.createElement('small');
    const pName = task.project && state.projects?.[task.project] ? state.projects[task.project].name : 'Genel';
    meta.textContent = `Proje: ${pName}${task.due ? ' · Tarih: ' + task.due : ''} · Kaynak: ${task.source}`;
    info.append(title, meta);
    const del = action('Sil', async () => {
      const res = await request('/api/productivity', {action:'delete_task', id:task.id});
      renderState(res.state);
    });
    row.append(chk, info, del);
    list.append(row);
  }
}

/* --- J. EON Command Center (Health) Page --- */
async function renderHealthPage() {
  try {
    const s = await request('/api/runtime', {action:'status'});
    const mib = val => typeof val === 'number' ? Math.round(val / 1048576) + ' MiB' : '—';
    const gib = val => typeof val === 'number' ? (val / 1073741824).toFixed(1) + ' GiB' : '—';
    const over = el('ccOverviewGrid');
    over.replaceChildren();
    const rows1 = [
      ['Uygulama Sürümü', `EON v${s.version || '0.5.0'}`],
      ['Gizlilik & Ağ Modu', s.privacy_mode || 'Tam Yerel'],
      ['Yerel Ollama Durumu', s.connected ? 'Bağlı (127.0.0.1:11434)' : 'Çevrimdışı'],
      ['Seçili Yerel Model', s.selected || '—'],
      ['Google Gemini Durumu', s.gemini_tested ? `Hazır (${s.gemini_models?.length || 0} model)` : s.gemini_configured ? 'Anahtar kayıtlı (test edilmedi)' : 'Anahtar girilmedi'],
      ['Şifreli Kasa (DPAPI)', s.storage],
      ['Son Kaydedilen Hata', s.last_error || 'Yok'],
    ];
    for (const [k, v] of rows1) {
      const item = document.createElement('div');
      item.className = 'cc-row';
      const b = document.createElement('strong'); b.textContent = k;
      const sp = document.createElement('span'); sp.textContent = v;
      item.append(b, sp);
      over.append(item);
    }

    const mem = el('ccMemoryGrid');
    mem.replaceChildren();
    const sys = s.system_memory || {};
    const loadedDesc = (s.loaded || []).length
      ? s.loaded.map(m => `${m.model}: RAM ${mib(m.bytes)} / VRAM ${mib(m.vram)}`).join(' | ')
      : 'Bellekte yüklü Ollama modeli yok (0 MiB)';
    const rows2 = [
      ['Windows Sistem RAM Kullanımı', sys.total_bytes ? `${gib(sys.used_bytes)} / ${gib(sys.total_bytes)} (%${sys.percent})` : 'Ölçülemedi'],
      ['Kullanılabilir Fiziksel RAM', sys.available_bytes ? gib(sys.available_bytes) : '—'],
      ['Ollama Yüklü Model Belleği', loadedDesc],
    ];
    for (const [k, v] of rows2) {
      const item = document.createElement('div');
      item.className = 'cc-row';
      const b = document.createElement('strong'); b.textContent = k;
      const sp = document.createElement('span'); sp.textContent = v;
      item.append(b, sp);
      mem.append(item);
    }

    const caps = s.capabilities || {};
    el('ccCapabilitiesBox').textContent = `Seçili Model Yetenekleri (${s.selected}): Akış (Streaming): Evet · Vision: ${caps.vision ? 'Evet' : 'Hayır'} · Düşünme (Thinking): ${caps.thinking ? 'Evet' : 'Hayır'} · Embeddings: ${caps.embeddings ? 'Evet' : 'Hayır'} · Bağlam Penceresi: ${caps.context_window || state.context} token`;

    const rLog = el('ccRequestLog');
    rLog.replaceChildren();
    const logs = s.request_log || [];
    if (!logs.length) {
      const empty = document.createElement('div');
      empty.className = 'empty-hint';
      empty.textContent = 'Bu oturumda henüz model isteği yapılmadı.';
      rLog.append(empty);
    } else {
      for (const req of logs) {
        const row = document.createElement('div');
        row.className = 'conversation-row';
        const info = document.createElement('div');
        info.className = 'conversation-open';
        const h = document.createElement('strong');
        const dt = req.time ? new Date(req.time * 1000).toLocaleTimeString() : '';
        h.textContent = `${dt} · ${req.provider.toUpperCase()} (${req.model}) · Durum: ${req.status}`;
        const sub = document.createElement('small');
        sub.textContent = `İlk token: ${req.first ?? '—'} sn · Toplam süre: ${req.seconds} sn · Çıktı token: ${req.tokens}`;
        info.append(h, sub);
        row.append(info);
        rLog.append(row);
      }
    }
  } catch (error) {
    toast(error.message);
  }
}

/* --- G. EON Vision & I. EON Voice Push-to-Talk --- */
function renderVisionBar() {
  const bar = el('visionPreviewBar');
  if (!bar) return;
  bar.replaceChildren();
  bar.classList.toggle('hidden', !pendingVisionImages.length);
  pendingVisionImages.forEach((img, idx) => {
    const chip = document.createElement('div');
    chip.className = 'vision-chip';
    const thumb = document.createElement('img');
    thumb.src = `data:${img.mime};base64,${img.data}`;
    thumb.alt = img.name;
    const label = document.createElement('span');
    label.textContent = `${img.name} (${Math.round(img.size / 1024)} KiB)`;
    const rm = action('×', () => {
      pendingVisionImages.splice(idx, 1);
      renderVisionBar();
    });
    chip.append(thumb, label, rm);
    bar.append(chip);
  });
}

let activeRecognition = null;
let liveVoiceRecognition = null;
let liveVoiceAutoLoop = false;

function setLiveVoiceUiState(mode, title, subtitle) {
  const orb = el('liveVoiceOrb');
  if (orb) orb.dataset.state = mode || 'idle';
  if (el('liveVoiceStatusTitle') && title != null) el('liveVoiceStatusTitle').textContent = title;
  if (el('liveVoiceTranscript') && subtitle != null) el('liveVoiceTranscript').textContent = subtitle;
  const lbl = el('liveVoiceListenLabel');
  if (lbl) lbl.textContent = mode === 'listening' ? 'Dinlemeyi Durdur' : 'Dinlemeyi Başlat';
}

function stopLiveVoiceListening() {
  if (liveVoiceRecognition) {
    try { liveVoiceRecognition.onend = null; liveVoiceRecognition.stop(); } catch {}
    liveVoiceRecognition = null;
  }
}

function startLiveVoiceListening() {
  stopVoicePlayback();
  if (activeRecognition) {
    try { activeRecognition.stop(); } catch {}
    activeRecognition = null;
  }
  if (liveVoiceRecognition) {
    stopLiveVoiceListening();
    setLiveVoiceUiState('idle', 'Dinleme Duraklatıldı', 'Konuşmaya devam etmek için küreye dokunun veya aşağıdan yazın.');
    return;
  }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    setLiveVoiceUiState('idle', 'Canlı Sesli Yanıt Hazır', 'Bu pencerede mikrofon tanıma yerine aşağıdaki kutudan yazarak anında sesli konuşabilirsiniz.');
    el('liveVoiceQuickInput')?.focus();
    return;
  }
  try {
    const rec = new SR();
    rec.lang = 'tr-TR';
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    liveVoiceRecognition = rec;
    let capturedText = '';
    let submitted = false;
    setLiveVoiceUiState('listening', 'Dinliyorum…', 'Konuşmaya başlayın, cümleniz bittiğinde EON sesli yanıtlayacak.');
    rec.onresult = evt => {
      let interim = '';
      let finalTxt = '';
      for (let i = evt.resultIndex; i < evt.results.length; i++) {
        const t = evt.results[i][0]?.transcript || '';
        if (evt.results[i].isFinal) finalTxt += t;
        else interim += t;
      }
      capturedText = (finalTxt || interim).trim();
      if (capturedText) {
        setLiveVoiceUiState('listening', 'Dinliyorum…', `“${capturedText}”`);
      }
      if (finalTxt.trim() && !submitted) {
        submitted = true;
        liveVoiceAutoLoop = true;
        stopLiveVoiceListening();
        submitLiveVoiceTurn(finalTxt.trim());
      }
    };
    rec.onerror = evt => {
      liveVoiceRecognition = null;
      const code = evt?.error || '';
      if (code === 'no-speech') {
        setLiveVoiceUiState('idle', 'Ses Algılanmadı', 'Tekrar konuşmak için küreye dokunun veya aşağıdan mesaj gönderin.');
      } else {
        setLiveVoiceUiState('idle', 'Canlı Ses Hazır', 'Mikrofon bağlı değil veya izin kapalı — aşağıdaki kutudan yazarak canlı sesli konuşabilirsiniz.');
        el('liveVoiceQuickInput')?.focus();
      }
    };
    rec.onend = () => {
      liveVoiceRecognition = null;
      if (!submitted && capturedText) {
        submitted = true;
        liveVoiceAutoLoop = true;
        submitLiveVoiceTurn(capturedText);
      } else if (!submitted && el('liveVoiceOrb')?.dataset.state === 'listening') {
        setLiveVoiceUiState('idle', 'Canlı Sesli Konuşma Hazır', 'Konuşmak için küreye dokunun veya aşağıdan sesli yanıt alın.');
      }
    };
    rec.start();
  } catch {
    liveVoiceRecognition = null;
    setLiveVoiceUiState('idle', 'Canlı Ses Hazır', 'Aşağıdaki kutudan mesajınızı yazıp anında sesli yanıt alabilirsiniz.');
  }
}

async function submitLiveVoiceTurn(text) {
  const clean = (text || '').trim();
  if (!clean || busy) return;
  stopLiveVoiceListening();
  stopVoicePlayback();
  setLiveVoiceUiState('thinking', 'Düşünüyor…', `“${clean}”`);
  if (el('liveVoiceReplyText')) el('liveVoiceReplyText').textContent = '';
  await streamAnswer(clean);
}

function openLiveVoiceOverlay() {
  const overlay = el('liveVoiceOverlay');
  if (!overlay) return;
  showPage('chat');
  overlay.classList.remove('hidden');
  el('liveVoiceToggle')?.setAttribute('aria-pressed', 'true');
  el('liveVoiceToggle')?.classList.add('active');
  if (el('liveVoicePersona') && el('voicePersonaSelect')) {
    el('liveVoicePersona').value = el('voicePersonaSelect').value || 'tr-TR-AhmetNeural';
  }
  if (el('liveVoiceReplyText')) el('liveVoiceReplyText').textContent = '';
  startLiveVoiceListening();
}

function closeLiveVoiceOverlay() {
  liveVoiceAutoLoop = false;
  stopLiveVoiceListening();
  stopVoicePlayback();
  el('liveVoiceOverlay')?.classList.add('hidden');
  el('liveVoiceToggle')?.setAttribute('aria-pressed', 'false');
  el('liveVoiceToggle')?.classList.remove('active');
}

function notifyLiveStreamFinished() {
  const overlayOpen = !el('liveVoiceOverlay')?.classList.contains('hidden');
  if (!overlayOpen) return;
  if (!liveSentenceBusy && !liveSentenceQueue.length) {
    if (el('liveVoiceOrb')?.dataset.state === 'thinking') {
      setLiveVoiceUiState('idle', 'Canlı Sesli Konuşma Hazır', 'Yeni bir şey söylemek için küreye dokunun.');
    }
  }
}

function togglePushToTalk() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const indicator = el('voiceIndicator');
  const btn = el('pttButton');
  if (activeRecognition) {
    try { activeRecognition.stop(); } catch {}
    activeRecognition = null;
    indicator?.classList.add('hidden');
    btn?.classList.remove('active');
    return;
  }
  if (!SR) {
    openLiveVoiceOverlay();
    return;
  }
  try {
    const rec = new SR();
    rec.lang = 'tr-TR';
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    activeRecognition = rec;
    const baseText = el('messageInput')?.value ? el('messageInput').value.trim() + ' ' : '';
    indicator?.classList.remove('hidden');
    btn?.classList.add('active');
    rec.onresult = evt => {
      let transcript = '';
      for (let i = 0; i < evt.results.length; i++) {
        transcript += evt.results[i][0]?.transcript || '';
      }
      if (transcript.trim()) {
        const inp = el('messageInput');
        inp.value = baseText + transcript.trim();
        inp.dispatchEvent(new Event('input'));
      }
    };
    rec.onerror = evt => {
      activeRecognition = null;
      indicator?.classList.add('hidden');
      btn?.classList.remove('active');
      if (evt?.error === 'not-allowed' || evt?.error === 'audio-capture' || evt?.error === 'service-not-allowed') {
        openLiveVoiceOverlay();
      } else if (evt?.error !== 'no-speech') {
        openLiveVoiceOverlay();
      }
    };
    rec.onend = () => {
      activeRecognition = null;
      indicator?.classList.add('hidden');
      btn?.classList.remove('active');
    };
    rec.start();
  } catch {
    openLiveVoiceOverlay();
  }
}

let activeAudioPlayer = null;
let liveSentenceQueue = [];
let liveSentenceBusy = false;

function stopVoicePlayback() {
  liveSentenceQueue = [];
  liveSentenceBusy = false;
  if (activeAudioPlayer) {
    try { activeAudioPlayer.pause(); activeAudioPlayer.src = ''; } catch {}
    activeAudioPlayer = null;
  }
  if ('speechSynthesis' in window) {
    try { window.speechSynthesis.cancel(); } catch {}
  }
}

function browserNaturalSpeakAsync(text, preferredVoice = 'tr-TR-AhmetNeural') {
  return new Promise(resolve => {
    if (!('speechSynthesis' in window)) return resolve(false);
    try {
      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = preferredVoice.startsWith('en-') ? 'en-US' : 'tr-TR';
      utter.rate = 1.03;
      utter.pitch = 1.0;
      const voices = window.speechSynthesis.getVoices() || [];
      const wantFemale = preferredVoice.includes('Emel') || preferredVoice.includes('Ava');
      const best = voices.find(v => v.name.includes('Natural') && v.lang.startsWith(utter.lang.slice(0, 2)) && (wantFemale ? /emel|ava|female/i.test(v.name) : /ahmet|andrew|male/i.test(v.name)))
        || voices.find(v => v.name.includes('Natural') && v.lang.startsWith(utter.lang.slice(0, 2)))
        || voices.find(v => v.lang.startsWith(utter.lang.slice(0, 2)));
      if (best) utter.voice = best;
      const timeout = setTimeout(() => resolve(true), Math.min(18000, Math.max(2500, text.length * 95)));
      utter.onend = () => { clearTimeout(timeout); resolve(true); };
      utter.onerror = () => { clearTimeout(timeout); resolve(false); };
      window.speechSynthesis.speak(utter);
    } catch {
      resolve(false);
    }
  });
}

async function processLiveSentenceQueue() {
  if (liveSentenceBusy || !liveSentenceQueue.length) return;
  liveSentenceBusy = true;
  const overlayOpen = !el('liveVoiceOverlay')?.classList.contains('hidden');
  if (overlayOpen) {
    setLiveVoiceUiState('speaking', 'Konuşuyor…', 'Kesmek veya yeni soru sormak için küreye dokunun.');
  }
  const text = liveSentenceQueue.shift();
  const voice = el('liveVoicePersona')?.value || el('voicePersonaSelect')?.value || state?.voice_state?.selected || 'tr-TR-AhmetNeural';
  try {
    const res = await request('/api/voice', {action:'speak', text, voice});
    if (res.audio_base64) {
      const bytes = Uint8Array.from(atob(res.audio_base64), c => c.charCodeAt(0));
      const url = URL.createObjectURL(new Blob([bytes], {type: res.mime || 'audio/mpeg'}));
      await new Promise(resolve => {
        const audio = new Audio(url);
        activeAudioPlayer = audio;
        audio.onended = () => { URL.revokeObjectURL(url); resolve(); };
        audio.onerror = () => { URL.revokeObjectURL(url); resolve(); };
        audio.play().catch(async () => {
          URL.revokeObjectURL(url);
          await browserNaturalSpeakAsync(res.cleaned_text || text, voice);
          resolve();
        });
      });
    } else if (res.cleaned_text) {
      await browserNaturalSpeakAsync(res.cleaned_text, voice);
    }
  } catch {}
  liveSentenceBusy = false;
  if (liveSentenceQueue.length) {
    processLiveSentenceQueue();
  } else if (!el('liveVoiceOverlay')?.classList.contains('hidden') && !activeStream) {
    if (liveVoiceAutoLoop) {
      setTimeout(() => {
        if (!el('liveVoiceOverlay')?.classList.contains('hidden') && !liveSentenceBusy && !activeStream) {
          startLiveVoiceListening();
        }
      }, 350);
    } else {
      setLiveVoiceUiState('idle', 'Yanıt Tamamlandı', 'Tekrar konuşmak için küreye dokunun veya aşağıdan yazın.');
    }
  }
}

function enqueueLiveSentence(sentence) {
  if (!sentence || sentence.length < 2) return;
  liveSentenceQueue.push(sentence);
  processLiveSentenceQueue();
}

async function inspectKnowledgeCitation(docId, chunkIndex = 0) {
  try {
    const {chunk} = await request('/api/knowledge', {action:'get_chunk', doc_id:docId, chunk_index:chunkIndex});
    const loc = chunk.page ? `Sayfa ${chunk.page}` : chunk.section;
    const body = dialog(`${chunk.name} · ${loc}`);
    const meta = document.createElement('p');
    meta.className = 'note-small';
    meta.textContent = `Bölüm ${chunk.chunk_index + 1} / ${chunk.chunk_count} · Kaynak belge içeriği (salt okunur)`;
    const pre = document.createElement('pre');
    pre.className = 'citation-modal-text';
    pre.textContent = chunk.text;
    const prevBtn = action('← Önceki Bölüm', () => inspectKnowledgeCitation(docId, Math.max(0, chunk.chunk_index - 1)));
    prevBtn.disabled = chunk.chunk_index <= 0;
    const nextBtn = action('Sonraki Bölüm →', () => inspectKnowledgeCitation(docId, Math.min(chunk.chunk_count - 1, chunk.chunk_index + 1)));
    nextBtn.disabled = chunk.chunk_index >= chunk.chunk_count - 1;
    const nav = document.createElement('div');
    nav.className = 'button-row';
    nav.append(prevBtn, nextBtn);
    body.append(meta, pre, nav);
  } catch (error) { toast(error.message); }
}

function browserNaturalSpeak(text, preferredVoice = 'tr-TR-AhmetNeural') {
  if (!('speechSynthesis' in window)) return false;
  stopVoicePlayback();
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = preferredVoice.startsWith('en-') ? 'en-US' : 'tr-TR';
  utter.rate = 1.02;
  utter.pitch = 1.0;
  const voices = window.speechSynthesis.getVoices() || [];
  const wantFemale = preferredVoice.includes('Emel') || preferredVoice.includes('Ava');
  const best = voices.find(v => v.name.includes('Natural') && v.lang.startsWith(utter.lang.slice(0, 2)) && (wantFemale ? /emel|ava|female/i.test(v.name) : /ahmet|andrew|male/i.test(v.name)))
    || voices.find(v => v.name.includes('Natural') && v.lang.startsWith(utter.lang.slice(0, 2)))
    || voices.find(v => v.lang.startsWith(utter.lang.slice(0, 2)));
  if (best) utter.voice = best;
  window.speechSynthesis.speak(utter);
  return true;
}

async function speakText(text) {
  try {
    stopVoicePlayback();
    const voice = el('voicePersonaSelect')?.value || state?.voice_state?.selected || 'tr-TR-AhmetNeural';
    const res = await request('/api/voice', {action:'speak', text, voice});
    if (res.audio_base64) {
      const bytes = Uint8Array.from(atob(res.audio_base64), c => c.charCodeAt(0));
      const url = URL.createObjectURL(new Blob([bytes], {type: res.mime || 'audio/mpeg'}));
      const audio = new Audio(url);
      activeAudioPlayer = audio;
      audio.onended = () => { URL.revokeObjectURL(url); if (activeAudioPlayer === audio) activeAudioPlayer = null; };
      audio.onerror = () => { URL.revokeObjectURL(url); browserNaturalSpeak(res.cleaned_text || text, voice); };
      await audio.play();
      toast('Neural HD doğal seslendirme oynatılıyor.');
      return;
    }
    if (res.engine === 'browser_natural') {
      if (browserNaturalSpeak(res.cleaned_text || text, voice)) {
        toast('Yerleşik doğal ses motoru başlatıldı.');
        return;
      }
    }
    if (!res.supported) toast(res.notice || 'Seslendirme desteklenmiyor.');
    else toast('Yerel seslendirme başlatıldı.');
  } catch (error) { toast(error.message); }
}

function wireStudio() {
  el('promptLibrary').onclick=promptLibrary;
  el('focusMode').onclick=focusMode;
  el('backupTools').onclick=backupTools;
  el('appSearch').oninput=renderApps;
  el('chatFind').onclick=findInChat;
  el('undoChat').onclick=async()=>{
    try {await extra({kind:'undo',id:state.active_chat_id});} catch(error){toast(error.message);}
  };
  const search=document.createElement('input');search.type='search';search.className='field';
  search.placeholder='Hafıza kaydı ara (metin, kategori veya proje)';search.setAttribute('aria-label','Hafıza kaydı ara');search.id='memorySearch';
  el('notes').before(search);search.oninput=renderNotes;

  if (el('exportMemoryBtn')) {
    el('exportMemoryBtn').onclick = () => {
      if (!confirm('Hafıza kayıtları şifrelenmemiş JSON dosyası olarak indirilecek. Devam edilsin mi?')) return;
      const payload = Object.entries(state.memory || {}).map(([id, text]) => ({
        id, text, ...(state.memory_meta?.[id] || {})
      }));
      const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], {type:'application/json;charset=utf-8'}));
      const a = document.createElement('a'); a.href = url; a.download = 'EON-Hafiza.json'; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    };
  }

  // Composer Vision, Research, Profile, Voice
  el('attachImageBtn').onclick = () => el('visionInput').click();
  el('visionInput').onchange = async () => {
    const files = [...el('visionInput').files];
    el('visionInput').value = '';
    for (const file of files) {
      if (pendingVisionImages.length >= 4) { toast('En fazla 4 görsel eklenebilir.'); break; }
      if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
        toast('Yalnız PNG, JPEG ve WebP görselleri desteklenir.'); continue;
      }
      if (file.size > 4 * 1024 * 1024) {
        toast('Görsel boyutu 4 MiB sınırını aşıyor.'); continue;
      }
      const bytes = new Uint8Array(await file.arrayBuffer());
      let bin = '';
      for (let i = 0; i < bytes.length; i += 8192) {
        bin += String.fromCharCode(...bytes.subarray(i, i + 8192));
      }
      pendingVisionImages.push({name: file.name, mime: file.type, size: file.size, data: btoa(bin)});
    }
    renderVisionBar();
  };

  el('pttButton').onclick = togglePushToTalk;
  el('voiceIndicator').onclick = togglePushToTalk;
  if (el('liveVoiceToggle')) {
    el('liveVoiceToggle').onclick = () => {
      const overlay = el('liveVoiceOverlay');
      if (overlay && overlay.classList.contains('hidden')) {
        openLiveVoiceOverlay();
      } else {
        closeLiveVoiceOverlay();
      }
    };
  }
  if (el('liveVoiceCloseBtn')) el('liveVoiceCloseBtn').onclick = closeLiveVoiceOverlay;
  if (el('liveVoiceEndBtn')) el('liveVoiceEndBtn').onclick = closeLiveVoiceOverlay;
  if (el('liveVoiceListenBtn')) el('liveVoiceListenBtn').onclick = () => startLiveVoiceListening();
  if (el('liveVoiceInterruptBtn')) {
    el('liveVoiceInterruptBtn').onclick = () => {
      liveVoiceAutoLoop = false;
      stopVoicePlayback();
      if (activeStream) request('/api/stop', {key:activeStream}).catch(() => {});
      setLiveVoiceUiState('idle', 'Ses Kesildi', 'Yeni bir şey söylemek için küreye dokunun veya aşağıdan yazın.');
    };
  }
  if (el('liveVoiceOrb')) {
    el('liveVoiceOrb').onclick = () => {
      const st = el('liveVoiceOrb').dataset.state;
      if (st === 'speaking' || liveSentenceBusy) {
        stopVoicePlayback();
        startLiveVoiceListening();
      } else if (st === 'listening') {
        stopLiveVoiceListening();
        setLiveVoiceUiState('idle', 'Dinleme Duraklatıldı', 'Tekrar konuşmak için küreye dokunun.');
      } else {
        startLiveVoiceListening();
      }
    };
  }
  if (el('liveVoicePersona')) {
    el('liveVoicePersona').onchange = async () => {
      const v = el('liveVoicePersona').value;
      if (el('voicePersonaSelect')) el('voicePersonaSelect').value = v;
      try {
        const res = await request('/api/voice', {action:'configure', voice:v});
        renderState(res.state);
      } catch {}
    };
  }
  const sendLiveQuick = () => {
    const inp = el('liveVoiceQuickInput');
    const val = inp?.value.trim() || '';
    if (!val) return;
    inp.value = '';
    liveVoiceAutoLoop = false;
    submitLiveVoiceTurn(val);
  };
  if (el('liveVoiceQuickSend')) el('liveVoiceQuickSend').onclick = sendLiveQuick;
  if (el('liveVoiceQuickInput')) {
    el('liveVoiceQuickInput').onkeydown = e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        sendLiveQuick();
      }
    };
  }
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !el('liveVoiceOverlay')?.classList.contains('hidden')) {
      closeLiveVoiceOverlay();
    }
  });
  if (el('studioTemplateSelect')) {
    el('studioTemplateSelect').onchange = () => {
      const tplKey = el('studioTemplateSelect').value;
      const tpl = state?.studio_templates?.[tplKey];
      if (tpl) {
        el('studioTitle').value = tpl.title;
        el('studioContent').value = tpl.content;
        el('studioPreviewBtn').click();
      }
    };
  }
  if (el('kbBatchFolderBtn')) {
    el('kbBatchFolderBtn').onclick = async () => {
      const folders = state?.actions_state?.allowed_folders || [];
      if (!folders.length) {
        toast('Toplu klasör aktarımı için önce Araçlar sekmesinden bir izinli çalışma klasörü ekleyin.');
        return showPage('actions');
      }
      const chosen = prompt('İçe aktarılacak izinli klasör yolunu onaylayın:', folders[0]);
      if (!chosen?.trim()) return;
      try {
        el('kbProgressStatus').textContent = 'Klasördeki belgeler taranıyor ve indeksleniyor...';
        const res = await request('/api/knowledge', {
          action:'import_folder',
          folder:chosen.trim(),
          project:el('kbProjectSelect').value,
        });
        renderState(res.state);
        renderKbPage();
        el('kbProgressStatus').textContent = `${res.imported} belge başarıyla toplu indekslendi.`;
        toast(`${res.imported} belge bilgi tabanına eklendi.`);
      } catch (error) {
        el('kbProgressStatus').textContent = 'Hata: ' + error.message;
        toast(error.message);
      }
    };
  }

  // Drag & Drop files onto chat view (Images -> Vision, Docs -> Knowledge Base)
  const chatView = el('view-chat');
  chatView.addEventListener('dragover', e => { e.preventDefault(); chatView.classList.add('drag-active'); });
  chatView.addEventListener('dragleave', () => chatView.classList.remove('drag-active'));
  chatView.addEventListener('drop', async e => {
    e.preventDefault();
    chatView.classList.remove('drag-active');
    const files = [...(e.dataTransfer?.files || [])];
    for (const file of files) {
      if (['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
        if (pendingVisionImages.length >= 4) { toast('En fazla 4 görsel eklenebilir.'); continue; }
        const bytes = new Uint8Array(await file.arrayBuffer());
        let bin = '';
        for (let i = 0; i < bytes.length; i += 8192) bin += String.fromCharCode(...bytes.subarray(i, i + 8192));
        pendingVisionImages.push({name:file.name, mime:file.type, size:file.size, data:btoa(bin)});
        renderVisionBar();
        toast(`Görsel eklendi: ${file.name}`);
      } else if (/\.(txt|md|pdf|docx|csv|xlsx)$/i.test(file.name)) {
        try {
          const bytes = new Uint8Array(await file.arrayBuffer());
          let bin = '';
          for (let i = 0; i < bytes.length; i += 8192) bin += String.fromCharCode(...bytes.subarray(i, i + 8192));
          const activeProj = currentChat()?.project || '';
          const res = await request('/api/knowledge', {action:'import', name:file.name, data:btoa(bin), project:activeProj});
          renderState(res.state);
          toast(`Belge aktif çalışma alanına indekslendi: ${file.name}`);
        } catch (error) { toast(error.message); }
      } else {
        toast(`Desteklenmeyen dosya türü: ${file.name}`);
      }
    }
  });
  if (el('voicePersonaSelect')) {
    el('voicePersonaSelect').onchange = async () => {
      try {
        const res = await request('/api/voice', {action:'configure', voice:el('voicePersonaSelect').value});
        renderState(res.state);
        toast('Doğal ses karakteri güncellendi.');
      } catch (error) { toast(error.message); }
    };
  }
  if (el('voiceSampleBtn')) {
    el('voiceSampleBtn').onclick = () => speakText('Merhaba, ben EON. Kişisel çalışma ortamında sana doğal ve akıcı bir sesle eşlik etmeye hazırım.');
  }
  if (el('ttsStopBtn')) el('ttsStopBtn').onclick = async () => {
    stopVoicePlayback();
    await request('/api/voice', {action:'stop'});
    toast('Seslendirme durduruldu.');
  };

  el('researchToggle').onclick = async () => {
    if (!state.cloud_model) {
      toast('Canlı web araştırması (Google Search Grounding) yalnız onaylı Gemini sohbetlerinde etkinleştirilebilir. Yerel belgeler için Bilgi Tabanı sekmesini kullanın.');
      return;
    }
    const cur = el('researchToggle').getAttribute('aria-pressed') === 'true';
    const next = !cur;
    await extra({kind:'chat', id:state.active_chat_id, research:next});
    toast(next ? 'Kaynaklı araştırma modu etkinleştirildi.' : 'Araştırma modu kapatıldı.');
  };

  el('profileSelect').onchange = async () => {
    try {
      await extra({kind:'chat', id:state.active_chat_id, profile:el('profileSelect').value});
      toast('Çalışma profili güncellendi.');
    } catch (error) { toast(error.message); }
  };

  // Projects 2.0 handlers
  el('wsProjectSelect').onchange = () => fillProjectForm(el('wsProjectSelect').value);
  el('newProjectBtn').onclick = () => { el('wsProjectSelect').value = ''; fillProjectForm(''); el('wsProjectName').focus(); };
  el('wsProjectSave').onclick = async () => {
    try {
      const pid = el('wsProjectSelect').value;
      const name = el('wsProjectName').value.trim();
      const instructions = el('wsProjectInstructions').value.trim();
      const beforeIds = new Set(Object.keys(state.projects));
      await library('project', {id:pid, name, instructions});
      const targetId = pid || Object.keys(state.projects).find(k => !beforeIds.has(k)) || '';
      if (targetId) {
        const checkedNotes = [...el('wsProjectMemoryList').querySelectorAll('input[type=checkbox]:checked')].map(c => c.value);
        await extra({
          kind:'project',
          id:targetId,
          model:el('wsProjectModel').value,
          mode:el('wsProjectMode').value,
          profile:el('wsProjectProfile').value,
          workspace_notes:el('wsProjectNotes').value,
          share_docs:el('wsProjectShareDocs').checked,
          notes:checkedNotes,
        });
        el('wsProjectSelect').value = targetId;
        fillProjectForm(targetId);
      }
      toast('Proje çalışma alanı kaydedildi.');
    } catch (error) { toast(error.message); }
  };
  el('wsProjectActivate').onclick = async () => {
    const pid = el('wsProjectSelect').value;
    if (!pid) return;
    try {
      const chat = currentChat();
      await library('configure', {id:chat.id, project:pid, mode:el('wsProjectMode').value || chat.mode});
      toast('Proje aktif sohbete atandı.');
      showPage('chat');
    } catch (error) { toast(error.message); }
  };
  el('wsProjectDelete').onclick = async () => {
    const pid = el('wsProjectSelect').value;
    if (!pid || !confirm('Bu proje ve bağlı bilgi tabanı indeksleri silinsin mi? Sohbetler Projesiz altında korunur.')) return;
    try {
      await library('project', {id:pid, delete:true});
      renderProjectsPage();
      toast('Proje silindi.');
    } catch (error) { toast(error.message); }
  };

  // Knowledge Base handlers
  el('kbImportBtn').onclick = async () => {
    const file = el('kbFileInput').files[0];
    if (!file) return toast('İçe aktarılacak bir belge seç.');
    if (file.size > 8 * 1024 * 1024) return toast('Dosya boyutu 8 MiB sınırını aşıyor.');
    const status = el('kbProgressStatus');
    const cancelBtn = el('kbCancelBtn');
    kbAbortController = new AbortController();
    cancelBtn.classList.remove('hidden');
    el('kbImportBtn').disabled = true;
    status.textContent = `${file.name} okunuyor (%20)...`;
    try {
      const bytes = new Uint8Array(await file.arrayBuffer());
      if (kbAbortController.signal.aborted) throw new Error('İçe aktarma iptal edildi.');
      status.textContent = `${file.name} indeksleniyor (%60)...`;
      let bin = '';
      for (let i = 0; i < bytes.length; i += 8192) {
        bin += String.fromCharCode(...bytes.subarray(i, i + 8192));
      }
      const res = await request('/api/knowledge', {
        action:'import',
        name:file.name,
        data:btoa(bin),
        project:el('kbProjectSelect').value,
        embed:el('kbUseEmbeddings').checked,
      });
      renderState(res.state);
      renderKbPage();
      el('kbFileInput').value = '';
      status.textContent = `${res.document.name} başarıyla indekslendi (${res.document.chunk_count} bölüm).`;
      toast('Belge bilgi tabanına eklendi.');
    } catch (error) {
      status.textContent = 'Hata: ' + error.message;
      toast(error.message);
    } finally {
      cancelBtn.classList.add('hidden');
      el('kbImportBtn').disabled = false;
      kbAbortController = null;
    }
  };
  el('kbCancelBtn').onclick = () => {
    kbAbortController?.abort();
    el('kbProgressStatus').textContent = 'İptal edildi.';
  };
  const runKbSearch = async () => {
    const query = el('kbSearchInput').value.trim();
    const box = el('kbSearchResults');
    box.replaceChildren();
    if (!query) return;
    try {
      const {results} = await request('/api/knowledge', {action:'search', query, project:el('kbProjectSelect').value});
      if (!results.length) {
        box.textContent = 'Bu proje kapsamında eşleşen belge bölümü bulunamadı.';
        return;
      }
      for (const hit of results) {
        const card = document.createElement('div');
        card.className = 'kb-hit-card';
        const head = document.createElement('strong');
        const loc = hit.page ? `Sayfa ${hit.page}` : hit.section;
        head.textContent = `${hit.name} · ${loc}`;
        const p = document.createElement('p');
        p.textContent = hit.snippet;
        card.append(head, p);
        box.append(card);
      }
    } catch (error) { toast(error.message); }
  };
  el('kbSearchBtn').onclick = runKbSearch;
  el('kbSearchInput').onkeydown = e => { if (e.key === 'Enter') runKbSearch(); };

  // Studio handlers
  el('studioLoadLastReply').onclick = () => {
    const last = [...(state?.history || [])].reverse().find(m => m.role === 'assistant');
    if (!last) return toast('Aktif sohbette henüz bir EON yanıtı yok.');
    openInStudio(last.content, currentChat()?.title || 'EON Raporu');
  };
  el('studioPreviewBtn').onclick = async () => {
    try {
      const {preview} = await request('/api/studio', {
        action:'preview',
        title:el('studioTitle').value,
        content:el('studioContent').value,
        format:el('studioFormat').value,
        folder:el('studioFolderSelect').value,
      });
      lastStudioPreview = preview;
      const box = el('studioPreviewBox');
      box.replaceChildren();
      const meta = document.createElement('strong');
      meta.textContent = `Dosya: ${preview.filename} (${preview.format.toUpperCase()} · ${preview.size_bytes} bayt)`;
      const loc = document.createElement('p');
      loc.textContent = `Kayıt Konumu: ${preview.target_path}`;
      const pre = document.createElement('pre');
      pre.textContent = preview.content_preview;
      box.append(meta, loc, pre);
      drawStudioChartIfTable(preview.table_preview);
      el('studioGenerateBtn').disabled = false;
    } catch (error) { toast(error.message); }
  };
  el('studioGenerateBtn').onclick = async () => {
    if (!lastStudioPreview) return toast('Önce belgeyi önizle.');
    try {
      const res = await request('/api/studio', {
        action:'generate',
        title:el('studioTitle').value,
        content:el('studioContent').value,
        format:el('studioFormat').value,
        folder:el('studioFolderSelect').value,
        confirm:true,
      });
      renderState(res.state);
      if (res.saved_path) {
        toast(`Belge kaydedildi: ${res.saved_path}`);
      } else {
        const bytes = Uint8Array.from(atob(res.data_base64), c => c.charCodeAt(0));
        const url = URL.createObjectURL(new Blob([bytes], {type:res.mime}));
        const a = document.createElement('a'); a.href = url; a.download = res.filename; a.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        toast(`Belge indirildi: ${res.filename}`);
      }
    } catch (error) { toast(error.message); }
  };

  // Actions handlers
  el('addAllowedFolderBtn').onclick = async () => {
    const path = el('allowedFolderInput').value.trim();
    if (!path) return toast('Tam klasör yolunu gir.');
    try {
      const res = await request('/api/actions', {action:'add_folder', path});
      el('allowedFolderInput').value = '';
      renderState(res.state);
      renderActionsPage();
      toast('İzinli çalışma klasörü eklendi.');
    } catch (error) { toast(error.message); }
  };
  el('actionSkillSelect').onchange = updateSkillForm;
  el('actionRunBtn').onclick = async () => {
    const skill = el('actionSkillSelect').value;
    const pathVal = el('actionParamPath').value.trim();
    const contentVal = el('actionParamContent').value;
    const params = skill === 'search_files' ? {query:pathVal}
      : skill === 'write_text_file' ? {path:pathVal, content:contentVal}
      : skill === 'rename_file' ? {path:pathVal, new_name:contentVal.trim()}
      : skill === 'open_app' ? {app_id:pathVal}
      : {path:pathVal};
    try {
      const res = await request('/api/actions', {action:'run', skill, params});
      renderState(res.state);
      renderActionsPage();
      const outBox = el('actionOutputBox');
      const pendBox = el('actionPendingBox');
      outBox.replaceChildren();
      pendBox.replaceChildren();
      if (res.requires_confirmation && res.preview) {
        pendBox.classList.remove('hidden');
        const p = res.preview;
        const h = document.createElement('strong');
        h.textContent = `Onay Gerekiyor: ${p.title} (Risk: ${p.risk.toUpperCase()})`;
        const desc = document.createElement('p');
        desc.textContent = `${p.change_summary} · Etkilenen: ${p.affected_files.join(', ')}`;
        pendBox.append(h, desc);
        if (p.preview_after) {
          const pre = document.createElement('pre');
          pre.textContent = p.preview_after;
          pendBox.append(pre);
        }
        const approveBtn = action('Onayla ve Uygula', async () => {
          const cRes = await request('/api/actions', {action:'confirm', token:p.token, approve:true});
          pendBox.classList.add('hidden');
          renderState(cRes.state);
          renderActionsPage();
          outBox.textContent = `İşlem tamamlandı: ${cRes.target || ''}`;
          toast('Eylem onaylandı ve uygulandı.');
        });
        const cancelBtn = action('İptal Et', async () => {
          const cRes = await request('/api/actions', {action:'confirm', token:p.token, approve:false});
          pendBox.classList.add('hidden');
          renderState(cRes.state);
          renderActionsPage();
          outBox.textContent = 'İşlem kullanıcı tarafından iptal edildi.';
        });
        pendBox.append(approveBtn, cancelBtn);
      } else {
        pendBox.classList.add('hidden');
        if (res.matches) {
          outBox.textContent = res.matches.length
            ? res.matches.map(m => `${m.name} (${m.path})`).join('\n')
            : 'Eşleşen dosya bulunamadı.';
        } else if (res.summary || res.content) {
          outBox.textContent = (res.summary ? 'Özet:\n' + res.summary + '\n\n' : '') + (res.content || '');
        }
      }
    } catch (error) { toast(error.message); }
  };
  el('actionRollbackBtn').onclick = async () => {
    if (!confirm('Son dosya değişikliği geri alınsın mı?')) return;
    try {
      const res = await request('/api/actions', {action:'rollback'});
      renderState(res.state);
      renderActionsPage();
      toast('Son dosya işlemi geri alındı: ' + (res.target || ''));
    } catch (error) { toast(error.message); }
  };

  // Focus & Tasks handlers
  const updateFocusClock = () => {
    const rem = Math.max(0, Math.ceil((focusDeadline - Date.now()) / 1000));
    const mm = String(Math.floor(rem / 60)).padStart(2, '0');
    const ss = String(rem % 60).padStart(2, '0');
    if (el('tasksFocusClock')) el('tasksFocusClock').textContent = rem ? `${mm}:${ss}` : `${String(el('tasksFocusMinutes')?.value || 25).padStart(2, '0')}:00`;
  };
  el('tasksFocusStart').onclick = () => {
    const mins = Number(el('tasksFocusMinutes').value);
    if (!Number.isInteger(mins) || mins < 1 || mins > 180) return toast('1–180 dakika arasında bir süre seç.');
    focusTargetMins = mins;
    focusDeadline = Date.now() + mins * 60000;
    clearInterval(focusInterval);
    updateFocusClock();
    focusInterval = setInterval(async () => {
      if (Date.now() >= focusDeadline) {
        clearInterval(focusInterval);
        focusDeadline = 0;
        updateFocusClock();
        toast('Odak oturumu tamamlandı!');
        try {
          const res = await request('/api/productivity', {action:'log_focus', minutes:focusTargetMins, label:el('tasksFocusLabel').value});
          renderState(res.state);
        } catch {}
      } else updateFocusClock();
    }, 1000);
    toast('Odak oturumu başladı.');
  };
  el('tasksFocusStop').onclick = () => {
    focusDeadline = 0;
    clearInterval(focusInterval);
    updateFocusClock();
  };
  el('addTaskBtn').onclick = async () => {
    const title = el('newTaskTitle').value.trim();
    if (!title) return toast('Görev başlığı gir.');
    try {
      const res = await request('/api/productivity', {
        action:'add_task',
        title,
        due:el('newTaskDue').value,
        project:currentChat()?.project || '',
      });
      el('newTaskTitle').value = '';
      renderState(res.state);
      toast('Görev eklendi.');
    } catch (error) { toast(error.message); }
  };
  el('exportIcsBtn').onclick = async () => {
    try {
      const {ics} = await request('/api/productivity', {action:'export_ics'});
      const url = URL.createObjectURL(new Blob([ics], {type:'text/calendar;charset=utf-8'}));
      const a = document.createElement('a'); a.href = url; a.download = 'EON-Gorevler.ics'; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { toast(error.message); }
  };
  el('importIcsInput').onchange = async () => {
    const file = el('importIcsInput').files[0];
    el('importIcsInput').value = '';
    if (!file) return;
    try {
      const text = await file.text();
      const res = await request('/api/productivity', {action:'import_ics', ics:text, project:currentChat()?.project || ''});
      renderState(res.state);
      toast(`${res.imported} takvim etkinliği görev olarak içe aktarıldı.`);
    } catch (error) { toast(error.message); }
  };

  // Command Center handlers
  el('ccRefreshBtn').onclick = renderHealthPage;
  el('ccTestOllama').onclick = async () => { await loadModels(); await renderHealthPage(); toast('Ollama model listesi yenilendi.'); };
  el('ccUnloadOllama').onclick = async () => {
    try { await request('/api/runtime', {action:'unload'}); await renderHealthPage(); toast('Model bellekten boşaltıldı.'); }
    catch (error) { toast(error.message); }
  };
  el('ccTestGemini').onclick = async () => {
    try {
      const {models, selected} = await request('/api/credentials', {action:'test'});
      options(el('cloudModel'), models.map(m => [m, m.slice(7)]), selected);
      state.gemini_models_ready = Boolean(models.length);
      await renderHealthPage();
      toast('Gemini bağlantısı doğrulandı.');
    } catch (error) { await renderHealthPage(); toast(error.message); }
  };
}
