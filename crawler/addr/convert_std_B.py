"""各縣市門牌原始檔 → 統一 UTF-8 CSV（鄉鎮市區代碼,村里,街路段,地區,巷,弄,號）"""
import csv, json, re, sys, unicodedata, glob
STD = ["鄉鎮市區代碼", "村里", "街路段", "地區", "巷", "弄", "號"]
ROAD = ["街、路段", "街路段", "街或路段", "街_路段"]
def pick(r, keys):
    for k in keys:
        if k in r: return r[k] or ""
    raise KeyError(keys)
def std(r):
    no = pick(r, ["號"])
    no = re.sub(r"I-", "號", no)                     # 新竹縣：「號」在 Big5 轉出成「I-」
    return {"鄉鎮市區代碼": str(r["鄉鎮市區代碼"]), "村里": r["村里"] or "", "街路段": pick(r, ROAD),
            "地區": r.get("地區") or "", "巷": re.sub(r"G-", "巷", r.get("巷") or ""),
            "弄": re.sub(r"H-", "弄", r.get("弄") or ""), "號": no}   # 新竹縣：巷→G-、弄→H-
ADDR = re.compile(r"^(?P<road>.*?)(?P<lane>\d+巷)?(?P<alley>\d+弄)?(?P<no>[臨]?\d+(之\d+)*號.*)$")
def split_addr(a):
    s = unicodedata.normalize("NFKC", a or "").replace(" ", "")
    m = ADDR.match(s)
    if not m: return None
    return m["road"], m["lane"] or "", m["alley"] or "", m["no"]
def rows(code, files):
    for f in files:
        if f.endswith(".json"):
            yield from json.load(open(f, encoding="utf-8-sig"))
        elif f.endswith(".xlsx"):
            import openpyxl
            ws = openpyxl.load_workbook(f, read_only=True).active
            it = ws.iter_rows(values_only=True); h = [str(x) for x in next(it)]
            for v in it: yield {k: ("" if x is None else str(x)) for k, x in zip(h, v)}
        else:
            raw = open(f, "rb").read()
            try: txt = raw.decode("utf-8-sig")
            except UnicodeDecodeError: txt = raw.decode("cp950", errors="replace")
            yield from csv.DictReader(txt.splitlines())
code, out, files = sys.argv[1], sys.argv[2], sorted(sys.argv[3:])
n = bad = 0
with open(out, "w", encoding="utf-8", newline="") as fo:
    w = csv.DictWriter(fo, STD); w.writeheader()
    for r in rows(code, files):
        n += 1
        if "地址" in r:
            p = split_addr(r["地址"])
            if not p: bad += 1; continue
            d = {"鄉鎮市區代碼": r["鄉鎮市區代碼"], "村里": r["村里"], "街路段": p[0], "地區": "", "巷": p[1], "弄": p[2], "號": p[3]}
        else:
            d = std(r)
        w.writerow(d)
print(code, "rows", n, "unparsed", bad, file=sys.stderr)
