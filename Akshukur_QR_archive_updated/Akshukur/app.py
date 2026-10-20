# -*- coding: utf-8 -*-
"""
АҚШҰҚЫР — ЦИФРЛЫҚ ШЕЖІРЕ
=======================
Ақшұқыр ауылының тарихын зерттеуге арналған интерактивті цифрлық жоба.
Flask backend: барлық деректер data/ папкасындағы JSON файлдардан оқылады.
Контентті өзгерту үшін Python кодты түрмей, тек JSON файлдарды өңдеу жеткілікті.
"""

import json
import os
import shutil

from flask import Flask, jsonify, render_template, request, send_from_directory, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DATA_DIR = os.path.join(BASE_DIR, "static", "data")


def ensure_project_data():
    """Support partial ZIP extractions and Vercel packaging by restoring the missing root data folder."""
    os.makedirs(DATA_DIR, exist_ok=True)
    fallback_dirs = [
        os.path.join(BASE_DIR, "screenshots", "data"),
        STATIC_DATA_DIR,
    ]
    for fallback_dir in fallback_dirs:
        if not os.path.isdir(fallback_dir):
            continue
        for name in os.listdir(fallback_dir):
            source = os.path.join(fallback_dir, name)
            target = os.path.join(DATA_DIR, name)
            if os.path.isfile(source) and not os.path.exists(target):
                shutil.copy2(source, target)
    return DATA_DIR


ensure_project_data()

app = Flask(__name__, static_folder="static", template_folder="templates")
# Қазақша әріптер JSON жауаптарда дұрыс көрсетілуі үшін
try:
    app.json.ensure_ascii = False          # Flask >= 2.2
except AttributeError:
    app.config["JSON_AS_ASCII"] = False    # Flask < 2.2

# ---------------------------------------------------------------------------
# Деректер дәлелдеме деңгейлері (бүкіл жобада ортақ)
# ---------------------------------------------------------------------------
EVIDENCE_LEVELS = {
    "written":        {"icon": "🟢", "label": "Жазба дерек",          "color": "#2ecc71"},
    "archive":        {"icon": "🔵", "label": "Архив дерегі",         "color": "#3b82f6"},
    "oral":           {"icon": "🟡", "label": "Ауызша дерек",         "color": "#eab308"},
    "research":       {"icon": "🟠", "label": "Зерттеу материалы",    "color": "#f97316"},
    "reconstruction": {"icon": "🟣", "label": "3D реконструкция",     "color": "#a855f7"},
    "needs_data":     {"icon": "⚪", "label": "Дерек қажет",          "color": "#94a3b8"},
}

_EVIDENCE_DESCS = {
    "written": "Жазба көздерде расталған мәлімет.",
    "archive": "Архив құжатына нақты сілтемесі бар дерек.",
    "oral": "Жергілікті адамдардың естелігі — кросс-тексеру қажет.",
    "research": "Ашық зерттеулер мен құжаттамалық материалдар.",
    "reconstruction": "Болжамды визуализация — тарихи факт емес.",
    "needs_data": "Әлі расталмаған — зерттеу барысында толықтырылады.",
}
for _k, _d in _EVIDENCE_DESCS.items():
    EVIDENCE_LEVELS[_k]["desc"] = _d

