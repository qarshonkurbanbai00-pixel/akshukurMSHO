"""Current update tests: python -m unittest tests.test_content_update -v."""
from pathlib import Path
import ast
import hashlib
import json
import sys
import unittest
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import app
from site_content import archive_catalog, index_site

class Assets(HTMLParser):
    def __init__(self):super().__init__();self.assets=[];self.ids=set()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.add(a['id'])
        for k in ['src','href']:
            u=a.get(k,'')
            if u.startswith(('/static/','/images/')):self.assets.append(u)

class ContentUpdate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.client=app.test_client()
    def test_all_routes_templates_assets(self):
        for p in ROOT.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
        for p in (ROOT/'templates').glob('*.html'):app.jinja_env.get_template(p.name)
        for rule in app.url_map.iter_rules():
            if '<' in rule.rule:continue
            with self.subTest(page=rule.rule):
                r=self.client.get(rule.rule);self.assertEqual(r.status_code,200)
                if r.mimetype=='text/html':
                    parser=Assets();parser.feed(r.get_data(as_text=True))
                    for url in parser.assets:
                        with self.client.get(url) as asset:self.assertEqual(asset.status_code,200,url)
    def test_full_text_search_sections(self):
        for query,path in [('ұрпақтар сабақтастығы','/tarikh/zhoba'),('фото қосылады','/tarikh/foto-arkhivi'),('тереңдігі','/rekonstrukciya'),('Ақшұқыр мектебі','/karta'),('Баланжан','/tulghalar'),('Мектеп','/mektep')]:
            with self.subTest(query=query):
                hits=self.client.get('/api/search',query_string={'q':query}).json
                self.assertTrue(hits)
                self.assertTrue(any(h['url'].startswith(path) for h in hits),hits)
                self.assertTrue(all(h['title'] and h['snippet'] and h['url'].startswith('/') for h in hits))
    def test_search_case_multiple_words_single_character_empty_and_no_results(self):
        for q in ['  ФОТО   ҚОСЫЛАДЫ  ','цифрлық мұраны','М']:
            self.assertTrue(self.client.get('/api/search',query_string={'q':q}).json)
        for q in ['', '  ', 'qwertynonexistent987654', '<script>alert(123)</script>']:
            self.assertEqual(self.client.get('/api/search',query_string={'q':q}).json,[])
    def test_search_page_fallback_and_escaping(self):
        self.assertIn('Іздеу бойынша нәтиже табылмады',self.client.get('/izdeu?q=zzz987654321').get_data(as_text=True))
        html=self.client.get('/izdeu',query_string={'q':'<script>alert(1)</script>'}).get_data(as_text=True)
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('&lt;script&gt;',html)
        self.assertIn('Фото архиві',self.client.get('/izdeu?q=фото').get_data(as_text=True))
    def test_result_pages_and_fragments(self):
        records=index_site(app)
        for r in records:
            parts=urlsplit(r['url']);response=self.client.get(parts.path)
            self.assertEqual(response.status_code,200,r['url'])
            if parts.fragment:
                parser=Assets();parser.feed(response.get_data(as_text=True))
                self.assertIn(unquote(parts.fragment),parser.ids,r['url'])
    def test_no_fabricated_historical_photos(self):
        catalog=archive_catalog(app)
        placeholders=[p for p in catalog if p['category']!='pending']
        self.assertEqual(len(placeholders),5)
        self.assertTrue(all(p['image'] is None and p['status']=='Фото қосылады' for p in placeholders))
        for p in catalog:
            self.assertEqual(p['year'],'Белгісіз');self.assertTrue(p['provenance'])
            if p['image']:
                with self.client.get(p['image']) as response:self.assertEqual(response.status_code,200)
                self.assertEqual(p['category'],'pending')
                self.assertIn('расталмаған',p['description'])
    def test_school_label_consistency(self):
        html=self.client.get('/mektep').get_data(as_text=True)
        self.assertIn('<h1 class="page-title reveal">Мектеп</h1>',html)
        self.assertNotIn('>Мектеп тарихы</a>',html)
        self.assertIn('Мектеп — ЦИФРЛЫҚ ШЕЖІРЕ',html)
    def test_preserved_protected_files_and_original_metadata(self):
        hashes=json.loads((ROOT/'verification/content-update/original-protected-hashes.json').read_text())
        for name,sha in hashes.items():
            with self.subTest(file=name):self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),sha)
    def test_school_only_labels_changed(self):
        source=(ROOT/'templates/school.html').read_text()
        source=source.replace('{% block title %}Мектеп —','{% block title %}Мектеп тарихы —').replace('>Мектеп</h1>','>Ақшұқырдың мектеп тарихы</h1>')
        expected=json.loads((ROOT/'verification/content-update/school-original-hash.json').read_text())['sha256']
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),expected)

if __name__=='__main__':unittest.main()
