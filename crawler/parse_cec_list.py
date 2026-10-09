#!/usr/bin/env python3
"""解析中選會「候選人登記彙總表」PDF（poppler pdftotext -bbox），輸出 JSON list。

用法：python3 parse_cec_list.py <pdf> <out.json>
每筆：{"area","date","name","party","note"}；area 為選舉區欄全文，換行處以 "|" 分隔（村里長＝「縣市鄉鎮市區|村里」）；page 為 PDF 頁碼。
做法：以表頭字位置切欄，以「登記日期」欄的日期當每筆錨點，其他字依 y 距離歸到最近的錨點。
"""
import json, re, subprocess, sys
from html import unescape

HEAD = ["選舉區", "登記日期", "姓名", "推薦之政黨", "備註"]
KEYS = ["area", "date", "name", "party", "note"]
DATE = re.compile(r"^1\d\d/\d\d/\d\d$")
WORD = re.compile(r'<page width|<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>')


def pages(pdf):
    html = subprocess.run(["pdftotext", "-bbox", pdf, "-"], capture_output=True, text=True, check=True).stdout
    page = None
    for m in WORD.finditer(html):
        if m.group(0).startswith("<page"):
            if page is not None:
                yield page
            page = []
        else:
            x0, y0, x1, y1 = map(float, m.group(1, 2, 3, 4))
            page.append((x0, y0, x1, y1, unescape(m.group(5))))
    if page:
        yield page


def join(ws, sep=""):
    """同一行直接接；換行處接 sep（選舉區欄用 "|" 保留「鄉鎮市區｜村里」分行）。"""
    out, last_y = "", None
    for w in sorted(ws, key=lambda w: (round(w[1]), w[0])):
        t = w[4]
        latin = out and re.match(r"[A-Za-z]", t) and re.search(r"[A-Za-z.]$", out)
        if last_y is not None and abs(w[1] - last_y) > 4:
            out += sep or (" " if latin else "")
        elif latin:
            out += " "
        out += t
        last_y = w[1]
    return out


def parse(pdf):
    rows, cols = [], None
    for pno, page in enumerate(pages(pdf), 1):
        head = {w[4]: (w[0] + w[2]) / 2 for w in page if w[4] in HEAD}
        if len(head) == 5:
            cols = [head[h] for h in HEAD]
        if cols is None:
            raise SystemExit(f"{pdf}: 找不到表頭")
        bounds = [(cols[i] + cols[i + 1]) / 2 for i in range(4)]
        head_y = max(w[3] for w in page if w[4] in HEAD) if head else 0
        col = lambda w: sum((w[0] + w[2]) / 2 > b for b in bounds)
        body = [w for w in page if w[1] > head_y and w[4] not in HEAD and "頁" not in w[4] and "製表" not in w[4]]
        anchors = sorted([w for w in body if col(w) == 1 and DATE.match(w[4])], key=lambda w: w[1])
        recs = [{k: [] for k in KEYS} for _ in anchors]
        for w in body:
            if not anchors:
                break
            yc = (w[1] + w[3]) / 2
            i = min(range(len(anchors)), key=lambda i: abs((anchors[i][1] + anchors[i][3]) / 2 - yc))
            recs[i][KEYS[col(w)]].append(w)
        for r in recs:
            row = {k: join(v, "|" if k == "area" else "") for k, v in r.items()}
            row["page"] = pno
            rows.append(row)
    return rows


if __name__ == "__main__":
    data = parse(sys.argv[1])
    json.dump(data, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(sys.argv[1], len(data))
