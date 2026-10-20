"""Optional integration suite: pip install playwright; python -m playwright install chromium.
Run: python tests/test_reconstruction_browser.py
Uses a local WSGI server and Chromium/SwiftShader. Not a Windows GPU validation.
"""
from pathlib import Path
import json
import sys
import threading
import math
ROOT = Path(__file__).resolve().parents[1]

def main():
    from playwright.sync_api import sync_playwright
    sys.path.insert(0, str(ROOT))
    from app import app
    from werkzeug.serving import make_server
    out = ROOT / 'verification' / 'reconstruction'
    out.mkdir(parents=True, exist_ok=True)
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/rekonstrukciya'
    results = []
    def check(name, condition, detail=None):
        results.append({'test': name, 'passed': bool(condition), 'detail': detail})
        if not condition:
            raise AssertionError(name + ': ' + str(detail))
    def state(page): return page.evaluate('window.akshukur3d.getState()')
    def settled(page): page.wait_for_function('window.akshukur3d && !window.akshukur3d.getState().flying'); page.wait_for_timeout(200)
    def distance(a, b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
            context = browser.new_context(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
            blocked, errors, responses = [], [], []
            def routing(route):
                if route.request.url.startswith(('http://127.0.0.1:', 'data:')): route.continue_()
                else: blocked.append(route.request.url); route.abort()
            context.route('**/*', routing)
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('response', lambda r: responses.append([r.url, r.status]))
            page.goto(url, wait_until='networkidle')
            page.wait_for_selector('#viewer3d[data-ready=true]')
            page.wait_for_function('window.akshukur3d.getState().frames > 5')
            check('offline_local_boot', not blocked and not errors and not state(page)['failure'], {'blocked': blocked, 'errors': errors})
            check('four_objects', page.locator('#objectList [data-object]').count()==4 and state(page)['meshCount']>50)
            page.locator('#reconShell').scroll_into_view_if_needed()
            page.locator('#reconShell').screenshot(path=str(out/'desktop.png'))
            for id in ['mosque', 'tree', 'well', 'coast']:
                page.locator(f'#objectList [data-object={id}]').click(); settled(page)
                s = state(page)
                expected = next(o for o in json.loads((ROOT/'static/data/reconstruction.json').read_text())['objects'] if o['id']==id)
                check('select_'+id, s['selected']==id and s['highlighted'] and distance(s['target'],expected['target'])<.02, s)
                check('card_'+id, page.locator('#cardTitle').inner_text()==expected['name'] and page.locator('#cardUnknown').inner_text()==expected['unknown'] and page.locator('#cardPhotoNote').is_visible())
            page.locator('#btnReset').click(); settled(page)
            home = state(page)
            check('reset_selection', home['selected'] is None and not home['highlighted'])
            page.locator('#btnOverview').click(); settled(page)
            check('overview_camera', distance(home['camera'], state(page)['camera'])>3)
            page.locator('#btnReset').click(); settled(page)
            # Pick actual mesh with a raycast, not just a UI label.
            rect = page.locator('#viewer3d').bounding_box()
            point = page.evaluate('window.akshukur3d.project("mosque")')
            page.mouse.click(rect['x']+point['x'],rect['y']+point['y']); settled(page)
            check('raycast_mesh_selection', state(page)['selected']=='mosque',state(page))
            page.locator('#btnReset').click(); settled(page)
            page.locator('#reconLabels [data-object=tree]').click(); settled(page)
            check('scene_label_selection', state(page)['selected']=='tree')
            d = state(page)['distance']; page.locator('#btnZoomIn').click(); page.wait_for_timeout(250)
            check('zoom_in_button', state(page)['distance']<d)
            page.locator('#btnZoomOut').click(); page.wait_for_timeout(250)
            check('zoom_out_button', state(page)['distance']>d*.95)
            page.locator('#btnWire').click()
            check('wireframe_on', state(page)['wire'] and page.locator('#btnWire').get_attribute('aria-pressed')=='true')
            page.locator('#btnWire').click(); check('wireframe_off', not state(page)['wire'])
            page.locator('#btnRotate').click(); c=state(page)['camera']; page.wait_for_timeout(700)
            check('autorotate',state(page)['autoRotate'] and distance(c,state(page)['camera'])>.01)
            page.locator('#btnRotate').click(); check('autorotate_stop',not state(page)['autoRotate'])
            page.locator('#viewer3d').focus(); c=state(page)['camera']; page.keyboard.press('ArrowLeft'); page.wait_for_timeout(300)
            check('keyboard_orbit',distance(c,state(page)['camera'])>.1)
            d=state(page)['distance'];page.keyboard.press('+');page.wait_for_timeout(250)
            check('keyboard_zoom',state(page)['distance']<d)
            page.keyboard.press('3'); settled(page); check('keyboard_select',state(page)['selected']=='well')
            page.locator('#viewer3d').focus(); page.keyboard.press('Home'); settled(page); check('keyboard_reset',state(page)['selected'] is None)
            # Mouse orbit, wheel zoom and right-button pan.
            rect=page.locator('#viewer3d').bounding_box();x=rect['x']+rect['width']*.55;y=rect['y']+rect['height']*.6
            c=state(page)['camera'];page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+90,y+30,steps=12);page.mouse.up();page.wait_for_timeout(350)
            check('mouse_orbit',distance(c,state(page)['camera'])>.5)
            d=state(page)['distance'];page.mouse.move(x,y);page.mouse.wheel(0,-160);page.wait_for_timeout(350)
            check('mouse_wheel_zoom',state(page)['distance']<d)
            t=state(page)['target'];page.mouse.down(button='right');page.mouse.move(x+60,y+20,steps=10);page.mouse.up(button='right');page.wait_for_timeout(350)
            check('mouse_pan',distance(t,state(page)['target'])>.1)
            # Tour has 5 real camera steps and reverse/restart.
            page.locator('#btnReset').click();settled(page)
            for index,id in enumerate(['mosque','tree','well','coast'],2):
                page.locator('#tourNext').click();settled(page)
                check('tour_step_'+str(index),state(page)['selected']==id and page.locator('#tourProgress').inner_text()==f'{index} / 5')
            page.locator('#tourPrev').click();settled(page);check('tour_back',state(page)['selected']=='well')
            page.locator('#tourNext').click();settled(page);page.locator('#tourNext').click();settled(page);check('tour_restart',state(page)['tour']==0 and state(page)['selected'] is None)
            page.locator('#btnCompare').click()
            check('comparison_open',page.locator('#comparisonPanel').is_visible() and page.locator('#comparisonRender').evaluate('(im)=>im.complete && im.naturalWidth>100') and page.locator('#comparisonPanel img').first.evaluate('(im)=>im.complete && im.naturalWidth>0'))
            old=page.locator('#comparisonRender').get_attribute('src');page.locator('#objectList [data-object=well]').click();settled(page);page.locator('#btnCapture').click()
            check('comparison_refresh',old!=page.locator('#comparisonRender').get_attribute('src'))
            page.locator('.recon-compare').screenshot(path=str(out/'comparison.png'))
            page.locator('#btnCompare').click();check('comparison_close',not page.locator('#comparisonPanel').is_visible())
            page.locator('#quality').select_option('light');check('light_mode',state(page)['quality']=='light')
            page.locator('#quality').select_option('full');check('full_mode',state(page)['quality']=='full')
            page.locator('#btnFull').click();page.wait_for_timeout(400)
            check('fullscreen_enter',page.evaluate('!!document.fullscreenElement'))
            page.locator('#btnFull').click();page.wait_for_timeout(300)
            check('fullscreen_exit',not page.evaluate('!!document.fullscreenElement'))
            check('no_missing_local_assets',not [r for r in responses if r[1]>=400],responses)
            check('no_javascript_exceptions',not errors,errors)
            # Mobile rendering with touch input, lightweight by default.
            mobile=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True)
            mobile.route('**/*',routing);mp=mobile.new_page();mp.goto(url,wait_until='networkidle');mp.wait_for_selector('#viewer3d[data-ready=true]')
            check('mobile_auto_light',state(mp)['quality']=='light')
            check('mobile_no_horizontal_overflow',mp.evaluate('document.documentElement.scrollWidth<=window.innerWidth'))
            mp.locator('#objectList [data-object=well]').tap();settled(mp)
            check('mobile_tap_selection',state(mp)['selected']=='well' and mp.locator('#cardTitle').inner_text()=='Құдық')
            mp.locator('#viewer3d').scroll_into_view_if_needed();rect=mp.locator('#viewer3d').bounding_box();x=rect['x']+rect['width']*.5;y=rect['y']+rect['height']*.65
            c=state(mp)['camera'];session=mobile.new_cdp_session(mp)
            session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
            for n in range(1,9):session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x+n*7,'y':y+n*2}]})
            session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});mp.wait_for_timeout(400)
            check('mobile_touch_orbit',distance(c,state(mp)['camera'])>.5)
            d=state(mp)['distance']
            session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'id':1,'x':x-25,'y':y},{'id':2,'x':x+25,'y':y}]})
            for n in range(1,7):session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'id':1,'x':x-25-n*4,'y':y},{'id':2,'x':x+25+n*4,'y':y}]})
            session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});mp.wait_for_timeout(400)
            check('mobile_pinch_zoom',state(mp)['distance']<d,{'before':d,'after':state(mp)['distance']})
            t=state(mp)['target'];session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'id':1,'x':x-25,'y':y},{'id':2,'x':x+25,'y':y}]})
            for n in range(1,7):session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'id':1,'x':x-25+n*4,'y':y+n*2},{'id':2,'x':x+25+n*4,'y':y+n*2}]})
            session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});mp.wait_for_timeout(400)
            check('mobile_two_finger_pan',distance(t,state(mp)['target'])>.05)
            mp.locator('#btnReset').click();settled(mp)
            mp.evaluate("window.scrollTo({top:document.getElementById('reconShell').getBoundingClientRect().top+scrollY-82,behavior:'instant'})")
            mp.wait_for_timeout(500);mp.screenshot(path=str(out/'mobile.png'))
            check('mobile_menu_remains_closed',mp.locator('#burger').get_attribute('aria-expanded')=='false' and not mp.locator('#mobileMenu').evaluate("e=>e.classList.contains('open')"))
            for width,height in [(320,740),(768,1024),(1024,768)]:
                mp.set_viewport_size({'width':width,'height':height});mp.wait_for_timeout(200)
                check('responsive_'+str(width),mp.evaluate('document.documentElement.scrollWidth<=window.innerWidth') and state(mp)['width']>0 and state(mp)['height']>0)
            page.close(); mobile.close()
            # Failure cases run in independent pages; data cards survive a missing engine.
            bad=context.new_page();bad.route('**/three.min.js',lambda route:route.abort());bad.goto(url,wait_until='networkidle');bad.wait_for_selector('#viewerFallback',state='visible')
            bad.locator('#objectList [data-object=mosque]').click()
            check('missing_library_fallback',bad.locator('#cardTitle').inner_text()=='Мешіт / медресе' and bad.locator('#btnWire').is_disabled())
            missing=context.new_page();missing.route('**/reconstruction.json',lambda route:route.fulfill(status=404,body='missing'));missing.goto(url,wait_until='networkidle')
            check('missing_json_fallback',missing.locator('#viewerFallback').is_visible() and '404' in missing.locator('#fallbackMessage').inner_text())
            corrupt=context.new_page();corrupt.route('**/reconstruction.json',lambda route:route.fulfill(status=200,content_type='application/json',body='{}'));corrupt.goto(url,wait_until='networkidle')
            check('invalid_json_structure_fallback',corrupt.locator('#viewerFallback').is_visible())
            missing.close(); corrupt.close()
            no_gl=browser.new_context();no_gl.add_init_script("HTMLCanvasElement.prototype.getContext = function(){return null;}")
            ng=no_gl.new_page();ng.goto(url,wait_until='networkidle');check('webgl_unavailable_fallback',ng.locator('#viewerFallback').is_visible())
            no_gl.close()
            lost=context.new_page();lost.goto(url,wait_until='networkidle')
            lost.wait_for_function("window.akshukur3d !== undefined")
            check('context_test_engine_ready',lost.locator('#viewer3d').get_attribute('data-ready')=='true',state(lost))
            lost.locator('#viewer3d canvas').evaluate("c=>c.getContext('webgl2').getExtension('WEBGL_lose_context').loseContext()")
            lost.wait_for_selector('#viewerFallback',state='visible');check('webgl_context_lost_fallback','контексті' in lost.locator('#fallbackMessage').inner_text())
            lost.locator('#reconShell').screenshot(path=str(out/'fallback.png'))
            lost.close()
            # Actual reload button works after missing library route removed.
            bad.unroute('**/three.min.js');bad.locator('#btnRetry').click();bad.wait_for_selector('#viewer3d[data-ready=true]')
            check('retry_button',not bad.locator('#viewerFallback').is_visible())
            bad.close()
            reduced_context=browser.new_context(reduced_motion='reduce');rp=reduced_context.new_page();rp.goto(url,wait_until='networkidle');rp.wait_for_selector('#viewer3d[data-ready=true]');rp.locator('#objectList [data-object=tree]').click()
            check('reduced_motion',state(rp)['selected']=='tree' and not state(rp)['flying'])
            browser.close()
    finally:
        server.shutdown()
        report={'environment':'Linux; Playwright Chromium 156; ANGLE SwiftShader (software WebGL); Windows not executed','url_path':'/rekonstrukciya','passed':sum(r['passed'] for r in results),'total':len(results),'results':results}
        (out/'browser-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
