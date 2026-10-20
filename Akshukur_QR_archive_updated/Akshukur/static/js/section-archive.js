/* Isolated enhancement for historical places and school. No shared modal changes. */
(function () {
  'use strict';
  const root = document.querySelector('.heritage-section');
  if (!root) return;
  const viewer = root.querySelector('#archiveViewer');
  let photos = [], position = 0, opener = null;
  const image = root.querySelector('#archiveViewerImage');
  function renderPhoto() {
    const photo = photos[position];
    image.hidden = false;
    root.querySelector('#archiveViewerError').hidden = true;
    image.src = photo.dataset.src;
    image.alt = photo.dataset.caption;
    root.querySelector('#archiveViewerCaption').textContent = photo.dataset.caption;
    root.querySelector('#archiveViewerNote').textContent = photo.dataset.note;
    root.querySelector('#archiveViewerSource').textContent = photo.dataset.provenance;
    root.querySelector('#archiveViewerCount').textContent = (position + 1) + ' / ' + photos.length;
    viewer.querySelectorAll('[data-viewer-prev], [data-viewer-next]').forEach(button => { button.disabled = photos.length < 2; });
  }
  function movePhoto(step) {
    if (!photos.length) return;
    position = (position + step + photos.length) % photos.length;
    renderPhoto();
  }
  if (viewer) {
    image.addEventListener('error', () => { image.hidden = true; root.querySelector('#archiveViewerError').hidden = false; });
    root.addEventListener('click', event => {
      const button = event.target.closest('[data-archive-photo]');
      if (!button) return;
      photos = Array.from(root.querySelectorAll('[data-archive-photo]')).filter(photo => photo.dataset.gallery === button.dataset.gallery && photo.dataset.src);
      position = photos.indexOf(button);
      opener = button;
      renderPhoto();
      viewer.showModal();
      viewer.querySelector('[data-viewer-close]').focus();
    });
    viewer.querySelector('[data-viewer-close]').addEventListener('click', () => viewer.close());
    viewer.querySelector('[data-viewer-prev]').addEventListener('click', () => movePhoto(-1));
    viewer.querySelector('[data-viewer-next]').addEventListener('click', () => movePhoto(1));
    viewer.addEventListener('keydown', event => {
      if (event.key === 'ArrowLeft') { event.preventDefault(); movePhoto(-1); }
      if (event.key === 'ArrowRight') { event.preventDefault(); movePhoto(1); }
    });
    viewer.addEventListener('click', event => {
      const rect = viewer.getBoundingClientRect();
      if (event.target === viewer && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) viewer.close();
    });
    viewer.addEventListener('close', () => { if (opener && opener.isConnected) opener.focus({preventScroll:true}); });
  }
  // Missing/corrupt images degrade locally; never guess another image path.
  root.querySelectorAll('.heritage-zoom img').forEach(img => {
    function missing() {
      const button = img.closest('button');
      const placeholder = document.createElement('div');
      placeholder.className = 'img-placeholder';
      placeholder.textContent = 'Фото жүктелмеді. Қосымша дерек қажет.';
      button.replaceWith(placeholder);
    }
    img.addEventListener('error', missing, {once:true});
    if (img.complete && img.naturalWidth === 0) missing();
  });
  const controls = root.querySelector('#schoolPeriodControls');
  if (controls) {
    controls.hidden = false;
    function choosePeriod(period) {
      controls.querySelectorAll('[data-period]').forEach(button => {
        const active = button.dataset.period === period;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', String(active));
      });
      root.querySelectorAll('[data-school-period]').forEach(card => { card.hidden = period !== 'all' && card.dataset.schoolPeriod !== period; });
      root.querySelector('#schoolPeriods').classList.toggle('is-single', period !== 'all');
      root.querySelector('#schoolPeriodStatus').textContent = period === 'all' ? 'Екі кезең көрсетілген.' : (period === 'yesterday' ? 'Кеше: тарихи материал.' : 'Бүгін: қазіргі мектеп.');
    }
    controls.addEventListener('click', event => {
      const button = event.target.closest('[data-period]');
      if (button) choosePeriod(button.dataset.period);
    });
    root.querySelectorAll('[data-period-link]').forEach(link => link.addEventListener('click', () => choosePeriod(link.dataset.periodLink)));
    if (location.hash === '#schoolToday') choosePeriod('today');
    if (location.hash === '#schoolYesterday') choosePeriod('yesterday');
  }
})();
