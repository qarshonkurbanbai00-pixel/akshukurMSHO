/* Whole-site search: accessible dialog, real API, keyboard and mobile support. */
(() => {
  'use strict';
  const overlay=document.getElementById('searchOverlay');
  if(!overlay)return;
  const input=document.getElementById('searchInput'), box=document.getElementById('searchResults');
  const status=document.getElementById('searchStatus'), form=document.getElementById('siteSearchForm');
  const triggers=[document.getElementById('searchBtn'),document.getElementById('mobileSearchBtn')].filter(Boolean);
  let opener=null,previousOverflow='',timer=null,controller=null,revision=0;
  function close(){
    if(!overlay.classList.contains('open'))return;
    overlay.classList.remove('open');overlay.setAttribute('aria-hidden','true');
    triggers.forEach(b=>b.setAttribute('aria-expanded','false'));
    document.body.style.overflow=previousOverflow;
    if(opener)opener.focus();
  }
  function open(event){
    opener=event.currentTarget;
    const mobile=document.getElementById('mobileMenu'),burger=document.getElementById('burger');
    if(mobile.classList.contains('open')){mobile.classList.remove('open');burger.classList.remove('open');burger.setAttribute('aria-expanded','false');document.body.style.overflow='';}
    previousOverflow=document.body.style.overflow;
    overlay.classList.add('open');overlay.setAttribute('aria-hidden','false');
    triggers.forEach(b=>b.setAttribute('aria-expanded','true'));
    document.body.style.overflow='hidden';input.focus();
  }
  triggers.forEach(b=>b.addEventListener('click',open));
  document.getElementById('searchClose').addEventListener('click',close);
  document.addEventListener('site-search-close',close);
  overlay.addEventListener('click',e=>{if(e.target===overlay)close();});
  overlay.addEventListener('keydown',e=>{
    if(e.key==='Escape'){e.preventDefault();close();}
    if(e.key==='Tab'){
      const items=[...overlay.querySelectorAll('input,button,a[href]')].filter(el=>el.getClientRects().length&&!el.disabled);
      const first=items[0],last=items[items.length-1];
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
      else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
    }
  });
  async function search(){
    clearTimeout(timer);if(controller)controller.abort();
    const version=++revision,q=input.value.trim();box.replaceChildren();
    document.getElementById('fullSearchLink').href='/izdeu?q='+encodeURIComponent(q);
    if(!q){status.textContent='Іздеу үшін сөз немесе сөйлем енгізіңіз.';box.removeAttribute('aria-busy');return;}
    controller=new AbortController();box.setAttribute('aria-busy','true');status.textContent='Іздеу орындалуда…';
    try{
      const response=await fetch('/api/search?q='+encodeURIComponent(q),{signal:controller.signal});
      if(!response.ok)throw new Error('search');
      const hits=await response.json();if(version!==revision)return;
      for(const hit of hits){
        const link=document.createElement('a');link.className='search-hit';link.href=hit.url;
        for(const [cls,text] of [['hit-sec',hit.section],['hit-title',hit.title],['hit-snippet',hit.snippet]]){
          const span=document.createElement('span');span.className=cls;span.textContent=text||'';link.append(span);
        }
        box.append(link);
      }
      status.textContent=hits.length?hits.length+' нәтиже табылды':'Іздеу бойынша нәтиже табылмады';
    }catch(error){if(error.name!=='AbortError'&&version===revision)status.textContent='Іздеу қатесі — сервермен байланысты тексеріп, қайта іздеңіз.';}
    finally{if(version===revision)box.removeAttribute('aria-busy');}
  }
  input.addEventListener('input',()=>{
    clearTimeout(timer);++revision;if(controller)controller.abort();box.replaceChildren();
    if(!input.value.trim()){status.textContent='Іздеу үшін сөз немесе сөйлем енгізіңіз.';box.removeAttribute('aria-busy');return;}
    status.textContent='Іздеу орындалуда…';timer=setTimeout(search,200);
  });
  form.addEventListener('submit',e=>{e.preventDefault();search();});
})();
