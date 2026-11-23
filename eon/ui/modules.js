/* EON v0.6.0 — Modular UI Extensions:
   - Offline Kill-Switch & Network Inspector
   - Clipboard Image Paste (Ctrl+V) + Windows Native OCR trigger
   - Hands-Free Barge-In Voice Mode
   - Live Studio Split-Pane Preview
   - Multi-step Agent Plan Approval Cards
   - Citation Search Term Highlighting
*/
'use strict';

function wireV060Modules() {
  // 1. Clipboard Image Paste (Ctrl+V screenshot directly into chat)
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
      if (activeAudioPlayer && typeof stopVoicePlayback === 'function') {
        stopVoicePlayback();
      }
    });
  }

  // 2. Live Split-Pane Studio Preview while typing
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

  // 3. Offline Kill-Switch & Desktop Shortcut buttons in Command Center
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
