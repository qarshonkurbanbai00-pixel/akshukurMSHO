"""Real Chromium tests. Optional dependencies: playwright; playwright install chromium.
Run: python tests/test_content_browser.py. Starts its own local server.
"""
from pathlib import Path
import json,sys,threading
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright


def main():
    out=ROOT/'verification/content-update';out.mkdir(parents=True,exist_ok=True)
    server=make_server('127.0.0.1',0,app,threaded=True)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base='http://127.0.0.1:'+str(server.server_port)
    checks=[];errors=[]
    def check(name,condition,detail=None):
        checks.append({'test':name,'passed':bool(condition),'detail':detail})
        if not condition:raise AssertionError(name+': '+str(detail))
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
            context=browser.new_context(viewport={'width':1440,'height':1000},device_scale_factor=1)
            context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) or route.request.url.startswith('data:') else route.abort())
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'/tarikh/zhoba',wait_until='networkidle')
            page.wait_for_selector('#loader.done')
            check('project_text_and_real_current_photo',page.locator('main h1').inner_text()=='Жоба' and page.locator('main article').count()>=7 and page.locator('main img').evaluate('(i)=>i.complete&&i.naturalWidth>0'))
            page.screenshot(path=str(out/'project-desktop.png'),full_page=True)
            page.locator('#searchBtn').click()
            check('desktop_search_opens_and_focuses',page.locator('#searchOverlay').is_visible() and page.locator('#searchInput').evaluate('(i)=>i===document.activeElement'))
            page.locator('#searchInput').fill('ұрпақтар сабақтастығы')
            page.wait_for_function("document.getElementById('searchStatus').textContent.includes('нәтиже табылды')")
            check('search_full_page_text',page.locator('#searchResults a[href^="/tarikh/zhoba"]').count()>0)
            page.locator('#searchInput').fill('qwerty987654nonexistent')
            page.wait_for_function("document.getElementById('searchStatus').textContent==='Іздеу бойынша нәтиже табылмады'")
            check('exact_empty_result_message',page.locator('#searchResults a').count()==0)
            page.locator('#searchInput').fill('<script>alert(1)</script>')
            page.wait_for_function("document.getElementById('searchStatus').textContent==='Іздеу бойынша нәтиже табылмады'")
            check('search_markup_not_executed',page.locator('#searchResults script').count()==0)
            page.locator('#searchInput').fill('Мектеп')
            page.locator('#siteSearchForm button[type=submit]').click()
            page.wait_for_selector('#searchResults a[href="/mektep"]')
            page.locator('#searchResults a[href="/mektep"]').first.click()
            page.wait_for_url('**/mektep')
            check('search_hit_opens_correct_page',page.locator('main h1').inner_text()=='Мектеп')
            # Full results page works without JavaScript.
            nojs=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
            np=nojs.new_page();np.goto(base+'/izdeu?q=фото')
            check('server_rendered_nojs_results',np.locator('.search-page-results a').count()>0)
            np.goto(base+'/izdeu?q=zzzz987654321')
            check('nojs_no_results', 'Іздеу бойынша нәтиже табылмады' in np.locator('main').inner_text());nojs.close()
            page.goto(base+'/tarikh/foto-arkhivi',wait_until='networkidle')
            check('five_placeholder_categories',page.locator('.photo-record:not([data-photo-category=pending])').count()==5)
            page.locator('.photo-record img').evaluate_all("imgs=>imgs.forEach(i=>i.loading='eager')")
            page.wait_for_function("[...document.querySelectorAll('.photo-record img')].every(i=>i.complete&&i.naturalWidth>0)")
            check('no_broken_catalog_images',page.locator('.photo-record img').evaluate_all('(imgs)=>imgs.every(i=>i.complete&&i.naturalWidth>0)'))
            page.locator('#photoFilters [data-photo-category=school]').click()
            check('category_filter',page.locator('.photo-record:visible').count()==1 and page.locator('#photo-school').is_visible())
            page.locator('#photo-school .photo-open').click()
            check('placeholder_detail_dialog',page.locator('#photoViewer').is_visible() and page.locator('#photoViewerPlaceholder').is_visible() and not page.locator('#photoViewerImage').is_visible())
            page.keyboard.press('Escape');check('native_dialog_escape_closes',not page.locator('#photoViewer').is_visible())
            page.locator('#photoFilters [data-photo-category=pending]').click()
            first=page.locator('.photo-record:visible').filter(has=page.locator('img')).first
            first.locator('.photo-open').click()
            page.wait_for_function("document.getElementById('photoViewerImage').complete && document.getElementById('photoViewerImage').naturalWidth>0")
            check('real_input_photo_large_view_and_source',page.locator('#photoViewerImage').is_visible() and 'Бастапқы файл:' in page.locator('#photoViewerSource').inner_text())
            title=page.locator('#photoViewerTitle').inner_text();page.locator('#photoNext').click()
            check('photo_next_navigation',page.locator('#photoViewerTitle').inner_text()!=title or page.locator('#photoViewerCount').inner_text()!='1 / 14')
            page.locator('#photoViewerClose').click()
            page.locator('#photoQuery').fill('impossible987654')
            check('combined_filter_empty_state',page.locator('#photoEmpty').is_visible() and page.locator('.photo-record:visible').count()==0)
            page.locator('#photoQuery').fill('');page.locator('#photoFilters [data-photo-category=all]').click()
            page.screenshot(path=str(out/'archive-desktop.png'),full_page=True)
            # Search error state, close/focus restoration and keyboard containment.
            page.locator('#searchBtn').click()
            page.locator('#searchInput').fill('фото');page.wait_for_selector('#searchResults .search-hit')
            page.locator('#fullSearchLink').focus();page.keyboard.press('Tab')
            check('search_focus_trap',page.locator('#searchInput').evaluate('(i)=>i===document.activeElement'))
            page.keyboard.press('Escape');check('search_escape_restores_focus',page.locator('#searchBtn').evaluate('(i)=>i===document.activeElement') and not page.locator('#searchOverlay').is_visible())
            context.route('**/api/search?*',lambda route:route.abort())
            page.locator('#searchBtn').click();page.locator('#searchInput').fill('байланыс')
            page.wait_for_function("document.getElementById('searchStatus').textContent.includes('Іздеу қатесі')")
            check('network_error_state',True);page.keyboard.press('Escape');context.unroute('**/api/search?*')
            # Responsive widths and mobile interactions.
            for width in [320,390,768,1024,1280,1440]:
                page.set_viewport_size({'width':width,'height':844})
                for route in ['/tarikh/zhoba','/tarikh/foto-arkhivi','/izdeu?q=мектеп']:
                    page.goto(base+route,wait_until='networkidle')
                    check('no_horizontal_overflow_'+str(width)+'_'+route.split('?')[0],page.evaluate('document.documentElement.scrollWidth<=innerWidth'),page.evaluate('({scroll:document.documentElement.scrollWidth,width:innerWidth})'))
            page.set_viewport_size({'width':390,'height':844});page.goto(base+'/tarikh/foto-arkhivi',wait_until='networkidle')
            page.locator('#mobileSearchBtn').click();page.locator('#searchInput').fill('цифрлық мұраны')
            page.wait_for_selector('#searchResults a[href^="/tarikh/zhoba"]')
            check('mobile_search_and_results',page.locator('#searchOverlay').is_visible())
            page.screenshot(path=str(out/'search-mobile.png'),full_page=True)
            page.locator('#searchClose').click()
            page.locator('#burger').click()
            page.locator('#mobileMenu a[href="/tarikh/zhoba"]').click();page.wait_for_url('**/tarikh/zhoba')
            check('mobile_history_project_navigation',page.locator('main h1').inner_text()=='Жоба')
            page.goto(base+'/tarikh/foto-arkhivi',wait_until='networkidle')
            page.locator('#photoFilters [data-photo-category=pending]').click()
            page.locator('.photo-record:visible').filter(has=page.locator('img')).first.locator('.photo-open').click()
            check('mobile_photo_dialog',page.locator('#photoViewer').is_visible() and page.locator('#photoViewer').evaluate('(d)=>d.getBoundingClientRect().width<=innerWidth'))
            page.locator('#photoViewerClose').click();page.screenshot(path=str(out/'archive-mobile.png'),full_page=True)
            # Previously improved school interactions remain available.
            page.goto(base+'/mektep',wait_until='networkidle')
            page.locator('#schoolPeriodControls [data-period=today]').click()
            check('school_previous_period_filter_preserved',page.locator('#schoolToday').is_visible() and not page.locator('#schoolYesterday').is_visible())
            # Local map still exposes original enriched cards, no remote tile success asserted.
            page.goto(base+'/karta',wait_until='networkidle')
            check('historic_places_cards_preserved',page.locator('#card-place-qoshqar').count()==1 and page.locator('#card-place-school-now').count()==1 and page.locator('#card-place-culture').count()==1)
            check('no_javascript_exceptions',not errors,errors)
            browser.close()
    finally:
        (out/'browser-results.json').write_text(json.dumps({'engine':'Chromium headless, Linux','checks':checks,'javascript_errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
        server.shutdown()
    print(str(len(checks))+' browser checks passed')
if __name__=='__main__':main()
