#!/usr/bin/env python3
"""選舉公報文字層 × 影像 OCR 交叉核對。

有些公報 PDF 的字型對照表有誤（例如畫面是「瑋」，文字層卻是「璋」），或部分行只有外框沒有文字。
這支把每張卡片的學歷／經歷／政見格子轉成影像，用 macOS Vision OCR 讀一次，和文字層比對，
記下相似度與不一致的片段，供 build 時決定要不要採用該格文字。

用法：python3 ocr_check_bulletin.py <PDF 目錄> <parse_bulletin 輸出 json> <輸出 json>
"""
import difflib, fitz, json, os, re, subprocess, sys, tempfile, unicodedata
from concurrent.futures import ThreadPoolExecutor

OCR = os.path.expanduser("~/claudecode/scripts/vision_ocr")
PUNCT = re.compile(r"[\s\W_]+", re.U)


def norm(t):
    t = unicodedata.normalize("NFKC", t)
    return PUNCT.sub("", t)


def ocr_rect(pdf, page, rect, tmpdir, tag):
    doc = fitz.open(pdf)
    pix = doc[page - 1].get_pixmap(clip=fitz.Rect(rect), dpi=220)
    png = os.path.join(tmpdir, tag + ".png")
    pix.save(png)
    out = subprocess.run([OCR, png, "--json"], capture_output=True, text=True, timeout=120).stdout
    os.remove(png)
    rows = [json.loads(l) for l in out.splitlines() if l.strip().startswith("{")]
    # Vision 座標左下為原點：由上而下、由左而右
    rows.sort(key=lambda r: (-round(r["bbox"]["y"] + r["bbox"]["h"], 2), r["bbox"]["x"]))
    return "\n".join(r["text"] for r in rows)


def compare(a, b):
    na, nb = norm(a), norm(b)
    sm = difflib.SequenceMatcher(None, na, nb, autojunk=False)
    diffs = [(na[i1:i2], nb[j1:j2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
    return round(sm.ratio(), 3), diffs, len(na), len(nb)


def main():
    src, inp, out = sys.argv[1:4]
    res = json.load(open(inp, encoding="utf-8"))
    cards = res["cards"]
    # 第 4 個參數：上一次的輸出；同檔、同頁、同格子、同文字的結果直接沿用
    cache = {}
    if len(sys.argv) > 4:
        for c in json.load(open(sys.argv[4], encoding="utf-8"))["cards"].values():
            for i, field in enumerate(("edu", "exp", "platform")):
                o = c.get("ocr", {}).get(field)
                if o and not o.get("err"):
                    cache[(c["file"], c["page"], tuple(c["rects"][i]), "".join(c[field]))] = o
    jobs = []
    for key, c in cards.items():
        for i, field in enumerate(("edu", "exp", "platform")):
            if c.get(field):
                hit = cache.get((c["file"], c["page"], tuple(c["rects"][i]), "".join(c[field])))
                if hit:
                    c.setdefault("ocr", {})[field] = hit
                    continue
                jobs.append((key, c["file"], c["page"], c["rects"][i], str(len(jobs)), field))
    print("OCR jobs", len(jobs), file=sys.stderr, flush=True)
    tmp = tempfile.mkdtemp()

    def run(j):
        key, fn, page, rect, tag, field = j
        for attempt in range(3):
            try:
                t = ocr_rect(os.path.join(src, fn), page, rect, tmp, tag)
                if t is not None:
                    return j, t
            except Exception:
                pass
        return j, None

    with ThreadPoolExecutor(6) as ex:
        for n, (j, text) in enumerate(ex.map(run, jobs), 1):
            key, fn, page, rect, tag, field = j
            c = cards[key]
            if text is None:
                c.setdefault("ocr", {})[field] = {"err": True}
                continue
            ratio, diffs, la, lb = compare("".join(c[field]), text)
            c.setdefault("ocr", {})[field] = {"ratio": ratio, "diffs": diffs[:40], "len_text": la, "len_ocr": lb}
            if n % 500 == 0:
                print(n, "/", len(jobs), file=sys.stderr, flush=True)
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
