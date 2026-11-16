#!/usr/bin/env python3
"""公報是圖檔（或號次為外框字）的縣市：整頁 OCR，找「號次數字＋正下方姓名」，只用來「確認」本站既有號次。

輸出 {縣市|選舉 id|候選人 id: {num, url, page}}，只收 OCR 號次與本站號次一致者；不一致者另列，交人工核對，不自動改。
用法：python3 ocr_numbers_bulletin.py <PDF 目錄> <parse 輸出> <bulletin_115.json> <輸出 json>
"""
import fitz, json, os, re, subprocess, sys, tempfile, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from parse_bulletin import fold, cn_part
from match_bulletin import districts_of
OCR = os.path.expanduser("~/claudecode/scripts/vision_ocr")
DATA = os.path.join(HERE, "..", "data")


def page_ocr(pdf, pno, tmp):
    pix = fitz.open(pdf)[pno].get_pixmap(dpi=150)
    png = os.path.join(tmp, "p.png"); pix.save(png)
    out = subprocess.run([OCR, png, "--json"], capture_output=True, text=True, timeout=300).stdout
    return [json.loads(l) for l in out.splitlines() if l.strip().startswith("{")]


def main():
    src, parsed_p, bul_p, out_p = sys.argv[1:5]
    parsed = json.load(open(parsed_p, encoding="utf-8"))
    bul = json.load(open(bul_p, encoding="utf-8"))
    idx = json.load(open(os.path.join(DATA, "index.json"), encoding="utf-8"))
    tmp = tempfile.mkdtemp()
    ok, bad = {}, []
    for cty in idx["counties"]:
        d = json.load(open(os.path.join(DATA, cty["file"]), encoding="utf-8"))
        need = [(r["id"], x) for r in d["races"] for x in r["candidates"]
                if f"{cty['name']}|{r['id']}|{x['id']}" not in bul["cards"] and x.get("number") is not None]
        if not need:
            continue
        for f in parsed:
            if cty["name"] not in f["path"]:
                continue
            is_mayor = "議員" not in f["path"]
            dists = districts_of(f["path"])
            pool = [(rid, x) for rid, x in need if (rid == "mayor") == is_mayor and (rid == "mayor" or not dists or int(rid.split("-")[1]) in dists)]
            if not pool:
                continue
            for pno in range(f["pages"]):
                rows = page_ocr(os.path.join(src, f["file"]), pno, tmp)
                for rid, x in pool:
                    key = f"{cty['name']}|{rid}|{x['id']}"
                    if key in ok:
                        continue
                    target = cn_part(x["name"]) or fold(x["name"])
                    for o in rows:
                        if fold(o["text"]) != target:
                            continue
                        b = o["bbox"]; cx = b["x"] + b["w"] / 2; top = b["y"] + b["h"]
                        digs = [r for r in rows if re.fullmatch(r"\d{1,2}", r["text"].strip())
                                and abs(r["bbox"]["x"] + r["bbox"]["w"] / 2 - cx) < 0.05 and 0 <= r["bbox"]["y"] - top < 0.06]
                        if len(digs) == 1:
                            n = int(digs[0]["text"])
                            rec = {"num": n, "url": f["url"], "page": pno + 1, "fname": urllib.parse.unquote(f["url"]).split("/")[-1]}
                            if n == x["number"]:
                                ok[key] = rec
                            else:
                                bad.append([key, x["name"], x["number"], rec])
                        break
    json.dump({"confirmed": ok, "mismatch": bad}, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("confirmed", len(ok), "mismatch", len(bad))
    for b in bad:
        print(b)


if __name__ == "__main__":
    main()
