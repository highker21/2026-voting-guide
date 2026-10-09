#!/usr/bin/env python3
"""把 parsed/ 的中選會登記名冊＋村里清單＋選區對照＋2022 當選名單，組成前端讀的 data/*.json。

用法：python3 build_data.py   （輸出到 ../data/）
"""
import json, os, re, shutil
from collections import defaultdict
from villages import load as load_villages

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data")
UPDATED = "2026-10-09"
STAGE = "登記階段（中選會 115/09/07 製表，尚未審定）"
CEC_PAGE = "https://web.cec.gov.tw/central/article/64709"
PDF = {  # 中選會 64709 附件
    "1-1": ("115年直轄市長選舉候選人登記彙總表", "https://web.cec.gov.tw/api/file/bb9a8d7a-9b8a-41ec-8e23-33efd009385a.pdf"),
    "2-1": ("115年直轄市議員選舉候選人登記彙總表", "https://web.cec.gov.tw/api/file/ccd7e51a-5fd0-4ea0-a81b-a120cd550c9c.pdf"),
    "3-1": ("115年縣市長選舉候選人登記彙總表", "https://web.cec.gov.tw/api/file/370f3bbf-6408-4fdc-b8d8-9b9214913f74.pdf"),
    "4-1": ("115年縣市議員選舉候選人登記彙總表", "https://web.cec.gov.tw/api/file/9ccb6224-20be-479e-931f-81aa6155f28a.pdf"),
    "9": ("115年村里長選舉候選人登記彙總表", "https://web.cec.gov.tw/api/file/f1abbda2-229b-4a02-8dfb-58beb3ceca61.pdf"),
}
ACCESSED = "2026-10-09"
EL_SRC = {"title": "中選會選舉資料庫 111年地方公職人員選舉當選名單（「現任」＝2022 當選，未計任內補選或解職）",
          "url": "https://data.cec.gov.tw/選舉資料庫/votedata.zip", "accessed": ACCESSED}
COUNTIES = [  # (名稱, code, 直轄市?)
    ("臺北市", "taipei", 1), ("新北市", "new-taipei", 1), ("桃園市", "taoyuan", 1), ("臺中市", "taichung", 1),
    ("臺南市", "tainan", 1), ("高雄市", "kaohsiung", 1), ("基隆市", "keelung", 0), ("新竹市", "hsinchu-city", 0),
    ("嘉義市", "chiayi-city", 0), ("新竹縣", "hsinchu-county", 0), ("苗栗縣", "miaoli", 0), ("彰化縣", "changhua", 0),
    ("南投縣", "nantou", 0), ("雲林縣", "yunlin", 0), ("嘉義縣", "chiayi-county", 0), ("屏東縣", "pingtung", 0),
    ("宜蘭縣", "yilan", 0), ("花蓮縣", "hualien", 0), ("臺東縣", "taitung", 0), ("澎湖縣", "penghu", 0),
    ("金門縣", "kinmen", 0), ("連江縣", "lienchiang", 0),
]
TIMELINE = [  # 中選會 115 年地方選舉工作進行程序表（全國一致的節點）
    ("2026-08-31～09-04", "候選人登記"),
    ("2026-10-16 前", "候選人資格審定"),
    ("2026-10-23", "號次抽籤（依各選委會公告）"),
    ("2026-11-17～11-22 前", "候選人名單公告（依選舉種類不同）"),
    ("2026-11-18 前後", "選舉公報發送（學經歷、政見）"),
    ("2026-11-28（六）", "投票日"),
]
TIMELINE_SRC = ("中選會：115年地方公職人員選舉投票日及工作進行程序表", "https://web.cec.gov.tw/central/article/61722")
# 名冊因罕用字缺字、靠前後筆與內政部村里清單排序比對補回（見 README）
VILLAGE_FIX = {4261: "龜売里", 4262: "龜売里", 4912: "檨林里", 5575: "塭南里", 5576: "塭南里", 5617: "公塭里"}
VILLAGE_ALIAS = {("雲林縣", "水林鄉", "瓊埔村"): "𣐤埔村"}