# ---------------------------------------------------------------------------
# «Тұлғалар» бөлімі: тексерілмеген өмірбаяндар енгізілмейді (Талап 8).
# Нақты жазба дерек табылған адамдар осы тізімге қосылады.
# ---------------------------------------------------------------------------
PERSONS = [
    {
        "id": "person-mashyryq",
        "name": "Машырық қажы",
        "role": "Рухани және білім дәуірімен байланыстырылатын тұлға",
        "summary": "Жергілікті ауызша деректер мен зерттеу материалдары Машырық қажы есімін Ақшұқыр өңіріндегі мешіт, медресе және білім беру дәуірімен байланыстырады.",
        "bio": "Тұлғаның өмір жылдары мен нақты іс-әрекеті туралы жазба дерек әзірге жинақталған жоқ. Ауызша деректер мен 1887 жылғы жазба дерек жанында тұрғызылып, зерттеу жүргізілуде. Расталмаған мәлімет факт ретінде көрсетілмейді.",
        "evidence": "oral",
        "image": None,
        "sources": [],
    },
    {
        "id": "person-qoshqar-ata",
        "name": "Қошқар ата",
        "role": "Қошқар ата қорымымен байланысты атақты есім",
        "summary": "Қорымға атын берген тұлға туралы нақты жазба деректер шектеулі — есім ауызша дәстүрде сақталған.",
        "bio": "Қошқар ата қорымы — жергілікті маңызы бар тарих және мәдениет ескерткіші (ресми мәдени мұра картасында тіркелген). Тұлғаның өмірбаяны ауызша тарих деңгейінде: нақты жылдар мен деректемелер зерттеу барысында толықтырылады.",
        "evidence": "oral",
        "image": "images/Koshkar-Ata-2.jpg",
        "sources": ["src-inmap-qoshqar", "src-wiki-qoshqar"],
    },
    {
        "id": "person-marshal-abdikhalykov",
        "name": "Маршал Әбдіхалықов",
        "role": "Жазушы, журналист, публицист (1936–1990)",
        "summary": "Маңғыстау өлкесінің тумасы, жазушы. Ақшұқыр ауылындағы мектеп-гимназияға оның есімі берілген, мектепте мұражайы бар.",
        "bio": "1936 жылы 26 шілдеде Маңғыстау өңірінде дүниеге келген (дереккөздерде туған жері әртүрлі көрсетілген: Форт-Шевченко қаласы; кейбір материалдарда Ақшұқыр маңы деп те айтылады). 1959 жылы Қазақ мемлекеттік университетінің филология факультетін бітірген. «Отызмыңыншы» (1965), «Маңғыстау хикаялары» (1967), «Жердің асты жеті қат» романы (1978) және басқа шығармалардың авторы. Маңғыстау облысы, Түпқараған ауданы, Ақшұқыр ауылындағы орта мектепке жазушының аты берілген және мектепте мұражайы бар. Мектеп қазір «Маршал Әбдіхалықов атындағы мектеп-гимназия» болып тіркелген.",
        "evidence": "written",
        "image": "images/marshal-abdihalikov.jpg",
        "sources": ["src-adebiportal-marshal", "src-marshal-school"],
    },
    {
        "id": "person-balanzhan-qozhashova",
        "name": "Қожашова Баланжан",
        "role": "Озат жылқышы, еңбек ардагері, Социалистік Еңбек Ері (1948)",
        "summary": "Социалистік Еңбек Ері (1948), «Орақ пен Балға» алтын медалінің және Ленин орденінің иегері. Ақшұқыр ауылында Баланжан Қожашова көшесі бар.",
        "bio": "1920 жылы Маңғыстау облысы, Түпқараған ауданы, Қызылөзен ауылында туған, 1982 жылы қайтыс болған. 16 жасында Калинин атындағы колхозда мал бағудан еңбек жолын бастаған; 1943–1958 жылдары жылқы фермасын басқарып, аудандық және облыстық жарыстардың бірнеше жыл қатарынан жеңімпазы болған (1947 жылы 105 биеден 105 құлын, 1948 жылы 132 биеден 132 құлын). 1963 жылы Қызылөзен түйе совхозында сауыншы болып жұмыс жасаған. Есте сақтау: Ақшұқыр ауылындағы Баланжан Қожашова көшесі.",
        "evidence": "written",
        "image": "images/qozhashova-balanzhan.jpg",
        "sources": ["src-wiki-balanzhan"],
    },
    {
        "id": "person-tamara-asar",
        "name": "Тамара Асар",
        "role": "Әнші, «Қазақстанның еңбек сіңірген қайраткері»",
        "summary": "1976 жылы 16 шілдеде Ақшұқыр ауылында ұстаздар отбасында туған әнші. «Құрмет» орденінің иегері (2014).",
        "bio": "Маңғыстау облыстық филармониясындағы Абыл Тарақұлы атындағы оркестрдің әншісі. Марапаттары: ҚР тәуелсіздігіне 10 жыл (2001) және 20 жыл (2011) медальдері, «Серпер» жастар сыйлығы (2007), «Құрмет» ордені (2014), Ақтау қаласының «Құрметті азаматы» (2018), «Қазақстанның еңбек сіңірген қайраткері» атағы (2019).",
        "evidence": "written",
        "image": "images/tamara-asar.jpg",
        "sources": ["src-wiki-tamara"],
    },
    {
        "id": "person-nurbayev-omirzaq",
        "name": "Нұрбаев Өмірзақ",
        "role": "Ақшұқырда есімі көшеге берілген тұлға",
        "summary": "Ақшұқыр ауылындағы көшелердің бірі Өмірзақ Нұрбаев есімін алып жүр — бұл Түпқараған ауданы әкімдігінің ресми дерегінде тіркелген.",
        "bio": "Тұлғаның өмірбаяны мен нақты еңбек жолы туралы жазба дерек әзірге жинақталған жоқ — зерттеу барысында толықтырылады. Қолда бар расталған дерек: Ақшұқыр ауылындағы Өмірзақ Нұрбаев көшесінің ресми атауы (Түпқараған ауданы әкімдігінің жарияланымы).",
        "evidence": "written",
        "image": "images/nurbaev-omirzaq.jpg",
        "sources": ["src-gov-tupkaragan-streets"],
    },
    {
        "id": "person-anar-shamshadinova",
        "name": "Анар Шамшадинова",
        "role": "Ақын, журналист, Қазақстан Жазушылар Одағының мүшесі",
        "summary": "1974 жылы Маңғыстау облысында туған ақын. Ақшұқырмен нақты байланысы қолда бар дереккөздерде көрсетілмеген — тексеру қажет.",
        "bio": "Әл-Фараби атындағы Қазақ Ұлттық университетінің журналистика және шығыстану факультеттерін бітірген (1996–97). «Поэзия көктемі — 2000» байқауының жеңімпазы, «Шабыт-2003» халықаралық фестивалінің жүлдегері. «Жанар» (2001), «Жоқсың сен» (2004), «Кешірсең мені сен ғана» (2009), «Тамызда қайтып оралшы» (2010) өлең жинақтарының авторы. «Ақтау ақпарат» газетінің аға тілшісі, «Жанартау» қоғамдық бірлестігінің төрайымы. Ақшұқыр ауылымен нақты байланысы туралы дереккөз әзірге жоқ — зерттеу барысында нақтыланады.",
        "evidence": "written",
        "image": "images/anar-shamshadinova.jpg",
        "sources": ["src-adebiportal-anar"],
    },
    {
        "id": "person-sarsenov-burkitbay",
        "name": "Сәрсенов Бүркітбай",
        "role": "Мәлімет тексерілуде",
        "summary": "Ашық дереккөздерден тұлға туралы сенімді жазба дерек әзірге табылған жоқ — мәлімет тексерілуде.",
        "bio": "Бұл тұлға туралы расталған мәлімет әзірге жинақталған жоқ. Ақшұқырмен немесе Маңғыстау өңірімен байланысы нақты дереккөзбен расталғанға дейін карточка «дерек қажет» мәртебесінде қалады. Қолыңызда құжат немесе фото болса, жоба дереккөздеріне енгізуге болады.",
        "evidence": "needs_data",
        "image": "images/sarsenov-burkitbay.jpg",
        "sources": [],
    },
]

