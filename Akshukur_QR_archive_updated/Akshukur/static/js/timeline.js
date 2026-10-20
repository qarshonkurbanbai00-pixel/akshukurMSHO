/* ============================================================
   timeline.js — тарихи тізбекті дәлелдеме деңгейі бойынша сүзу
   ============================================================ */
(function () {
  'use strict';
  const bar = document.getElementById('timelineFilters');
  if (!bar) return;
  const items = document.querySelectorAll('.tl-item');
  const empty = document.getElementById('timelineEmpty');

  bar.addEventListener('click', e => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    bar.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const f = btn.dataset.filter;
    let visible = 0;
    items.forEach(it => {
      const show = f === 'all' || it.dataset.evidence === f;
      it.classList.toggle('hide', !show);
      if (show) visible++;
    });
    if (empty) empty.hidden = visible > 0;
  });

  // URL hash арқылы нақты кезеңге келгенде карточканы жарқылдату
  if (location.hash) {
    const target = document.querySelector(location.hash);
    if (target) {
      setTimeout(() => {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        const card = target.querySelector('.tl-card');
        if (card) {
          card.style.borderColor = 'var(--gold)';
          setTimeout(() => { card.style.borderColor = ''; }, 2500);
        }
      }, 300);
    }
  }
})();
