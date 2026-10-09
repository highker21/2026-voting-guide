#!/usr/bin/env python3
"""高雄市門牌 → 村里 索引建置。
資料：高雄市115年門牌坐標資料-TWD97（data.kcg.gov.tw）＋內政部村里界圖(NLSC)
流程：CSV(TWD97 TM2) → WGS84 → 點在多邊形內(even-odd ray casting, numpy 向量化) → 里 → 三層索引 JSON
前置：raw/kh_doorplate/doorplate_115_10.csv、code_map.csv、kh_village.json
  kh_village.json 產法：cd raw/village_boundary && npx -y mapshaper@0.6 VILLAGE_NLSC_1150817.shp \
      -filter 'COUNTYNAME=="高雄市"' -o ../kh_doorplate/kh_village.json format=geojson
輸出：addr_index/kaohsiung/<區>.json ＋ raw/kh_doorplate/build_stats.json
"""
import csv, json, re, sys, unicodedata, collections, math
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw' / 'kh_doorplate'
OUT = ROOT / 'addr_index' / 'kaohsiung'
LI = ROOT.parent / 'data' / 'kaohsiung'
URL = 'https://data.kcg.gov.tw/DataSet/Detail/1d7e3a54-6884-4cb0-b07c-c7c9cd411414'
DATE = '2026-10-09'

# ---------- TWD97 TM2 -> WGS84（與 nhi-facility-finder/scripts/twd97.py 同公式，numpy 版）----------
def twd97_to_lonlat(E, N):
    a = 6378137.0; f = 1/298.257222101; e2 = f*(2-f)
    lon0 = math.radians(121.0); k0 = 0.9999
    E = E-250000.0
    M = N/k0
    mu = M/(a*(1-e2/4-3*e2**2/64-5*e2**3/256))
    e1 = (1-math.sqrt(1-e2))/(1+math.sqrt(1-e2))
    fp = (mu+(3*e1/2-27*e1**3/32)*np.sin(2*mu)+(21*e1**2/16-55*e1**4/32)*np.sin(4*mu)
          +(151*e1**3/96)*np.sin(6*mu)+(1097*e1**4/512)*np.sin(8*mu))
    e2p = e2/(1-e2)
    C1 = e2p*np.cos(fp)**2; T1 = np.tan(fp)**2
    R1 = a*(1-e2)/(1-e2*np.sin(fp)**2)**1.5
    N1 = a/np.sqrt(1-e2*np.sin(fp)**2)
    D = E/(N1*k0)
    lat = fp-(N1*np.tan(fp)/R1)*(D**2/2-(5+3*T1+10*C1-4*C1**2-9*e2p)*D**4/24
          +(61+90*T1+298*C1+45*T1**2-3*C1**2-252*e2p)*D**6/720)
    lon = lon0+(D-(1+2*T1+C1)*D**3/6+(5-2*C1+28*T1-3*C1**2+8*e2p+24*T1**2)*D**5/120)/np.cos(fp)
    return np.degrees(lon), np.degrees(lat)

# ---------- 文字正規化 ----------
def norm(s):
    s = unicodedata.normalize('NFKC', s).strip()
    return s.replace('台', '臺')

NUMRE = re.compile(r'^(?P<head>[^號]*)號(?P<tail>.*)$')
def parse_hao(raw):
    """回傳 (extra_lane, 號) 或 None。去樓層；'N號之M樓..' 的 之M 併入號；巷弄混在號欄位時拆出。"""
    s = norm(raw)
    m = NUMRE.match(s)
    if not m: return None
    head, tail = m.group('head'), m.group('tail')
    t = re.match(r'之(\d+)', tail)
    if t: head += '之' + t.group(1)
    extra = ''
    mm = re.match(r'^(.*(?:巷|弄))(.+)$', head)
    if mm: extra, head = mm.group(1), mm.group(2)
    if not head: return None
    return extra, head

