#!/usr/bin/env python3
"""依 OCR 交叉核對結果，決定每位候選人哪些欄位的公報文字可以轉載，輸出 build_data 讀的 bulletin_115.json。

規則：
- 欄位文字層與 OCR 相似度 ≥ 0.85，且 OCR 字數沒有明顯多於文字層（≤ 1.25 倍 + 10 字，否則代表有些行只有外框、沒抓到）→ 轉載。
- 不符合 → 不轉載該欄，前端改顯示「請見公報原檔」。
- 政見格有 30% 以上面積是圖片 → 標示「以圖片刊登」。
- 找不到卡片的候選人（掃描檔、外框字）→ 列出所屬選區的公報檔連結。
- 出生年月日、性別、出生地一律不收（parse 階段已排除，這裡再檢查一次）。

用法：python3 finalize_bulletin.py <ocr_check 輸出> <parse 輸出> <輸出 bulletin_115.json>
"""
import json, os, re, sys, urllib.parse
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from match_bulletin import districts_of

DATA = os.path.join(HERE, "..", "data")
PUA = re.compile(r"[\ue000-\uf8ff]")
PUA_DECOR = re.compile(r"^[\ue000-\uf8ff]+\s*|[\ue000-\uf8ff]+(?=\s*[｜|])")
BIRTH = re.compile(r"出生年月日|出生地[:：]|生日[:：]|性別[:：]")


def ok_field(o):
    if not o:
        return True, "no-ocr"
    if o.get("err"):
        return True, "ocr-err"
    if o["len_text"] <= 3:   # 「無」之類的短字，OCR 常讀不到
        return True, "ok"
    good = o["ratio"] >= 0.85 and o["len_ocr"] <= 1.25 * o["len_text"] + 10
    return good, "ok" if good else f"ratio={o['ratio']} text={o['len_text']} ocr={o['len_ocr']}"


def main():
    m = json.load(open(sys.argv[1], encoding="utf-8"))
    parsed = json.load(open(sys.argv[2], encoding="utf-8"))
    pages = {f["file"]: f["pages"] for f in parsed}
    out = {"cards": {}, "files": {}, "stats": {}}
    why = Counter()
    rejected = []
    for key, c in m["cards"].items():
        ok, img = {}, {}
        for field in ("edu", "exp", "platform"):
            # 私用區字元：在行首或「｜」前多半是裝飾符號，拿掉；夾在文字中間（例如數字用私用字型）就整欄不轉載
            c[field] = [x for x in (PUA_DECOR.sub("", t).strip() for t in c.get(field, [])) if x]
            g, reason = ok_field(c.get("ocr", {}).get(field)) if c.get(field) else (True, "empty")
            if g and any(PUA.search(t) for t in c[field]):
                g, reason = False, "PUA 字元（字型私用區，無法確定原字）"
            ok[field] = g
            why[(field, reason if reason in ("ok", "no-ocr", "ocr-err", "empty") else "rejected")] += 1
            if not g:
                rejected.append([key, field, reason])
            for t in c.get(field, []):
                if BIRTH.search(t):
                    raise SystemExit(f"含出生資料：{key} {field} {t}")
        img["platform"] = c.get("platform_img", 0) > 0.3
        img["edu"] = c.get("edu_img", 0) > 0.5 and not c.get("edu")
        img["exp"] = c.get("exp_img", 0) > 0.5 and not c.get("exp")
        fname = urllib.parse.unquote(c["url"]).split("/")[-1]
        out["cards"][key] = {"url": c["url"], "fname": fname, "page": c["page"], "pages": pages.get(c["file"], 1),
                             "num": c.get("num"), "name_text": c.get("name_text"), "match": c.get("match"),
                             "edu": c.get("edu", []), "exp": c.get("exp", []), "platform": c.get("platform", []),
                             "ok": ok, "img": img}
    # 沒有卡片的候選人：給所屬選區的公報檔
    idx = json.load(open(os.path.join(DATA, "index.json"), encoding="utf-8"))
    for cty in idx["counties"]:
        d = json.load(open(os.path.join(DATA, cty["file"]), encoding="utf-8"))
        for r in d["races"]:
            missing = [x for x in r["candidates"] if f"{cty['name']}|{r['id']}|{x['id']}" not in out["cards"]]
            if not missing:
                continue
            fl = []
            for f in parsed:
                if cty["name"] not in f["path"] or f["chars"] < 0 or "公版" in f["path"] or "投開票所" in f["path"]:
                    continue
                is_mayor_file = "議員" not in f["path"]
                if r["id"] == "mayor" and is_mayor_file:
                    fl.append(f)
                elif r["id"] != "mayor" and not is_mayor_file and int(r["id"].split("-")[1]) in districts_of(f["path"]):
                    fl.append(f)
            if fl:
                out["files"][f"{cty['name']}|{r['id']}"] = [{"url": f["url"], "name": urllib.parse.unquote(f["url"]).split("/")[-1]} for f in fl]
    out["stats"] = {"cards": len(out["cards"]), "fields": {f"{a}:{b}": n for (a, b), n in sorted(why.items())},
                    "rejected": rejected, "missing_with_file": sorted(out["files"]),
                    "partial_name": [[k, v["name_text"]] for k, v in out["cards"].items() if v["match"] != "name"]}
    json.dump(out, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out["stats"].items() if k != "rejected"}, ensure_ascii=False, indent=1))
    print("rejected", len(rejected))


if __name__ == "__main__":
    main()