RESEARCH_METHODS = [
    ("🗂️", "Ақпаратты жинау", "Ашық дереккөздер, энциклопедиялық материалдар, интернет-ресурстар бойынша алғашқы мәліметтерді жинау."),
    ("🗄️", "Архивтік деректерді қарастыру", "Архив құжаттарын (сондай-ақ 1887 жылғы статистикалық деректі) тауып, деректемесін тіркеу."),
    ("📚", "Кітап/мақалаларды зерттеу", "Аймақ тарихына арналған басылымдар мен ғылыми мақалаларды талдау."),
    ("🖼️", "Фотоларды жинау", "Отбасылық архивтер мен мектеп мұрағатынан ескі фотоларды сканерлеу және каталогтау."),
    ("🎙️", "Тұрғындармен сұхбат", "Ауыл ақсақалдары мен ұзақ жылдық тұрғындардан естеліктер жазып алу."),
    ("🗺️", "Тарихи орындарды картаға түсіру", "Әр нүктенің координатасын анықтап, интерактивті картаға енгізу."),
    ("⚖️", "Ескі және қазіргі деректерді салыстыру", "Бір нысанның әр кезеңдегі деректерін жұптап, өзгерісті құжаттау."),
    ("✅", "Қорытынды жасау", "Тек кемінде бір нақты дерекпен расталған мәліметтерді ғана факт ретінде ұсыну."),
]