# ---------- 多邊形 ----------
def load_polys():
    gj = json.load(open(RAW/'kh_village.json', encoding='utf-8'))
    polys = []  # dict(town, vill, rings(list of ndarray Nx2), bbox)
    for f in gj['features']:
        g = f['geometry']; p = f['properties']
        parts = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        for part in parts:
            rings = [np.asarray(r, dtype=float) for r in part]
            o = rings[0]
            polys.append(dict(town=p['TOWNNAME'], vill=p['VILLNAME'], rings=rings,
                              bbox=(o[:, 0].min(), o[:, 1].min(), o[:, 0].max(), o[:, 1].max())))
    return polys

def inside(px, py, rings):
    """even-odd：外環＋洞一起數交點奇偶。"""
    cnt = np.zeros(len(px), dtype=np.int32)
    for r in rings:
        x1, y1 = r[:-1, 0], r[:-1, 1]; x2, y2 = r[1:, 0], r[1:, 1]
        for i in range(0, len(x1), 256):
            a, b, c, d = x1[i:i+256], y1[i:i+256], x2[i:i+256], y2[i:i+256]
            with np.errstate(divide='ignore', invalid='ignore'):
                cond = (b[None, :] > py[:, None]) != (d[None, :] > py[:, None])
                xi = a[None, :]+(py[:, None]-b[None, :])*(c-a)[None, :]/(d-b)[None, :]
                cnt += (cond & (px[:, None] < xi)).sum(axis=1)
    return (cnt & 1) == 1

def nearest_poly(px, py, plist):
    """回傳每點最近多邊形索引（plist 內），距離以邊線段最短距離（經度依緯度縮放）。"""
    best = np.full(len(px), np.inf); bi = np.zeros(len(px), dtype=int)
    kx = math.cos(math.radians(22.7))
    for k, P in enumerate(plist):
        for r in P['rings']:
            x1, y1 = r[:-1, 0]*kx, r[:-1, 1]; x2, y2 = r[1:, 0]*kx, r[1:, 1]
            dx, dy = x2-x1, y2-y1; L = dx*dx+dy*dy; L[L == 0] = 1e-18
            X = px[:, None]*kx; Y = py[:, None]
            t = np.clip(((X-x1)*dx+(Y-y1)*dy)/L, 0, 1)
            d = np.hypot(X-(x1+t*dx), Y-(y1+t*dy)).min(axis=1)
            m = d < best; best[m] = d[m]; bi[m] = k
    return bi, best

