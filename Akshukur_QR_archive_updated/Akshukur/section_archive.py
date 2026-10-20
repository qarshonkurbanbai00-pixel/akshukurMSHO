# -*- coding: utf-8 -*-
"""View-only enrichment for /karta and /mektep. Shared JSON/API data stay intact."""
from copy import deepcopy
from pathlib import Path
from flask import url_for

PROVENANCE = 'Жобаға берілген бастапқы ZIP архиві. Фото авторы мен түсірілген күні көрсетілмеген.'
PHOTO_RECORDS = {
    'qoshqar-statue': ('Koshkar-Ata-2.jpg', 'Қошқар ата қорымындағы қошқар мүсіні', 'Нысан бастапқы фото тізілімінде сәйкестендірілген.'),
    'qoshqar-entry': ('Koshkar-Ata-2.jpeg', 'Қошқар ата қорымының кіреберісі', 'Фотодағы «Қошқар-ата» жолсілтегіші арқылы сәйкестендірілген.'),
    'culture': ('akshukur-culture-house.jpeg', 'Ақшұқыр мәдениет үйінің кіреберісі', 'Қасбеттегі «Ақшұқыр мәдениет үйі» жазуы арқылы сәйкестендірілген.'),
    'school-building': ('akshukur-school.jpeg', 'Мектеп ғимараты және Маршал Әбдіхалықов ескерткіші', 'Файл атауы және ескерткіш тақтасындағы жазу салыстырылды. Бұл бүкіл ғимараттың панорамасы емес.'),
    'school-display': ('school.jpeg', '«Мектеп басшылары» стенді', 'Бұл ғимараттың сыртқы көрінісі емес. Тұлғалардың есімдері мен қызмет жылдары көшіріліп жазылмады.'),
    'village': ('after.jpeg', 'Ақшұқырдың қазіргі көрінісі — фотоколлаж', 'Бастапқы photos.json тізілімінде ауыл көрінісі ретінде көрсетілген.'),
    'old-candidate': ('first-school-1943.jpeg', 'Архивтік ғимарат: нысан мен жыл расталмаған', 'Файл атауы 1943 жылды меңзейді, бірақ before.jpeg файлының дәл көшірмесі. Бастапқы фото тізілімінде ғимарат анықталмаған. Алғашқы мектептің расталған фотосы ретінде қолданылмайды.'),
    'cemetery-candidate': ('galery.jpg', 'Қорым көрінісі: нақты орны расталмаған', 'Бастапқы фото тізілімінде орны расталмаған. Қошқар ата нысанына байланыстырылмайды.'),
}


def archive_photo(static_folder, key):
    filename, caption, note = PHOTO_RECORDS[key]
    relative = 'images/' + filename
    exists = (Path(static_folder) / relative).is_file()
    return dict(key=key, filename=filename, caption=caption, note=note,
                provenance=PROVENANCE, url=url_for('static', filename=relative) if exists else None)


def places_view(static_folder, places, sources):
    result = deepcopy(places)
    galleries = {
        'place-akshukur': ['village'], 'place-modern': ['village'],
        'place-qoshqar': ['qoshqar-statue', 'qoshqar-entry'],
        'place-culture': ['culture'],
        'place-school-now': ['school-building', 'school-display'],
    }
    source_lookup = {s['id']: s for s in sources}
    for place in result:
        place['gallery'] = [archive_photo(static_folder, key) for key in galleries.get(place['id'], [])]
        place['image_url'] = next((p['url'] for p in place['gallery'] if p['url']), None)
        place['source_details'] = [source_lookup[sid] for sid in place.get('sources', []) if sid in source_lookup]
        if place['id'] == 'place-school-1943':
            place.update(summary='Бастапқы жобада алғашқы мектеп 1943 жылмен байланыстырылған. Қосымша дерек қажет.',
                         description='Ашылу жылы, алғашқы ғимараттың орны, мұғалімдер мен оқушылар туралы архив құжаты тіркелмеген. Бұл мәліметтер әзірге тарихи факт ретінде ұсынылмайды.', evidence='needs_data',
                         photo_note='Алғашқы мектептің расталған фотосы жоқ. Қосымша дерек қажет.')
        if place['id'] == 'place-medrese':
            place.update(summary='Жоба материалында 1887 жылғы медресе туралы жазба аталады. Қосымша дерек қажет.',
                         description='Тіркелген дереккөзде нақты архив, қор, тізім және бет нөмірі көрсетілмеген. Жазбаның түпнұсқасы мен нысанның орны анықталғанша мәлімет расталған факт деп белгіленбейді.', evidence='needs_data')
        if place['id'] == 'place-mashyryq':
            place['description'] = 'Жоба материалында бұл орын Машырық қажының қызметімен ауызша деректер деңгейінде байланыстырылады. Жазба құжат пен нақты орын тіркелмеген. Қосымша дерек қажет.'
        if place.get('lat') is None or place.get('lng') is None:
            place['coordinate_note'] = 'Координатасы нақтылануда. Қосымша дерек қажет; маркер қойылмайды.'
        elif place.get('coordinate_status') == 'owner_provided':
            place['coordinate_note'] = 'Бастапқы жобадағы нүкте сақталды. Координатаны жоба иесі берген; тәуелсіз растауға қосымша дерек қажет.'
        elif place['id'] == 'place-modern':
            place['coordinate_note'] = 'Бастапқы жобада ауыл орталығымен бір координатада берілген шолу нүктесі. Бұл жеке ғимараттың координатасы емес.'
        else:
            place['coordinate_note'] = 'Бастапқы жобадағы координата өзгеріссіз сақталды. Негіздемесі: ' + place.get('coordinate_source', 'data/sources.json ішіндегі картографиялық дереккөз.')
    return result


def school_view(static_folder, sources):
    wanted = ['src-marshal-school', 'src-map-school', 'src-mektep-muragat']
    lookup = {s['id']: s for s in sources}
    return dict(
        building=archive_photo(static_folder, 'school-building'),
        display=archive_photo(static_folder, 'school-display'),
        candidate=archive_photo(static_folder, 'old-candidate'),
        sources=[lookup[sid] for sid in wanted if sid in lookup],
    )
