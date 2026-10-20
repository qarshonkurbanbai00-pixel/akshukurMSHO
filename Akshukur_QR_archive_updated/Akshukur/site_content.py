"""History subpages and dependency-free, local full-text site search."""
from pathlib import Path
from html.parser import HTMLParser
import json
import re
import unicodedata
from threading import RLock

PHOTO_CATEGORIES = [
    ('village', 'Ауыл көріністері', 'Ауыл көшелері, тұрмыс пен елді мекеннің бұрынғы келбеті.'),
    ('buildings', 'Ғимараттар мен нысандар', 'Ғимараттың атауы мен түсірілген орны расталған материалдар.'),
    ('school', 'Мектеп өмірі', 'Сыныптар, мұғалімдер, оқушылар мен мектеп оқиғалары.'),
    ('culture', 'Мәдени іс-шаралар', 'Мерекелер, шығармашылық ұжымдар және мәдени кездесулер.'),
    ('people', 'Ауыл тұрғындары', 'Отбасылық фото, ауыл адамдарының өмірі мен еңбегі.'),
]

def available_photos(app):
    """Only files actually available under static/images enter the galleries."""
    photos = json.loads((Path(app.root_path)/'data/photos.json').read_text(encoding='utf-8'))
    result = []
    for item in photos:
        candidates = [item.get('display_image'), item.get('image')]
        relative = next((name for name in candidates if name and
                         name.startswith('images/') and
                         (Path(app.static_folder)/name).is_file()), None)
        if relative:
            result.append(dict(item, resolved_image=relative))
    return result


def archive_catalog(app):
    """Preserve existing photos without inventing provenance or empty cards."""
    records = []
    for i, p in enumerate(available_photos(app)):
        pending = p.get('identification') == 'unverified'
        category = p.get('category', 'pending')
        if not pending and category == 'pending':
            category = 'people' if p.get('identification') == 'filename' else 'village' if p.get('subject') == 'Қазіргі Ақшұқыр' else 'buildings'
        records.append(dict(id='candidate-'+str(i+1), category=category, title=p['caption'],
            year=p.get('year') or 'Белгісіз',
            description=p.get('description') or ('Бастапқы ZIP-тегі материал. Ақшұқыр ауылы, нақты оқиға, адамдар және тарихи кезеңмен байланысы тәуелсіз расталмаған.' if pending else 'Бастапқы жобадағы фото сақталды. Сәйкестендіру негізі бастапқы сипаттамада көрсетілген; бұл расталған тарихи фото дегенді білдірмейді.'),
            status='Сәйкестендіру қажет' if pending else 'Жоба фотоқоры · тарихи мерзімі расталмаған',
            provenance=p.get('provenance', 'Дереккөзі нақтылануда.')+' Бастапқы файл: '+p['image'].split('/')[-1],
            image='/static/'+p['resolved_image'],
            note='Жылы мен орны файл атауынан анықталмайды; түпнұсқа, иесінің түсіндірмесі және жариялау рұқсаты қажет.'))
    return records


def normalize(text):
    return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',text).casefold()))

