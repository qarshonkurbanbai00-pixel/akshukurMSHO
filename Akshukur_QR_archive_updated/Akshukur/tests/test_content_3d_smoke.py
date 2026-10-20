"""Small independent 3D preservation smoke test; not the previous exhaustive stress suite."""
import sys,json,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app import app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright

def main():
    server=make_server('127.0.0.1',0,app,threaded=True);threading.Thread(target=server.serve_forever,daemon=True).start()
    base='http://127.0.0.1:'+str(server.server_port);out=ROOT/'verification/content-update';results=[]
    def check(name,ok):
        results.append({'test':name,'passed':bool(ok)})
        assert ok,name
    try:
        with sync_playwright() as p:
            b=p.chromium.launch(args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
            ctx=b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce',device_scale_factor=1)
            ctx.route('**/*',lambda r:r.continue_() if r.request.url.startswith(base) or r.request.url.startswith('data:') else r.abort())
            page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'/rekonstrukciya',wait_until='networkidle',timeout=20000)
            page.wait_for_selector('#viewer3d[data-ready=true]',timeout=20000)
            page.wait_for_function('window.akshukur3d.getState().frames>2',timeout=20000)
            check('3d_engine_ready_offline',not page.evaluate('window.akshukur3d.getState().failure'))
            check('four_objects_preserved',page.locator('#objectList [data-object]').count()==4)
            for key in ['mosque','tree','well','coast']:
                page.locator('#objectList [data-object='+key+']').click()
                check('select_'+key,page.evaluate('window.akshukur3d.getState().selected')==key)
            page.locator('#btnReset').click()
            check('reset_control',page.evaluate('window.akshukur3d.getState().selected') is None)
            check('mobile_no_overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            check('no_js_errors',not errors)
            page.locator('#reconShell').scroll_into_view_if_needed();page.screenshot(path=str(out/'3d-mobile-smoke.png'))
            b.close()
    finally:
        server.shutdown();(out/'3d-smoke-results.json').write_text(json.dumps({'environment':'Linux Chromium SwiftShader, 390x844, reduced motion','checks':results},ensure_ascii=False,indent=2))
    print(str(len(results))+' 3D smoke checks passed')
if __name__=='__main__':main()
