"""由 crawler/raw/ly/ 的立法院官方原始資料，產出 crawler/records_legislator.json。
只讀本機 raw，不連網。用法：python3 build_records.py
數字口徑見 METHOD 常數（也寫入 crawler/raw/ly/summary_counts.json 供重算比對）。
"""
import glob, json, os, re, subprocess, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
RAW = os.path.join(ROOT, 'crawler', 'raw', 'ly')
OUT = os.path.join(ROOT, 'crawler', 'records_legislator.json')
CUTOFF = '2026-10-09'  # 抓取日；各資料集當日 01:00–04:30 已更新（見 dataset 頁「更新時間」）

STANDING = ['內政委員會', '外交及國防委員會', '經濟委員會', '財政委員會', '教育及文化委員會',
            '交通委員會', '司法及法制委員會', '社會福利及衛生環境委員會']
# 第 11 屆就任日；院會出席與提案皆以此為起算
T11_START = '2024-02-01'

# 同名同人確認：候選人(縣市,姓名) -> 說明（黨籍不同或選區不同時的人工判斷依據）
# 判準：姓名完全相同＋黨籍相同（或有可由官方資料佐證的轉換）；中選會名單無身分證字號，無法更進一步。
PARTY_NOTE = {
    '高虹安': '候選人登記為無政黨推薦；官方委員資料第 10 屆黨籍為台灣民眾黨（不分區），僅以姓名比對，另無同名他人',
    '徐欣瑩': '第 8 屆黨籍為民國黨、第 11 屆為中國國民黨；同為新竹縣選區，僅以姓名＋選區比對',
    '莊競程': '第 10 屆選區為臺中市第 5 選舉區，候選人登記縣市為新竹市；官方資料經歷載交通大學助理教授，僅以姓名＋黨籍比對，無其他同名委員',
}

DS = {  # 資料集 id -> (名稱, 說明頁)
    16: '歷屆委員資料', 20: '議案提案', 14: '各委員會-委員名單資料', 45: '議事錄原始檔案',
    41: '公報原始檔案', 6: '質詢事項(本院委員質詢部分)',
}


def ds_url(i):
    return f'https://data.ly.gov.tw/getds.action?id={i}'


def ds_date(i):
    """從 raw/ly/ds{i}.html 讀「更新時間」，讀不到就用 CUTOFF"""
    p = os.path.join(RAW, f'ds{i}.html')
    if os.path.exists(p):
        s = open(p, encoding='utf8', errors='ignore').read()
        t = re.sub(r'<[^>]+>', ' ', s)
        m = re.search(r'更新時間\s*(\d{4})-(\d\d)-(\d\d)', t)
        if m:
            return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    return CUTOFF


def norm(s):
    s = re.sub(r'[\s　]', '', s)
    return s.replace('臺', '台').replace('啓', '啟')


def load_json(path):
    t = open(path, encoding='utf8').read()
    return json.loads(t[t.index('{'):])


def candidates():
    """縣市 -> [(姓名, 黨籍)]，來源 data/*.json races[0]（id mayor）"""
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', '*.json'))):
        if f.endswith('index.json'):
            continue
        d = json.load(open(f, encoding='utf8'))
        r = d['races'][0]
        assert r['id'] == 'mayor', f
        out[d['meta']['county']] = [(c['name'], c.get('party')) for c in r['candidates']]
    return out


def load_legislators():
    rows = []
    for f in sorted(glob.glob(RAW + '/id16_p*.json'), key=lambda s: int(s.split('_p')[1][:-5])):
        rows += load_json(f)['jsonList']
    return [r for r in rows if r.get('name')]


def d_slash(s):
    return s.replace('/', '-') if s else None


def committee_ranges(cstr, term):
    """ID16 的 committee 字串 -> {常設委員會: [會期...]}（僅常設）"""
    res = collections.OrderedDict()
    for part in (cstr or '').split(';'):
        m = re.match(r'第(\d+)屆第(\d+)會期：(.+)', part.strip())
        if not m or int(m.group(1)) != int(term):
            continue
        c = m.group(3).strip()
        if c in STANDING:
            res.setdefault(c, []).append(int(m.group(2)))
    return res


