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
  body.append(action('Onayla ve kaydet',async()=>{
    renderState(await request('/api/memory',{value:note.value}));el('libraryDialog').close();
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
let focusDeadline=0, focusInterval=0;
function focusMode() {
  const body=dialog('Odak modu');
  const minutes=field(body,'Dakika','input');minutes.type='number';minutes.min=1;minutes.max=120;minutes.value=25;
  const display=document.createElement('p');body.append(display);
  const update=()=>{
    const remaining=Math.max(0,Math.ceil((focusDeadline-Date.now())/1000));
    display.textContent=remaining ? Math.floor(remaining/60)+':'+String(remaining%60).padStart(2,'0') : 'Oturum hazır';
  };
  body.append(action('Başlat',()=>{
    if(!minutes.checkValidity() || !minutes.value) throw new Error('1–120 dakika seç.');
    focusDeadline=Date.now()+Number(minutes.value)*60000;
    clearInterval(focusInterval);update();
    focusInterval=setInterval(()=>{
      if(Date.now()>=focusDeadline) {clearInterval(focusInterval);toast('Odak oturumu tamamlandı.');}
      update();
    },1000);
  }),action('Durdur',()=>{focusDeadline=0;clearInterval(focusInterval);update();}));
  update();
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
  const body=dialog('Şifreli yedek');
  const advice=document.createElement('p');advice.textContent='Yedek sohbetleri ve EON tercihlerini içerir. API anahtarını ve Windows uygulama yollarını yeniden girmen gerekir.';
  body.append(advice);
  const pass=field(body,'Yedek parolası','input');pass.type='password';pass.autocomplete='new-password';
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
  search.placeholder='Hafıza kaydı ara';search.setAttribute('aria-label','Hafıza kaydı ara');search.id='memorySearch';
  el('notes').before(search);search.oninput=renderNotes;
}
