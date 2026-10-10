#!/usr/bin/env python3
"""中選會選舉資料庫（votedata.zip）2014／2018／2022 村里長選舉 → 每位候選人在該村里的參選紀錄（得票、得票率、是否當選）。

輸出 village_history.json：{"縣市|鄉鎮市區|村里|姓名(正規化)": [{"year","elected","votes","rate"}]}
"""
import csv, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from villages import fix, load as load_villages

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw/cec_2022/x/votedata/votedata/voteData")
YEARS = {"2014": "2014-103年地方公職人員選舉", "2018": "2018-107年地方公職人員選舉", "2022": "2022-111年地方公職人員選舉"}


def norm(n):
    return re.sub(r"[\s．‧·・.]", "", n or "")


def rd(p):
    with open(p, encoding="utf-8", newline="") as f:
        return [[c.strip().lstrip("'") for c in r] for r in csv.reader(f) if r]   # 2014／2018 檔的欄位前有單引號


VIL = {}
for v in load_villages():
    VIL.setdefault((v["county"], v["town"]), set()).add(v["village"])


def canon_village(county, town, vil):
    """選舉資料庫的罕用字常以造字（PUA）表示或直接漏字：在同區官方村里清單中找唯一相符者。"""
    names = VIL.get((county, town), set())
    for k, v in {"\ue006": "塭", "\ue012": "檨", "\ue02d": "廍"}.items():   # 選舉資料庫村里名的造字
        vil = vil.replace(k, v)
    if vil in names:
        return vil
    pat = re.compile("^" + "".join("." if "\ue000" <= ch <= "\uf8ff" else re.escape(ch) for ch in vil) + "$")
    m = [n for n in names if pat.match(n)]
    if len(m) == 1:
        return m[0]
    if len(vil) >= 2:   # 漏一個字（例：石𥕢里 → 石里）
        m = [n for n in names if len(n) == len(vil) + 1 and any(n[:i] + n[i + 1:] == vil for i in range(len(n)))]
        if len(m) == 1:
            return m[0]
    return vil


out = {}
for year, folder in YEARS.items():
    dirs = [os.path.dirname(p) for p in glob.glob(os.path.join(BASE, folder, "**", "elcand.csv"), recursive=True)
            if "村里長" in p or "/V1/" in p]
    n = 0
    for d in dirs:
        base = {tuple(r[:5]): r[5] for r in rd(os.path.join(d, "elbase.csv"))}
        tks = {}
        for r in rd(os.path.join(d, "elctks.csv")):
            if r[5] in ("0000", "0"):  # 投開票所合計（2022 為 0000，2014／2018 為 0）
                tks[(tuple(r[:5]), r[6])] = (int(r[7] or 0), float(r[8] or 0))
        for r in rd(os.path.join(d, "elcand.csv")):
            k = tuple(r[:5])
            county = base.get((k[0], k[1], "00", "000", "0000"), "")
            town = base.get((k[0], k[1], k[2], k[3], "0000")) or base.get((k[0], k[1], "00", k[3], "0000"), "")   # 2014 第 3 欄是選區碼
            vil = base.get(k) or base.get((k[0], k[1], "00", k[3], k[4]), "")
            votes, rate = tks.get((k, r[5]), (None, None))
            county, town = fix(county).replace("台", "臺"), fix(town)
            key = "|".join([county, town, canon_village(county, town, fix(vil)), norm(r[6])])
            out.setdefault(key, []).append({"year": int(year), "elected": r[14] == "*", "votes": votes, "rate": rate})
            n += 1
    print(year, len(dirs), "dirs", n, "candidates")
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "village_history.json"), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
print("keys", len(out))
