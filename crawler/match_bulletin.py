#!/usr/bin/env python3
"""把 parse_bulletin 抽出的卡片對回本站候選人（縣市＋選舉＋姓名），每人留一張內容最完整的卡。

對應順序：
1. 姓名完全相同（含異體字正規化、原住民名只比中文部分）。同縣市同名多筆時，用檔名的選區與號次分辨。
2. 文字層姓名有缺字或錯字（字型對照表錯誤）：同縣市、檔名選區內、號次相同，且姓名至少共用一半的字 → 採用，並記下文字層姓名。
號次：卡片上讀得到的數字與本站號次不同時列入衝突清單（不自動改）。

用法：python3 match_bulletin.py <parse 輸出> <輸出 json>
"""
import json, os, re, sys, unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
sys.path.insert(0, HERE)
from parse_bulletin import fold, cn_part

ZH = "零一二三四五六七八九十"


def zh2int(s):
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if s.startswith("十"):
        return 10 + ZH.index(s[1])
    if "十" in s:
        a, b = s.split("十")
        return ZH.index(a) * 10 + (ZH.index(b) if b else 0)
    return ZH.index(s)


def districts_of(path):
    """檔名裡的選區編號，例如「第12、13選舉區」「(2、10、12選區)」「第一選區」。"""
    name = re.sub(r"[及和、]第", "、", path.split("/")[-1]).replace("及", "、")
    out = set()
    for m in re.finditer(r"第?([0-9一二三四五六七八九十]+(?:[、.,及和][0-9一二三四五六七八九十]+)*)\s*選(?:舉)?區", name):
        for x in re.split(r"[、.,及和]", m.group(1)):
            try:
                out.add(zh2int(x))
            except ValueError:
                pass
    m = re.search(r"\(([0-9、]+)選區\)", name)
    if m:
        out |= {int(x) for x in m.group(1).split("、")}
    return out


def score(c):
    return sum(len("".join(c.get(k, []))) for k in ("edu", "exp", "platform")) + 500 * (c.get("platform_img", 0) > 0.3)


def main():
    bul = json.load(open(sys.argv[1], encoding="utf-8"))
    idx = json.load(open(os.path.join(DATA, "index.json"), encoding="utf-8"))
    DB = {}
    for c in idx["counties"]:
        d = json.load(open(os.path.join(DATA, c["file"]), encoding="utf-8"))
        DB[c["name"]] = [(r["id"], x) for r in d["races"] for x in r["candidates"] if not x.get("name_unreadable")]
    picked = defaultdict(list)
    unmatched, conflicts = [], []
    for f in bul:
        cty = next((k for k in DB if k in f["path"]), None)
        is_mayor_file = "議員" not in f["path"]
        dists = districts_of(f["path"])
        for c in f["cards"]:
            if "err" in c:
                unmatched.append([f["file"], c.get("page"), c.get("num"), c.get("name"), c["err"]]); continue
            k = fold(c["name"])
            m = [t for t in DB[cty] if fold(t[1]["name"]) == k or (cn_part(t[1]["name"]) == k and len(k) >= 2)]
            how = "name"
            if len(m) > 1:
                m2 = [t for t in m if (t[0] == "mayor") == is_mayor_file]
                m = m2 or m
            if len(m) > 1 and dists:
                m = [t for t in m if t[0] == "mayor" or int(t[0].split("-")[1]) in dists] or m
            if len(m) > 1 and c.get("num"):
                m = [t for t in m if t[1].get("number") == c["num"]] or m
            if not m and c.get("num"):
                pool = [t for t in DB[cty] if t[1].get("number") == c["num"] and (t[0] == "mayor") == is_mayor_file
                        and (t[0] == "mayor" or not dists or int(t[0].split("-")[1]) in dists)]
                cand = []
                for t in pool:
                    dbn = cn_part(t[1]["name"]) or fold(t[1]["name"])
                    common = sum(1 for a, b in zip(k, dbn) if a == b)
                    if len(k) >= 1 and (dbn.startswith(k) or (len(k) >= 2 and k in dbn)) or common * 2 >= max(len(dbn), 2) and len(k) == len(dbn):
                        cand.append(t)
                if len(cand) == 1:
                    m, how = cand, "number+partial_name"
            if len(m) != 1:
                unmatched.append([f["file"], c.get("page"), c.get("num"), c.get("name"), f"{len(m)} hits"]); continue
            rid, x = m[0]
            if c.get("num") is not None and x.get("number") is not None and c["num"] != x["number"]:
                conflicts.append([cty, rid, x["name"], x["number"], c["num"], f["file"], c["page"]])
            picked[(cty, rid, x["id"])].append({**c, "match": how, "file": f["file"], "url": f["url"], "name_text": c.get("name_raw", c["name"]), "name": x["name"]})
    out = {}
    for (cty, rid, cid), cs in picked.items():
        best = max(cs, key=score)
        best["copies"] = len(cs)
        out[f"{cty}|{rid}|{cid}"] = best
    missing = [[k, rid, x["name"], x.get("number")] for k, v in DB.items() for rid, x in v if f"{k}|{rid}|{x['id']}" not in out]
    json.dump({"cards": out, "unmatched": unmatched, "conflicts": conflicts, "missing": missing},
              open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"候選人 {sum(len(v) for v in DB.values())}，對到 {len(out)}，缺 {len(missing)}；未對應卡片 {len(unmatched)}；號次衝突 {len(conflicts)}")
    from collections import Counter
    print("缺：", dict(Counter(m[0] for m in missing)))
    print("部分姓名對應：", [(v["name_text"], v["name"]) for v in out.values() if v["match"] != "name"])


if __name__ == "__main__":
    main()
