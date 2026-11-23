/* EON v0.6.1 — Modular UI Extensions:
   - In-process Windows Core Audio Master Volume slider + instant mute
   - Gemini-first setup flow + hardware-tuned local Ollama model recommendations
   - Offline Kill-Switch & Network Inspector
   - Clipboard Image Paste (Ctrl+V) + Windows Native OCR trigger
   - Live Studio Split-Pane Preview
*/
'use strict';

let currentVolMuted = false;
let volTimer = 0;

function syncVolumeUi(v) {
  if (!v || !v.supported) return;
  currentVolMuted = Boolean(v.muted);
  const lvl = Number.isFinite(v.level) ? v.level : 50;
  if (el('volSlider')) el('volSlider').value = String(lvl);
  if (el('settingsVolSlider')) el('settingsVolSlider').value = String(lvl);
  if (el('volPercentLabel')) el('volPercentLabel').textContent = currentVolMuted ? 'Sessiz' : `${lvl}%`;
  el('volumeBar')?.classList.toggle('muted', currentVolMuted);
}

async function refreshVolumeState() {
  try {
    const v = await request('/api/volume', {action:'get'});
    syncVolumeUi(v);
  } catch {}
}

function setMasterVolumeFast(level) {
  const clean = Math.max(0, Math.min(100, Math.round(Number(level))));
  if (el('volPercentLabel')) el('volPercentLabel').textContent = `${clean}%`;
  if (el('volSlider')) el('volSlider').value = String(clean);
  if (el('settingsVolSlider')) el('settingsVolSlider').value = String(clean);
  clearTimeout(volTimer);
  volTimer = setTimeout(async () => {
    try {
      const v = await request('/api/volume', {action:'set', level:clean});
      syncVolumeUi(v);
    } catch (error) { toast(error.message); }
  }, 35);
}

async function toggleMasterMuteFast() {
  try {
    const v = await request('/api/volume', {action:'mute', muted:!currentVolMuted});
    syncVolumeUi(v);
    toast(v.muted ? 'Bilgisayar sesi kısıldı (Sessiz).' : `Bilgisayar sesi açıldı (%${v.level}).`);
  } catch (error) { toast(error.message); }
}

function renderHardwareAndSetupBanner() {
  if (!state) return;
  const hw = state.hardware;
  const hwBox = el('hardwareRecommendationBox');
  if (hw && hwBox) {
    const modelsText = (hw.models || []).map(m => `• ${m.name} (${m.size}) — ${m.why}`).join('\n');
    hwBox.textContent = `Donanım Profili: ${hw.label} (${hw.ram_gb ?? '?'} GB RAM · ${hw.cores} çekirdek)\n`
      + `Otomatik Optimize Ayar: Bağlam ${hw.defaults?.context} token · Bekletme ${hw.defaults?.keep_alive}\n`
      + `İsteğe Bağlı Yerel Ollama Kurulumu İçin Bu Bilgisayara Önerilen Modeller:\n${modelsText}\n`
      + `(Kurmak istersen terminalde: ollama pull ${(hw.models?.[0]?.name) || 'qwen3:4b'})`;
  }
  const prefSel = el('preferredProviderSelect');
  if (prefSel && state.setup?.provider) {
    prefSel.value = state.setup.provider;
  }

  let banner = el('welcomeSetupBanner');
  if (!banner && el('welcome')) {
    banner = document.createElement('div');
    banner.id = 'welcomeSetupBanner';
    banner.className = 'welcome-setup-banner';
    el('welcome').appendChild(banner);
  }
  if (banner) {
    banner.replaceChildren();
    const isGeminiReady = Boolean(state.cloud_model && state.cloud_allowed);
    const isOllamaReady = installedModels.length > 0;
    const recModel = hw?.models?.[0]?.name || 'qwen3:4b';
    const title = document.createElement('strong');
    title.textContent = isGeminiReady
      ? `Google Gemini Öncelikli Mod Etkin (${state.cloud_model.replace('models/', '')})`
      : 'Hızlı Başlangıç — Google Gemini API Öncelikli veya İsteğe Bağlı Yerel Ollama';
    const desc = document.createElement('div');
    desc.textContent = isGeminiReady
      ? 'Sohbetlerin doğrudan Google Gemini ile çalışır; Ollama kurman gerekmez.'
      : `1) Önerilen: Ollama kurmadan doğrudan Google Gemini API anahtarınla hemen başla.  2) İsteğe bağlı yerel model: Bilgisayarına (${hw?.ram_gb ?? '?'} GB RAM) uygun önerilen model: ${recModel} (${isOllamaReady ? 'Yerel model hazır' : 'Kurulu değil — isteğe bağlı'}).`;
    const btnRow = document.createElement('div');
    btnRow.className = 'button-row';
    btnRow.append(
      action('Google Gemini API Anahtarı Ayarla (Öncelikli)', () => { showPage('settings'); el('directApiKeyInput')?.focus(); }),
      action(`Yerel Model Önerilerini Gör (${recModel})`, () => { showPage('settings'); el('hardwareRecommendationBox')?.scrollIntoView({block:'center'}); })
    );
    banner.append(title, desc, btnRow);
  }
}

