#!/usr/bin/env python3
"""tools/centers/*.json（市町ごとの元データ）から、山口市以外の「地域交流センター」の geojson を作る。
位置は国土地理院の住所検索（住所からの推定・現地未確認）。範囲チェックと一致状況を表示する。"""
import json, glob, time, urllib.parse, urllib.request, os, sys
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
cache_p = os.path.join(here, 'geocode_cache.json')
cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
def geocode(addr):
    if addr in cache: return cache[addr]
    u = 'https://msearch.gsi.go.jp/address-search/AddressSearch?q=' + urllib.parse.quote(addr)
    r = json.load(urllib.request.urlopen(u, timeout=30))
    cache[addr] = [(x['properties']['title'], x['geometry']['coordinates']) for x in r][:3]
    time.sleep(0.3); return cache[addr]
# 使い方: build_centers.py [centers|kominkan|jichikai|cafes]（既定は centers）
LAYER = sys.argv[1] if len(sys.argv) > 1 else 'centers'
CONF = {'centers': ('centers_pref.geojson', '地域交流センター（山口市以外）'),
        'kominkan': ('kominkan_pref.geojson', '公民館（山口市以外）'),
        'jichikai': ('jichikai_pref.geojson', '自治会館・集会所（山口市以外）'),
        'cafes': ('ninchisho_cafe_pref.geojson', '認知症カフェ（山口市以外）')}
OUT, KUBUN = CONF[LAYER]
feats, bad = [], []
for f in sorted(glob.glob(os.path.join(here, LAYER, '*.json'))):
    d = json.load(open(f, encoding='utf-8'))
    for r in d['items']:
        if 'lonlat' in r:   # 人が確認した座標があるときは、それを使う
            lon, lat = r['lonlat']; title = r['lonlat_source']
        else:
            g = geocode(r.get('geocode_query', r['address']))
            if not g: bad.append((r['name'], '見つからない')); continue
            title, (lon, lat) = g[0]
        if not (130.7 <= lon <= 132.5 and 33.6 <= lat <= 34.8):
            bad.append((r['name'], f'範囲外 {lon},{lat}')); continue   # 山口県の範囲（経度緯度の取り違えも検出）
        p = {'name': r['name'], '地方公共団体名': '山口県' + d['municipality'], '所在地_連結表記': r['address'],
             '電話番号': r.get('phone') or None, 'データ区分': KUBUN,
             '出典': d['source'], 'URL': r.get('props', {}).get('出典ページ') or d['source_url'], '情報更新日': r.get('updated', d['updated']),
             '位置の根拠': ('ユーザー提供の座標（Googleマップ）' if 'lonlat' in r else '国土地理院 住所検索（住所からの推定・現地未確認）'), '位置の一致': title,
             '位置の精度': ('ユーザー提供の座標で確定' if 'lonlat' in r else '番地まで一致') if ('lonlat' in r or any(c in title for c in '0123456789０１２３４５６７８９')) else '町字までしか一致せず（実際の位置とずれが大きい可能性）'}
        for k, v in r.get('props', {}).items():
            if k != '出典ページ': p[k] = v
        if r.get('note'): p['備考'] = r['note']
        feats.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [lon, lat]}, 'properties': p})
        print(d['municipality'], '|', r['name'], '|', r['address'], '->', title)
json.dump(cache, open(cache_p, 'w'), ensure_ascii=False)
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(root, OUT), 'w'), ensure_ascii=False, indent=1)
print('total', len(feats), 'bad', bad)