# ---------- 主程式 ----------
def main():
    code2d = {r['鄉鎮市區代碼']: r['鄉鎮市區名稱'] for r in csv.DictReader(open(RAW/'code_map.csv', encoding='utf-8-sig'))}
    polys = load_polys()
    by_town = collections.defaultdict(list)
    for P in polys: by_town[P['town']].append(P)

    # 讀 CSV，依區分組
    rows = collections.defaultdict(list)  # town -> [(street, lane, hao, E, N, csvvill)]
    skipped = collections.Counter()
    with open(RAW/'doorplate_115_10.csv', encoding='utf-8-sig') as fh:
        rd = csv.reader(fh); next(rd)
        for r in rd:
            town = code2d.get(r[1])
            if not town: skipped['unknown_district'] += 1; continue
            street = norm(r[4] or r[5])
            if not street: skipped['no_street'] += 1; continue
            ph = parse_hao(r[8])
            if not ph: skipped['bad_hao'] += 1; continue
            extra, hao = ph
            lane = norm(r[6])+norm(r[7])+extra
            try: E = float(r[9]); N = float(r[10])
            except ValueError: skipped['bad_xy'] += 1; continue
            rows[town].append((street, lane, hao, E, N, r[2]))
    print('skipped', dict(skipped), file=sys.stderr)

    OUT.mkdir(parents=True, exist_ok=True)
    stats = dict(towns={}, skipped=dict(skipped))
    for town in code2d.values():
        lst = rows.get(town, [])
        E = np.array([x[3] for x in lst]); N = np.array([x[4] for x in lst])
        lon, lat = twd97_to_lonlat(E, N)
        # 座標去重
        key = np.round(lon, 7)*1e3+np.round(lat, 7)  # 僅作分組粗鍵，下面用 unique rows
        uq, inv = np.unique(np.stack([np.round(lon, 7), np.round(lat, 7)], 1), axis=0, return_inverse=True)
        inv = inv.reshape(-1)
        ux, uy = uq[:, 0], uq[:, 1]
        vill = np.full(len(uq), None, dtype=object)
        done = np.zeros(len(uq), dtype=bool)
        for P in by_town[town]:
            x0, y0, x1, y1 = P['bbox']
            cand = np.where(~done & (ux >= x0) & (ux <= x1) & (uy >= y0) & (uy <= y1))[0]
            if len(cand) == 0: continue
            hit = cand[inside(ux[cand], uy[cand], P['rings'])]
            vill[hit] = P['vill']; done[hit] = True
        miss = np.where(~done)[0]
        cross = out_ = 0
        if len(miss):
            # 是否落在他區多邊形內（跨區邊界）
            incross = np.zeros(len(miss), dtype=bool)
            for t, pl in by_town.items():
                if t == town: continue
                for P in pl:
                    x0, y0, x1, y1 = P['bbox']
                    c = np.where(~incross & (ux[miss] >= x0) & (ux[miss] <= x1) & (uy[miss] >= y0) & (uy[miss] <= y1))[0]
                    if len(c): incross[c[inside(ux[miss][c], uy[miss][c], P['rings'])]] = True
            bi, dist = nearest_poly(ux[miss], uy[miss], by_town[town])
            for j, m in enumerate(miss): vill[m] = by_town[town][bi[j]]['vill']
        # 以「筆」計外部數
        miss_set = np.zeros(len(uq), dtype=bool); miss_set[miss] = True
        cross_set = np.zeros(len(uq), dtype=bool)
        if len(miss): cross_set[miss[incross]] = True
        n_out = int(miss_set[inv].sum()); n_cross = int(cross_set[inv].sum())

        # 與 CSV 自帶村里欄位比對（附帶檢查）
        agree = sum(1 for i, x in enumerate(lst) if vill[inv[i]] == x[5])

        # 建三層樹，去重（樓層已去掉）
        tree = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(set)))
        for i, (s, l, h, *_r) in enumerate(lst):
            tree[s][l][h].add(vill[inv[i]])
        addr_n = sum(len(nn) for ll in tree.values() for nn in ll.values())

        def leafval(vs):
            return sorted(vs)[0] if len(vs) == 1 else sorted(vs)
        out = {}
        n_street = n_str_collapsed = 0
        for s in sorted(tree):
            n_street += 1
            allv = set()
            for l in tree[s].values():
                for vs in l.values(): allv |= vs
            if len(allv) == 1:
                out[s] = next(iter(allv)); n_str_collapsed += 1; continue
            lanes = {}
            for l in sorted(tree[s]):
                nums = tree[s][l]
                lv = set().union(*nums.values())
                if len(lv) == 1: lanes[l] = next(iter(lv))
                else: lanes[l] = {h: leafval(nums[h]) for h in sorted(nums)}
            out[s] = lanes
        doc = {'_meta': {'src': '高雄市115年門牌坐標資料-TWD97＋內政部村里界圖', 'url': URL, 'date': DATE, 'count': addr_n}}
        doc.update(out)
        fp = OUT / f'{town}.json'
        fp.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

        # 里名對齊 li-<區>.json
        li_names = set()
        lf = LI / f'li-{town}.json'
        if lf.exists():
            li_names = {r['village'] for r in json.load(open(lf, encoding='utf-8'))['races']}
        used = {v for v in vill if v}
        stats['towns'][town] = dict(csv_rows=len(lst), addr=addr_n, outside=n_out, cross_district=n_cross,
                                    csv_vill_agree=agree, bytes=fp.stat().st_size,
                                    streets=n_street, streets_str=n_str_collapsed,
                                    li_not_in_index=sorted(li_names-used), index_not_in_li=sorted(used-li_names))
        print(town, stats['towns'][town]['addr'], 'out', n_out, 'cross', n_cross, file=sys.stderr)
    json.dump(stats, open(RAW/'build_stats.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
