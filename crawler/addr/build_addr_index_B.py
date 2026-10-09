#!/usr/bin/env python3
"""門牌 → 村里 索引（2026 投票指南）

輸入：各縣市「門牌位置數值資料」CSV（政府資料開放授權條款第1版）
輸出：data/addr/<code>/<鄉鎮市區>.json

格式（A 訂，前端只認這一種）：
{ "_meta": {"src":資料集名稱, "url":..., "date":"YYYY-MM-DD", "count":門牌筆數},
  "<路街段>": "<里>" | { "<巷弄>": "<里>" | { "<號>": "<里>" | ["甲里","乙里"] } } }
- 路街段：官方原文（段用中文數字）；沒有路街段而只有「地區」的門牌，以地區名當路街段
- 巷弄：沒有巷弄用 ""；例「12巷」「12巷3弄」「正隆巷46弄」，半形數字
- 號：「391」「391之1」，半形，不含「號」與樓層
- 全形→半形（NFKC）、「台」→「臺」在產檔時處理
- 同一號對到多個里 → 陣列
- 門牌資料的里名不在網站現行村里清單（多為已合併、改名）→ 該門牌不收錄，前端查不到就讓使用者自己選
"""
import csv, json, os, re, sys, unicodedata, urllib.request, urllib.parse, collections

SITE = "https://highker21.github.io/2026-voting-guide/data/"
COUNTIES = {
    "new-taipei": ("full_ntpc.csv",
                   dict(area="areacode", village="village", road="street、road、section", region="area", lane="lane", alley="alley", no="number"),
                   {"src": "新北市門牌位置數值資料（新北市政府，政府資料開放授權條款第1版）", "url": "https://data.gov.tw/dataset/168887"}),
    "taipei": ("full_taipei.csv",
               dict(area="鄉鎮市區代碼", village="村里", road="街路段", region="地區", lane="巷", alley="弄", no="號"),
               {"src": "臺北市門牌位置數值資料（臺北市政府，政府資料開放授權條款第1版）", "url": "https://data.gov.tw/dataset/155472"}),
    "tainan": ("full_tainan.csv",
               dict(area="地址-行政區域代碼", village="村里", road="街路段", region="地區", lane="巷", alley="弄", no="號"),
               {"src": "臺南市門牌坐標資料（臺南市政府，官方標示僅供參考；政府資料開放授權條款第1版）", "url": "https://data.gov.tw/dataset/120044"}),
    "taichung": ("full_taichung_raw.csv",
                 dict(area="鄉鎮市區代碼", village="村里", road="街、路段", region="地區", lane="巷", alley="弄", no="號"),
                 {"src": "臺中市GIS門牌號碼（臺中市政府，115年1月版；政府資料開放授權條款第1版）", "url": "https://data.gov.tw/dataset/169806"}),
    "taitung": ("full_taitung.csv",
                dict(area="鄉鎮市區代碼", village="村里", road="街、路段", region="地區", lane="巷", alley="弄", no="號樓"),
                {"src": "臺東縣門牌坐標資料（臺東縣政府，政府資料開放授權條款第1版）", "url": "https://data.gov.tw/dataset/165619", "encoding": "cp950"}),
}
# 其餘縣市：原始檔先經 convert_std.py 轉成統一欄位的 UTF-8 CSV（std_<code>.csv）
STD_F = dict(area="鄉鎮市區代碼", village="村里", road="街路段", region="地區", lane="巷", alley="弄", no="號")
for _code, _name, _id, _note in [
    ("taoyuan", "桃園市門牌位置坐標資料（115年8月）", 157689, ""),
    ("hsinchu-city", "新竹市門牌坐標資料", 157547, "，官方標示僅供參考"),
    ("hsinchu-county", "新竹縣門牌位置", 172380, ""),
    ("miaoli", "苗栗縣門牌點位維護系統門牌座標資料（迄115年6月30日）", 178083, ""),
    ("changhua", "彰化縣門牌點位資料", 170727, ""),
    ("yunlin", "雲林縣門牌座標資料（1140505版）", 166201, ""),
    ("chiayi-county", "嘉義縣門牌位置（1150327產製）", 172873, ""),
    ("pingtung", "屏東縣全縣門牌檔（1150914更新）", 170847, ""),
    ("hualien", "花蓮縣門牌點位資料", 175221, ""),
    ("penghu", "澎湖縣門牌位置數值資料", 170852, ""),
    ("kinmen", "金門縣門牌位置數值資料", 171571, ""),
]:
    COUNTIES[_code] = (f"std_{_code}.csv", STD_F,
        {"src": f"{_name}（{_name[:3]}政府{_note}；政府資料開放授權條款第1版）", "url": f"https://data.gov.tw/dataset/{_id}"})

def norm(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s or "")).replace("台", "臺")

def norm_no(s):
    s = norm(s)
    m = re.match(r"^(.*?)號", s)
    return m.group(1) if m else s

