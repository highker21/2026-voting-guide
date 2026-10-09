"""抓取立法院官方開放資料（data.ly.gov.tw）與院會議事錄，存 crawler/raw/ly/。
已存在的檔案會略過（重跑只補缺）。每次請求間隔 >= 1 秒。
"""
import json, os, sys, urllib.parse
from lyfetch import get, load_json, RAW

B = 'https://data.ly.gov.tw/odw/'
TERM = '11'


def fetch_lists():
    # ID16 歷屆委員資料（分頁，每頁 1000）
    p = 1
    while True:
        f = get(B + f'openDatasetJson.action?id=16&selectTerm=all&page={p}', RAW + f'/id16_p{p}.json')
        if not load_json(f)['jsonList']:
            os.remove(f); break
        p += 1
    # ID20 議案提案、ID6 質詢事項(本院委員)、ID1 質詢(行政院答復)、ID45 議事錄原始檔案：第 11 屆
    get(B + f'ID20Action.action?term={TERM}&sessionPeriod=&sessionTimes=&meetingTimes=&billName=&billOrg=&billProposer=&billCosignatory=&fileType=json', RAW + '/id20_term11.json')
    get(B + f'ID6Action.action?term={TERM}&sessionPeriod=&sessionTimes=&item=&fileType=json', RAW + '/id6_term11.json')
    get(B + f'ID1Action.action?term={TERM}&sessionPeriod=&sessionTimes=&item=&fileType=json', RAW + '/id1_term11.json')
    get(B + f'ID45Action.action?term={TERM}&sessionPeriod=&sessionTimes=&meetingTimes=&sessionType=&fileType=json', RAW + '/id45_term11.json')
    # ID41 公報原始檔案（分頁），用以找「質詢事項」(agendaType=4) 公報
    p = 1
    while True:
        f = get(B + f'openDatasetJson.action?id=41&selectTerm=all&page={p}', RAW + f'/id41_p{p}.json')
        if not load_json(f)['jsonList']:
            os.remove(f); break
        p += 1


def fetch_committees(names):
    for n in names:
        get(B + 'ID14Action.action?committee=&name=' + urllib.parse.quote(n) + '&fileType=json', RAW + f'/id14_{n}.json')


def fetch_minutes():
    d = load_json(RAW + '/id45_term11.json')['dataList']
    for x in d:
        if x['sessionType'] != '02':  # 02 = 常會/臨時會院會議事錄
            continue
        name = f"{x['term']}-{x['sessionPeriod']}-{x['sessionTimes']}-{x['meetingTimes']}.docx"
        get(x['docUrl'], RAW + '/minutes/' + name, referer='https://ppg.ly.gov.tw/', binary_ok=True)


def fetch_meta():
    for i in (6, 14, 16, 20, 41, 45):
        get(f'https://data.ly.gov.tw/getds.action?id={i}', RAW + f'/ds{i}.html')


def fetch_questions():
    # 公報「質詢事項」中「本院委員質詢部分」(書面質詢清單) 的 doc
    import glob
    rows = []
    for f in sorted(glob.glob(RAW + '/id41_p*.json'), key=lambda s: int(s.split('_p')[1][:-5])):
        rows += load_json(f)['jsonList']
    for r in rows:
        if r['term'] == TERM and r['agendaType'] == '4' and '本院委員質詢部分' in r['subject']:
            name = os.path.basename(r['docUrl'])
            get(r['docUrl'], RAW + '/questions/' + name, referer='https://ppg.ly.gov.tw/', binary_ok=True)


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'lists'
    if what == 'lists': fetch_lists()
    elif what == 'committees': fetch_committees(sys.argv[2:])
    elif what == 'minutes': fetch_minutes()
    elif what == 'questions': fetch_questions()
    elif what == 'meta': fetch_meta()
