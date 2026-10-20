"""Optional browser QA. pip install playwright && playwright install chromium.
Run: python tests/check_qr_archive_browser.py
"""
from pathlib import Path
import sys,threading,json,logging
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app import app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
logging.getLogger('werkzeug').setLevel(logging.ERROR)
results=[]
def check(name,condition):
 results.append({'test':name,'passed':bool(condition)})
 if not condition:raise AssertionError(name)
server=make_server('127.0.0.1',0,app,threaded=True)
threading.Thread(target=server.serve_forever,daemon=True).start()
base='http://127.0.0.1:'+str(server.server_port)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  for width in [1440,390,320]:
   context=browser.new_context(viewport={'width':width,'height':900},reduced_motion='no-preference',ignore_https_errors=True)
   page=context.new_page();errors=[];notfound=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('response',lambda r:notfound.append(r.url) if r.status>=400 and r.url.startswith(base) else None)
   for path in ['/tarikh','/tarikh/foto-arkhivi','/auyzsha-tarikh','/muragat','/mektep','/karta']:
    errors.clear();page.goto(base+path,wait_until='networkidle',timeout=35000)
    page.locator('#loader').wait_for(state='hidden')
    check(str(width)+path+'_no_horizontal_overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    for card in page.locator('.photo-record,.archive-photo-grid .gallery-item,.qr-card').all():
     card.scroll_into_view_if_needed();page.wait_for_timeout(30)
    for image in page.locator('main img:visible').all():
     image.scroll_into_view_if_needed()
     image.evaluate("i=>i.complete ? Promise.resolve() : new Promise(r=>{i.addEventListener('load',r,{once:true});i.addEventListener('error',r,{once:true});setTimeout(r,5000)})")
    page.wait_for_timeout(450)
    check(str(width)+path+'_images_loaded',page.evaluate("[...document.querySelectorAll('main img:not([hidden])')].filter(i=>i.getClientRects().length).every(i=>i.complete&&i.naturalWidth>0)"))
    check(str(width)+path+'_no_local_http_error',not notfound)
    check(str(width)+path+'_no_js_errors',not errors)
    if path=='/tarikh/foto-arkhivi':
     check(str(width)+'_all_20_photos',page.locator('.photo-record').count()==20)
     page.locator('#photoQuery').fill('портреті');check(str(width)+'_archive_search',page.locator('.photo-record:visible').count()==2)
     page.locator('#photoQuery').fill('zznone98765');check(str(width)+'_archive_no_results',page.locator('#photoEmpty').is_visible())
     page.locator('#photoQuery').fill('');page.locator('#photoFilters [data-photo-category=pending]').click()
     check(str(width)+'_archive_filter',page.locator('.photo-record:visible').count()==12)
     page.locator('[data-photo-category=all]').click()
     page.locator('.photo-open').first.click();check(str(width)+'_viewer_opens',page.locator('#photoViewer').is_visible())
     page.locator('#photoNext').click();check(str(width)+'_viewer_next',page.locator('#photoViewerCount').inner_text().startswith('2 /'))
     page.keyboard.press('Escape');check(str(width)+'_viewer_closes',not page.locator('#photoViewer').is_visible())
     page.locator('#photoCatalog').scroll_into_view_if_needed();page.wait_for_timeout(450)
     if width!=320:page.screenshot(path=str(ROOT/'verification'/('qr-archive-photos-'+str(width)+'.png')))
    if path=='/tarikh':
     qr=page.locator('#video-qr');qr.scroll_into_view_if_needed()
     check(str(width)+'_3_qr_cards',qr.locator('.qr-card').count()==3)
     check(str(width)+'_qr_static',qr.locator('img').evaluate_all("els=>els.every(i=>getComputedStyle(i).transform==='none'&&getComputedStyle(i).animationName==='none')"))
     check(str(width)+'_qr_readable_size',qr.locator('img').evaluate_all("els=>els.every(i=>i.getBoundingClientRect().width>=200)"))
     if width!=320:qr.screenshot(path=str(ROOT/'verification'/('qr-archive-codes-'+str(width)+'.png')))
   # Reduced-motion preference can be switched while page is open.
   page.goto(base+'/tarikh/foto-arkhivi',wait_until='networkidle');page.emulate_media(reduced_motion='reduce')
   check(str(width)+'_reduced_motion_content_visible',page.locator('.reveal').evaluate_all("els=>els.every(e=>getComputedStyle(e).opacity==='1')"))
   check(str(width)+'_reduced_motion_scroll',page.evaluate("getComputedStyle(document.documentElement).scrollBehavior==='auto'"))
   # Mobile menu must remain usable.
   if width<700:
    page.locator('#burger').click();check(str(width)+'_mobile_menu',page.locator('#mobileMenu').is_visible())
    page.locator('#mobileMenu a[href="/mektep"]').click();check(str(width)+'_mobile_navigation',page.url.endswith('/mektep'))
   context.close()
  # JS disabled: archive and all QR links remain present and visible.
  context=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
  page=context.new_page();page.goto(base+'/tarikh',wait_until='networkidle')
  check('no_js_gallery_visible',page.locator('.archive-photo-grid .gallery-item').first.is_visible())
  check('no_js_qr_visible',page.locator('.qr-card img').count()==3)
  context.close();browser.close()
finally:
 server.shutdown()
 (ROOT/'verification/qr-archive-browser-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(str(len(results))+' browser checks passed')
