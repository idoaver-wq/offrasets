import csv, json, os, re
# Source of truth lives in src/ of repo idoaver-wq/offrasets; the built site is the repo root.
# Usage: python3 src/build.py  ->  rewrites index.html, then commit + push (GitHub Pages serves https://offrasets.com)
SRC = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC)
os.chdir(SRC)

def rd(f):
    with open(f, encoding='utf-8-sig') as h:
        return list(csv.DictReader(h))

events = rd('events.csv')
tracks = rd('tracks.csv')
songs = {s['canonical_song_id']: s for s in rd('canonical_songs.csv')}
archive = rd('archive.csv')

# EVT_xx -> readable id, in file order
readable = []
for a in archive:
    if a['event_id'] not in readable:
        readable.append(a['event_id'])
evmap = {e['event_id']: readable[i] for i, e in enumerate(events)}

KIND = [('Rosh Hashanah', 'ראש השנה'), ('Hanukkah', 'חנוכה'), ('Purim', 'פורים'),
        ('Sukkot', 'סוכות'), ('NYC Pride', 'גאווה ניו יורק'), ('Pride Tel Aviv', 'גאווה תל אביב'),
        ('White Party Bangkok', 'White Party בנגקוק')]
# events not recorded by @idoaver (credit as printed on the image)
CREDIT = {'hanukkah_2025': '@eladdon',
          'sukkot_2026': {'he': 'רשימת טראקים @offra_before_offra · סטוריז @tal_huga',
                          'en': 'Tracklist @offra_before_offra · Stories @tal_huga'}}
CITY = {'Tel Aviv': 'תל אביב', 'Bangkok': 'בנגקוק', 'New York': 'ניו יורק'}

def kind(ed):
    for en, he in KIND:
        if ed.startswith(en):
            return en, he
    return ed, ed

EV = []
for e in events:
    rid = evmap[e['event_id']]
    en, he = kind(e['event_edition'])
    img = f'images/{rid}.jpg'  # images live in the repo root images/ folder
    EV.append({
        'id': rid, 'kind': en, 'he': he, 'edition': e['event_edition'],
        'name': e['event_name'], 'date': e['event_date'], 'venue': e['venue'],
        'city': CITY.get(e['city'], e['city']), 'city_en': e['city'], 'country': e['country'],
        'start': e['set_start_time'], 'end': e['set_end_time'], 'dur': e['set_duration'],
        'img': img if os.path.exists(os.path.join(ROOT, img)) else None,
        'credit': CREDIT.get(rid),
        't': []
    })
EVI = {e['id']: e for e in EV}

# approved live recordings (live_links.csv, approved == yes)
if os.path.exists('live_links.csv'):
    with open('live_links.csv', encoding='utf-8-sig') as h:
        for r in csv.DictReader(h):
            if r['approved'].strip().lower() == 'yes' and r['event_id'] in EVI:
                EVI[r['event_id']].setdefault('live', []).append({'part': r['part'], 'url': r['url'], 'platform': r['platform']})

for t in tracks:
    ev = EVI[evmap[t['event_id']]]
    ev['t'].append([int(t['sequence_number']), t['canonical_song_id'], t['normalized_artist'],
                    t['normalized_title'], t['version_or_remix']])
for e in EV:
    e['t'].sort(key=lambda r: r[0])

SO = {sid: [s['display_artist'], s['display_title']] for sid, s in songs.items()}
# approved listening links per song (track_links.csv, approved == yes)
LINKS = {}
SHOW_TRACK_LINKS = False  # paused by archive owner 27.09.2026; approvals kept in track_links.csv
if SHOW_TRACK_LINKS and os.path.exists('track_links.csv'):
    with open('track_links.csv', encoding='utf-8-sig') as h:
        for r in csv.DictReader(h):
            if r['approved'].strip().lower() == 'yes':
                LINKS[r['canonical_song_id']] = ['yt' if r['platform'] == 'YouTube' else 'sc', r['url']]
from datetime import datetime
from zoneinfo import ZoneInfo
UPDATED = datetime.now(ZoneInfo('Asia/Jerusalem')).strftime('%d.%m.%Y')  # build date, Israel time
data = {'events': EV, 'songs': SO, 'links': LINKS, 'updated': UPDATED}

tpl = open('template.html', encoding='utf-8').read()
out = tpl.replace('/*DATA*/null', json.dumps(data, ensure_ascii=False, separators=(',', ':')))
head = ('<!doctype html>\n<html lang="he">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0;font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>\n')
t = out.split('</style>', 1)
page = head + t[0] + '</style>\n</head>\n<body>\n' + t[1] + '\n</body>\n</html>\n'
open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(page)
open(os.path.join(ROOT, 'CNAME'), 'w').write('offrasets.com\n')
open(os.path.join(ROOT, '.nojekyll'), 'w').write('')
print('events', len(EV), 'tracks', sum(len(e['t']) for e in EV), 'songs', len(SO),
      'images', sum(1 for e in EV if e['img']))
