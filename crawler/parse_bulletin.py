#!/usr/bin/env python3
"""解析中選會 115 年選舉公報 PDF（bulletin.cec.gov.tw），取出每位候選人的號次、姓名、學歷、經歷、政見。

公報是全國統一的表格版型（號次·姓名｜學歷｜經歷／政見），但各選委會排版尺寸不同、有的用框線、有的用矩形。
做法：以「大號數字＋正下方姓名」當錨點，沿錨點上方的表頭橫線切出三欄邊界，再往下找內容列與政見列的橫線，
只取落在格子內的文字。出生日期等基本資料一律不取。

用法：python3 parse_bulletin.py <PDF 目錄> <輸出 json>
PDF 目錄內檔名＝公報網址路徑把 / 換成 __（manifest.txt 有原始路徑）。
"""
import fitz, glob, json, os, re, sys, urllib.parse

BASE = "https://bulletin.cec.gov.tw/"
LABELS = {"學歷", "經歷", "政見", "號次", "姓名", "號次姓名", "號次．姓名", "號次·姓名", "號次‧姓名", "基本資料", "推薦之政黨",
          "候選人之具結情形", "學　歷", "經　歷", "政　見"}
DROP = re.compile(r"^(出生年月日|性別|出生地)[:：]")


def hv_segments(page):
    H, V = [], []
    for d in page.get_drawings():
        for it in d["items"]:
            k = it[0]
            if k == "l":
                a, b = it[1], it[2]
                if abs(a.y - b.y) < 1.5 and abs(a.x - b.x) > 15:
                    H.append((min(a.x, b.x), max(a.x, b.x), (a.y + b.y) / 2))
                elif abs(a.x - b.x) < 1.5 and abs(a.y - b.y) > 15:
                    V.append(((a.x + b.x) / 2, min(a.y, b.y), max(a.y, b.y)))
            elif k in ("re", "qu"):
                r = it[1] if k == "re" else it[1].rect
                if r.height < 3 and r.width > 15:
                    H.append((r.x0, r.x1, (r.y0 + r.y1) / 2))
                elif r.width < 3 and r.height > 15:
                    V.append(((r.x0 + r.x1) / 2, r.y0, r.y1))
                else:
                    if r.width > 15:
                        H += [(r.x0, r.x1, r.y0), (r.x0, r.x1, r.y1)]
                    if r.height > 15:
                        V += [(r.x0, r.y0, r.y1), (r.x1, r.y0, r.y1)]
    # 號次常是外框字，筆畫的短橫線不能當表格線
    H = [h for h in H if h[1] - h[0] >= 60]
    # 貼齊頁緣的線多半是整頁底色框或裁切框，不是表格線
    W, Ht = page.rect.width, page.rect.height
    H = [h for h in H if h[0] > 12 and h[1] < W - 12]
    V = [v for v in V if v[1] > 12 and v[2] < Ht - 12]
    return H, V


def text_lines(page):
    """每一行保留逐字座標：PyMuPDF 會把同一基線、不同欄的字併成一行，要按字切回各格。"""
    out = []
    for b in page.get_text("rawdict")["blocks"]:
        for l in b.get("lines", []):
            chars = [(c["c"], fitz.Rect(c["bbox"]), s["size"]) for s in l["spans"] for c in s["chars"]]
            t = "".join(c[0] for c in chars)
            if not t.strip():
                continue
            size = max(s["size"] for s in l["spans"])
            out.append({"t": t, "bb": fitz.Rect(l["bbox"]), "size": size, "chars": chars})
    return out


def clip_lines(lines, r):
    out = []
    for l in lines:
        cs = [c for c in l["chars"] if r.x0 - 1 <= (c[1].x0 + c[1].x1) / 2 <= r.x1 + 1 and r.y0 - 1 <= (c[1].y0 + c[1].y1) / 2 <= r.y1 + 1]
        if not cs:
            continue
        t = "".join(c[0] for c in cs)
        if not t.strip():
            continue
        bb = fitz.Rect(cs[0][1])
        for c in cs[1:]:
            bb |= c[1]
        out.append({"t": t, "bb": bb, "size": max(c[2] for c in cs)})
    return out


