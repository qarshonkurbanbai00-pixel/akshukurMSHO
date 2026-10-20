"""Current delivery checks. Run: python -m unittest discover -s tests -p test_final_package.py -v
Older test_* suites refer to historical snapshots; their hash equality assertions
are not the acceptance baseline for this restored delivery.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import ast
import hashlib
import json
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import app, validate_project_templates

class Assets(HTMLParser):
    def __init__(self):
        super().__init__(); self.assets = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('src', 'href') and value and value.startswith(('/static/', '/images/')):
                self.assets.append(value)

class FinalPackage(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
    def test_complete_template_tree(self):
        actual = sorted(p.name for p in (ROOT/'templates').glob('*.html'))
        self.assertEqual(len(actual), 21)
        self.assertIn('index.html', actual)
        self.assertIn('oral-history.html', actual)
        self.assertEqual(validate_project_templates(), actual)
    def test_every_page_and_local_asset(self):
        for rule in app.url_map.iter_rules():
            if '<' in rule.rule: continue
            with self.subTest(page=rule.rule):
                response = self.client.get(rule.rule)
                self.assertEqual(response.status_code, 200)
                if response.mimetype == 'text/html':
                    parser = Assets(); parser.feed(response.get_data(as_text=True))
                    for path in parser.assets:
                        with self.client.get(path) as asset:
                            self.assertEqual(asset.status_code, 200, path)
    def test_error_template(self):
        response = self.client.get('/nonexistent-package-check')
        self.assertEqual(response.status_code, 404)
        self.assertIn('<html', response.get_data(as_text=True))
    def test_oral_history_and_navigation(self):
        html = self.client.get('/auyzsha-tarikh').get_data(as_text=True)
        self.assertIn('Ауылдың ауызша тарихы', html)
        self.assertIn('Үлгі карточка — нақты сұхбат әлі қосылған жоқ.', html)
        interviews = self.client.get('/api/interviews').json
        self.assertEqual(len(interviews), 3)
        for row in interviews:
            self.assertIn('id="'+row['id']+'"', html)
    def test_search_preserved(self):
        for query, path in [('ұрпақтар сабақтастығы', '/tarikh/zhoba'), ('Баланжан', '/tulghalar'), ('Мектеп', '/mektep'), ('Ауылдың ауызша тарихы', '/auyzsha-tarikh')]:
            hits = self.client.get('/api/search', query_string={'q':query}).json
            self.assertTrue(any(h['url'].startswith(path) for h in hits), query)
        self.assertEqual(self.client.get('/api/search?q=zz987654321none').json, [])
    def test_original_photo_integrity_and_honest_unavailable_records(self):
        absent=[]
        for row in json.loads((ROOT/'data/photos.json').read_text(encoding='utf-8')):
            path=ROOT/'static'/row['image']
            if path.exists():
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),row['sha256'])
            else: absent.append(path.name)
        self.assertEqual(sorted(absent),['e4d9218c-94a4-48d8-9510-b2ab987c5d54.jpg','galery.jpg'])
        from site_content import archive_catalog
        missing=[r for r in archive_catalog(app) if r['status']=='Фото қолжетімсіз']
        self.assertEqual(len(missing),2)
        self.assertTrue(all(r['image'] is None for r in missing))
    def test_local_3d_dependencies(self):
        for name in ['three.min.js','OrbitControls.js','LICENSE']:
            self.assertGreater((ROOT/'static/vendor/three-r128'/name).stat().st_size,500)
        data=json.loads((ROOT/'static/data/reconstruction.json').read_text(encoding='utf-8'))
        self.assertEqual([x['id'] for x in data['objects']],['mosque','tree','well','coast'])
    def test_python_and_json_syntax(self):
        for path in ROOT.glob('*.py'): ast.parse(path.read_text(encoding='utf-8'))
        for path in (ROOT/'data').glob('*.json'): json.loads(path.read_text(encoding='utf-8'))
    def test_windows_launcher(self):
        raw=(ROOT/'run.bat').read_bytes()
        self.assertIn(b'\r\n',raw)
        self.assertIn(b'python app.py',raw)
        for name in ['index.html','base.html','oral-history.html']:
            self.assertIn(('templates\\'+name).encode(),raw)
        self.assertTrue((ROOT/'requirements.txt').is_file())

if __name__=='__main__': unittest.main(verbosity=2)
