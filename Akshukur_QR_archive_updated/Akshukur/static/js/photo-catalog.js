(() => {
  'use strict';
  const data=document.getElementById('photoCatalogData');if(!data)return;
  const catalog=JSON.parse(data.textContent),cards=[...document.querySelectorAll('.photo-record')];
  const dialog=document.getElementById('photoViewer'), image=document.getElementById('photoViewerImage');
  const query=document.getElementById('photoQuery');let category='all',current=null,opener=null;
  const el=id=>document.getElementById(id);
  const visible=()=>cards.filter(c=>!c.hidden).map(c=>catalog.find(r=>r.id===c.id));
  function apply(){
    const tokens=query.value.trim().toLocaleLowerCase('kk').split(/\s+/).filter(Boolean);
    cards.forEach(c=>{c.hidden=!(category==='all'||c.dataset.photoCategory===category)||!tokens.every(t=>c.dataset.photoSearch.includes(t));});
    const count=visible().length;el('photoCount').textContent=count+' фото · тарихи мерзімі деректемемен тексеріледі';el('photoEmpty').hidden=count!==0;
  }
  el('photoFilters').addEventListener('click',e=>{
    const b=e.target.closest('[data-photo-category]');if(!b)return;category=b.dataset.photoCategory;
    el('photoFilters').querySelectorAll('button').forEach(x=>{const active=x===b;x.classList.toggle('active',active);x.setAttribute('aria-pressed',String(active));});apply();
  });query.addEventListener('input',apply);
  function render(){
    const r=catalog.find(x=>x.id===current);if(!r)return;
    image.hidden=!r.image;el('photoViewerPlaceholder').hidden=!!r.image;el('photoViewerError').hidden=true;
    image.alt=r.title+' — '+r.status;if(r.image)image.src=r.image;else image.removeAttribute('src');
    el('photoViewerPlaceholder').textContent=r.status+' · Нақты тарихи фото емес';
    for(const [id,text] of [['photoViewerTitle',r.title],['photoViewerStatus',r.status],['photoViewerYear','Түсірілген жылы: '+r.year],['photoViewerDescription',r.description],['photoViewerSource','Дереккөз: '+r.provenance],['photoViewerNote',r.note]])el(id).textContent=text;
    const list=visible();el('photoViewerCount').textContent=(list.findIndex(x=>x.id===r.id)+1)+' / '+list.length;
    el('photoPrev').disabled=el('photoNext').disabled=list.length<2;
  }
  function show(id,button){current=id;opener=button;render();dialog.showModal();document.body.style.overflow='hidden';el('photoViewerClose').focus();}
  function move(step){const list=visible();let idx=list.findIndex(x=>x.id===current);current=list[(idx+step+list.length)%list.length].id;render();}
  document.querySelectorAll('[data-photo-open]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.photoOpen,b)));
  el('photoViewerClose').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('close',()=>{document.body.style.overflow='';if(opener)opener.focus();});
  dialog.addEventListener('click',e=>{const r=dialog.getBoundingClientRect();if(e.target===dialog&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))dialog.close();});
  dialog.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'){e.preventDefault();move(-1);}if(e.key==='ArrowRight'){e.preventDefault();move(1);}});
  el('photoPrev').addEventListener('click',()=>move(-1));el('photoNext').addEventListener('click',()=>move(1));
  image.addEventListener('error',()=>{image.hidden=true;el('photoViewerError').hidden=false;});
})();