function wireV060Modules() {
  // 1. Fast Master Volume Controls
  el('volSlider')?.addEventListener('input', e => setMasterVolumeFast(e.target.value));
  el('settingsVolSlider')?.addEventListener('input', e => setMasterVolumeFast(e.target.value));
  el('volMuteBtn')?.addEventListener('click', toggleMasterMuteFast);
  el('settingsVolMuteBtn')?.addEventListener('click', toggleMasterMuteFast);
  setTimeout(refreshVolumeState, 120);

  // 2. Direct in-page Gemini API Key save & Gemini-first provider preference
  if (el('directKeySaveBtn')) {
    el('directKeySaveBtn').onclick = async () => {
      const keyVal = el('directApiKeyInput')?.value.trim() || '';
      if (!keyVal) return toast('Google Gemini API anahtarını gir.');
      try {
        el('directApiKeyInput').value = '';
        const result = await request('/api/credentials', {action:'set', key:keyVal});
        await request('/api/setup', {action:'complete', provider:'gemini'});
        if (result.models?.length) {
          options(el('cloudModel'), result.models.map(m => [m, m.slice(7)]), result.selected);
          state.gemini_models_ready = true;
        }
        toast(result.models?.length ? 'API anahtarı DPAPI kasasına şifrelendi ve Gemini modelleri hazır!' : 'API anahtarı şifrelenerek kaydedildi.');
      } catch (error) { toast(error.message); }
    };
  }
  if (el('preferredProviderSelect')) {
    el('preferredProviderSelect').onchange = async () => {
      try {
        const res = await request('/api/setup', {action:'complete', provider:el('preferredProviderSelect').value});
        renderState(res.state);
        toast('Varsayılan sağlayıcı önceliği kaydedildi.');
      } catch (error) { toast(error.message); }
    };
  }

  // 3. Clipboard Image Paste (Ctrl+V screenshot directly into chat)
  const msgInput = el('messageInput');
  if (msgInput) {
    msgInput.addEventListener('paste', async evt => {
      const items = [...(evt.clipboardData?.items || [])];
      const imgItems = items.filter(it => it.kind === 'file' && ['image/png', 'image/jpeg', 'image/webp'].includes(it.type));
      if (!imgItems.length) return;
      evt.preventDefault();
      for (const item of imgItems) {
        const file = item.getAsFile();
        if (!file) continue;
        if (pendingVisionImages.length >= 4) { toast('En fazla 4 görsel eklenebilir.'); break; }
        if (file.size > 4 * 1024 * 1024) { toast('Görsel boyutu 4 MiB sınırını aşıyor.'); continue; }
        const bytes = new Uint8Array(await file.arrayBuffer());
        let bin = '';
        for (let i = 0; i < bytes.length; i += 8192) bin += String.fromCharCode(...bytes.subarray(i, i + 8192));
        pendingVisionImages.push({
          name: `pano_${new Date().toLocaleTimeString().replace(/:/g, '')}.png`,
          mime: file.type,
          size: file.size,
          data: btoa(bin),
        });
      }
      if (typeof renderVisionBar === 'function') renderVisionBar();
      toast('Panodaki ekran görüntüsü sohbete eklendi.');
    });

    // Barge-in: stop speech immediately when user starts typing
    msgInput.addEventListener('keydown', () => {
      if (typeof stopVoicePlayback === 'function') {
        stopVoicePlayback();
      }
    });
  }

  // 4. Live Split-Pane Studio Preview while typing
  const stContent = el('studioContent');
  const stTitle = el('studioTitle');
  let studioDebounce = 0;
  const triggerLiveStudioPreview = () => {
    clearTimeout(studioDebounce);
    studioDebounce = setTimeout(() => {
      if (stTitle?.value.trim() && stContent?.value.trim()) {
        el('studioPreviewBtn')?.click();
      }
    }, 450);
  };
  stContent?.addEventListener('input', triggerLiveStudioPreview);
  stTitle?.addEventListener('input', triggerLiveStudioPreview);

  // 5. Offline Kill-Switch & Desktop Shortcut buttons in Command Center
  const killBtn = el('ccOfflineKillSwitchBtn');
  if (killBtn) {
    killBtn.onclick = async () => {
      const next = !Boolean(state?.offline_kill_switch);
      try {
        const updated = await request('/api/runtime', {action:'offline', value:next});
        renderState(updated);
        if (typeof renderHealthPage === 'function') await renderHealthPage();
        toast(next ? 'Tam Çevrimdışı Mod (Kill-Switch) etkinleştirildi. Tüm dış ağ çağrıları bloke edildi.' : 'Tam Çevrimdışı Mod kapatıldı.');
      } catch (error) { toast(error.message); }
    };
  }

  const scBtn = el('ccDesktopShortcutBtn');
  if (scBtn) {
    scBtn.onclick = async () => {
      try {
        const res = await request('/api/runtime', {action:'desktop_shortcut'});
        toast(`Masaüstü kısayolu oluşturuldu: ${res.shortcut}`);
      } catch (error) { toast(error.message); }
    };
  }
}

