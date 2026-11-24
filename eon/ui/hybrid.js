'use strict';

const cities = [
  ['Adana',37.000,35.321],['Ankara',39.933,32.860],['Antalya',36.897,30.713],
  ['Berlin',52.520,13.405],['Bursa',40.195,29.061],['Diyarbakır',37.914,40.230],
  ['Eskişehir',39.767,30.525],['Gaziantep',37.066,37.379],['İstanbul',41.009,28.978],
  ['İzmir',38.424,27.143],['Konya',37.872,32.485],['Londra',51.507,-0.128],['Trabzon',41.002,39.717]
];
let weatherLoaded = false, weatherEpoch = 0;
const CURATED_GEMINI_MODELS = [
  ['models/gemini-3.8-flash', 'Gemini 3.8 Flash'],
  ['models/gemini-4.0-helium', 'Gemini 4.0 Helium'],
  ['models/gemini-3.8-pro', 'Gemini 3.8 Pro'],
  ['models/gemini-2.5-flash', 'Gemini 2.5 Flash'],
  ['models/gemini-2.5-pro', 'Gemini 2.5 Pro'],
];

function formatGeminiModelLabel(id) {
  const short = String(id || '').replace(/^models\//, '');
  const match = CURATED_GEMINI_MODELS.find(([k]) => k === id || k.endsWith(short));
  if (match) return match[1];
  return 'Gemini · ' + short;
}

function getAvailableGeminiEntries() {
  const raw = Array.isArray(state?.cloud_models) && state.cloud_models.length
    ? state.cloud_models
    : CURATED_GEMINI_MODELS.map(([k]) => k);
  const seen = new Set();
  const entries = [];
  for (const id of raw) {
    if (!seen.has(id)) {
      seen.add(id);
      entries.push([id, formatGeminiModelLabel(id)]);
    }
  }
  return entries;
}

function syncUnifiedModelSelect() {
  const sel = el('modelSelect');
  if (!sel || !state) return;
  const chat = currentChat();
  const chatOpts = state.extras?.chat_options?.[chat?.id] || {};
  const projOpts = state.extras?.projects?.[chat?.project] || {};
  const local = chatOpts.model || projOpts.model || state.model;
  const activeVal = state.cloud_model || local || 'models/gemini-3.8-flash';
  sel.replaceChildren();
  sel.hidden = false;
  sel.disabled = false;

  const geminiGroup = document.createElement('optgroup');
  geminiGroup.label = 'Google Gemini (Önerilen)';
  for (const [val, label] of getAvailableGeminiEntries()) {
    geminiGroup.appendChild(new Option(label, val));
  }
  sel.appendChild(geminiGroup);

  if (installedModels.length) {
    const localGroup = document.createElement('optgroup');
    localGroup.label = 'Yerel Ollama';
    for (const m of installedModels) {
      localGroup.appendChild(new Option('Yerel · ' + m, m));
    }
    sel.appendChild(localGroup);
  }
  if ([...sel.options].some(o => o.value === activeVal)) {
    sel.value = activeVal;
  } else if (sel.options.length) {
    sel.selectedIndex = 0;
  }
}

function renderHybrid() {
  const metrics = state.metrics || {};
  const chat = currentChat();
  const chatOpts = state.extras.chat_options[chat.id] || {};
  const projOpts = state.extras.projects[chat.project] || {};
  const local = chatOpts.model || projOpts.model || state.model;
  const activeProfile = chatOpts.profile || projOpts.profile || 'balanced';
  const profileLabel = state.profiles?.[activeProfile]?.name || 'Dengeli';
  const tokLabel = metrics.measured_tokens && metrics.output_tokens != null
    ? `${metrics.output_tokens} tok`
    : '';
  const modelLabel = state.cloud_model
    ? formatGeminiModelLabel(state.cloud_model)
    : 'Yerel · ' + local;
  el('providerBadge').textContent = modelLabel
    + ' · ' + profileLabel
    + (metrics.seconds != null ? ' · ' + metrics.seconds + ' sn' : '')
    + (tokLabel ? ' · ' + tokLabel : '');
  el('providerBadge').title = metrics.time ? new Date(metrics.time*1000).toLocaleString()+
    ' · '+metrics.model+' · İlk token '+(metrics.first ?? '—')+' sn · '+
    (metrics.measured_tokens ? `Girdi: ${metrics.input_tokens ?? '—'}, Çıktı: ${metrics.output_tokens ?? '—'}` : `Yaklaşık bağlam: ${metrics.context_estimate ?? '—'} token`) : '';
  syncUnifiedModelSelect();
  if (el('profileSelect')) el('profileSelect').value = activeProfile;
  const resBtn = el('researchToggle');
  if (resBtn) {
    const resOn = Boolean(chatOpts.research && state.cloud_model);
    resBtn.setAttribute('aria-pressed', String(resOn));
    resBtn.classList.toggle('active', resOn);
  }
  const pBadge = el('privacySidebarBadge');
  if (pBadge) {
    pBadge.firstChild.textContent = state.cloud_model && state.cloud_allowed ? 'GEMINI' : 'LOCAL';
    pBadge.title = state.cloud_model && state.cloud_allowed ? 'Google Gemini bulut bağlantısı etkin' : 'Tam yerel çalışma modu';
  }
  if (!disconnected) {
    el('connection').classList.toggle('connected', Boolean((state.cloud_model && state.cloud_allowed) || installedModels.length));
    el('connectionText').textContent = state.cloud_model
      ? (state.cloud_allowed ? formatGeminiModelLabel(state.cloud_model) : 'Gemini · anahtar bekleniyor')
      : installedModels.length ? 'Yerel model hazır' : 'Hazır';
  }
  el('keepAlive').value = state.keep_alive;
  const geminiPrefs = state.gemini_preferences || {consent:false,memory:false,instructions:false,model:''};
  const gemEntries = getAvailableGeminiEntries();
  const preferredGem = geminiPrefs.model || state.cloud_model || 'models/gemini-3.8-flash';
  options(el('cloudModel'), gemEntries, preferredGem);
  el('shareMemory').checked = geminiPrefs.memory;
  el('sharePrefs').checked = geminiPrefs.instructions;
  el('cloudPrivacyOff').hidden = !geminiPrefs.consent;
  const pref = state.weather_pref || {enabled:false};
  if (el('forecast')) {
    el('forecast').hidden = !pref.enabled;
    if (pref.enabled) el('forecast').textContent = pref.last || 'Hava durumu';
  }
  if (!weatherLoaded) {
    weatherLoaded = true;
    el('weatherConsent').checked = Boolean(pref.enabled);
    el('weatherRead').disabled = !pref.enabled;
    el('lat').value = pref.lat ?? '';
    el('lon').value = pref.lon ?? '';
  }
}
function wireHybrid() {
  function bind(id, fn) {
    el(id).onclick = async () => {
      const button = el(id);
      button.disabled = true;
      try { await fn(); } catch(error) { toast(error.message); }
      finally { button.disabled = id === 'weatherRead' && !el('weatherConsent').checked; }
    };
  }
  bind('keyEnter', async()=>{
    const result = await request('/api/credentials',{action:'enter'});
    if (result.cancelled) return;
    el('cloudModel').replaceChildren();
    if (result.models?.length) {
      options(el('cloudModel'),result.models.map(m=>[m,m.slice(7)]),result.selected);
      state.gemini_models_ready=true;
    }
    toast(result.models?.length ? 'Anahtar kaydedildi; Gemini modeli hazır.' : result.configured ? 'Anahtar kaydedildi; model listesi için Google bağlantısını test et.' : 'Anahtar eklenmedi.');
  });
  bind('keyDelete',async()=>{
    if (!confirm('Gemini anahtarını kaldırmak istiyor musun?')) return;
    await request('/api/credentials',{action:'remove'});
    el('cloudModel').replaceChildren(); toast('Anahtar kaldırıldı.');
  });
  bind('cloudTest',async()=>{
    const {models,selected}=await request('/api/credentials',{action:'test'});
    options(el('cloudModel'),models.map(m=>[m,m.slice(7)]),selected);
    state.gemini_models_ready=Boolean(models.length);
    toast(models.length ? 'Google model listesi güncellendi.' : 'Uygun model bulunamadı.');
  });
  bind('cloudSample',async()=>{
    const model = el('cloudModel').value;
    if (!model) throw new Error('Önce Google bağlantısını test et.');
    if (!confirm('Sabit bir örnek istem Google’a gönderilecek ve kota kullanılabilir. Devam edilsin mi?')) return;
    const result=await request('/api/credentials',{action:'sample',model,consent:true});
    el('comparison').textContent = result.answer;
  });
  bind('cloudNew',async()=>{
    if(!state.gemini_models_ready) {
      const found=await request('/api/credentials',{action:'test'});
      options(el('cloudModel'),found.models.map(m=>[m,m.slice(7)]),found.selected);
      state.gemini_models_ready=Boolean(found.models.length);
    }
    const model=el('cloudModel').value;
    if (!model) throw new Error('Önce Google bağlantısını test et.');
    const memory=el('shareMemory').checked, instructions=el('sharePrefs').checked;
    const prefs=state.gemini_preferences || {consent:false,memory:false,instructions:false};
    const requiresConsent=!prefs.consent || (memory&&!prefs.memory) || (instructions&&!prefs.instructions);
    if (requiresConsent) {
      const shared=['bu Gemini sohbetinin mesajları ve yakın geçmişi'];
      if(memory) shared.push(state.conversations.find(c=>c.id===state.active_chat_id)?.project ? 'yalnızca mevcut projede seçilen hafıza notları' : 'genel hafıza');
      if(instructions) shared.push('genel kişisel yönergeler ve yalnızca mevcut projenin yönergeleri/modu');
      const first=!prefs.consent;
      const intro=first?(state.gemini_consent_persistent?'Bu, gelecekteki Gemini sohbetleri için kalıcı bir bulut paylaşım izni verir. ':'Şifreli kasa kullanılamıyor; bu izin yalnızca bu oturum boyunca geçerli olacak. '):'Seçilen ek bağlam Google ile paylaşılacak. ';
      if (!confirm(intro+'Google’a gönderilecek: '+shared.join(', ')+'. API kotası/ücreti uygulanabilir; API hesabındaki veri koşulları geçerlidir. İzni daha sonra Ayarlar’dan kapatabilirsin. Onaylıyor musun?')) return;
    }
    const id = state.cloud_model===model ? state.active_chat_id : null;
    renderState(await request('/api/cloud/new',{id,model,consent:requiresConsent,memory,instructions})); showPage('chat');
  });
  bind('cloudPrivacyOff',async()=>{
    if(!confirm('Gemini aktarım iznini kapatılsın mı? Mevcut Gemini sohbetleri bu oturumda yeniden etkinleştirilene kadar yanıt üretemez.')) return;
    renderState(await request('/api/cloud/privacy',{enabled:false}));
    toast('Gemini bulut paylaşım izni kapatıldı.');
  });
  bind('compareModels', async()=>{
    if(!el('cloudModel').value) throw new Error('Önce Google bağlantısını test et.');
    if(!confirm('Aynı 7 × 8 sorusu yerel modele ve Google’a gönderilecek. API kotası kullanılabilir. Devam edilsin mi?')) return;
    const result=await request('/api/compare',{model:el('cloudModel').value,consent:true});
    el('comparison').textContent=result.results.map(r=>r.name+' · '+(r.correct?'doğru':'farklı yanıt')+
      ' · ilk parça '+r.first+' sn · toplam '+r.seconds+' sn').join(' / ');
  });
  bind('localNew',newChat);
  el('keepAlive').onchange = async()=>{
    try { renderState(await request('/api/runtime',{action:'keep',value:el('keepAlive').value})); }
    catch(error){el('keepAlive').value=state.keep_alive;toast(error.message);}
  };
  async function health(action) {
    const s=await request('/api/runtime',{action});
    const mib = value=>typeof value==='number' ? Math.round(value/1048576)+' MiB' : '—';
    const models=s.loaded.map(m=>m.model+' · Model '+mib(m.bytes)+' · VRAM '+mib(m.vram)+
      (m.expires ? ' · Bekletme bitişi '+new Date(m.expires).toLocaleTimeString() : ''));
    el('healthInfo').textContent = [s.connected ? 'Ollama bağlı' : 'Ollama çevrimdışı',...models,
      s.busy ? 'Yanıt hazırlanıyor' : 'Boşta',s.loaded.some(m=>m.model===s.selected)?'Seçili model yüklü':'Seçili model bellekte değil','Yerel sunucu hazır',s.storage,s.gemini_tested ? 'Google model listesi alındı' : 'Google bağlantısı doğrulanmadı'].join(' · ');
  }
  bind('unloadModel',()=>health('unload'));
  bind('runtimeStatus',()=>health('status'));
  cities.forEach(([name],i)=>el('city').append(new Option(name,i)));
  el('city').onchange=()=>{
    if(el('city').value!=='') {
      const [,lat,lon]=cities[Number(el('city').value)];
      el('lat').value=lat; el('lon').value=lon;
    }
  };
  async function saveWeather(enabled) {
    renderState(await request('/api/weather/preferences',{enabled,lat:el('lat').valueAsNumber,lon:el('lon').valueAsNumber}));
    el('weatherRead').disabled=!enabled;
    if (el('forecast')) {
      el('forecast').hidden = !enabled;
      if(!enabled) el('forecast').textContent='';
    }
  }
  el('weatherConsent').onchange=async()=>{
    weatherEpoch++;
    el('weatherRead').disabled=!el('weatherConsent').checked;
    if (!el('weatherConsent').checked) {
      try {await saveWeather(false);} catch(error){toast(error.message);}
    }
  };
  bind('weatherSave',async()=>{await saveWeather(el('weatherConsent').checked);toast('Hava durumu tercihi kaydedildi.');});
  bind('weatherRead',async()=>{
    const version=++weatherEpoch;
    await saveWeather(el('weatherConsent').checked);
    el('forecast').textContent='Hava durumu yükleniyor…';
    try {
      const report=await request('/api/weather',{consent:true});
      if(version===weatherEpoch) el('forecast').textContent=report.label;
    } catch(error) {
      if(version===weatherEpoch) el('forecast').textContent=state.weather_pref.last ? 'Çevrimdışı · eski veri · '+state.weather_pref.last : 'Hava verisi alınamadı';
      throw error;
    }
  });
  el('iconFile').onchange=async()=>{
    const id=editId;
    try {
      const pixels=await iconPixels(el('iconFile').files[0]);
      apps=(await request('/api/apps/icon',{id,pixels})).apps;renderApps();toast('Simge kaydedildi.');
    } catch(error){toast(error.message);}
    el('iconFile').value='';
  };
  bind('iconClear',async()=>{apps=(await request('/api/apps/icon',{id:editId,pixels:null})).apps;renderApps();});
  bind('iconWindows',async()=>{apps=(await request('/api/apps/windows-icon',{id:editId})).apps;renderApps();});
}
function iconDimensions(bytes,type) {
  const v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
  if(bytes.length<24) return null;
  if(type==='image/png' && v.getUint32(0)===0x89504e47 && v.getUint32(4)===0x0d0a1a0a && v.getUint32(12)===0x49484452) {
    for(let pos=8;pos+12<=bytes.length;) {
      if(v.getUint32(pos+4)===0x6163544c) return null;
      pos+=12+v.getUint32(pos);
    }
    return [v.getUint32(16),v.getUint32(20)];
  }
  if(type==='image/jpeg' && v.getUint16(0)===0xffd8) {
    for(let p=2;p+9<bytes.length && bytes[p]===255;) {
      const marker=bytes[p+1], size=v.getUint16(p+2);
      if([192,193,194].includes(marker)) return [v.getUint16(p+5),v.getUint16(p+7)];
      if(size<2 || marker===218) break;
      p+=size+2;
    }
  }
  if(type==='image/webp' && bytes.length>=30 && v.getUint32(0)===0x52494646 && v.getUint32(8)===0x57454250) {
    const tag=v.getUint32(12);
    if(tag===0x56503820 && v.getUint32(23)>>>8===0x9d012a) return [v.getUint16(26,true)&16383,v.getUint16(28,true)&16383];
    if(tag===0x5650384c && bytes[20]===47) {
      const dims=v.getUint32(21,true);
      return [1+(dims&16383),1+((dims>>>14)&16383)];
    }
  }
  if(['image/x-icon','image/vnd.microsoft.icon'].includes(type) && v.getUint32(0)===256 && v.getUint16(4,true)===1) {
    const offset=v.getUint32(18,true), size=v.getUint32(14,true);
    if(offset>=22 && size<=bytes.length-offset) return iconDimensions(bytes.subarray(offset,offset+size),'image/png');
  }
  return null;
}
async function iconPixels(file) {
  if (!file || !file.size || file.size>1048576) throw new Error('En fazla 1 MiB boyutunda bir görsel seç.');
  const bytes=new Uint8Array(await file.arrayBuffer());
  const dimensions=iconDimensions(bytes,file.type);
  if (!dimensions || dimensions.some(n=>!n || n>1024)) throw new Error('Bozuk, hareketli veya 1024 piksel sınırını aşan simge.');
  const bmp=await createImageBitmap(file);
  try {
    if(Math.max(bmp.width,bmp.height)>1024) throw new Error('Simge 1024 piksel sınırını aşıyor.');
    const canvas=document.createElement('canvas'); canvas.width=canvas.height=48;
    const ctx=canvas.getContext('2d');
    const scale=48/Math.max(bmp.width,bmp.height);
    ctx.drawImage(bmp,(48-bmp.width*scale)/2,(48-bmp.height*scale)/2,bmp.width*scale,bmp.height*scale);
    return btoa(String.fromCharCode(...ctx.getImageData(0,0,48,48).data));
  } finally {bmp.close();}
}
function drawAppIcon(container,app) {
  const pixels=app.icon;
  if(pixels) {
    const canvas=document.createElement('canvas');canvas.width=canvas.height=48;
    const ctx=canvas.getContext('2d');
    const data=ctx.createImageData(48,48);
    data.data.set(Uint8Array.from(atob(pixels),c=>c.charCodeAt(0)));
    ctx.putImageData(data,0,0);container.append(canvas);
  } else container.append(svgIcon('i-apps'));
}