class MainText(HTMLParser):
    """Extract visible main content, page headings and addressable article bodies."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.main=False;self.skip=0;self.text=[];self.blocks=[];self.current=None
        self.heading=None;self.h1=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='main':self.main=True
        if not self.main:return
        if tag in ('script','style','dialog'):self.skip+=1;return
        if self.skip:return
        if tag=='article':self.current={'id':attrs.get('id'),'text':[],'title':[]}
        if tag in ('h1','h2','h3'):self.heading=tag
    def handle_endtag(self,tag):
        if tag=='main':self.main=False
        if tag in ('script','style','dialog') and self.skip:self.skip-=1;return
        if tag=='article' and self.current:
            self.blocks.append(self.current);self.current=None
        if tag in ('h1','h2','h3'):self.heading=None
    def handle_data(self,data):
        if not self.main or self.skip:return
        text=' '.join(data.split())
        if not text:return
        self.text.append(text)
        if self.heading=='h1':self.h1.append(text)
        if self.current:
            self.current['text'].append(text)
            if self.heading:self.current['title'].append(text)

PAGES=[('index','/','Басты бет'),('history','/tarikh','Тарих'),
 ('project_page','/tarikh/zhoba','Жоба'),('photo_archive_page','/tarikh/foto-arkhivi','Фото архиві'),
 ('school','/mektep','Мектеп'),('map_page','/karta','Тарихи орындар'),
 ('persons','/tulghalar','Тұлғалар'),('mashyryq','/mashyryq','Машырық қажы'),
 ('reconstruction','/rekonstrukciya','3D реконструкция'),('archive','/muragat','Цифрлық архив'),
 ('oral_history','/auyzsha-tarikh','Ауызша тарих'),('excursion','/eksursiya','Виртуалды экскурсия'),
 ('research','/zertteu','Зерттеу'),('sources_page','/derek-kozder','Дереккөздер')]
_cache={'signature':None,'records':[]}
_lock=RLock()

def index_site(app):
    root=Path(app.root_path)
    files=sorted([*(root/'templates').glob('*.html'),*(root/'data').glob('*.json'),root/'static/data/reconstruction.json',root/'site_content.py'])
    signature=tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in files)
    with _lock:
        if _cache['signature']==signature:return _cache['records']
        records=[]
        for endpoint,path,section in PAGES:
            # Separate real page contexts: search is never part of the index.
            with app.test_request_context(path):
                html=app.make_response(app.view_functions[endpoint]()).get_data(as_text=True)
            parser=MainText();parser.feed(html)
            text=' '.join(parser.text)
            records.append({'title':' '.join(parser.h1) or section,'text':text,'url':path,'section':section})
            for block in parser.blocks:
                if not block['id']:continue
                records.append({'title':' '.join(block['title']) or section,
                    'text':' '.join(block['text']),'url':path+'#'+block['id'],'section':section})
        # Dynamic 3D object descriptions are loaded by JavaScript, not in initial HTML.
        data=json.loads((root/'static/data/reconstruction.json').read_text(encoding='utf-8'))
        for obj in data.get('objects',[]):
            records.append({'title':obj['name'],'text':' '.join(str(obj.get(k,'')) for k in ['name','description','source','unknown','photo_note']),
                'url':'/rekonstrukciya','section':'3D реконструкция'})
        # Data-backed place names use their exact original names and reliable anchors.
        places=json.loads((root/'data/places.json').read_text(encoding='utf-8'))
        for p in places:
            records.append({'title':p['name'],'text':' '.join(str(v) for v in p.values() if isinstance(v,(str,int))),
                'url':'/karta#card-'+p['id'],'section':'Тарихи орындар'})
        for r in records:r['normalized']=normalize(r['title']+' '+r['text'])
        _cache.update(signature=signature,records=records)
        return records

def search_site(app,query):
    query=normalize(str(query)[:200])
    if not query:return []
    tokens=query.split();hits=[];seen=set()
    for r in index_site(app):
        if not all(t in r['normalized'] for t in tokens):continue
        key=(r['url'],r['title'])
        if key in seen:continue
        seen.add(key)
        text=r['text'];fold=text.casefold();pos=fold.find(tokens[0])
        start=max(0,pos-65) if pos>=0 else 0
        snippet=('…' if start else '')+text[start:start+230]+('…' if len(text)>start+230 else '')
        title=normalize(r['title'])
        score=(100 if query==title else 0)+(30 if query in title else 0)+(15 if '#' in r['url'] else 0)+(5 if query in r['normalized'] else 0)
        hits.append((score,{'section':r['section'],'title':r['title'],'snippet':snippet,'url':r['url']}))
    hits.sort(key=lambda x:-x[0])
    return [h[1] for h in hits]
