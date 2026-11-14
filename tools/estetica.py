#!/usr/bin/env python3
"""AutYG - «Aesthetic di oggi»: sceglie le cose belle del giorno dalle pagine estetiche (pagine.json, "estetica": true)
e «la frase di oggi» da Zenxogg (frasi di SpongeBob su video aesthetic).
Uso: python3 tools/estetica.py FILE [FILE...]
FILE = output di Apify (la corsa normale della notte e/o quella d'archivio sulle pagine estetiche).
- Aesthetic: prima i post nuovi (ultime 40 ore, massimo 4), poi post a caso dall'archivio fino a 6:
  pagine diverse, mai mostrati negli ultimi 60 giorni, scelta diversa ogni giorno (seme = data).
- Frase: il post nuovo di Zenxogg se c'è, altrimenti uno a caso del suo archivio, ogni giorno diverso
  (si ripete solo dopo averli mostrati tutti). Scrive anche tools/work/frase_candidati.md: Claude controlla
  che il post scelto sia davvero una frase e, se non lo è, ne sceglie un altro scrivendo tools/work/frase.json.
Scrive tools/work/estetica.json (letto da merge.py) e aggiorna tools/storico_estetica.json e tools/storico_frase.json."""
import json, os, sys, time, random, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prepare import load, g, media, clean, T, W

N, MAX_NUOVI, MAX_ORE, GIORNI = 6, 4, 40, 60
FRASE = 'zenxogg'
CFG = json.load(open(os.path.join(T, 'pagine.json')))
EST = {p['u']: p for p in CFG['pagine'] if p.get('estetica')}

def jload(p, d):
    try: return json.load(open(p))
    except Exception: return d

def main(files):
    items = []
    for f in files:
        try: items += load(f)
        except Exception as e: print('salto', f, e)
    tz = dt.timezone(dt.timedelta(hours=1)); oggi = dt.datetime.now(tz).strftime('%Y-%m-%d')
    sp, fp = os.path.join(T, 'storico_estetica.json'), os.path.join(T, 'storico_frase.json')
    storico, sfrase = jload(sp, {}), jload(fp, {})
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
                     'media': m[:10], 'nuovo': bool(ts) and now - ts < MAX_ORE * 3600 and not x.get('is_pinned'),
                     'didascalia': clean(g(x, 'caption.text') or '')[:600]})
    rng = random.Random(oggi)
    # la frase di oggi (Zenxogg)
    zx = [p for p in pool if p['page'] == FRASE]
    frase = next((p for p in zx if sfrase.get(p['id']) == oggi), None)
    if not frase and zx:
        nuovi = sorted([p for p in zx if p['nuovo'] and p['id'] not in sfrase], key=lambda p: p['time'], reverse=True)
        mai = [p for p in zx if p['id'] not in sfrase]; rng.shuffle(mai)
        vecchi = sorted(zx, key=lambda p: sfrase.get(p['id'], ''))
        cand = nuovi + [p for p in mai if p not in nuovi] + [p for p in vecchi if p not in mai and p not in nuovi]
        frase = cand[0]
        with open(os.path.join(W, 'frase_candidati.md'), 'w') as f:
            f.write('# Candidati per «la frase di oggi» (Zenxogg), in ordine di preferenza\n'
                    'Scelto in automatico il primo. Se non è una frase, scrivi tools/work/frase.json = {"id": "...", "testo": "la frase"}.\n\n')
            for p in cand[:12]:
                f.write(f"## {p['id']}{' | NUOVO' if p['nuovo'] else ''} | {p['url']}\n{p['didascalia'] or '(nessuna didascalia)'}\n\n")
        json.dump(cand[:12], open(os.path.join(W, 'frase_candidati.json'), 'w'), ensure_ascii=False)
    if frase: sfrase[frase['id']] = oggi
    # l'Aesthetic di oggi
    resto = [p for p in pool if p['page'] != FRASE]          # Zenxogg serve solo alla frase
    fissi = [p for p in resto if storico.get(p['id']) == oggi]
    if fissi: scelta = fissi
    else:
        nuovi = sorted([p for p in resto if p['nuovo'] and p['id'] not in storico], key=lambda p: p['time'], reverse=True)[:MAX_NUOVI]
        arch = [p for p in resto if not p['nuovo'] and p['id'] not in storico]
        rng.shuffle(arch)
        scelta, pagine = list(nuovi), {p['page'] for p in nuovi}
        for p in arch:                      # prima una per pagina, poi il resto
            if len(scelta) >= N: break
            if p['page'] not in pagine: scelta.append(p); pagine.add(p['page'])
        for p in arch:
            if len(scelta) >= N: break
            if p not in scelta: scelta.append(p)
        for p in scelta: storico[p['id']] = oggi
    out = lambda p: {k: v for k, v in p.items() if k != 'didascalia'}
    json.dump({'items': [out(p) for p in scelta], 'frase': out(frase) if frase else None},
              open(os.path.join(W, 'estetica.json'), 'w'), ensure_ascii=False)
    json.dump(storico, open(sp, 'w'), indent=0, sort_keys=True)
    json.dump(sfrase, open(fp, 'w'), indent=0, sort_keys=True)
    print(f"aesthetic di oggi: {len(scelta)} ({sum(p['nuovo'] for p in scelta)} nuovi) da un archivio di {len(pool)} post; "
          f"frase: {frase['id'] if frase else 'nessuna (Zenxogg non trovato)'} su {len(zx)} post di Zenxogg")

if __name__ == '__main__':
    main(sys.argv[1:])