const _origRenderStateV061 = typeof renderState === 'function' ? renderState : null;
if (_origRenderStateV061) {
  window.renderState = function (next) {
    _origRenderStateV061(next);
    renderHardwareAndSetupBanner();
  };
}

// Enhance renderVisionBar to include offline Windows OCR button on attached images
const _origRenderVisionBar = typeof renderVisionBar === 'function' ? renderVisionBar : null;
if (_origRenderVisionBar) {
  window.renderVisionBar = function () {
    _origRenderVisionBar();
    const bar = el('visionPreviewBar');
    if (!bar || !pendingVisionImages.length) return;
    [...bar.querySelectorAll('.vision-chip')].forEach((chip, idx) => {
      const img = pendingVisionImages[idx];
      if (!img) return;
      const ocrBtn = action('OCR Metin Çıkar', async () => {
        try {
          toast('Windows yerleşik OCR ile metin çıkarılıyor...');
          const res = await request('/api/knowledge', {action:'ocr', name:img.name, data:img.data});
          const inp = el('messageInput');
          inp.value = (inp.value ? inp.value + '\n\n' : '') + `[Görsel OCR Metni - ${img.name}]:\n` + res.text;
          inp.dispatchEvent(new Event('input'));
          toast('Görseldeki metin mesaj alanına aktarıldı.');
        } catch (error) { toast(error.message); }
      });
      chip.insertBefore(ocrBtn, chip.lastElementChild);
    });
  };
}

// Enhance renderHealthPage to populate Network Inspector Log and Kill-Switch state
const _origRenderHealthPage = typeof renderHealthPage === 'function' ? renderHealthPage : null;
if (_origRenderHealthPage) {
  window.renderHealthPage = async function () {
    await _origRenderHealthPage();
    try {
      const s = await request('/api/runtime', {action:'status'});
      const killBtn = el('ccOfflineKillSwitchBtn');
      if (killBtn) {
        const on = Boolean(s.offline_kill_switch);
        killBtn.setAttribute('aria-pressed', String(on));
        killBtn.classList.toggle('active', on);
        killBtn.textContent = on ? 'Tam Çevrimdışı Mod: ETKİN (Dış Ağ Kapalı)' : 'Tam Çevrimdışı Mod: Kapalı';
      }
      const nLog = el('ccNetworkLog');
      if (nLog) {
        nLog.replaceChildren();
        const logs = s.network_log || [];
        if (!logs.length) {
          const empty = document.createElement('div');
          empty.className = 'empty-hint';
          empty.textContent = 'Bu oturumda herhangi bir dış ağ bağlantısı yapılmadı (100% Yerel).';
          nLog.append(empty);
        } else {
          for (const net of logs) {
            const row = document.createElement('div');
            row.className = 'conversation-row';
            const info = document.createElement('div');
            info.className = 'conversation-open';
            const h = document.createElement('strong');
            const dt = net.time ? new Date(net.time * 1000).toLocaleTimeString() : '';
            h.textContent = `${dt} · ${net.host} · ${net.status}`;
            const sub = document.createElement('small');
            sub.textContent = `Amaç: ${net.purpose}`;
            info.append(h, sub);
            row.append(info);
            nLog.append(row);
          }
        }
      }
    } catch {}
  };
}

document.addEventListener('DOMContentLoaded', wireV060Modules);
