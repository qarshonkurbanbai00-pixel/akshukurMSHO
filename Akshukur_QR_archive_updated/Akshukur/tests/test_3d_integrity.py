"""Reconstruction-specific integrity checks. Run with unittest; only Flask required."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import app
ALLOWED_ORIGINAL_CHANGES={'README.md','run.bat','templates/reconstruction.html','static/js/3d.js','static/models/README.txt','tests/test_regression.py'}

class LocalAssets(HTMLParser):
    def __init__(self): super().__init__();self.paths=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        for k in ['src','href']:
            url=attrs.get(k,'')
            if url.startswith('/static/') or url.startswith('/images/'):
                self.paths.append(url)

class ReconstructionIntegrity(unittest.TestCase):
    def test_original_scope_and_no_deletions(self):
        baseline=json.loads((ROOT/'verification/reconstruction/original-audit.json').read_text(encoding='utf-8'))
        for name,info in baseline['source_files'].items():
            with self.subTest(file=name):
                p=ROOT/name
                self.assertTrue(p.is_file(),name)
                if name not in ALLOWED_ORIGINAL_CHANGES:
                    self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),info['sha256'],name)

    def test_all_other_routes_byte_identical(self):
        baseline=json.loads((ROOT/'verification/reconstruction/original-audit.json').read_text(encoding='utf-8'))
        c=app.test_client()
        self.assertEqual({r.rule for r in app.url_map.iter_rules() if '<' not in r.rule},set(baseline['routes']))
        for path,info in baseline['routes'].items():
            with self.subTest(path=path):
                r=c.get(path);self.assertEqual(r.status_code,info['status'])
                if path!='/rekonstrukciya':self.assertEqual(hashlib.sha256(r.data).hexdigest(),info['sha256'])

    def test_python_syntax_and_render_templates(self):
        for p in ROOT.rglob('*.py'):
            ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
        tree=ast.parse((ROOT/'app.py').read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='render_template':
                self.assertIsInstance(node.args[0],ast.Constant)
                self.assertTrue((ROOT/'templates'/node.args[0].value).is_file())
        for p in (ROOT/'templates').glob('*.html'):app.jinja_env.get_template(p.name)

    def test_all_rendered_local_assets(self):
        c=app.test_client()
        for rule in app.url_map.iter_rules():
            if '<' in rule.rule:continue
            response=c.get(rule.rule)
            if response.mimetype!='text/html':continue
            parser=LocalAssets();parser.feed(response.get_data(as_text=True))
            for url in parser.paths:
                with self.subTest(page=rule.rule,asset=url):
                    r=c.get(url);self.assertEqual(r.status_code,200,url);r.close()

    def test_four_object_schema_and_no_false_photos(self):
        data=json.loads((ROOT/'static/data/reconstruction.json').read_text(encoding='utf-8'))
        self.assertEqual([o['id'] for o in data['objects']],['mosque','tree','well','coast'])
        for o in data['objects']:
            for name in ['name','description','source','unknown','photo_note']:self.assertTrue(o[name])
            self.assertEqual(len(o['camera']),3);self.assertEqual(len(o['target']),3)
            self.assertTrue(all(isinstance(v,(int,float)) for v in o['camera']+o['target']))
            self.assertIsNone(o['photo'])  # archive has no verified photos of these objects
        photo=ROOT/'static'/data['comparison']['image'];self.assertTrue(photo.is_file())
        self.assertEqual(hashlib.sha256(photo.read_bytes()).hexdigest(),'1866198fb98cba79d3942f19f1e82c801a8e15da7023de1ba66ff7ff299c6509')

    def test_offline_libraries_and_no_missing_glb_request(self):
        html=app.test_client().get('/rekonstrukciya').get_data(as_text=True)
        self.assertNotRegex(html,r'<script[^>]+src=["\']https?://')
        for file in ['three.min.js','OrbitControls.js','LICENSE']:
            self.assertTrue((ROOT/'static/vendor/three-r128'/file).stat().st_size>500)
        self.assertIn('128',(ROOT/'static/vendor/three-r128/three.min.js').read_text(encoding='utf-8'))
        js=(ROOT/'static/js/3d.js').read_text(encoding='utf-8')
        self.assertNotIn('mashyryq.glb',js)
        self.assertNotRegex(js,r'https?://')

    def test_windows_launcher_static_structure(self):
        raw=(ROOT/'run.bat').read_bytes();self.assertIn(b'\r\n',raw)
        text=raw.decode('utf-8')
        for fragment in ['cd /d "%~dp0"','where python','sys.version_info >= (3,10)','python -m pip install -r requirements.txt','python app.py','if errorlevel 1','pause']:
            self.assertIn(fragment,text)
        labels=set(re.findall(r'^:([a-z_]+)',text,re.M))
        for target in re.findall(r'goto ([a-z_]+)',text):self.assertIn(target,labels)
        self.assertEqual((ROOT/'requirements.txt').read_text().strip(),'Flask>=2.2,<4.0')

    def test_readme_urls_and_windows_commands(self):
        text=(ROOT/'README.md').read_text(encoding='utf-8')
        self.assertIn('http://127.0.0.1:5000/rekonstrukciya',text)
        self.assertIn('python -m pip install -r requirements.txt',text)
        self.assertIn('python app.py',text)
        self.assertTrue((ROOT/'templates/index.html').is_file())

if __name__=='__main__':unittest.main(verbosity=2)
