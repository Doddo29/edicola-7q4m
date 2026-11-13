#!/usr/bin/env python3
"""Edicola - passo 1: legge i post grezzi di Apify e prepara il lavoro per Claude.
Uso: python3 tools/prepare.py FILE [FILE...]
FILE = output salvato di get-dataset-items (anche più pagine) oppure un array JSON di post.
Scrive tools/work/raw.json (post selezionati e normalizzati) e tools/work/todo.md (da leggere)."""
import json, re, sys, os, time, datetime as dt
T = os.path.dirname(os.path.abspath(__file__)); W = os.path.join(T, 'work'); os.makedirs(W, exist_ok=True)
CFG = json.load(open(os.path.join(T, 'pagine.json')))
PAGES = {p['u']: p for p in CFG['pagine']}
CAP_ALTO, CAP = 4, 5            # post massimi per pagina in un'edizione
MAX_ORE = 40                    # oltre questo i post non entrano

def load(path):
    txt = open(path, encoding='utf-8').read().strip()
    out = []
    try:
        obj = json.loads(txt)
    except Exception:
        obj = None
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and 'type' in obj[0] and 'text' in obj[0]:
        for blk in obj:
            out += load_text(blk['text'])
        return out
    if isinstance(obj, list): return obj
    if isinstance(obj, dict) and 'items' in obj: return obj['items']
    return load_text(txt)

def load_text(t):
    i = t.find('{'); j = t.find('[')
    starts = [x for x in (i, j) if x >= 0]
    if not starts: return []
    o, _ = json.JSONDecoder().raw_decode(t[min(starts):])
    if isinstance(o, dict): return o.get('items', [])
    return o

def g(x, path, d=None):
    for k in path.split('.'):
        if isinstance(x, dict) and k in x: x = x[k]
        elif isinstance(x, dict) and path in x: return x[path]
        else: return d
    return x

SPAM = re.compile(r'(segui(ci)? (anche )?@|follow @|link in (bio|descrizione)|seguici|iscriviti|salva (questo|il) post|condividi (questo|il) post|tagga (un|qualcuno)|commenta qui sotto|attiva le notifiche|👉 ?@|📲|➡️ ?@)', re.I)
SPONS = re.compile(r'(#adv\b|#ad\b|#sponsorizzato|#sponsored|in collaborazione con|paid partnership|partnership retribuita|#advertising|#gifted|codice sconto|link in bio per (acquistare|comprare))', re.I)
EN = set('the and of to is in that for with this you are on was it be as at by from have has will his her they their what new one first'.split())
IT = set('il la di che e è per non un una con del della sono le gli lo ha ai al nel nella più come anche dei delle questo questa'.split())

def clean(c):
    lines = []
    for l in c.replace('\r', '').split('\n'):
        s = l.strip()
        if not s: lines.append(''); continue
        words = s.split()
        if words and all(w.startswith('#') or w.startswith('@') for w in words): continue
        if SPAM.search(s) and len(s) < 160: continue
        s = re.sub(r'(\s#[\wÀ-ÿ]+)+\s*$', '', s)
        lines.append(s)
    out = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()
    out = re.sub(r'@([\w.]+)', lambda m: m.group(1).replace('_', ' ').replace('.', ' ').strip(), out)
    return out

def lang(c):
    w = re.findall(r"[a-zàèéìòù']+", c.lower())
    en = sum(x in EN for x in w); it = sum(x in IT for x in w)
    return 'en' if en > it * 1.5 and en >= 3 else 'it'

def media(x):
    mt = g(x, 'media_type')
    if mt == 8 and x.get('carousel_media'):
        return [({'t': 'v', 'src': c['video_url'], 'poster': c.get('image_url')} if c.get('video_url') else {'t': 'i', 'src': c.get('image_url')}) for c in x['carousel_media'] if c.get('image_url') or c.get('video_url')]
    if x.get('video_url'): return [{'t': 'v', 'src': x['video_url'], 'poster': x.get('image_url')}]
    return [{'t': 'i', 'src': x.get('image_url')}]

def main(files):
    items = []
    for f in files: items += load(f)
    now = time.time()
    # stato delle pagine (ultimo post visto) per il monitoraggio
    sp = os.path.join(T, 'stato.json')
    stato = json.load(open(sp)) if os.path.exists(sp) else {}
    vp = os.path.join(T, 'visti.json')
    visti = json.load(open(vp)) if os.path.exists(vp) else {}
    by = {}
    done = set()
    for x in items:
        if x.get('code') in done: continue
        done.add(x.get('code'))
        u = (g(x, 'user.username') or x.get('scraped_username') or '').lower()
        if u not in PAGES or not x.get('code'): continue
        ts = g(x, 'taken_at') or 0
        if ts > stato.get(u, {}).get('ultimo', 0):
            stato.setdefault(u, {})['ultimo'] = ts
        if x.get('is_pinned') or x['code'] in visti or now - ts > MAX_ORE * 3600: continue
        cap = g(x, 'caption.text') or ''
        p = PAGES[u]
        by.setdefault(u, []).append({
            'id': x['code'], 'page': u, 'pageName': p['nome'], 'cat': p['cat'], 'briefing': p['briefing'],
            'time': dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat().replace('+00:00', 'Z'),
            'url': x.get('post_url') or f"https://www.instagram.com/p/{x['code']}/",
            'media': media(x), 'likes': x.get('like_count') or 0,
            'caption_raw': cap, 'caption': clean(cap), 'lang': lang(cap),
            'tags': ['Sponsorizzato'] if SPONS.search(cap) else []})
    posts = []
    for u, l in by.items():
        if PAGES[u]['alto']: l = sorted(l, key=lambda p: -p['likes'])[:CAP_ALTO]
        else: l = sorted(l, key=lambda p: p['time'], reverse=True)[:CAP]
        posts += l
    posts.sort(key=lambda p: p['time'], reverse=True)
    for u in PAGES: stato.setdefault(u, {}).setdefault('dal', int(now))
    json.dump(stato, open(sp, 'w'), indent=1, sort_keys=True)
    json.dump(posts, open(os.path.join(W, 'raw.json'), 'w'), ensure_ascii=False)
    with open(os.path.join(W, 'todo.md'), 'w') as f:
        f.write(f"# {len(posts)} post da arricchire\n\n")
        for p in posts:
            c = p['caption'] if p['lang'] == 'en' else p['caption'][:900]
            kind = 'carosello %d' % len(p['media']) if len(p['media']) > 1 else ('video' if p['media'][0]['t'] == 'v' else 'foto')
            f.write(f"## {p['id']} | {p['pageName']} | {p['cat']} | {kind} | lingua {p['lang']}{' | ' + ','.join(p['tags']) if p['tags'] else ''}\n{c or '(nessuna didascalia)'}\n\n")
    print(f"post grezzi: {len(items)} | selezionati: {len(posts)} | pagine con post: {len(by)}")

if __name__ == '__main__':
    main(sys.argv[1:])