SITE_NAME = "АҚШҰҚЫР — ЦИФРЛЫҚ ШЕЖІРЕ"


def load_data(filename):
    """JSON файлын root data/ ішінен оқиды; Vercel/ZIP жеткіліксіздігі болса резервті каталогтан алады."""
    candidates = [
        os.path.join(DATA_DIR, filename),
        os.path.join(BASE_DIR, "screenshots", "data", filename),
        os.path.join(STATIC_DATA_DIR, filename),
    ]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            app.logger.warning("Дерек файлы дұрыс емес (%s): %s", filename, exc)
            return []
    app.logger.warning("Дерек файлы табылмады (%s)", filename)
    return []


def image_url(image):
    """Local uploaded photos always live under static/images; keep original names."""
    if not image:
        return None
    filename = image.lstrip('/')
    if filename.startswith('static/'):
        filename = filename[len('static/'):]
    if not filename.startswith('images/'):
        filename = 'images/' + filename
    for photo in load_data('photos.json'):
        if photo.get('image') == filename and photo.get('display_image'):
            filename = photo['display_image']
            break
    if not os.path.isfile(os.path.join(app.static_folder, filename)):
        return None
    return url_for('static', filename=filename)


def places_with_images():
    return [dict(p, image_url=image_url(p.get('image')))
            for p in load_data('places.json')]


@app.context_processor
def inject_globals():
    """Барлық шаблонда қолжетімді ортақ айнымалылар."""
    return {
        "site_name": SITE_NAME,
        "image_url": image_url,
        "evidence_levels": EVIDENCE_LEVELS,
        "current_year": 2026,
        "qr_videos": [item for item in load_data("qr_videos.json")
                      if os.path.isfile(os.path.join(app.static_folder, item["image"]))]
                     if request.endpoint in ("history", "archive", "oral_history", "map_page") else [],
    }


@app.route("/images/<path:filename>")
def serve_project_image(filename):
    """Жоба ішіндегі нақты суреттерді қауіпсіз түрде көрсету."""
    allowed = (".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif", ".bmp", ".avif")
    if not filename.lower().endswith(allowed):
        return "", 404
    return send_from_directory(os.path.join(BASE_DIR, 'static', 'images'),
                               filename.removeprefix('images/'))


# ---------------------------------------------------------------------------
# Беттер
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    history = load_data("history.json")
    places = load_data("places.json")
    stats = [
        {"value": "1943", "label": "Алғашқы мектеп ашылған жыл", "evidence": "written"},
        {"value": "1887", "label": "Медресе туралы жазба дерек", "evidence": "archive"},
        {"value": str(len(places)), "label": "Картадағы тарихи нүкте", "evidence": "research"},
        {"value": "9+", "label": "Зерттелетін тарихи кезең", "evidence": "research"},
    ]
    return render_template("index.html", history=history, places=places, stats=stats)


@app.route("/tarikh")
def history():
    from site_content import available_photos
    return render_template("history.html", history=load_data("history.json"),
                           sources=load_data("sources.json"), photos=available_photos(app))


@app.route("/tulghalar")
def persons():
    return render_template("persons.html", persons=PERSONS,
                           sources=load_data("sources.json"))


@app.route("/mashyryq")
def mashyryq():
    return render_template("mashyryq.html", sources=load_data("sources.json"))