def find_anchors(lines):
    """大號數字（號次）＋正下方（或右方）較大的中文姓名。"""
    out = []
    names = [o for o in lines if re.search(r"[一-鿿]", o["t"]) and o["size"] >= 12
             and len(re.sub(r"\s", "", o["t"])) <= 12 and re.sub(r"\s", "", o["t"]) not in LABELS]
    for ln in lines:
        s = ln["t"].strip()
        if not re.fullmatch(r"\d{1,2}", s) or ln["size"] < 24:
            continue
        nb = ln["bb"]
        cx = (nb.x0 + nb.x1) / 2
        cy = (nb.y0 + nb.y1) / 2
        best = None
        for o in names:
            ob = o["bb"]
            below = cy + 10 <= (ob.y0 + ob.y1) / 2 <= cy + 110 and ob.x0 - 30 <= cx <= ob.x1 + 30
            if below and (best is None or ob.y0 < best["bb"].y0):
                best = o
        if best:
            out.append({"num": int(s), "name": re.sub(r"\s", "", best["t"]), "nb": nb, "namebb": best["bb"]})
    return out


VARIANT = str.maketrans({"黄": "黃", "啓": "啟", "温": "溫", "姫": "姬", "恒": "恆", "峯": "峰", "裏": "裡", "眞": "真",
                         "靑": "青", "淸": "清", "爲": "為", "說": "說", "敎": "教", "冲": "沖", "鷄": "雞", "群": "群", "凃": "涂",
                         "叶": "葉", "鄕": "鄉", "彥": "彥", "彦": "彥", "羣": "群", "銹": "鏽", "綫": "線"})


def fold(t):
    import unicodedata
    t = unicodedata.normalize("NFKC", t or "")
    return re.sub(r"[\s．‧·・.]", "", t).translate(VARIANT)


def cn_part(t):
    m = re.match(r"[\u3400-\u9fff\uf900-\ufaff\U00020000-\U0002ffff]+", fold(t))
    return m.group() if m else ""


def find_name_anchors(lines, hints):
    """以候選人名冊姓名找錨點（號次若是外框字或圖片，抓不到數字時用）。hints：fold 後姓名或中文部分 → 名冊姓名。"""
    out = []
    for l in lines:
        k = fold(l["t"])
        # 原住民長名字常縮小字級：整行剛好等於完整登記名才放寬到 10pt
        if l["size"] < 14 and not (l["size"] >= 10 and k in hints and fold(hints[k]) == k):
            continue
        name = hints.get(k) or (hints.get(cn_part(l["t"])) if len(cn_part(l["t"])) >= 2 and cn_part(l["t"]) == k[:len(cn_part(l["t"]))] else None)
        if name:
            out.append({"num": None, "name": name, "nb": l["bb"], "namebb": l["bb"], "by": "name"})
    return out


def chain_at(H, y, x, tol=2.5):
    """y 這條水平線上、包含 x 的連續線段，回傳各段端點（欄位邊界）。"""
    segs = sorted({(round(a, 1), round(b, 1)) for a, b, yy in H if abs(yy - y) < tol})
    if not segs:
        return []
    # 合併重疊／相接，保留切點
    pts = set()
    groups = []
    for a, b in segs:
        if groups and a <= groups[-1][1] + 6:
            groups[-1][1] = max(groups[-1][1], b)
            groups[-1][2].update((a, b))
        else:
            groups.append([a, b, {a, b}])
    for g in groups:
        if g[0] - 6 <= x <= g[1] + 6:
            return sorted(g[2])
    return []


def covers(H, x, y_after, y_before=1e9, min_y_gap=8):
    ys = sorted(yy for a, b, yy in H if a - 3 <= x <= b + 3 and y_after + min_y_gap < yy < y_before)
    return ys


def dedup_pts(pts, gap=12):
    out = []
    for p in pts:
        if not out or p - out[-1] > gap:
            out.append(p)
    return out


