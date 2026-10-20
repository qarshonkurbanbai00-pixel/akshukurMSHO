/* ============================================================
   map.js — Leaflet интерактивті картасы
   - Санат бойынша сүзу (маркерлер + тізім + карточкалар)
   - Маркер popup: атауы, фото орны, сипаттама, дереккөз
   - Координатасыз нүктелерге жалған маркер қойылмайды
   - CDN жүктелмесе (интернетсіз) fallback хабарлама көрсетіледі
   ============================================================ */
(function () {
  'use strict';
  const mapEl = document.getElementById('map');
  const fallback = document.getElementById('mapFallback');
  if (!mapEl) return;

  const EV_LABELS = {
    written: '🟢 Жазба дерек', archive: '🔵 Архив дерегі', oral: '🟡 Ауызша дерек',
    research: '🟠 Зерттеу материалы', reconstruction: '🟣 3D реконструкция', needs_data: '⚪ Дерек қажет'
  };
  const CAT_COLORS = {
    auyl: '#2ecc71', qorym: '#e8c47a', medrese: '#a855f7', mektep: '#3b82f6', tulga: '#f97316', madeniet: '#2dd4bf'
  };

  // Leaflet жүктелмесе — жоба бұзылмайды, түсіндірме шығарамыз
  const leafletOK = typeof L !== 'undefined';
  let map = null;
  if (leafletOK) {
    const CENTER = [43.7832, 51.0605]; // Ақшұқыр — бастапқы бағыт
    map = L.map(mapEl, { scrollWheelZoom: true }).setView(CENTER, 13);
    const tiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> қатысушылары'
    }).addTo(map);
    let tileErrors = 0;
    tiles.on('tileerror', () => {
      tileErrors += 1;
      const notice = document.getElementById('mapTileNotice');
      if (notice && tileErrors >= 3) notice.hidden = false;
    });
  } else {
    mapEl.style.display = 'none';
    if (fallback) fallback.hidden = false;
  }

  function markerIcon(cat, duplicateIndex = 0) {
    const color = CAT_COLORS[cat] || '#d9b36c';
    return L.divIcon({
      className: 'custom-marker',
      html: `<div style="width:22px;height:22px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);
             background:${color};border:2px solid #0b1526;box-shadow:0 4px 12px rgba(0,0,0,.5)"></div>`,
      iconSize: [22, 22], iconAnchor: [11 - duplicateIndex * 26, 22], popupAnchor: [duplicateIndex * 26, -22]
    });
  }

  const markers = {}; // place_id -> marker
  const bounds = [];
  const coordinateUses = {};
  let popupTimer;
  const escapeHtml = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function selectCard(id) {
    document.querySelectorAll('.place-card, .place-item').forEach(el => {
      el.classList.toggle('archive-selected', el.dataset.place === id);
    });
    const status = document.getElementById('placeSelectionStatus');
    const card = document.getElementById('card-' + id);
    if (status && card) status.textContent = 'Таңдалды: ' + card.querySelector('h3').textContent;
  }

  const embeddedPlaces = document.getElementById('archivePlacesData');
  const placesPromise = embeddedPlaces
    ? Promise.resolve(JSON.parse(embeddedPlaces.textContent))
    : fetch('/api/places').then(r => { if (!r.ok) throw new Error('places'); return r.json(); });
  placesPromise
    .then(places => {
      if (leafletOK) {
        places.forEach(p => {
          if (!Number.isFinite(p.lat) || !Number.isFinite(p.lng)) return; // координатасыз нүкте картада көрсетілмейді
          // Escape popup content before adding it to Leaflet's HTML.
          const original = p;
          p = {...p, name: escapeHtml(p.name), summary: escapeHtml(p.summary), description: escapeHtml(p.description), photo_note: escapeHtml(p.photo_note)};
          const ev = EV_LABELS[p.evidence] || EV_LABELS.needs_data;
          const srcLinks = (p.sources || []).map(sid =>
            `<a href="/derek-kozder#${encodeURIComponent(sid)}" style="color:#e8c47a">${escapeHtml(sid)}</a>`).join(' · ');
          const imageSrc = p.image_url ? escapeHtml(p.image_url) : null;
          const imgHtml = imageSrc
            ? `<img src="${imageSrc}" alt="${p.name}" style="border-radius:8px;margin:8px 0;width:100%;max-height:200px;object-fit:contain">`
            : `<div style="padding:10px;border:1px dashed rgba(232,196,122,.4);border-radius:8px;color:#9fb0c6;font-size:.8rem;margin:8px 0">${p.photo_note || 'Расталған фото жоқ'}</div>`;
          const coordKey = p.lat + ',' + p.lng;
          const duplicateIndex = coordinateUses[coordKey] || 0;
          coordinateUses[coordKey] = duplicateIndex + 1;
          // Offset only the icon, NEVER the recorded coordinates.
          const m = L.marker([p.lat, p.lng], { icon: markerIcon(p.category, duplicateIndex), title: original.name, alt: original.name })
            .addTo(map)
            .bindPopup(
              `<strong>${p.name}</strong><br>
               <span class="popup-ev">${ev}</span>
               ${imgHtml}
               <span style="font-size:.85rem;color:#c6d2e2">${p.summary}</span><p style="font-size:.85rem;margin-top:8px">${p.description}</p>
               <p style="font-size:.78rem">${escapeHtml(p.coordinate_note || '')}</p>
               <a href="#card-${escapeHtml(p.id)}" data-popup-card="${escapeHtml(p.id)}">Толығырақ →</a>
               ${srcLinks ? `<div style="margin-top:6px;font-size:.78rem">Дереккөз: ${srcLinks}</div>` : ''}`,
              { maxWidth: 300 }
            );
          m.on('click', () => selectCard(p.id));
          m.on('popupopen', () => selectCard(p.id));
          m._cat = p.category;
          markers[p.id] = m;
          bounds.push([p.lat, p.lng]);
        });
        // Барлық маркер сыйатындай шекара (Ақшұқыр аймағына бағытталған)
        if (bounds.length > 1) map.fitBounds(L.latLngBounds(bounds).pad(0.2));
      }

      /* ---- Санат сүзгісі ---- */
      const filterBar = document.getElementById('mapFilters');
      if (filterBar) {
        filterBar.addEventListener('click', e => {
          const btn = e.target.closest('.filter-btn');
          if (!btn) return;
          filterBar.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          filterBar.querySelectorAll('.filter-btn').forEach(b => b.setAttribute('aria-pressed', String(b === btn)));
          clearTimeout(popupTimer);
          if (map) map.closePopup();
          const cat = btn.dataset.cat;
          // Маркерлер
          if (leafletOK) {
            Object.values(markers).forEach(m => {
              const show = cat === 'all' || m._cat === cat;
              if (show && !map.hasLayer(m)) m.addTo(map);
              if (!show && map.hasLayer(m)) map.removeLayer(m);
            });
          }
          // Тізім + карточкалар
          document.querySelectorAll('.place-item').forEach(el => {
            el.style.display = (cat === 'all' || el.dataset.cat === cat) ? '' : 'none';
          });
          document.querySelectorAll('.place-card').forEach(el => {
            el.style.display = (cat === 'all' || el.dataset.cat === cat) ? '' : 'none';
          });
        });
      }

      /* ---- Тізімнен басқанда ---- */
      document.querySelectorAll('.place-item').forEach(btn => {
        btn.addEventListener('click', () => {
          const id = btn.dataset.place;
          selectCard(id);
          const m = markers[id];
          if (leafletOK && m) {
            clearTimeout(popupTimer);
            map.flyTo(m.getLatLng(), 15, { duration: 0.45 });
            popupTimer = setTimeout(() => { if (map.hasLayer(m)) m.openPopup(); }, 500);
          } else {
            // Координатасыз нүкте — ақпараттық карточкасына скролл
            const card = document.getElementById('card-' + id);
            if (card) {
              card.scrollIntoView({ behavior: 'smooth', block: 'center' });
              card.style.borderColor = 'var(--gold)';
              setTimeout(() => { card.style.borderColor = ''; }, 2000);
            }
          }
        });
      });
      // The original list action also powers card → marker navigation.
      document.querySelectorAll('.place-card').forEach(card => {
        function activate() {
          const button = Array.from(document.querySelectorAll('.place-item')).find(b => b.dataset.place === card.dataset.place);
          if (button) button.click();
          if (map && markers[card.dataset.place]) mapEl.scrollIntoView({behavior:'smooth', block:'center'});
        }
        card.addEventListener('click', e => {
          if (e.target.closest('a, button, summary, details')) return;
          activate();
        });
        card.addEventListener('keydown', e => {
          if (e.target !== card || !['Enter', ' '].includes(e.key)) return;
          e.preventDefault(); activate();
        });
        const mapButton = card.querySelector('[data-show-on-map]');
        if (mapButton) mapButton.addEventListener('click', activate);
      });
      document.addEventListener('click', e => {
        const link = e.target.closest('[data-popup-card]');
        if (!link) return;
        const card = document.getElementById('card-' + link.dataset.popupCard);
        if (card) { selectCard(link.dataset.popupCard); card.querySelector('details').open = true; card.focus({preventScroll:true}); }
      });
      mapEl.dataset.archiveReady = 'true';
    })
    .catch(() => {
      if (mapEl) mapEl.style.display = 'none';
      if (fallback) fallback.hidden = false;
    });
})();