def jload(name, default=None):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def norm(n):
    """比對用：去空白與原住民名分隔點。"""
    return re.sub(r"[\s．‧·・.]", "", n or "")


def council_inc(el, county, dist, name):
    """同縣市同名且同選區 → True；同縣市同名但選區不同（可能重劃或換區）→ None 待人工確認；否則 False。"""
    if not el:
        return None
    d = el.get((county, norm(name)))
    if d is None:
        return False
    return True if d == dist else None


def party(p):
    return "無政黨推薦" if p in ("", "無") else p


def cand(r, sid, cid, inc):
    name = r["name"] or f"（姓名含罕用字，請見官方名冊第 {r['page']} 頁）"
    c = {"id": cid, "name": name, "party": party(r["party"]), "number": None, "incumbent": inc,
         "bio": [], "record": [], "platform": [], "donation_2022": None,
         "reg": {"date": r["date"], "page": r["page"], "src": [sid]}}
    if not r["name"]:
        c["name_unreadable"] = True
    return c


def main():
    vl = load_villages()
    dmap = jload("district_map.json", {})
    el = jload("elected_2022.json", {})
    el_mayor = {(x["county"], norm(x["name"])) for x in el.get("mayor", [])}
    el_council = {(x["county"], norm(x["name"])): x["district"] for x in el.get("council", [])}
    el_village = {(x["county"], x["town"], x["village"], norm(x["name"])) for x in el.get("village", [])}
    el_has_village = {x["county"] for x in el.get("village", [])}
    P = {k: jload(f"parsed/cec_{k}.json") for k in PDF}

    towns_of = defaultdict(list)
    vil_of = defaultdict(list)
    for v in vl:
        if v["town"] not in towns_of[v["county"]]:
            towns_of[v["county"]].append(v["town"])
        vil_of[(v["county"], v["town"])].append(v["village"])
    full = {v["county"] + v["town"] + v["village"]: v for v in vl}

    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    index = []
    for cname, code, special in COUNTIES:
        S = {}
        def src(key, page=None):
            title, url = PDF[key]
            sid = "R" + key.replace("-", "")
            S[sid] = {"title": f"中選會 {title}（115/09/07 製表）", "url": url, "accessed": ACCESSED}
            return sid
        S["T"] = {"title": TIMELINE_SRC[0], "url": TIMELINE_SRC[1], "accessed": ACCESSED}
        S["E"] = EL_SRC
        races = []
        # 首長
        mk = "1-1" if special else "3-1"
        rows = [r for r in P[mk] if r["area"] == cname]
        sid = src(mk)
        has_el = bool(el_mayor)
        races.append({"id": "mayor", "type": "直轄市長" if special else "縣市長", "name": f"{cname}長",
                      "area": "全" + cname[-1], "seats": 1, "note": "",
                      "candidates": [cand(r, sid, f"mayor-{i+1}", ((cname, norm(r["name"])) in el_mayor) if has_el else None)
                                     for i, r in enumerate(rows)]})
        # 議員
        ck = "2-1" if special else "4-1"
        sid = src(ck)
        dm = dmap.get(cname, {})
        if dm.get("src"):
            S["D"] = {"title": dm.get("src_title") or f"{cname}議員選舉區劃分", "url": dm["src"], "accessed": ACCESSED}
        groups = defaultdict(list)
        for r in P[ck]:
            if r["area"].startswith(cname):
                groups[r["area"][len(cname):]].append(r)
        def dnum(k):
            m = re.search(r"\d+", k)
            return int(m.group()) if m else 999
        for dist in sorted(set(groups) | set(dm.get("districts", {})), key=dnum):
            info = dm.get("districts", {}).get(dist, {})
            note = []
            if info.get("indigenous"):
                note.append(f"{info['indigenous']}原住民選舉區：只有具該原住民身分的選民投這一區。")
            if info.get("women_min"):
                note.append(f"婦女保障至少 {info['women_min']} 席。")
            if info.get("note"):
                note.append(info["note"])
            if not info:
                note.append("本選區涵蓋的鄉鎮市區尚待補上。")
            races.append({"id": f"council-{dnum(dist)}", "type": "議員", "name": f"{cname}議員 {dist}",
                          "area": "、".join(info.get("towns", [])) or "（涵蓋範圍待補）", "seats": info.get("seats"),
                          "districts": info.get("towns", []), "note": " ".join(note),
                          "candidates": [cand(r, sid, f"council-{dnum(dist)}-{i+1}",
                                              council_inc(el_council, cname, dist, r["name"]))
                                         for i, r in enumerate(groups.get(dist, []))]})
        meta = {"title": f"2026 {cname}投票指南", "county": cname, "code": code, "updated": UPDATED, "stage": STAGE,
                "vote_date": "2026-11-28", "timeline": [{"date": d, "item": t, "src": ["T"]} for d, t in TIMELINE]}
        json.dump({"meta": meta, "sources": S, "towns": towns_of[cname], "races": races},
                  open(os.path.join(OUT, f"{code}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        # 村里長：每個鄉鎮市區一檔，包含無人登記的村里
        vs = defaultdict(list)
        for i, r in enumerate(P["9"]):
            a = r["area"].replace("|", "")
            if not a.startswith(cname):
                continue
            if i in VILLAGE_FIX:
                a = next(k for k in full if k.endswith(VILLAGE_FIX[i]) and k.startswith(a))
            if a not in full:
                for (c, t, v), real in VILLAGE_ALIAS.items():
                    if a == c + t + v:
                        a = c + t + real
            if a not in full:
                raise SystemExit(f"村里對不到：{i} {r}")
            v = full[a]
            vs[(v["town"], v["village"])].append(r)
        os.makedirs(os.path.join(OUT, code), exist_ok=True)
        S9 = {"R9": {"title": f"中選會 {PDF['9'][0]}（115/09/07 製表）", "url": PDF["9"][1], "accessed": ACCESSED},
              "E": EL_SRC,
              "V": {"title": "內政部戶政司 各村（里）統計（ODRP010，115/09）村里清單", "url": "https://www.ris.gov.tw/rs-opendata/api/v1/datastore/ODRP010/11509", "accessed": ACCESSED}}
        nli = 0
        for town in towns_of[cname]:
            lraces = []
            for vil in vil_of[(cname, town)]:
                rows = vs.get((town, vil), [])
                lraces.append({"id": f"li-{vil}", "type": "村里長", "name": f"{town}{vil}{vil[-1]}長", "village": vil,
                               "area": vil, "seats": 1, "note": "" if rows else "名冊上沒有人登記參選。",
                               "candidates": [cand(r, "R9", f"li-{vil}-{j+1}",
                                                   ((cname, town, vil, norm(r["name"])) in el_village) if cname in el_has_village else None)
                                              for j, r in enumerate(rows)]})
                nli += len(rows)
            json.dump({"meta": {"county": cname, "town": town, "updated": UPDATED, "stage": STAGE}, "sources": S9, "races": lraces},
                      open(os.path.join(OUT, code, f"li-{town}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        index.append({"code": code, "name": cname, "file": f"{code}.json", "stage": STAGE, "updated": UPDATED,
                      "counts": {"mayor": len(races[0]["candidates"]), "council": sum(len(r["candidates"]) for r in races[1:]),
                                 "village": nli}})
    json.dump({"title": "2026 投票指南", "updated": UPDATED, "vote_date": "2026-11-28（六）", "counties": index},
              open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tot = {k: sum(c["counts"][k] for c in index) for k in ("mayor", "council", "village")}
    print("counties", len(index), tot)


if __name__ == "__main__":
    main()