def in_rect(ln, r):
    b = ln["bb"]
    cx, cy = (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2
    return r.x0 - 1 <= cx <= r.x1 + 1 and r.y0 - 1 <= cy <= r.y1 + 1


ENUM = re.compile(r"^\s*(\(?\d{1,2}[\.、．)）]|[（(]?[一二三四五六七八九十]{1,3}[、．.)）]|[•‧·●◆■□★☆◎○▲►▶✓✔◉]|[①-⑳]|[\ue000-\uf8ff]\s*[\.．、])")


def cell_items(lines, r, joinall=False, edu=False, split_inline=False):
    ls = clip_lines(lines, r)
    ls = [l for l in ls if re.sub(r"\s", "", l["t"]) not in LABELS and not DROP.match(re.sub(r"\s", "", l["t"]))]
    # 同一列（y 重疊）由左到右
    ls.sort(key=lambda l: (round((l["bb"].y0 + l["bb"].y1) / 2 / 4), l["bb"].x0))
    items = []
    prev = None
    for l in ls:
        t = l["t"].strip()
        newitem = prev is None or bool(ENUM.match(t))
        if prev is not None and not newitem:
            # 前一行寫到格子右緣附近＝自動換行，接續；否則視為新的一項
            near_right = prev["bb"].x1 >= r.x1 - max(2.2 * prev["size"], 14)
            same_row = abs(l["bb"].y0 - prev["bb"].y0) < 3
            newitem = not (near_right or same_row or joinall)
            # 學歷一行一校：上一行以學位／學校結尾就算寫滿也視為新的一項
            if edu and not same_row and re.search(r"(士|業|系|所|組|校|學|中|小|班|科|院|肄|修|在學|[)）])$", items[-1]) \
                    and not re.match(r"(畢業|肄業|結業|修業|在學|學士|碩士|博士|[（(])", t):
                newitem = True
        if newitem:
            items.append(t)
        else:
            sep = "" if re.search(r"[一-鿿，、。：；（）「」]$", items[-1]) or re.match(r"[一-鿿，、。：；（）「」]", t) else " "
            items[-1] += sep + t
        prev = l
    items = [re.sub(r"^[\ue000-\uf8ff]\s*[\.．、]\s*", "", re.sub(r"\s{2,}", " ", x).strip()) for x in items if x.strip()]
    items = [x for x in items if x]
    if split_inline:   # 「…會長2．武陵國小…」同一行連寫多項：在編號前切開
        items = [y.strip() for x in items for y in re.split(r"(?<=[\u4e00-\u9fff。）)])(?=\d{1,2}[．.、](?!\d))", x) if y.strip()]
    return items


def image_cover(page, r):
    tot = 0.0
    for info in page.get_image_info():
        ib = fitz.Rect(info["bbox"]) & r
        if not ib.is_empty:
            tot += ib.width * ib.height
    return tot / max(r.width * r.height, 1)


def merge_anchors(num_a, name_a, hints):
    out = []
    for a in num_a:
        k = fold(a["name"])
        cp = cn_part(a["name"])
        a["name_raw"] = a["name"]
        a["name"] = hints.get(k) or hints.get(cp) or a["name"]
        out.append(a)
    for b in name_a:
        if any(fitz.Rect(b["nb"]).intersects(a["namebb"]) for a in out):
            continue
        out.append(b)
    return out


def parse_page(page, hints=None):
    H, V = hv_segments(page)
    lines = text_lines(page)
    cards = []
    anchors = merge_anchors(find_anchors(lines), find_name_anchors(lines, hints or {}), hints or {})
    for a in anchors:
        nb = a["nb"]
        ax = (nb.x0 + nb.x1) / 2
        # 表頭下緣：錨點上方最近、跨過錨點 x 的水平線
        ys = sorted(yy for x0, x1, yy in H if x0 - 3 <= ax <= x1 + 3 and nb.y0 - 140 < yy < (nb.y0 + nb.y1) / 2)
        if not ys:
            cards.append({**a, "err": "找不到表頭線"}); continue
        yh = ys[-1]
        # 欄界：優先用穿過表頭列的垂直線；不夠才用表頭橫線的切段端點
        vpts = dedup_pts(sorted({x for x, y0, y1 in V if y0 < yh - 4 < y1}))
        iv = max([k for k, p in enumerate(vpts) if p <= ax + 1] or [-1])
        if iv >= 0 and iv + 3 < len(vpts) and vpts[iv + 3] - vpts[iv + 1] > 200:
            pts = vpts
        else:
            pts = dedup_pts(chain_at(H, yh, ax))
        i = max([k for k, p in enumerate(pts) if p <= ax + 1] or [-1])
        if i < 0 or i + 3 >= len(pts):
            cards.append({**a, "err": f"欄界不足 {[round(p) for p in pts]}"}); continue
        x0, x1, x2, x3 = pts[i], pts[i + 1], pts[i + 2], pts[i + 3]
        mid_e = (x1 + x2) / 2
        mid_p = (x1 + x3) / 2
        yc_l = covers(H, mid_e, yh, min_y_gap=20)
        if not yc_l:
            cards.append({**a, "err": "找不到學經歷下緣"}); continue
        yc = yc_l[0]
        # 內容列的學歷／經歷分隔線可能和表頭不同位置：以內容列中段相交的垂直線為準
        ym = (yh + yc) / 2
        vx = [x for x, y0, y1 in V if y0 < ym < y1 and x1 + 20 < x < x3 - 20]
        if vx:
            x2 = min(vx, key=lambda v: abs(v - x2))
        edu_r = fitz.Rect(x1, yh, x2, yc)
        exp_r = fitz.Rect(x2, yh, x3, yc)
        # 政見：學經歷下緣之後，下一條跨過整個 x1..x3 的線（政見表頭下緣），再到下一條橫跨 90% 寬的線
        def full_span(yy):
            return sum(min(b, x3) - max(a_, x1) for a_, b, y_ in H if abs(y_ - yy) < 2.5 and b > x1 and a_ < x3) >= 0.9 * (x3 - x1)
        later = [yy for yy in covers(H, mid_p, yc, min_y_gap=4) if full_span(yy)]
        if not later:
            cards.append({**a, "err": "找不到政見列"}); continue
        yp = later[0] if later[0] - yc < 60 else yc
        after = [yy for yy in later if yy > yp + 40]
        ye = after[0] if after else page.rect.y1 - 20
        pol_r = fitz.Rect(x1, yp, x3, ye)
        if a.get("num") is None:   # 名字錨點：在號次格裡找數字
            ds = [l for l in lines if re.fullmatch(r"\d{1,2}", l["t"].strip()) and l["size"] >= 20
                  and x0 - 2 <= (l["bb"].x0 + l["bb"].x1) / 2 <= x1 + 2 and yh - 2 <= (l["bb"].y0 + l["bb"].y1) / 2 <= nb.y0 + 5]
            if len(ds) == 1:
                a = {**a, "num": int(ds[0]["t"].strip())}
        if any(c.get("rects") and abs(c["rects"][0][0] - x1) < 2 and abs(c["rects"][0][1] - yh) < 2 for c in cards):
            continue   # 同一張卡被數字與姓名各抓一次
        card = {**a, "page": page.number + 1,
                "edu": cell_items(lines, edu_r, edu=True, split_inline=True), "exp": cell_items(lines, exp_r, split_inline=True),
                "platform": cell_items(lines, pol_r),
                "platform_img": round(image_cover(page, pol_r), 2),
                "edu_img": round(image_cover(page, edu_r), 2), "exp_img": round(image_cover(page, exp_r), 2),
                "rects": [list(map(lambda v: round(v, 1), r)) for r in (edu_r, exp_r, pol_r)]}
        cards.append(card)
    for c in cards:
        c.pop("nb", None); c.pop("namebb", None)
    return cards


DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def name_hints(path):
    """依檔名的縣市，載入該縣市所有候選人姓名當錨點提示。"""
    idx = json.load(open(os.path.join(DATA, "index.json"), encoding="utf-8"))
    hints, cn = {}, {}
    for c in idx["counties"]:
        if c["name"] not in path:
            continue
        d = json.load(open(os.path.join(DATA, c["file"]), encoding="utf-8"))
        for r in d["races"]:
            for x in r["candidates"]:
                if x.get("name_unreadable"):
                    continue
                hints[fold(x["name"])] = x["name"]
                p = cn_part(x["name"])
                if len(p) >= 2 and p != fold(x["name"]):
                    cn.setdefault(p, set()).add(x["name"])
    for p, ns in cn.items():
        if len(ns) == 1 and p not in hints:
            hints[p] = ns.pop()
    return hints


def parse_file(args):
    src, path = args
    fn = path.replace("01選舉公報/", "").replace("/", "__")
    doc = fitz.open(os.path.join(src, fn))
    hints = name_hints(path)
    cards = []
    for p in doc:
        for c in parse_page(p, hints):
            c["page"] = p.number + 1
            cards.append(c)
    nchar = sum(len(re.sub(r"\s", "", p.get_text())) for p in doc)
    return {"path": path, "file": fn, "url": BASE + urllib.parse.quote(path), "pages": len(doc), "chars": nchar, "cards": cards}


def main():
    from multiprocessing import Pool
    src, out = sys.argv[1], sys.argv[2]
    man = [l.strip() for l in open(os.path.join(src, "manifest.txt"), encoding="utf-8") if l.strip()]
    if len(sys.argv) > 3:
        man = [m for m in man if sys.argv[3] in m]
    with Pool(8) as pool:
        res = pool.map(parse_file, [(src, m) for m in man])
    for r in res:
        print(f"{len(r['cards']):3d} {sum(1 for c in r['cards'] if 'err' in c):2d}err {r['chars']:6d}ch {r['file']}", file=sys.stderr)
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
