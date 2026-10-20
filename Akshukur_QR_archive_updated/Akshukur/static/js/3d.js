/* Akshukur reconstruction. Local Three.js r128, MIT. All geometry is illustrative.
   No model is presented as a measured, archival or geographically accurate object. */
(function () {
  'use strict';
  const root = document.getElementById('reconstruction');
  if (!root) return;
  const el = id => document.getElementById(id);
  const host = el('viewer3d'), shell = el('reconShell');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let engine = null, objects = [], selected = null, tour = 0, data = null, failure = null;
  const home = { camera: [28, 22, 34], target: [0, 1, -2] };
  const overview = { camera: [38, 37, 30], target: [0, 0, -6] };
  const steps = [
    ['Кеңістікті шолу', 'Бұл орта — өлшенген тарихи мекен емес. Алдымен дерек пен иллюстрацияның айырмасын есте сақтаңыз.', null],
    ['Мешіт / медресе', 'Бастапқы жобада 1887 жылғы медресе туралы жазба бар. Архив шифры берілмеген; модель пішіні расталмаған.', 'mosque'],
    ['Ескі ағаш', 'Бұл ағаш — табиғи ортаның шартты элементі. Жасы, түрі мен нақты орны белгісіз.', 'tree'],
    ['Құдық', 'Күнделікті тіршіліктің иллюстрациясы. Нақты құдықтың орны мен құрылысына тарихи дәлел берілмеген.', 'well'],
    ['Каспий жағалауы', 'Теңіз бен ауыл кеңістігін салыстырыңыз. Жағалау сызығы мен арақашықтықтар — көркем шарттылық.', 'coast']
  ];
  function error(message) {
    failure = message;
    el('fallbackMessage').textContent = message;
    el('viewerFallback').hidden = false;
    el('modelStatus').textContent = '3D қолжетімсіз · деректер сақталған';
    document.querySelectorAll('[data-engine]').forEach(b => { b.disabled = true; });
    if (engine) engine.failed = true;
    if (!objects.length) document.querySelectorAll('#objectList button').forEach(b => { b.disabled = true; });
  }
  el('btnRetry').onclick = () => window.location.reload();
  function photoMissing() {
    el('cardPhoto').hidden = true;
    el('cardPhotoNote').hidden = false;
    el('cardPhotoNote').textContent = 'Фото жүктелмеді. Бастапқы файл жолын тексеріңіз; бұл фото тарихи дәлел ретінде қолданылмайды.';
  }
  el('cardImage').onerror = photoMissing;
  function card(item) {
    selected = item.id;
    ['Label', 'Title', 'Description', 'Source', 'Unknown'].forEach((field, i) => {
      el('card' + field).textContent = item[['label', 'name', 'description', 'source', 'unknown'][i]];
    });
    el('cardPhotoNote').textContent = item.photo_note;
    el('cardPhotoNote').hidden = false;
    el('cardPhoto').hidden = !item.photo;
    if (item.photo) {
      el('cardImage').alt = item.name + ' — бастапқы архив материалы';
      el('cardImage').src = root.dataset.static + item.photo;
      el('cardPhotoCaption').textContent = item.photo_note;
    }
    const link = el('cardSourceLink');
    link.hidden = !item.source_url;
    if (item.source_url) link.href = item.source_url;
    document.querySelectorAll('[data-object]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.object === item.id)));
  }
  function choose(id, move = true) {
    const item = objects.find(o => o.id === id);
    if (!item) return;
    card(item);
    if (engine && !engine.failed) {
      engine.highlight(id);
      engine.rotate(false);
      if (move) engine.fly(item.camera, item.target);
    }
  }
  el('objectList').onclick = e => {
    const b = e.target.closest('[data-object]');
    if (b) choose(b.dataset.object);
  };
  function showTour(index) {
    tour = index;
    const [title, text, id] = steps[tour];
    el('tourTitle').textContent = String(tour + 1).padStart(2, '0') + ' / 05 · ' + title;
    el('tourText').textContent = text;
    el('tourProgress').textContent = (tour + 1) + ' / 5';
    el('tourPrev').disabled = tour === 0 || !!failure;
    el('tourNext').textContent = tour === 4 ? 'Қайта бастау ↺' : 'Келесі →';
    if (id) choose(id);
    else reset(overview, false);
  }
  function reset(view = home, resetTour = true) {
    selected = null;
    document.querySelectorAll('[data-object]').forEach(b => b.setAttribute('aria-pressed', 'false'));
    el('cardLabel').textContent = 'ТАНЫСУ'; el('cardTitle').textContent = 'Төрт нысан — бір орта';
    el('cardDescription').textContent = data.notice;
    el('cardSource').textContent = 'Бастапқы жоба материалдары; егжей-тегжейі нысан карточкаларында.';
    el('cardUnknown').textContent = 'Нақты орындар, өлшемдер және тарихи пішіндер расталмаған.';
    el('cardPhotoNote').textContent = 'Осы төрт нысанның сәйкестендірілген фотолары архивте жоқ.';
    el('cardPhoto').hidden = true; el('cardSourceLink').hidden = true;
    if (engine && !engine.failed) { engine.highlight(null); engine.rotate(false); engine.fly(view.camera, view.target); }
    if (resetTour) { tour = 0; showTour(0); if (engine) engine.fly(view.camera, view.target); }
  }
  el('tourPrev').onclick = () => showTour(Math.max(0, tour - 1));
  el('tourNext').onclick = () => showTour((tour + 1) % 5);
  el('btnReset').onclick = () => reset();
  el('btnOverview').onclick = () => reset(overview);
  function createEngine() {
    if (typeof THREE === 'undefined' || !THREE.OrbitControls) throw new Error('Жергілікті Three.js кітапханасы табылмады. ZIP архивін толық шығарып, static/vendor папкасын тексеріңіз.');
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true });
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = .93;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    host.appendChild(renderer.domElement);
    const scene = new THREE.Scene(); scene.background = new THREE.Color(0xc2d5db);
    scene.fog = new THREE.Fog(0xc2d5db, 85, 195);
    const camera = new THREE.PerspectiveCamera(44, 1, .15, 280);
    function fittedPosition(pos, target) {
      const point = new THREE.Vector3(...pos);
      if (pos === home.camera || pos === overview.camera) {
        const aspect = host.clientWidth / Math.max(1, host.clientHeight);
        const factor = THREE.MathUtils.clamp(1.22 / aspect, 1, 1.6);
        const center = new THREE.Vector3(...target);
        return point.sub(center).multiplyScalar(factor).add(center);
      }
      return point;
    }
    camera.position.copy(fittedPosition(home.camera, home.target));
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.target.fromArray(home.target); controls.enableDamping = true; controls.dampingFactor = .085;
    controls.minDistance = 5; controls.maxDistance = 100;
    controls.minPolarAngle = .16; controls.maxPolarAngle = Math.PI / 2.06;
    controls.autoRotateSpeed = .6; controls.screenSpacePanning = false;
    controls.touches.ONE = THREE.TOUCH.ROTATE; controls.touches.TWO = THREE.TOUCH.DOLLY_PAN;
    scene.add(new THREE.HemisphereLight(0xe5f5ff, 0x8e6f41, .72));
    const sun = new THREE.DirectionalLight(0xffe5bc, 1.3);
    sun.position.set(-26, 42, 24); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048); sun.shadow.camera.left = -45; sun.shadow.camera.right = 45;
    sun.shadow.camera.top = 40; sun.shadow.camera.bottom = -40; sun.shadow.camera.far = 130;
    sun.shadow.normalBias = .025; scene.add(sun);
    const fill = new THREE.DirectionalLight(0xc1d9f5, .4); fill.position.set(35, 18, -20); scene.add(fill);
    const material = (color, roughness = .88) => new THREE.MeshStandardMaterial({ color, roughness });
    const sand = material(0xc7aa79), wall = material(0xe5cf9f), trim = material(0xb99862), dark = material(0x4e483a);
    const blue = material(0x2e6872, .45), wood = material(0x695139), leaf = material(0x61764a), leaf2 = material(0x81915b);
    const details = new THREE.Group(); scene.add(details);
    const groups = {}, pickMeshes = [], positions = {};
    let highlight = null, flight = null, wire = false, quality = 'full', disposed = false;
    function mesh(geo, mat, x, y, z, parent = scene) {
      const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; parent.add(m); return m;
    }
    function box(w, h, d, mat, x, y, z, parent) { return mesh(new THREE.BoxGeometry(w, h, d), mat, x, y, z, parent); }
    function group(id, x, y, z) { const g = new THREE.Group(); g.position.set(x, y, z); scene.add(g); groups[id] = g; return g; }
    function branch(a, b, radius, mat, parent) {
      const start = new THREE.Vector3(...a), end = new THREE.Vector3(...b), vec = end.clone().sub(start);
      const m = mesh(new THREE.CylinderGeometry(radius * .65, radius, vec.length(), 9), mat, 0, 0, 0, parent);
      m.position.copy(start.add(end).multiplyScalar(.5)); m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), vec.normalize()); return m;
    }
    function arch(w, h, depth, mat, x, y, z, parent) {
      const shape = new THREE.Shape(); const r = w / 2;
      shape.moveTo(-r, 0); shape.lineTo(-r, h - r); shape.absarc(0, h - r, r, Math.PI, 0, true);
      shape.lineTo(r, 0); shape.closePath();
      return mesh(new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false, curveSegments: 16 }), mat, x, y, z, parent);
    }
    // A low-relief coastal diorama, deliberately not a geographic model.
    const terrainGeo = new THREE.PlaneGeometry(160, 120, 50, 35); terrainGeo.rotateX(-Math.PI / 2);
    const attr = terrainGeo.attributes.position;
    for (let i = 0; i < attr.count; i++) { const x = attr.getX(i), z = attr.getZ(i) + 42; attr.setZ(i, z); attr.setY(i, .09 * Math.sin(x * .3) * Math.cos(z * .22) + Math.max(0, Math.abs(x) - 24) * .017); }
    terrainGeo.computeVertexNormals(); const land = mesh(terrainGeo, sand, 0, -.12, 0); land.castShadow = false;
    const seaGeo = new THREE.PlaneGeometry(210, 112, 55, 25); seaGeo.rotateX(-Math.PI / 2);
    const sea = mesh(seaGeo, material(0x397f8d, .32), 0, -.25, -74); sea.castShadow = false; sea.material.metalness = .12;
    const beach = mesh(new THREE.PlaneGeometry(160, 5), material(0xb59f77), 0, -.09, -16); beach.rotation.x = -Math.PI / 2; beach.castShadow = false;
    const foam = new THREE.Group(); details.add(foam);
    for (let i = 0; i < 48; i++) {
      const f = mesh(new THREE.PlaneGeometry(1.8 + (i % 4), .08 + (i % 3) * .035), new THREE.MeshBasicMaterial({ color: 0xd2e6df, transparent: true, opacity: .35, depthWrite: false }), (i % 16) * 6 - 44, -.04, -18.8 - Math.floor(i / 16) * 1.8, foam);
      f.rotation.x = -Math.PI / 2; f.rotation.z = Math.sin(i) * .1; f.castShadow = false;
    }
    // Mosque: illustrative architectural vocabulary, not a reconstruction claim.
    const mosque = group('mosque', -10, 0, 7);
    box(10.8, .35, 8.8, trim, 0, .18, 0, mosque);
    box(9.6, 4.5, 7.7, wall, 0, 2.6, 0, mosque);
    box(10, .26, 8.05, trim, 0, 4.9, 0, mosque);
    box(9.8, .18, 7.9, wall, 0, 5.1, 0, mosque);
    mesh(new THREE.CylinderGeometry(2.6, 2.6, .6, 40), wall, 0, 5.4, -.3, mosque);
    mesh(new THREE.SphereGeometry(2.6, 40, 24, 0, Math.PI * 2, 0, Math.PI / 2), blue, 0, 5.7, -.3, mosque);
    for (let i = 0; i < 20; i++) {
      const points = []; const az = i * Math.PI / 10;
      for (let j = 0; j <= 20; j++) { const t = j * Math.PI / 40; points.push(new THREE.Vector3(Math.sin(t) * 2.615 * Math.cos(az), 5.7 + Math.cos(t) * 2.615, -.3 + Math.sin(t) * 2.615 * Math.sin(az))); }
      const rib = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), new THREE.LineBasicMaterial({ color: 0x71938a })); mosque.add(rib);
    }
    branch([0, 8.25, -.3], [0, 8.95, -.3], .05, trim, mosque);
    const crescent = mesh(new THREE.TorusGeometry(.25, .045, 7, 28, Math.PI * 1.5), trim, 0, 8.93, -.3, mosque); crescent.rotation.z = -.8;
    box(3.5, 5.9, 1, trim, 0, 3.2, 4.05, mosque);
    box(3.16, 5.5, 1.05, wall, 0, 3.1, 4.07, mosque);
    arch(2.3, 4, .06, trim, 0, .36, 4.61, mosque);
    arch(1.75, 3.2, .07, dark, 0, .36, 4.69, mosque);
    for (let x of [-3.3, 3.3]) { arch(1.18, 2.05, .05, trim, x, 1.65, 3.87, mosque); arch(.84, 1.7, .06, dark, x, 1.78, 3.94, mosque); }
    for (let x of [-4.6, 4.6]) for (let z of [-3.7, 3.7]) box(.4, 4.65, .45, trim, x, 2.62, z, mosque);
    for (let j = 0; j < 3; j++) box(4.4 + j * .8, .13, 1, trim, 0, .29 - j * .09, 4.9 + j * .58, mosque);
    const minaret = new THREE.Group(); minaret.position.set(5.8, 0, -1.8); mosque.add(minaret);
    mesh(new THREE.CylinderGeometry(.65, .85, 7.6, 16), wall, 0, 3.8, 0, minaret);
    [.5, 5.7, 6.1, 7.5].forEach(h => mesh(new THREE.CylinderGeometry(.91, .91, .2, 16), trim, 0, h, 0, minaret));
    mesh(new THREE.ConeGeometry(.95, 1.5, 24), blue, 0, 8.4, 0, minaret);
    // Old tree: hand-constructed asymmetric branching and layered low-poly crown.
    const tree = group('tree', 11, 0, 7);
    branch([0, 0, 0], [.15, 3.4, -.15], .48, wood, tree);
    const endpoints = [[-2.4, 5.2, .4], [2.2, 5.5, .7], [.7, 6.1, -1.5], [-.9, 5.9, -1.3], [1, 4.6, 2]];
    endpoints.forEach((p, i) => {
      branch([.1, 2.8, -.15], p, .19, wood, tree);
      const c = mesh(new THREE.IcosahedronGeometry(1.8, 1), i % 2 ? leaf : leaf2, ...p, tree); c.scale.set(1.1, .65, .9);
      mesh(new THREE.IcosahedronGeometry(1.1, 1), leaf, p[0] + .6, p[1] + .3, p[2] + .3, tree).scale.set(1, .8, 1);
    });
    for (let i = 0; i < 6; i++) branch([0, .3, 0], [Math.cos(i) * 1.2, .05, Math.sin(i) * 1.2], .12, wood, tree);
    // Well: open ring, dark interior, masonry joints, rope and handle.
    const well = group('well', 0, 0, -6);
    mesh(new THREE.CylinderGeometry(1.15, 1.27, 1.15, 32, 1, true), new THREE.MeshStandardMaterial({ color: 0xcdb688, side: THREE.DoubleSide, roughness: .95 }), 0, .58, 0, well);
    mesh(new THREE.CylinderGeometry(1.08, 1.08, .05, 32), material(0x193b44), 0, .12, 0, well);
    const ring = mesh(new THREE.TorusGeometry(1.15, .17, 8, 36), trim, 0, 1.16, 0, well); ring.rotation.x = Math.PI / 2;
    for (let i = 0; i < 18; i++) {
      const angle = i * Math.PI / 9;
      branch([Math.cos(angle) * 1.22, .05, Math.sin(angle) * 1.22], [Math.cos(angle) * 1.17, 1.1, Math.sin(angle) * 1.17], .014, dark, well);
    }
    [-1.45, 1.45].forEach(x => box(.16, 3.1, .2, wood, x, 1.55, 0, well));
    branch([-1.65, 2.75, 0], [1.65, 2.75, 0], .12, wood, well);
    branch([0, 2.8, 0], [0, .35, 0], .025, trim, well);
    branch([1.65, 2.75, 0], [1.65, 2.2, 0], .07, wood, well);
    branch([1.65, 2.2, 0], [2.05, 2.2, 0], .07, wood, well);
    mesh(new THREE.CylinderGeometry(.2, .15, .35, 12, 1, true), wood, 0, .75, 0, well);
    const coast = group('coast', 0, 0, -23);
    // Invisible pick plane follows visible water, not a fake historical model.
    const coastPick = mesh(new THREE.PlaneGeometry(110, 78), new THREE.MeshBasicMaterial({ visible: false, side: THREE.DoubleSide }), 0, -.15, -32, coast); coastPick.rotation.x = -Math.PI / 2;
    // Sparse terrain detail, fixed deterministic distribution.
    for (let i = 0; i < 70; i++) {
      const x = Math.sin(i * 16.37) * 34, z = Math.cos(i * 7.13) * 15 + 9;
      if ((Math.abs(x + 10) < 8 && Math.abs(z - 7) < 7) || (Math.abs(x - 11) < 4 && Math.abs(z - 7) < 4) || (Math.abs(x) < 3 && Math.abs(z + 6) < 3)) continue;
      if (i % 3) {
        for (let j = 0; j < 3; j++) { const grass = mesh(new THREE.ConeGeometry(.045, .45 + .1 * j, 4), leaf, x + j * .1, .2, z, details); grass.rotation.z = (j - 1) * .2; grass.castShadow = false; }
      } else { const rock = mesh(new THREE.DodecahedronGeometry(.16 + (i % 5) * .07), trim, x, .13, z, details); rock.scale.set(1.4, .6, 1); rock.rotation.y = i; }
    }
    const halo = mesh(new THREE.RingGeometry(1, 1.07, 72), new THREE.MeshBasicMaterial({ color: 0xffd173, side: THREE.DoubleSide, transparent: true, opacity: .85, depthWrite: false }), 0, .12, 0);
    halo.rotation.x = -Math.PI / 2; halo.visible = false; halo.castShadow = false;
    Object.entries(groups).forEach(([id, g]) => {
      g.traverse(o => { if (o.isMesh) { o.userData.objectId = id; pickMeshes.push(o); } });
      const item = objects.find(o => o.id === id);
      positions[id] = new THREE.Vector3(...item.target); positions[id].y += id === 'mosque' ? 6.7 : id === 'tree' ? 4.2 : id === 'well' ? 2.9 : 1;
      if (id === 'coast') positions[id].set(-22, .4, -35);
      const b = document.createElement('button'); b.type = 'button'; b.textContent = id === 'coast' ? 'Каспий жағалауы' : item.name; b.dataset.object = id; b.setAttribute('aria-pressed', 'false');
      b.onclick = () => choose(id); el('reconLabels').appendChild(b);
    });
    function rotate(on) { controls.autoRotate = on; el('btnRotate').setAttribute('aria-pressed', String(on)); }
    function fly(pos, target) {
      controls.enableDamping = false; controls.update(); controls.enableDamping = true;
      flight = { start: performance.now(), from: camera.position.clone(), to: fittedPosition(pos, target), targetFrom: controls.target.clone(), targetTo: new THREE.Vector3(...target) };
      if (reduced) { camera.position.copy(flight.to); controls.target.copy(flight.targetTo); flight = null; controls.update(); }
    }
    function cancelFlight() { flight = null; rotate(false); }
    controls.addEventListener('start', cancelFlight);
    let down = null;
    renderer.domElement.addEventListener('pointerdown', e => { host.focus({ preventScroll: true }); down = { x: e.clientX, y: e.clientY, button: e.button, time: performance.now() }; });
    const ray = new THREE.Raycaster(), pointer = new THREE.Vector2();
    renderer.domElement.addEventListener('pointerup', e => {
      if (!down || down.button !== 0 || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 7 || performance.now() - down.time > 700) { down = null; return; }
      down = null; const rect = renderer.domElement.getBoundingClientRect();
      pointer.set((e.clientX - rect.left) / rect.width * 2 - 1, -(e.clientY - rect.top) / rect.height * 2 + 1);
      ray.setFromCamera(pointer, camera); const hits = ray.intersectObjects(pickMeshes, false);
      if (hits.length) choose(hits[0].object.userData.objectId);
    });
    renderer.domElement.addEventListener('pointercancel', () => { down = null; });
    function setHighlight(id) {
      if (highlight) { scene.remove(highlight); highlight.geometry.dispose(); highlight.material.dispose(); highlight = null; }
      scene.traverse(o => { if (o.isMesh && o.userData.originalEmissive !== undefined) { o.material.emissive.setHex(o.userData.originalEmissive); } });
      halo.visible = !!id;
      if (!id) return;
      const item = objects.find(o => o.id === id); halo.position.set(item.target[0], .14, item.target[2]);
      halo.scale.setScalar(id === 'mosque' ? 7.4 : id === 'tree' ? 4 : id === 'coast' ? 7 : 2.3);
      if (id !== 'coast') {
        highlight = new THREE.BoxHelper(groups[id], 0xffd173); scene.add(highlight);
        groups[id].traverse(o => {
          if (o.isMesh && o.material.emissive) {
            if (o.userData.originalEmissive === undefined) { o.material = o.material.clone(); o.userData.originalEmissive = o.material.emissive.getHex(); }
            o.material.emissive.setHex(0x2b1d09);
          }
        });
      }
    }
    function zoom(factor) { cancelFlight(); const offset = camera.position.clone().sub(controls.target); offset.setLength(THREE.MathUtils.clamp(offset.length() * factor, controls.minDistance, controls.maxDistance)); camera.position.copy(controls.target).add(offset); controls.update(); }
    function setQuality(value) {
      quality = value; renderer.setPixelRatio(value === 'light' ? 1 : Math.min(devicePixelRatio || 1, 1.75));
      renderer.shadowMap.enabled = value === 'full'; sun.castShadow = value === 'full'; details.visible = value === 'full';
      resize(); el('modelStatus').textContent = (value === 'light' ? 'Жеңіл сапа · ' : 'Толық сапа · ') + 'иллюстрация';
      el('quality').value = value;
    }
    function resize() { const w = Math.max(1, host.clientWidth), h = Math.max(1, host.clientHeight); camera.aspect = w / h; camera.updateProjectionMatrix(); renderer.setSize(w, h, false); }
    new ResizeObserver(resize).observe(host);
    window.addEventListener('resize', resize); document.addEventListener('fullscreenchange', resize);
    el('btnZoomIn').onclick = () => zoom(.82); el('btnZoomOut').onclick = () => zoom(1.22);
    el('btnRotate').onclick = () => { flight = null; rotate(!controls.autoRotate); };
    el('btnWire').onclick = () => {
      wire = !wire; Object.values(groups).forEach(g => g.traverse(o => { if (o.isMesh && o.material.visible !== false) o.material.wireframe = wire; })); sea.material.wireframe = wire;
      el('btnWire').setAttribute('aria-pressed', String(wire)); el('btnWire').textContent = wire ? '▦ Толық модель' : '▦ Каркас';
    };
    el('quality').onchange = e => setQuality(e.target.value);
    el('btnFull').onclick = async () => {
      try { if (!document.fullscreenElement) { if (!shell.requestFullscreen) throw new Error('unsupported'); await shell.requestFullscreen(); } else await document.exitFullscreen(); }
      catch (_) { el('modelStatus').textContent = 'Толық экранға рұқсат жоқ. Браузер мәзірін қолданыңыз.'; }
    };
    document.addEventListener('fullscreenchange', () => { el('btnFull').textContent = document.fullscreenElement ? '⛶ Экраннан шығу' : '⛶ Толық экран'; });
    host.addEventListener('keydown', e => {
      if (e.target !== host && e.target !== renderer.domElement) return;
      if (['1', '2', '3', '4'].includes(e.key)) { e.preventDefault(); choose(objects[Number(e.key) - 1].id); return; }
      if (e.key === 'Home') { e.preventDefault(); reset(); return; }
      if (['+', '=', '-', '_'].includes(e.key)) { e.preventDefault(); zoom(['+', '='].includes(e.key) ? .85 : 1.18); return; }
      if (e.key.startsWith('Arrow')) {
        e.preventDefault(); cancelFlight(); const s = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
        if (e.key === 'ArrowLeft') s.theta -= .12; if (e.key === 'ArrowRight') s.theta += .12;
        if (e.key === 'ArrowUp') s.phi -= .1; if (e.key === 'ArrowDown') s.phi += .1;
        s.phi = THREE.MathUtils.clamp(s.phi, controls.minPolarAngle, controls.maxPolarAngle);
        camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(s)); controls.update();
      }
    });
    function capture() { renderer.render(scene, camera); el('comparisonRender').src = renderer.domElement.toDataURL('image/png'); }
    el('btnCompare').onclick = () => {
      const panel = el('comparisonPanel'); panel.hidden = !panel.hidden;
      el('btnCompare').setAttribute('aria-expanded', String(!panel.hidden)); el('btnCompare').textContent = panel.hidden ? 'Салыстыруды ашу' : 'Салыстыруды жабу';
      if (!panel.hidden) capture();
    };
    el('btnCapture').onclick = capture;
    renderer.domElement.addEventListener('webglcontextlost', e => { e.preventDefault(); error('WebGL графикалық контексті жоғалды. Басқа ауыр беттерді жауып, «Қайта жүктеу» батырмасын басыңыз.'); });
    const seaPosition = seaGeo.attributes.position, base = seaPosition.array.slice();
    let last = 0, frameCount = 0;
    function animate(now) {
      if (disposed) return; requestAnimationFrame(animate);
      if ((engine && engine.failed) || document.hidden || (quality === 'light' && now - last < 32)) return;
      last = now;
      try {
        if (flight) {
          const t = Math.min(1, (now - flight.start) / 850), eased = t * t * (3 - 2 * t);
          camera.position.lerpVectors(flight.from, flight.to, eased); controls.target.lerpVectors(flight.targetFrom, flight.targetTo, eased); if (t === 1) flight = null;
        }
        if (quality === 'full' && !reduced) {
          for (let i = 0; i < seaPosition.count; i++) seaPosition.setY(i, Math.sin(base[i * 3] * .24 + now * .0007) * .055 + Math.cos(base[i * 3 + 2] * .32 + now * .0005) * .035);
          seaPosition.needsUpdate = true;
          if (frameCount % 8 === 0) seaGeo.computeVertexNormals();
          foam.position.z = Math.sin(now * .0004) * .22;
        }
        controls.update(); camera.updateMatrixWorld();
        // Keep panning within the illustrative scene, preserving the view direction.
        const bounded = controls.target.clone(); bounded.x = THREE.MathUtils.clamp(bounded.x, -35, 35); bounded.z = THREE.MathUtils.clamp(bounded.z, -42, 32); bounded.y = THREE.MathUtils.clamp(bounded.y, 0, 12);
        camera.position.add(bounded.clone().sub(controls.target)); controls.target.copy(bounded);
        const occupied = [];
        document.querySelectorAll('#reconLabels button').forEach(b => {
          const p = positions[b.dataset.object].clone().project(camera); const visible = p.z < 1 && p.z > -1 && Math.abs(p.x) < .94 && Math.abs(p.y) < .9;
          b.hidden = !visible;
          if (visible) {
            const w = b.offsetWidth, h = b.offsetHeight;
            const x = THREE.MathUtils.clamp((p.x + 1) * host.clientWidth / 2, w / 2 + 6, host.clientWidth - w / 2 - 6);
            let y = Math.max(h + 8, (-p.y + 1) * host.clientHeight / 2);
            for (let attempt = 0; attempt < 8; attempt++) {
              const collision = occupied.find(r => Math.abs(r.x - x) < (r.w + w) / 2 + 6 && Math.abs(r.y - y) < (r.h + h) / 2 + 8);
              if (!collision) break;
              y = collision.y + (collision.h + h) / 2 + 9;
            }
            y = Math.min(y, host.clientHeight - 12);
            occupied.push({ x, y, w, h });
            b.style.transform = 'translate(' + x + 'px,' + y + 'px) translate(-50%,-100%)';
          }
        });
        renderer.render(scene, camera); frameCount++;
      } catch (e) { error('3D көрсету кезінде қате болды. Бетті қайта жүктеңіз немесе жеңілірек браузерді қолданыңыз. ' + e.message); }
    }
    setQuality(window.matchMedia('(max-width: 760px)').matches ? 'light' : 'full'); controls.update(); resize(); requestAnimationFrame(animate);
    window.addEventListener('pageshow', e => { if (e.persisted) window.location.reload(); });
    window.addEventListener('pagehide', () => { disposed = true; controls.dispose(); scene.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material && o.material.dispose) o.material.dispose(); }); renderer.dispose(); }, { once: true });
    return { failed: false, fly, highlight: setHighlight, rotate,
      state: () => ({ camera: camera.position.toArray(), target: controls.target.toArray(), distance: camera.position.distanceTo(controls.target), wire, quality, autoRotate: controls.autoRotate, selected, tour, highlighted: halo.visible, frames: frameCount, flying: !!flight, meshCount: pickMeshes.length, width: host.clientWidth, height: host.clientHeight, failure }),
      project: id => { const item = objects.find(o => o.id === id); const p = new THREE.Vector3(...item.target).project(camera); return { x: (p.x + 1) * host.clientWidth / 2, y: (-p.y + 1) * host.clientHeight / 2 }; }
    };
  }
  async function init() {
    try {
      const response = await fetch(root.dataset.config, { cache: 'no-cache' });
      if (!response.ok) throw new Error('3D деректер файлы жүктелмеді (' + response.status + ').');
      data = await response.json();
      if (!Array.isArray(data.objects) || data.objects.length !== 4) throw new Error('3D деректер құрылымы қате. static/data/reconstruction.json файлын тексеріңіз.');
      objects = data.objects;
      try { engine = createEngine(); host.dataset.ready = 'true'; }
      catch (e) { error(e.message.startsWith('Жергілікті') ? e.message : 'WebGL іске қосылмады. Chrome немесе Edge жаңартып, аппараттық жеделдетуді қосыңыз. Дерек карточкалары қолжетімді.'); }
    } catch (e) { error(e.message + ' Архивті толық шығарып, Flask сервері арқылы ашыңыз.'); el('cardSource').textContent = 'Дерек файлы оқылмады. /derek-kozder бетін қараңыз.'; }
    // Read-only diagnostic surface for reproducible tests; no history or content mutation.
    window.akshukur3d = Object.freeze({ getState: () => engine ? engine.state() : { failure, selected, tour }, project: id => engine ? engine.project(id) : null });
  }
  init();
})();
