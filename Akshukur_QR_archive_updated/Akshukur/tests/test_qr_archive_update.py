"""Current QR/archive acceptance checks. Runtime dependency: Flask only.
Run: python -m unittest discover -s tests -p test_qr_archive_update.py -v
"""
import ast
import hashlib
import json
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import app,validate_project_templates
from site_content import available_photos,archive_catalog, index_site

class Markup(HTMLParser):
    def __init__(self):
        super().__init__();self.assets=[];self.images=[];self.ids=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if tag=='img':self.images.append(a)
        for key in ('href','src'):
            if a.get(key,'').startswith(('/static/','/images/')):self.assets.append(a[key])

class QRArchiveUpdate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.client=app.test_client()
    def test_all_routes_and_local_assets(self):
        report=[]
        for rule in app.url_map.iter_rules():
            if '<' in rule.rule:continue
            response=self.client.get(rule.rule)
            self.assertEqual(response.status_code,200,rule.rule)
            report.append({'path':rule.rule,'status':response.status_code})
            if response.mimetype=='text/html':
                markup=Markup();markup.feed(response.get_data(as_text=True))
                self.assertEqual(len(markup.ids),len(set(markup.ids)),rule.rule)
                for url in markup.assets:
                    with self.client.get(url) as asset:self.assertEqual(asset.status_code,200,(rule.rule,url))
        (ROOT/'verification/qr-archive-routes.json').write_text(json.dumps(report,indent=2))
        self.assertEqual(self.client.get('/nonexistent-qr-update').status_code,404)
    def test_templates_and_python_syntax(self):
        templates=validate_project_templates()
        self.assertEqual(set(templates),{p.name for p in (ROOT/'templates').glob('*.html')})
        self.assertIn('_qr_videos.html',templates)
        for path in ROOT.glob('*.py'):ast.parse(path.read_text())
        for path in (ROOT/'data').glob('*.json'):json.loads(path.read_text())
    def test_only_existing_photos_no_empty_cards(self):
        photos=available_photos(app);catalog=archive_catalog(app)
        source=json.loads((ROOT/'data/photos.json').read_text())
        self.assertEqual(len(catalog),len(photos))
        self.assertEqual(len(photos),len(source)-2)
        self.assertTrue(all(r['image'] for r in catalog))
        for r in catalog:
            with self.client.get(r['image']) as img:self.assertEqual(img.status_code,200)
            self.assertTrue(r['provenance']);self.assertEqual(r['year'],'Белгісіз')
        for path in ['/tarikh','/muragat','/tarikh/foto-arkhivi']:
            html=self.client.get(path).get_data(as_text=True)
            self.assertNotIn('<span class="photo-slot">',html)
            self.assertNotIn('class="img-placeholder"',html)
            markup=Markup();markup.feed(html)
            self.assertTrue(all(i.get('alt','').strip() for i in markup.images),path)
    def test_original_images_and_protected_features(self):
        expected=json.loads((ROOT/'verification/qr-archive-protected.json').read_text())
        for name,sha in expected.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),sha,name)
    def test_exact_original_qr_files_and_no_fabricated_links(self):
        records=json.loads((ROOT/'data/qr_videos.json').read_text())
        self.assertEqual({r['image'] for r in records},{'images/aksakal_memories.jpeg','images/aksakal_memories (2).jpeg','images/qoshkar-ata.jpeg'})
        for r in records:
            self.assertIsNone(r['youtube_url']);self.assertEqual(r['status'],'unresolved')
            self.assertTrue((ROOT/'static'/r['image']).is_file())
        for path,count in [('/tarikh',3),('/auyzsha-tarikh',3),('/muragat',3),('/karta',1)]:
            html=self.client.get(path).get_data(as_text=True)
            self.assertEqual(html.count('class="qr-card glass"'),count)
            self.assertEqual(html.count('QR-кодты сканерлеу арқылы видеоны ашыңыз'),count)
            self.assertIn('Сілтеме анықталмады',html)
            self.assertNotIn('href="https://youtu',html)
    def test_original_route_map_and_no_new_dependencies(self):
        expected=json.loads((ROOT/'verification/qr-archive-route-baseline.json').read_text())
        self.assertEqual(sorted(r.rule for r in app.url_map.iter_rules()),expected)
        self.assertEqual((ROOT/'requirements.txt').read_text().strip(),'Flask>=2.2,<4.0')
    def test_search_preserved(self):
        for q,path in [('Мектеп','/mektep'),('Баланжан','/tulghalar'),('ұрпақтар сабақтастығы','/tarikh/zhoba'),('QR','/tarikh')]:
            hits=self.client.get('/api/search',query_string={'q':q}).json
            self.assertTrue(any(h['url'].startswith(path) for h in hits),(q,hits))
        self.assertEqual(self.client.get('/api/search?q=zz98765none').json,[])
        for r in index_site(app):
            parts=urlsplit(r['url']);response=self.client.get(parts.path)
            self.assertEqual(response.status_code,200)
            if parts.fragment:
                markup=Markup();markup.feed(response.get_data(as_text=True))
                self.assertIn(unquote(parts.fragment),markup.ids)
    def test_motion_and_small_script_changes(self):
        css=(ROOT/'static/css/content-update.css').read_text()
        self.assertIn('prefers-reduced-motion:reduce',css)
        self.assertIn('.qr-original img',css)
        self.assertIn('animation:none!important',css)
        js=(ROOT/'static/js/main.js').read_text()
        self.assertIn('!motionQuery.matches',js)
        self.assertIn("behavior: motionQuery.matches ? 'instant' : 'smooth'",js)

if __name__=='__main__':unittest.main(verbosity=2)
