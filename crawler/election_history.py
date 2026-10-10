#!/usr/bin/env python3
"""中選會選舉資料庫（votedata）2014／2018／2022 縣市長與議員選舉 → 每位候選人的參選結果。

輸出 election_history.json：{"縣市|姓名(正規化)": [{"year","office","district","party","elected","votes","rate","dup"}]}
dup＝當年同縣市同名的候選人數（>1 時前端不採用，避免同名誤認）。
"""
import csv, glob, json, os, re, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from villages import fix

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "raw/cec_2022/x/votedata/votedata/voteData")
YEARS = {"2014": "2014-103年地方公職人員選舉", "2018": "2018-107年地方公職人員選舉", "2022": "2022-111年地方公職人員選舉"}
KINDS = [  # (office, 2014/2018 資料夾, 2022 資料夾)
    ("mayor", ["直轄市市長", "縣市市長"], ["C1/city", "C1/prv"]),
    ("council", ["直轄市區域議員", "縣市區域議員"], ["T1/city", "T1/prv"]),
    ("council-plain", ["直轄市平原議員", "縣市平原議員"], ["T2/city", "T2/prv"]),
    ("council-mountain", ["直轄市山原議員", "縣市山原議員"], ["T3/city", "T3/prv"]),
]


def norm(n):
    return re.sub(r"[\s．‧·・.]", "", n or "")


def rd(p):
    with open(p, encoding="utf-8", newline="") as f:
        return [[c.strip().lstrip("'") for c in r] for r in csv.reader(f) if r]


out, seen = {}, Counter()
for year, folder in YEARS.items():
    for office, old_dirs, new_dirs in KINDS:
        for sub in (new_dirs if year == "2022" else old_dirs):
            d = os.path.join(BASE, folder, sub)
            if not os.path.exists(os.path.join(d, "elcand.csv")):
                continue
            base = {tuple(r[:5]): r[5] for r in rd(os.path.join(d, "elbase.csv"))}
            party = {r[0]: r[1] for r in rd(os.path.join(d, "elpaty.csv"))}
            tks = {}
            for r in rd(os.path.join(d, "elctks.csv")):
                if r[5] in ("0000", "0"):
                    tks[(tuple(r[:5]), r[6])] = (int(r[7] or 0), float(r[8] or 0))
            for r in rd(os.path.join(d, "elcand.csv")):
                k = tuple(r[:5])
                county = fix(base.get((k[0], k[1], "00", "000", "0000"), "")).replace("台", "臺")
                dist = ""
                if office != "mayor":
                    dist = base.get((k[0], k[1], k[2], "000", "0000"), "") or base.get(k, "")
                    dist = re.sub(r"第0*(\d+)選(舉)?區", r"第\1選舉區", dist)
                votes, rate = tks.get((k, r[5])) or tks.get(((k[0], k[1], "00", k[3], k[4]), r[5]), (None, None))
                key = f"{county}|{norm(r[6])}"
                seen[(year, key)] += 1
                out.setdefault(key, []).append({"year": int(year), "office": office, "district": dist,
                                                "party": party.get(r[7], r[7]), "elected": r[14] == "*",
                                                "votes": votes, "rate": rate})
for key, hs in out.items():
    for h in hs:
        h["dup"] = seen[(str(h["year"]), key)]
json.dump(out, open(os.path.join(HERE, "election_history.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
c = Counter((h["year"], h["office"], h["votes"] is None, "" in key.split("|")[:1]) for key, hs in out.items() for h in hs)
print(sorted(c.items()))