def fmt_ranges(nums):
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(f'{nums[i]}' if i == j else f'{nums[i]}–{nums[j]}')
        i = j + 1
    return '、'.join(out)


# ---------------- 議案提案 ----------------
def split_names(s):
    toks = [t for t in re.split('　　', s or '') if t.strip()]
    return [norm(t) for t in toks]


def name_in(name, toks):
    n = norm(name)
    for t in toks:
        if t == n or (t.startswith(n) and re.match(r'[A-Za-z]', t[len(n):len(n) + 1] or '0')):
            return True
    return False


def is_law_bill(b):
    nm = b['billName']
    return ('草案' in nm) or nm.startswith('廢止「')


def bills():
    d = load_json(RAW + '/id20_term11.json')['dataList']
    by = {}
    for x in d:
        by.setdefault(x['billNo'], x)  # 同一議案編號可能在多個會次重複列出，去重
    return list(by.values()), len(d)


# ---------------- 書面質詢 ----------------
Q_ITEM = re.compile(r'^（([一二三四五六七八九十百]+)）本院(.+?)委員(.+?)[，,]')


def doc_text(path):
    out = path + '.txt'
    if not os.path.exists(out):
        # textutil 依內容判斷格式，副檔名需正確
        tmp = path + ('.docx' if open(path, 'rb').read(2) == b'PK' else '.doc')
        os.symlink(path, tmp) if not os.path.exists(tmp) else None
        subprocess.run(['textutil', '-convert', 'txt', tmp, '-output', out], check=True, capture_output=True)
        os.unlink(tmp)
    return open(out, encoding='utf8', errors='ignore').read()


def _qkey(name, line):
    """去重鍵：質詢人全名 + 「委員名，」之後的案由前 30 字（兩個資料集的措辭前段相同）"""
    after = line.split('，', 1)[1] if '，' in line else line
    return (name, norm(after)[:30])


def questions():
    """回傳 [(會期,會次,姓名,來源)]。來源兩種互補：
    (a) 公報「質詢事項」之「本院委員質詢部分」doc（ID41）；(b) 議事日程「質詢事項(本院委員質詢部分)」（ID6）。
    以 (質詢人, 案由前 30 字) 去重後計數。"""
    rows = []
    for f in sorted(glob.glob(RAW + '/id41_p*.json'), key=lambda s: int(s.split('_p')[1][:-5])):
        rows += load_json(f)['jsonList']
    docs = [r for r in rows if r['term'] == '11' and r['agendaType'] == '4' and '本院委員質詢部分' in r['subject']]
    items = {}
    for r in docs:
        p = os.path.join(RAW, 'questions', os.path.basename(r['docUrl']))
        if not os.path.exists(p):
            continue
        for line in doc_text(p).split('\n'):
            line = line.strip()
            m = Q_ITEM.match(line)
            if not m:
                continue
            name = norm(m.group(2) + m.group(3))
            items.setdefault(_qkey(name, line), (r['sessionPeriod'], r['sessionTimes'], name, 'ID41'))
    n41 = len(items)
    q6 = re.compile(r'^[一二三四五六七八九十百]+、本院(.+?)委員(.+?)[，,]')
    for x in load_json(RAW + '/id6_term11.json')['dataList']:
        line = x['item'].strip()
        m = q6.match(line)
        if not m:
            continue
        name = norm(m.group(1) + m.group(2))
        items.setdefault(_qkey(name, line), (x['sessionPeriod'], x['sessionTimes'], name, 'ID6'))
    return list(items.values()), docs, n41


