"""Run: python -m unittest discover -s tests -v (only Flask is required)."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import app, PERSONS


def load(name):
    return json.loads((ROOT / 'data' / name).read_text(encoding='utf-8'))


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        # Hidden 3D capture/card images receive their src at runtime.
        # Runtime image completeness is covered by test_reconstruction_browser.py.
        if tag == 'img' and dict(attrs).get('src'):
            self.urls.append(dict(attrs)['src'])


class WebsiteRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.baseline = json.loads((ROOT / 'tests/baseline.json').read_text(encoding='utf-8'))

    def test_routes_and_rendered_images(self):
        for rule in app.url_map.iter_rules():
            if '<' in rule.rule:
                continue
            with self.subTest(path=rule.rule):
                response = self.client.get(rule.rule)
                self.assertEqual(response.status_code, 200)
                if response.mimetype == 'text/html':
                    images = Images()
                    images.feed(response.get_data(as_text=True))
                    for url in images.urls:
                        image = self.client.get(url)
                        self.assertEqual(image.status_code, 200, url)
                        self.assertTrue(image.mimetype.startswith('image/'), url)
                        image.close()
                response.close()

    def test_qoshqar_unique_and_exact(self):
        places = load('places.json')
        self.assertEqual(len({p['id'] for p in places}), len(places))
        q = [p for p in places if p['id'] == 'place-qoshqar']
        self.assertEqual(len(q), 1)
        self.assertEqual([q[0]['lat'], q[0]['lng']], [43.777911, 51.080546])
        self.assertEqual(q[0]['name'], 'Қошқар ата')
        self.assertEqual(q[0]['image'], 'images/Koshkar-Ata-2.jpg')

    def test_separate_verified_village_objects(self):
        places = {p['id']: p for p in load('places.json')}
        school, culture = places['place-school-now'], places['place-culture']
        self.assertEqual(school['name'], 'Ақшұқыр мектебі')
        self.assertEqual(culture['name'], 'Ақшұқыр мәдениет үйі')
        self.assertEqual([school['lat'], school['lng']], [43.778691, 51.070312])
        self.assertEqual([culture['lat'], culture['lng']], [43.781322, 51.061553])
        for p in [school, culture]:
            self.assertEqual(p['coordinate_status'], 'verified')
            self.assertTrue(p['coordinate_source'].startswith('https://'))
            self.assertIsNone(p['image'])  # never use unrelated building photos
            self.assertIn('фотосы', p['photo_note'])

    def test_historic_places_preserved(self):
        places = {p['id']: p for p in load('places.json')}
        for id in self.baseline['original_place_ids']:
            self.assertIn(id, places)
        for id, coord in self.baseline['unchanged_coordinates'].items():
            self.assertEqual([places[id]['lat'], places[id]['lng']], coord)

    def test_historical_text_and_persons_unchanged(self):
        self.assertEqual(PERSONS, self.baseline['persons'])
        current = {h['id']: h for h in load('history.json')}
        for h in self.baseline['history']:
            for key, value in h.items():
                self.assertEqual(current[h['id']][key], value, (h['id'], key))

    def test_protected_files_unchanged(self):
        # These three files are deliberately changed by the reconstruction update.
        allowed_changes = {'templates/reconstruction.html', 'static/js/3d.js', 'run.bat'}
        for file, sha in self.baseline['protected_sha256'].items():
            if file in allowed_changes:
                continue
            self.assertEqual(hashlib.sha256((ROOT / file).read_bytes()).hexdigest(), sha, file)

    def test_all_original_photos_preserved_and_displayed(self):
        photos = load('photos.json')
        self.assertEqual(len(photos), 22)
        for p in photos:
            original = ROOT / 'static' / p['image']
            self.assertTrue(original.is_file())
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), p['sha256'])
            if p.get('display_image'):
                self.assertTrue((ROOT / 'static' / p['display_image']).is_file())
        for url in ['/tarikh', '/muragat']:
            html = self.client.get(url).get_data(as_text=True)
            self.assertEqual(html.count('Сәйкестендіру расталмаған'), 14)
            for p in photos:
                self.assertIn(p['caption'], html)

    def test_api_image_paths_and_legacy_urls(self):
        for p in self.client.get('/api/places').json:
            if p.get('image_url'):
                with self.client.get(p['image_url']) as response:
                    self.assertEqual(response.status_code, 200)
        for url in ['/images/before.jpeg', '/images/images/Koshkar-Ata-2.jpg']:
            with self.client.get(url) as response:
                self.assertEqual(response.status_code, 200)

    def test_search_keeps_both_village_objects(self):
        for query, title in [('мәдениет', 'Ақшұқыр мәдениет үйі'), ('мектебі', 'Ақшұқыр мектебі')]:
            results = self.client.get('/api/search', query_string={'q': query}).json
            self.assertIn(title, [r['title'] for r in results])


if __name__ == '__main__':
    unittest.main()