@app.route("/karta")
def map_page():
    # View-only enrichment: shared places.json and /api/places remain untouched.
    from section_archive import archive_photo, places_view
    places = places_view(app.static_folder, load_data("places.json"), load_data("sources.json"))
    categories = sorted({p.get("category", "auyl") for p in places})
    return render_template("map.html", places=places, categories=categories,
                           unverified_photo=archive_photo(app.static_folder, "cemetery-candidate"))


@app.route("/rekonstrukciya")
def reconstruction():
    return render_template("reconstruction.html")


@app.route("/mektep")
def school():
    history = load_data("history.json")
    school_periods = [h for h in history if h.get("school_related")]
    from section_archive import school_view
    return render_template("school.html", school_periods=school_periods,
                           school_archive=school_view(app.static_folder, load_data("sources.json")))


@app.route("/muragat")
def archive():
    from site_content import available_photos
    sources = load_data("sources.json")
    categories = sorted({s.get("type", "zertteu") for s in sources})
    return render_template("archive.html", sources=sources, categories=categories, photos=available_photos(app))


@app.route("/auyzsha-tarikh")
def oral_history():
    return render_template("oral-history.html", interviews=load_data("interviews.json"))


@app.route("/eksursiya")
def excursion():
    places = places_with_images()
    # Экскурсия маршруты — реті places.json ішіндегі excursion_order бойынша
    route = sorted([p for p in places if p.get("excursion_order")],
                   key=lambda p: p["excursion_order"])
    return render_template("excursion.html", route=route)


@app.route("/zertteu")
def research():
    return render_template("research.html", methods=RESEARCH_METHODS)


@app.route("/derek-kozder")
def sources_page():
    return render_template("sources.html", sources=load_data("sources.json"))


# ---------------------------------------------------------------------------
# JSON API (JS компоненттері пайдаланады: timeline, карта, іздеу)
# ---------------------------------------------------------------------------
@app.route("/api/history")
def api_history():
    return jsonify(load_data("history.json"))


@app.route("/api/places")
def api_places():
    return jsonify(places_with_images())


@app.route("/api/sources")
def api_sources():
    return jsonify(load_data("sources.json"))


@app.route("/api/interviews")
def api_interviews():
    return jsonify(load_data("interviews.json"))


@app.route("/api/persons")
def api_persons():
    return jsonify(PERSONS)


@app.route("/api/search")
def api_search():
    from site_content import search_site
    return jsonify(search_site(app, request.args.get("q", "")))


@app.route("/zhoba")
@app.route("/tarikh/zhoba")
def project_page():
    return render_template("project.html")


@app.route("/foto-arkhivi")
@app.route("/tarikh/foto-arkhivi")
def photo_archive_page():
    from site_content import archive_catalog, PHOTO_CATEGORIES
    return render_template("photo-archive.html", catalog=archive_catalog(app), photo_categories=PHOTO_CATEGORIES)


@app.route("/izdeu")
def search_page():
    from site_content import search_site
    query = request.args.get("q", "").strip()
    return render_template("search.html", query=query, hits=search_site(app, query))


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


def validate_project_templates():
    """Fail early if a partial extraction omitted a page or Jinja dependency."""
    import ast
    from jinja2 import meta
    required = {"index.html", "base.html", "oral-history.html", "404.html"}
    with open(__file__, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "render_template" and node.args
                and isinstance(node.args[0], ast.Constant)):
            required.add(node.args[0].value)
    checked = set()
    while required - checked:
        name = sorted(required - checked)[0]
        source, _, _ = app.jinja_env.loader.get_source(app.jinja_env, name)
        parsed = app.jinja_env.parse(source)
        app.jinja_env.get_template(name)
        required.update(n for n in meta.find_referenced_templates(parsed) if n)
        checked.add(name)
    return sorted(checked)


if __name__ == "__main__":
    # python -m pip install -r requirements.txt && python app.py
    try:
        validate_project_templates()
    except Exception as exc:
        raise SystemExit("Project template check failed. Extract the COMPLETE ZIP. " + str(exc))
    app.run(host="127.0.0.1", port=5000, debug=False)