# ---------------- 院會出席 ----------------
def minutes():
    """回傳 [(會期,會次,日期ISO,出席名單set)]，來自 ID45 院會議事錄（sessionType=02）"""
    out = []
    for p in sorted(glob.glob(RAW + '/minutes/*.docx')):
        txt = doc_text(p)
        lines = txt.split('\n')
        title = next((l for l in lines[:3] if '議事錄' in l and '第' in l), '')
        mt = re.search(r'第(\d+)屆第(\d+)會期第(\d+)次', title)
        tm = next((l for l in lines[:6] if l.startswith('時')), '')
        md = re.search(r'民國\s*(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日', tm)
        date = f'{int(md.group(1)) + 1911}-{int(md.group(2)):02d}-{int(md.group(3)):02d}' if md else None
        att = None
        for l in lines:
            if l.startswith('出席委員'):
                att = set(norm(t) for t in re.split(r'[　]{2,}', l[4:].strip()) if t.strip())
                break
        out.append(dict(file=os.path.basename(p), title=title.strip(), date=date, att=att,
                        sess=(mt.group(2), mt.group(3)) if mt else None))
    return out


def main():
    cand = candidates()
    legs = load_legislators()
    by_name = collections.defaultdict(list)
    for r in legs:
        by_name[norm(r['name'])].append(r)

    matches = {}  # (縣市, 姓名) -> rows
    for cty, lst in cand.items():
        for n, party in lst:
            hit = by_name.get(norm(n))
            if hit:
                matches[(cty, n)] = (party, hit)

    bl, bl_rows = bills()
    qs, qdocs, n41 = questions()
    mins = minutes()
    print('候選人比對到立委:', len(matches), '議案(去重)', len(bl), '原列', bl_rows, '質詢項', len(qs), '(其中ID41', n41, ')', '議事錄', len(mins))

    result = {}
    audit = {}
    for (cty, n), (party, hit) in sorted(matches.items()):
        hit = sorted(hit, key=lambda r: int(r['term']))
        terms = [int(r['term']) for r in hit]
        rec = []
        src16 = dict(src_title='立法院資料開放平台「歷屆委員資料」（資料集 ID16）', src_url=ds_url(16), src_date=ds_date(16))

        # 11 屆以外
        for r in hit:
            t = int(r['term'])
            if t == 11:
                continue
            area = r['areaName']
            start = d_slash(r['onboardDate'])
            txt = f'第{t}屆立法委員（{area}），{start} 起'
            if r.get('leaveDate'):
                txt += f'，{d_slash(r["leaveDate"])} {r.get("leaveReason") or "離職"}'
            cr = committee_ranges(r.get('committee'), t)
            if cr:
                txt += '；所屬常設委員會：' + '、'.join(f'{c}（第{fmt_ranges(s)}會期）' for c, s in cr.items())
            rec.append(dict(text=txt, **src16))

        cnt = {}
        if 11 in terms:
            r = [x for x in hit if int(x['term']) == 11][0]
            area = r['areaName']
            start = d_slash(r['onboardDate'])
            leave = d_slash(r.get('leaveDate')) if r.get('leaveFlag') == '是' else None
            head = f'第11屆立法委員（{area}），{start} 起'
            if leave:
                head += f'，{leave} {r.get("leaveReason") or "離職"}'
            else:
                head += f'，截至 {CUTOFF} 仍在任（官方資料離職欄無日期）'
            rec.append(dict(text=head, **src16))

            end = leave or CUTOFF
            # 提案
            mine_p = [b for b in bl if is_law_bill(b) and name_in(n, split_names(b['billProposer']))]
            mine_c = [b for b in bl if is_law_bill(b) and name_in(n, split_names(b['billCosignatory']))]
            all_p = [b for b in bl if name_in(n, split_names(b['billProposer']))]
            src20 = dict(src_title='立法院資料開放平台「議案提案」（資料集 ID20，第 11 屆）', src_url=ds_url(20), src_date=ds_date(20))
            txt = (f'第11屆議案提案（{start} 起至 {end}，資料集更新於 {ds_date(20)}）：'
                   f'列名於「提案人」欄之法律案 {len(mine_p)} 件；列名於「連署人」欄之法律案 {len(mine_c)} 件'
                   f'（同一議案編號只計 1 件；不含黨團提案、政府提案）')
            rec.append(dict(text=txt, **src20))
            cnt['law_proposer'] = len(mine_p); cnt['law_cosign'] = len(mine_c); cnt['bills_proposer_all'] = len(all_p)

            # 書面質詢
            nn = norm(n)
            mq = [q for q in qs if q[2] == nn or (q[2].startswith(nn) and re.match(r'[A-Za-z]', q[2][len(nn):len(nn) + 1] or '0'))]
            sess_cov = sorted({q[0] for q in qs})
            rec.append(dict(
                text=(f'第11屆書面質詢：公報「質詢事項」及議事日程「質詢事項」之「本院委員質詢部分」載明該委員為質詢人者 {len(mq)} 項'
                      f'（已去除兩資料集重複列載；涵蓋第 {",".join(str(int(s)) for s in sess_cov)} 會期，第 6 會期尚無資料）'),
                src_title='立法院資料開放平台「公報原始檔案」（資料集 ID41，質詢事項）、「質詢事項(本院委員質詢部分)」（資料集 ID6）',
                src_url=ds_url(41), src_date=ds_date(41)))
            cnt['written_q'] = len(mq)

            # 委員會（ID14）
            p14 = os.path.join(RAW, f'id14_{n}.json')
            c11, chair = collections.OrderedDict(), []
            if os.path.exists(p14):
                for x in load_json(p14)['dataList']:
                    if int(x['term']) != 11 or norm(x['name']) != nn:
                        continue
                    s = int(x['sessionPeriod'])
                    if x['committee'] in STANDING:
                        c11.setdefault(x['committee'], []).append(s)
                    if x['isCoChairman'] == 'Y':
                        chair.append((s, x['committee']))
            if c11:
                txt = '第11屆所屬常設委員會：' + '、'.join(f'{c}（第{fmt_ranges(s)}會期）' for c, s in c11.items())
                if chair:
                    chair.sort()
                    g = collections.OrderedDict()
                    for s, c in chair:
                        g.setdefault(c, []).append(s)
                    txt += '；擔任召集委員：' + '、'.join(f'{c}（第{fmt_ranges(s)}會期）' for c, s in g.items())
                else:
                    txt += '；官方名單無召集委員紀錄'
                rec.append(dict(text=txt, src_title='立法院資料開放平台「各委員會-委員名單資料」（資料集 ID14）',
                                src_url=ds_url(14), src_date=ds_date(14)))
            cnt['committees'] = {c: s for c, s in c11.items()}; cnt['chair'] = chair

            # 院會出席
            den = [m for m in mins if m['date'] and m['att'] is not None and start <= m['date'] <= end]
            att = [m for m in den if (nn in m['att']) or any(a.startswith(nn) and re.match(r'[A-Za-z]', a[len(nn):len(nn)+1] or '0') for a in m['att'])]
            if den:
                pct = round(100 * len(att) / len(den), 1)
                rec.append(dict(
                    text=(f'第11屆院會出席：已公布議事錄之院會會次中，在任期間共 {len(den)} 次、議事錄「出席委員」名單列名 {len(att)} 次'
                          f'（{pct}%）；僅反映議事錄簽到名單，未列名者之原因（請假等）議事錄未逐一載明'),
                    src_title='立法院資料開放平台「議事錄原始檔案」（資料集 ID45，院會議事錄）',
                    src_url=ds_url(45), src_date=ds_date(45)))
            cnt['att_den'] = len(den); cnt['att_num'] = len(att)

        # 比對說明
        if n in PARTY_NOTE:
            rec.append(dict(text='同名比對說明：' + PARTY_NOTE[n], **src16))
        result.setdefault(cty, {})[n] = dict(record=rec, cutoff=CUTOFF)
        audit[f'{cty}/{n}'] = dict(terms=terms, party_cand=party, party_ly=[x['party'] for x in hit], **cnt)

    json.dump(result, open(OUT, 'w', encoding='utf8'), ensure_ascii=False, indent=2)
    json.dump(audit, open(os.path.join(RAW, 'summary_counts.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=2)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