def site_towns(code):
    with urllib.request.urlopen(SITE + code + ".json") as r:
        d = json.load(r)
    out = {}
    for t in [t if isinstance(t, str) else t["name"] for t in d.get("towns", [])]:
        with urllib.request.urlopen(SITE + f"{code}/li-{urllib.parse.quote(t)}.json") as r:
            li = json.load(r)
        out[t] = {norm(x.get("village", "")) for x in li.get("races", []) if x.get("village")}
    return out

# 原始檔亂碼、無法用萬用比對還原的里名；每筆都經「同區唯一缺漏的里」與「相鄰門牌所屬里」兩項確認
ALIASES = {"hsinchu-city": {"香C-": "香村里"},          # 香山區資料缺香村里、多出香C-（1,896 筆）
           "hsinchu-county": {"上�閮�": "上舘里",       # 竹東中豐路二段207號，前後 205、211 號皆上舘里
                              "上?里": "上舘里"}}       # 有了上舘里原名後萬用比對會排除它，明列

VARIANTS = [("壳売殼", "殼")]

def fix_village(v, site_vs, literal_vs):
    """罕用字替代符號（■ ? [石曹] (塭)）→ 網站現行里名；找不到回 None。"""
    if v in site_vs:
        return v
    v = re.sub(r"\d+$", "", v)                         # 「廣福里010」尾端誤植鄰號
    if v in site_vs:
        return v
    for a, b in VARIANTS:                             # 異體字（龜壳里／龜売里／龜殼里）
        for x in site_vs:
            if v.translate(str.maketrans(a, b * len(a))) == x.translate(str.maketrans(a, b * len(a))):
                return x
    lit = re.sub(r"\(([^)]+)\)", r"\1", v)           # 「(塭)南里」先照原字試
    if lit != v and lit in site_vs:
        return lit
    pat = re.sub(r"\[[^\]]+\]|\([^)]+\)|[■?？]", ".", v)
    if pat == v:
        return None
    hits = [x for x in site_vs if re.fullmatch(pat, x)]
    if len(hits) > 1:                                 # 多個候選才排除「門牌資料已用原名出現」的里
        hits = [x for x in hits if x not in literal_vs]
    return hits[0] if len(hits) == 1 else None

def collapse(d):
    """同一層全部同一個里 → 收成字串。"""
    vals = set()
    for v in d.values():
        if isinstance(v, str): vals.add(v)
        else: return d
    return vals.pop() if len(vals) == 1 else d

def build(code, src_dir, out_dir, date):
    path, F, meta = COUNTIES[code]
    by_area = collections.defaultdict(list)
    n = 0
    enc = meta.pop("encoding", "utf-8-sig")
    with open(os.path.join(src_dir, path), encoding=enc, newline="") as f:
        for row in csv.DictReader(f):
            n += 1
            v = norm(ALIASES.get(code, {}).get(row[F["village"]], row[F["village"]]))
            road = norm(row[F["road"]]) or norm(row[F["region"]])
            if not v or not road:
                continue
            lane = norm(row[F["lane"]]) + norm(row[F["alley"]])
            by_area[row[F["area"]].strip()].append((road, lane, norm_no(row[F["no"]]), v))
    towns = site_towns(code)
    mapping = {}
    for area, rows in by_area.items():
        vs = {r[3] for r in rows}
        mapping[area] = max(towns, key=lambda t: len(vs & towns[t]))
    st = {"rows": n, "files": 0, "kept": 0, "dropped_unknown": 0, "conflict_numbers": 0,
          "dup_town": [t for t, c in collections.Counter(mapping.values()).items() if c > 1],
          "unmapped_site_towns": sorted(set(towns) - set(mapping.values())), "renamed": {}, "unknown": []}
    os.makedirs(os.path.join(out_dir, code), exist_ok=True)
    for area, rows in by_area.items():
        town = mapping[area]; site_vs = towns[town]; literal_vs = {r[3] for r in rows}
        fixed = {v: fix_village(v, site_vs, literal_vs) for v in literal_vs}
        for v, fv in fixed.items():
            if fv is None: st["unknown"].append(f"{town}:{v}")
            elif fv != v: st["renamed"][f"{town}:{v}"] = fv
        tree = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(set)))
        cnt = 0
        for road, lane, no, v in rows:
            fv = fixed[v]
            if fv is None:
                st["dropped_unknown"] += 1; continue
            tree[road][lane][no].add(fv); cnt += 1
        st["kept"] += cnt
        out = {"_meta": dict(meta, date=date, count=cnt)}
        for road, lanes in sorted(tree.items()):
            ld = {}
            for lane, nos in lanes.items():
                nd = {}
                for no, vs in nos.items():
                    if len(vs) > 1:
                        st["conflict_numbers"] += 1; nd[no] = sorted(vs)
                    else:
                        nd[no] = next(iter(vs))
                ld[lane] = collapse(nd)
            out[road] = collapse(ld)
        with open(os.path.join(out_dir, code, f"{town}.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        st["files"] += 1
    return st

if __name__ == "__main__":
    src_dir, out_dir, date = sys.argv[1], sys.argv[2], sys.argv[3]
    for code in sys.argv[4:] or COUNTIES:
        print(code, json.dumps(build(code, src_dir, out_dir, date), ensure_ascii=False))
