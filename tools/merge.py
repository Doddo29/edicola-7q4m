#!/usr/bin/env python3
"""Edicola - passo 2: unisce i post (work/raw.json) con i testi di Claude (work/enrich.json).
Scrive data.json (il sito), briefing.json (per il briefing delle 5) e aggiorna visti.json.
enrich.json = {"ID": {"title":..., "summary":..., "cat"?:..., "story"?:..., "tags"?:[...],
                      "caption"?: testo (obbligatorio se il post è in inglese: traduzione), "top"?: true, "skip"?: true},
             "_storie": [{"titolo":..., "emoji":..., "peso": 1-3, "post": [ID, ...]}]}"""
import json, os, sys, time, datetime as dt
T = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(T); W = os.path.join(T, 'work')
CFG = json.load(open(os.path.join(T, 'pagine.json'))); PAGES = {p['u']: p for p in CFG['pagine']}
raw = json.load(open(os.path.join(W, 'raw.json')))
en = json.load(open(os.path.join(W, 'enrich.json')))
tz = dt.timezone(dt.timedelta(hours=1))  # ora italiana (solare); va bene anche d'estate per la data
now = dt.datetime.now(tz)
posts, missing = [], []
for p in raw:
    e = en.get(p['id'])
    if not e: missing.append(p['id']); continue
    if e.get('skip'): continue
    tags = list(dict.fromkeys((p.get('tags') or []) + (e.get('tags') or []) + (['Da non perdere'] if e.get('top') else [])))
    cap = e.get('caption') or p['caption']
    posts.append({'id': p['id'], 'page': p['page'], 'pageName': p['pageName'], 'time': p['time'], 'url': p['url'],
                  'media': p['media'], 'cat': e.get('cat') or p['cat'], 'story': e.get('story') or '',
                  'title': e['title'], 'summary': e['summary'], 'caption': cap, 'tags': tags,
                  'lang': e.get('lang') or p['lang'], 'briefing': p['briefing']})
if missing:
    print('ATTENZIONE: post senza testi (esclusi):', len(missing), missing[:10])
order = {c: i for i, c in enumerate(CFG['categorie'])}
cats = sorted({p['cat'] for p in posts}, key=lambda c: order.get(c, 99))
ids = {p['id'] for p in posts}
stories = []
for st in en.get('_storie', []):
    post = [i for i in st.get('post', []) if i in ids]
    if post and st.get('titolo'):
        stories.append({'titolo': st['titolo'], 'emoji': st.get('emoji') or '🗞️', 'peso': max(1, min(3, int(st.get('peso', 1)))), 'post': post})
stories.sort(key=lambda x: -x['peso'])
data = {'edition': now.strftime('%Y-%m-%d'), 'updated': now.isoformat(timespec='minutes'), 'cats': cats, 'stories': stories,
        'posts': [{k: v for k, v in p.items() if k != 'briefing'} for p in posts]}
json.dump(data, open(os.path.join(R, 'data.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
# monitoraggio pagine
stato = json.load(open(os.path.join(T, 'stato.json')))
sil = []
for u, p in PAGES.items():
    st = stato.get(u, {}); ts = st.get('ultimo') or st.get('dal') or time.time()
    days = int((time.time() - ts) / 86400)
    if days >= 30: sil.append({'pagina': p['nome'], 'giorni_senza_post': days, 'mai_visto': not st.get('ultimo')})
brief = {'edition': data['edition'], 'sito': 'https://doddo29.github.io/edicola-7q4m/', 'post': len(posts),
         'pagine': len({p['page'] for p in posts}),
         'per_categoria': {c: sum(p['cat'] == c for p in posts) for c in cats},
         'notizie_dalle_pagine': [{'pagina': p['pageName'], 'cat': p['cat'], 'titolo': p['title'], 'riassunto': p['summary']} for p in posts if p['briefing']],
         'prima_pagina': [{'titolo': x['titolo'], 'peso': x['peso'], 'post': len(x['post'])} for x in stories],
         'da_non_perdere': [{'pagina': p['pageName'], 'titolo': p['title'], 'riassunto': p['summary']} for p in posts if 'Da non perdere' in p['tags']],
         'pagine_silenziose': sil}
json.dump(brief, open(os.path.join(R, 'briefing.json'), 'w'), ensure_ascii=False, indent=1)
vp = os.path.join(T, 'visti.json'); visti = json.load(open(vp)) if os.path.exists(vp) else {}
for p in raw: visti[p['id']] = data['edition']
cut = (now - dt.timedelta(days=7)).strftime('%Y-%m-%d')
visti = {k: v for k, v in visti.items() if v >= cut}
json.dump(visti, open(vp, 'w'), indent=0, sort_keys=True)
print(f"edizione {data['edition']}: {len(posts)} post, {brief['pagine']} pagine, {len(brief['notizie_dalle_pagine'])} per il briefing, {len(sil)} pagine silenziose")
