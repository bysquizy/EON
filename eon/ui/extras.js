/* EON arayüz eklentisi — mevcut istemci işlevlerini (state, openChat, renderState) kullanır; ağ isteği yapmaz. */
(() => {
  'use strict';
  const root = document.documentElement, $ = id => document.getElementById(id);
  const store = {get: k => { try { return localStorage.getItem(k); } catch { return null; } },
                 set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* tercih kaydedilemedi */ } }};
  if (store.get('eon-rail') === 'min') root.dataset.rail = 'min';

  // Kenar çubuğu: sohbet listesi + daraltma
  const rail = document.createElement('div');
  rail.id = 'chatRail';
  rail.setAttribute('aria-label', 'Sohbetler');
  document.querySelector('.sidebar .nav-divider').after(rail);
  document.querySelector('[data-view=memory]').innerHTML = '<svg viewBox="0 0 24 24"><path d="M6 4h12v16l-6-4-6 4z"/></svg>';
  const toggle = document.createElement('button');
  toggle.type = 'button'; toggle.id = 'railToggle'; toggle.className = 'icon-button';
  toggle.title = 'Kenar çubuğu (Ctrl+B)'; toggle.setAttribute('aria-label', toggle.title);
  toggle.innerHTML = '<svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h10"/></svg>';
  document.querySelector('.brand').prepend(toggle);
  toggle.setAttribute('aria-controls', 'chatRail');
  toggle.setAttribute('aria-expanded', String(root.dataset.rail !== 'min'));
  toggle.onclick = () => {
    const min = root.dataset.rail !== 'min';
    if (min) root.dataset.rail = 'min'; else delete root.dataset.rail;
    toggle.setAttribute('aria-expanded', String(!min));
    store.set('eon-rail', min ? 'min' : 'max');
  };
  document.addEventListener('keydown', e => {
    if (matchMedia('(min-width:1101px)').matches && e.ctrlKey && !e.altKey && e.code === 'KeyB') { e.preventDefault(); toggle.click(); }
  });
  function renderRail() {
    if (typeof state === 'undefined' || !state) return;
    rail.replaceChildren();
    const chats = state.conversations;
    for (const [label, list] of [['SABİTLENENLER', chats.filter(c => c.pinned)], ['SOHBETLER', chats.filter(c => !c.pinned)]]) {
      if (!list.length) continue;
      const head = document.createElement('h6');
      head.textContent = label;
      rail.append(head);
      for (const chat of list) {
        const item = document.createElement('button'), text = document.createElement('span');
        item.type = 'button'; item.title = chat.title; text.textContent = chat.title;
        item.className = 'rail-item' + (chat.id === state.active_chat_id ? ' on' : '');
        if (chat.id === state.active_chat_id) item.setAttribute('aria-current', 'true');
        item.append(text);
        item.onclick = () => openChat(chat.id);
        rail.append(item);
      }
    }
  }

  // Tahmini bağlam doluluğu (sunucudaki bayt bütçesiyle aynı yaklaşım)
  const meter = document.createElement('span'), bar = document.createElement('i'),
        fill = document.createElement('b'), label = document.createElement('em'), enc = new TextEncoder();
  meter.id = 'ctxMeter'; meter.title = 'Tahmini bağlam doluluğu';
  bar.append(fill); meter.append(label, bar);
  $('busyMessage').before(meter);
  function renderMeter() {
    if (typeof state === 'undefined' || !state) return;
    const budget = Math.max(1, (state.context - state.output) * 2);
    const used = state.history.slice(-24).reduce((n, m) => n + enc.encode(m.content).length + 24, 400);
    const pct = Math.min(100, Math.round(used / budget * 100));
    fill.style.width = pct + '%';
    label.textContent = 'Bağlam ~%' + pct;
    meter.classList.toggle('warn', pct > 85);
  }

  // En alta kaydır düğmesi
  const log = $('chatLog'), down = document.createElement('button');
  down.id = 'toBottom'; down.type = 'button'; down.className = 'hidden'; down.setAttribute('aria-label', 'En alta kaydır');
  down.innerHTML = '<svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg>';
  $('view-chat').append(down);
  const sync = () => down.classList.toggle('hidden', log.scrollHeight - log.scrollTop - log.clientHeight < 160);
  log.addEventListener('scroll', sync, {passive: true});
  down.onclick = () => log.scrollTo({top: log.scrollHeight, behavior: root.dataset.reduced === 'true' || matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});

  // Yazma alanı otomatik yükseklik (tek satırda kaydırma çubuğu oklarını gizler)
  const input = $('messageInput');
  const fit = () => {
    if (!input.value) {
      input.style.height = '24px';
      input.style.overflowY = 'hidden';
      return;
    }
    input.style.height = '24px';
    const sh = input.scrollHeight;
    input.style.height = Math.min(Math.max(sh, 24), 140) + 'px';
    input.style.overflowY = sh > 140 ? 'auto' : 'hidden';
  };
  input.addEventListener('input', fit);
  input.addEventListener('keydown', () => setTimeout(fit));
  $('sendButton').addEventListener('click', () => setTimeout(fit));

  const original = renderState;
  renderState = function (next) { original(next); renderRail(); renderMeter(); fit(); sync(); };
  renderRail(); renderMeter();
})();
