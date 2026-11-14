#!/usr/bin/env python3
"""AutYG - «Aesthetic di oggi»: sceglie le cose belle del giorno dalle pagine estetiche (pagine.json, "estetica": true).
Uso: python3 tools/estetica.py FILE [FILE...]
FILE = output di Apify (la corsa normale della notte e/o quella d'archivio sulle pagine estetiche).
Prima i post nuovi (ultime 40 ore), poi riempie fino a 6 con post a caso dall'archivio:
pagine diverse, mai mostrati negli ultimi 60 giorni, scelta diversa ogni giorno (seme = data).
Scrive tools/work/estetica.json (letto da merge.py) e aggiorna tools/storico_estetica.json."""
import json, os, sys, time, random, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prepare import load, g, media, T, W

N, MAX_NUOVI, MAX_ORE, GIORNI = 6, 4, 40, 60
CFG = json.load(open(os.path.join(T, 'pagine.json')))
EST = {p['u']: p for p in CFG['pagine'] if p.get('estetica')}

def main(files):
    items = []
    for f in files:
        try: items += load(f)
        except Exception as e: print('salto', f, e)
    tz = dt.timezone(dt.timedelta(hours=1)); oggi = dt.datetime.now(tz).strftime('%Y-%m-%d')
    sp = os.path.join(T, 'storico_estetica.json')
    storico = json.load(open(sp)) if os.path.exists(sp) else {}
    cut = (dt.datetime.now(tz) - dt.timedelta(days=GIORNI)).strftime('%Y-%m-%d')
    storico = {k: v for k, v in storico.items() if v >= cut}
    now, seen, pool = time.time(), set(), []
    for x in items:
        c = x.get('code'); u = (g(x, 'user.username') or x.get('scraped_username') or '').lower()
        if not c or c in seen or u not in EST: continue
        seen.add(c)
        m = [y for y in media(x) if y.get('src')]
        if not m: continue
        ts = g(x, 'taken_at') or 0
        pool.append({'id': c, 'page': u, 'pageName': EST[u]['nome'], 'url': x.get('post_url') or f'https://www.instagram.com/p/{c}/',
                     'time': dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat().replace('+00:00', 'Z') if ts else '',
                     'media': m[:10], 'nuovo': bool(ts) and now - ts < MAX_ORE * 3600 and not x.get('is_pinned')})
    # già scelti oggi (la corsa si può ripetere): stessa scelta
    fissi = [p for p in pool if storico.get(p['id']) == oggi]
    if fissi: scelta = fissi
    else:
        nuovi = sorted([p for p in pool if p['nuovo'] and p['id'] not in storico], key=lambda p: p['time'], reverse=True)[:MAX_NUOVI]
        rng = random.Random(oggi)
        arch = [p for p in pool if not p['nuovo'] and p['id'] not in storico]
        rng.shuffle(arch)
        scelta, pagine = list(nuovi), {p['page'] for p in nuovi}
        for p in arch:                      # prima una per pagina, poi il resto
            if len(scelta) >= N: break
            if p['page'] not in pagine: scelta.append(p); pagine.add(p['page'])
        for p in arch:
            if len(scelta) >= N: break
            if p not in scelta: scelta.append(p)
        for p in scelta: storico[p['id']] = oggi
    json.dump(scelta, open(os.path.join(W, 'estetica.json'), 'w'), ensure_ascii=False)
    json.dump(storico, open(sp, 'w'), indent=0, sort_keys=True)
    print(f"aesthetic di oggi: {len(scelta)} ({sum(p['nuovo'] for p in scelta)} nuovi) da un archivio di {len(pool)} post")

if __name__ == '__main__':
    main(sys.argv[1:])
