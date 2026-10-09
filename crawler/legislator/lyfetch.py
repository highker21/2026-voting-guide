"""立法院官方資料抓取共用函式：curl + 重試，請求間隔 >= 1 秒，原始檔存 crawler/raw/ly/。"""
import json, os, re, subprocess, time

RAW = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'raw', 'ly'))
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'
_last = [0.0]


def _wait():
    d = time.time() - _last[0]
    if d < 1.1:
        time.sleep(1.1 - d)
    _last[0] = time.time()


def get(url, out, tries=5, referer=None, binary_ok=False):
    """下載 url 到 out（已存在且非空則略過）。回傳 out。"""
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    for i in range(tries):
        _wait()
        cmd = ['curl', '-sS', '-L', '-m', '180', '-A', UA, '-o', out + '.part', '-w', '%{http_code}']
        if referer:
            cmd += ['-e', referer]
        cmd.append(url)
        r = subprocess.run(cmd, capture_output=True, text=True)
        ok = r.stdout.strip() == '200' and os.path.exists(out + '.part') and os.path.getsize(out + '.part') > 0
        if ok:
            head = open(out + '.part', 'rb').read(400)
            if (not binary_ok) and (b'\xe7\xb3\xbb\xe7\xb5\xb1\xe7\xb6\xad\xe8\xad\xb7\xe4\xb8\xad' in open(out + '.part', 'rb').read()):
                ok = False  # 「系統維護中」頁
            if binary_ok and head.lstrip().lower().startswith((b'<!doctype html', b'<html')):
                ok = False  # 被導回首頁
        if ok:
            os.replace(out + '.part', out)
            return out
        time.sleep(3 * (i + 1))
    raise RuntimeError('下載失敗: ' + url)


def load_json(path):
    t = open(path, encoding='utf8').read()
    return json.loads(t[t.index('{'):])
