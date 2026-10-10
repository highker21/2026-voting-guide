#!/usr/bin/env python3
"""把 parsed/ 的中選會登記名冊＋村里清單＋選區對照＋2022 當選名單，組成前端讀的 data/*.json。

用法：python3 build_data.py   （輸出到 ../data/）
"""
import json, os, re, shutil
from collections import Counter, defaultdict
from villages import load as load_villages, fix as fix_name

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
EL_SRC = {"title": "中選會選舉資料庫（103／107／111 年地方公職人員選舉候選人與得票；「2022 當選」未計任內補選或解職）",
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


def bio_item(x, sid):
    """經歷條目：新聞標未確認、自述加標籤；舊年度公報標年份；含「現任」者註明是來源原文（可能已過期）。"""
    item = {"text": x["text"], "src": [sid]}
    if x["tier"] == "news":
        item["official"] = False
    elif x["tier"] == "self":
        item["label"] = "候選人／政黨自述"
    y = re.search(r"(20\d\d)年?\)?）?", x.get("src_title", "")) if "公報" in x.get("src_title", "") else None
    if y and y.group(1) != "2026":
        item["label"] = f"{y.group(1)} 年選舉公報"
    if "現任" in x["text"] and str(x.get("src_date", "")).startswith("2026"):
        pass   # 今年的資料，「現任」就是現在
    elif "現任" in x["text"] and not item.get("label"):
        item["label"] = "來源頁原文，「現任」可能已過期"
    elif "現任" in x["text"]:
        item["label"] += "；「現任」為當年"
    return item


def past_runs(ehist, county, name, dup2026):
    """縣市長／議員過去三屆參選結果（中選會選舉資料庫）；同年同縣市同名、或今年同縣市同名者不採用。"""
    if dup2026 > 1:
        return []
    out = []
    for h in sorted(ehist.get(f"{county}|{norm(name)}", []), key=lambda h: -h["year"]):
        if h["dup"] > 1:
            continue
        if h["office"] == "mayor":
            what = f"{county}{county[-1]}長" if county[-1] == "縣" else f"{county}長"
        else:
            dist = re.sub(r"^.{2}[縣市]", "", h["district"])
            tag = {"council-plain": "（平地原住民）", "council-mountain": "（山地原住民）"}.get(h["office"], "")
            what = f"{county}議員{dist}{tag}"
        res = "當選" if h["elected"] else "未當選"
        num = f"（{h['votes']:,} 票，得票率 {h['rate']:.2f}%）" if h["votes"] is not None else ""
        note = f"（{h['note']}）" if h.get("note") else ""
        out.append({"text": f"{h['year']} 年參選{what}{note}：{res}{num}", "src": ["E"]})
    return out


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
    recm = jload("records_mayor.json", {})
    biom = jload("bio_mayor.json", {})
    for f in ("bio_mayor_news_B.json", "bio_mayor_party_B.json", "bio_mayor_party_B2.json"):
      for county, people in jload(f, {}).items():   # 原本查無資料者，以媒體／自述補上
        for name, v in people.items():
            if not biom.get(county, {}).get(name, {}).get("bio"):
                biom.setdefault(county, {})[name] = v
    recl = jload("records_legislator.json", {})
    vhist = jload("village_history.json", {})
    ehist = jload("election_history.json", {})
    don = jload("donation_2022_B.json", {})
    news = {}
    for f in ("news_B.json", "news_B2.json", "news_B3.json"):
        for county, people in jload(f, {}).items():
            for name, items in people.items():
                news.setdefault(county, {}).setdefault(norm(name), []).extend(items)   # 姓名正規化（原住民名空格寫法不一）
    bio_li = jload("bio_li_self.json", {})
    vil22 = {tuple(k.split("|")[:3]) for k, v in vhist.items() if any(h["year"] == 2022 for h in v)}   # 2022 有選舉的村里
    hist_by_town = defaultdict(list)
    for k, v in vhist.items():
        c_, t_, v_, n_ = k.split("|")
        hist_by_town[(c_, t_, n_)].append((v_, v))
    recc = {}
    for f in ("records_council.json", "records_council_2.json", "records_council_b.json"):
        recc.update(jload(f, {}))
    bioc = {}
    for f in ("bio_council.json", "bio_council_2.json", "bio_council_news_B.json", "bio_council_news_B2.json", "bio_council_party_B.json", "bio_council_news_B3.json", "bio_council_party_B2.json"):
        for county, dists in jload(f, {}).items():
            for dist, people in dists.items():
                tgt = bioc.setdefault(county, {}).setdefault(re.sub(r"（.*）", "", dist), {})
                for name, v in people.items():
                    if ("_news_B" in f or "_party_B" in f) and tgt.get(name, {}).get("bio"):
                        continue   # 媒體／自述只補空白，不覆蓋官方資料
                    tgt[name] = v
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
    nvb = 0
    search = []  # [姓名, 政黨, code, 選舉名稱, 分頁, 鄉鎮市區, 村里, 候選人 id]
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
        mrows = [cand(r, sid, f"mayor-{i+1}", ((cname, norm(r["name"])) in el_mayor) if has_el else None)
                 for i, r in enumerate(rows)]
        def add_src(prefix, x):
            k = f"{prefix}{len([1 for key in S if key.startswith(prefix)]) + 1}"
            for key, v in S.items():  # 同一份來源只列一次
                if key.startswith(prefix) and v["url"] == x["src_url"]:
                    return key
            S[k] = {"title": f"{x['src_title']}（{x['src_date']}）" if x.get("src_date") else x["src_title"],
                    "url": x["src_url"], "accessed": ACCESSED}
            return k
        names26 = Counter(norm(r["name"]) for k in ("1-1", "3-1", "2-1", "4-1") for r in P[k] if r["area"].startswith(cname))
        def set_news(c):
            if names26[norm(c["name"])] == 1 and news.get(cname, {}).get(norm(c["name"])):
                c["news"] = [{k: x.get(k, "") for k in ("title", "url", "source", "date")} for x in news[cname][norm(c["name"])]][:5]
        def set_don(c):
            d = don.get(cname, {}).get(c["name"])
            if d and names26[norm(c["name"])] == 1:
                k = add_src("G", {"src_url": d["src_url"], "src_title": d["src_title"] + "；首次申報，不含後續更正"})
                c["donation_2022"] = {"income": d["income"], "expense": d["expense"], "src": [k]}
        for c in mrows:
            c["record"].extend(past_runs(ehist, cname, c["name"], names26[norm(c["name"])]))
            set_don(c)
            set_news(c)
        for c in mrows:
            b = biom.get(cname, {}).get(c["name"])
            for x in (b or {}).get("bio", []):
                c["bio"].append(bio_item(x, add_src("B", x)))
            lg = recl.get(cname, {}).get(c["name"])
            for x in (lg or {}).get("record", []):
                if "書面質詢" in x["text"]:  # 立法院開放資料集收錄不全（多數委員 0–9 件），暫不呈現以免誤導
                    continue
                t = x["text"]
                if "議案提案" in t:
                    t += "。註：立法院開放資料有部分議案未登錄提案人與連署人名單，「列名提案人」與「連署」件數可能偏低。以上三項件數已由第二方以同一資料集獨立重算核對（2026-10-09）。"
                if "院會出席" in t:
                    t += "（此項尚未經第二方核對）"
                c["record"].append({"text": t, "src": [add_src("L", x)], "label": "立委時期（立法院資料）"})
        rm = recm.get(cname)
        for c in mrows:
            if rm and c["incumbent"] and norm(c["name"]) == norm(rm["name"]):
                for j, x in enumerate(rm["record"], 1):
                    rid = f"M{j}"
                    S[rid] = {"title": f"{x['src_title']}（{x['src_date']}）", "url": x["src_url"], "accessed": ACCESSED}
                    item = {"text": x["text"], "src": [rid]}
                    if re.search(r"施政(總)?報告|(縣|市)政府新聞稿", x["src_title"]):
                        item["label"] = "縣市府自述（施政報告／新聞稿）"
                    c["record"].append(item)
        races.append({"id": "mayor", "type": "直轄市長" if special else "縣市長", "name": f"{cname}長",
                      "area": "全" + cname[-1], "seats": 1, "note": "",
                      "candidates": mrows})
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
            ind = info.get("indigenous")
            area = "、".join(info.get("towns", []))
            if ind:
                area = f"{ind}原住民選舉人" + (f"（設籍：{area}）" if area else f"（全{cname[-1]}）")
                note.insert(0, f"僅具{ind}原住民身分的選舉人投這一區，其他選舉人投一般選區。")
                note = [n for n in note if not n.startswith(f"{ind}原住民選舉區：")]
            ccands = [cand(r, sid, f"council-{dnum(dist)}-{i+1}", council_inc(el_council, cname, dist, r["name"]))
                      for i, r in enumerate(groups.get(dist, []))]
            for c in ccands:
                c["record"].extend(past_runs(ehist, cname, c["name"], names26[norm(c["name"])]))
                set_don(c)
                set_news(c)
            for c in ccands:
                b = bioc.get(cname, {}).get(dist, {}).get(c["name"])
                for x in (b or {}).get("bio", []):
                    c["bio"].append(bio_item(x, add_src("B", x)))
            rc = recc.get(cname)
            if rc:
                S["C"] = {"title": f"{rc['src_title']}；期間 {rc['period']}", "url": rc["src_url"], "accessed": ACCESSED}
            for c in ccands:
                if not c["incumbent"]:
                    continue
                items = (rc or {}).get("members", {}).get(c["name"])
                for x in items or []:
                    k = add_src("CU", {"src_url": x["src_url"], "src_title": f"{cname}議會官方資料（{c['name']}）"})
                    c["record"].append({"text": x["text"] + ("" if "截至" in x["text"] else "（截至 2026-10-09）"),
                                        "src": [k, "C"]})
            if rc and any(c["incumbent"] for c in ccands):
                note.append("任內紀錄取自議會官方系統：提案數含共同提案；連署件數含本人同時列為提案人的案件；各縣市議會計法不同，不宜跨縣市比較。")
            if not rc and any(c["incumbent"] for c in ccands):
                note.append("本縣市議會官網未提供可依議員查詢的完整提案或質詢資料，2022 當選者的任內紀錄暫缺。")
            races.append({"id": f"council-{dnum(dist)}", "type": "議員", "name": f"{cname}議員 {dist}" + (f"（{ind}原住民）" if ind else ""),
                          "indigenous": ind or None,
                          "area": area or "（涵蓋範圍待補）", "seats": info.get("seats"),
                          "districts": info.get("towns", []), "note": " ".join(note),
                          "candidates": ccands})
        for r in races:
            t = "" if r["id"] == "mayor" else (r.get("districts") or [""])[0]
            for c in r["candidates"]:
                if not c.get("name_unreadable"):
                    search.append([c["name"], c["party"], code, r["name"], "mayor" if r["id"] == "mayor" else "council", t, "", c["id"]])
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
                lcands = [cand(r, "R9", f"li-{vil}-{j+1}",
                               ((cname, town, vil, norm(r["name"])) in el_village) if cname in el_has_village else None)
                          for j, r in enumerate(rows)]
                for c in lcands:  # 過去三屆的參選紀錄（中選會選舉資料庫）
                    rows_h = [(vil, h) for h in vhist.get(f"{cname}|{town}|{vil}|{norm(c['name'])}", [])]
                    if not rows_h and (cname, town, vil) not in vil22:
                        # 2022 後新設或調整的村里：改看同區同名（只有一個舊村里時才採用）
                        olds = hist_by_town.get((cname, town, norm(c["name"])), [])
                        if len(olds) == 1:
                            rows_h = [(olds[0][0], h) for h in olds[0][1]]
                    for v_, h in rows_h:
                        if v_ != vil and h["year"] == 2022 and h["elected"]:
                            c["elected_2022_elsewhere"] = v_   # 新設村里：2022 年在原村里當選
                    for v_, h in sorted(rows_h, key=lambda x: -x[1]["year"]):
                        res = "當選" if h["elected"] else "未當選"
                        num = f"（{h['votes']:,} 票，得票率 {h['rate']:.2f}%）" if h["votes"] is not None else ""
                        if v_ == vil:
                            txt = f"{h['year']} 年參選本{vil[-1]}{vil[-1]}長：{res}{num}"
                        else:
                            txt = f"{h['year']} 年參選{v_}{v_[-1]}長：{res}{num}（{vil}當時尚未設立）"
                        c["record"].append({"text": txt, "src": ["E"]})
                    for x in bio_li.get(cname, {}).get(town, {}).get(vil, {}).get(c["name"], {}).get("bio", []):
                        sid = "S" + str(len([k for k in S9 if k.startswith("S")]) + 1)
                        if not any(v.get("url") == x["src_url"] for k, v in S9.items() if k.startswith("S")):
                            S9[sid] = {"title": x["src_title"], "url": x["src_url"], "accessed": ACCESSED}
                        else:
                            sid = next(k for k, v in S9.items() if k.startswith("S") and v.get("url") == x["src_url"])
                        c["bio"].append(bio_item(x, sid))
                lraces.append({"id": f"li-{vil}", "type": "村里長", "name": f"{town}{vil}{vil[-1]}長", "village": vil,
                               "area": vil, "seats": 1, "note": "" if rows else "名冊上沒有人登記參選。",
                               "candidates": lcands})
                nli += len(rows)
                for c in lraces[-1]["candidates"]:
                    if not c.get("name_unreadable"):
                        search.append([c["name"], c["party"], code, f"{cname}{town}{vil}{vil[-1]}長", "li", town, vil, c["id"]])
            json.dump({"meta": {"county": cname, "town": town, "updated": UPDATED, "stage": STAGE}, "sources": S9, "races": lraces},
                      open(os.path.join(OUT, code, f"li-{town}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        # 村里界圖（內政部國土測繪中心，data.gov.tw 7438；mapshaper 簡化 12%）→ 給地址定位在瀏覽器內判斷村里
        for town in towns_of[cname]:
            src_vb = os.path.join(HERE, "village_boundary", f"{cname}_{town}.json")
            if not os.path.exists(src_vb):
                alt = [f for f in os.listdir(os.path.join(HERE, "village_boundary")) if f.startswith(cname + "_") and fix_name(f[len(cname) + 1:-5]) == town]
                src_vb = os.path.join(HERE, "village_boundary", alt[0]) if alt else None
            if src_vb:
                names = vil_of[(cname, town)]
                def vname(n):
                    n = fix_name(n or "")
                    if n in names:
                        return n
                    n2 = re.sub(r"\[(.)\]", r"\1", n).replace("濂", "濓").replace("欍埔", "𣐤埔")  # 界圖以 [字] 表示罕用字；瑞芳「濓」異體
                    if n2 in names:
                        return n2
                    if "[" not in n:
                        return n
                    pat = re.compile("^" + re.sub(r"\\\[.*?\\\]", ".", re.escape(n)) + "$")  # 界圖以 [字] 表示罕用字
                    m = [x for x in names if pat.match(x)]
                    return m[0] if len(m) == 1 else n
                feats = [{"v": vname(ft["properties"]["VILLNAME"]), "g": ft["geometry"]}
                         for ft in json.load(open(src_vb, encoding="utf-8"))["features"]
                         if ft["geometry"] and (ft["properties"]["VILLNAME"] or "").strip()]
                json.dump(feats, open(os.path.join(OUT, code, f"vb-{town}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
                nvb += 1
        index.append({"code": code, "name": cname, "file": f"{code}.json", "stage": STAGE, "updated": UPDATED,
                      "counts": {"mayor": len(races[0]["candidates"]), "council": sum(len(r["candidates"]) for r in races[1:]),
                                 "village": nli}})
    # 門牌 → 村里索引（各縣市開放門牌資料；crawler/addr_index/<code>/<區>.json）
    addr_src = os.path.join(HERE, "addr_index")
    addr_codes = []
    if os.path.isdir(addr_src):
        for code in sorted(os.listdir(addr_src)):
            d = os.path.join(addr_src, code)
            if os.path.isdir(d) and any(f.endswith(".json") for f in os.listdir(d)):
                shutil.copytree(d, os.path.join(OUT, "addr", code))
                addr_codes.append(code)
    for e in index:
        e["addr_index"] = e["code"] in addr_codes
    json.dump({"title": "2026 投票指南", "updated": UPDATED, "vote_date": "2026-11-28（六）", "counties": index},
              open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 壓縮：政黨與選舉各自去重成表，每人只存 [姓名, 政黨序號, 選舉序號, 候選人 id 尾碼]
    parties, races_t, pi, ri, rows = [], [], {}, {}, []
    for name, party_, code, rname, tab, t, v, cid in search:
        if party_ not in pi:
            pi[party_] = len(parties); parties.append(party_)
        key = (code, rname, tab, t, v)
        if key not in ri:
            ri[key] = len(races_t); races_t.append([code, rname, tab, t, v, cid.rsplit("-", 1)[0]])
        rows.append([name, pi[party_], ri[key], int(cid.rsplit("-", 1)[1])])
    json.dump({"parties": parties, "races": races_t, "rows": rows}, open(os.path.join(OUT, "search.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    tot = {k: sum(c["counts"][k] for c in index) for k in ("mayor", "council", "village")}
    print("counties", len(index), tot, "village-boundary files", nvb)


if __name__ == "__main__":
    main()
