"""全台村里清單（內政部戶政司 ODRP010 115/09）＋罕用字（造字 PUA）對應。"""
import json, os, unicodedata

# 戶政司開放資料用造字區（PUA）表示的罕用字 → Unicode 標準字
PUA = {"\U000fffa8": "磘", "\U000fffb5": "獇", "\U000fb56f": "塭", "\U000fffc0": "萡", "\U000fcc79": "嵵"}


def fix(s):
    """造字區換成標準字；CJK 相容表意字（如 U+2F8EB）以 NFC 正規化成統一字（檨），否則部分字型顯示不出來。"""
    for k, v in PUA.items():
        s = s.replace(k, v)
    return unicodedata.normalize("NFC", s)


def load():
    here = os.path.dirname(os.path.abspath(__file__))
    vl = json.load(open(os.path.join(here, "raw/ris_villages_11509.json"), encoding="utf-8"))
    return [{"code": v["code"], "county": v["town"][:3], "town": fix(v["town"][3:]), "village": fix(v["village"])} for v in vl]
