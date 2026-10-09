# 合併 新北市／新竹市／新竹縣 → records_council_2.json（連江縣因公開資料不完整未輸出，見 council_records_survey 補充說明）
import json
R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/'
out={}
for k,f in [('新北市','新北市/new_taipei_records.json'),('新竹縣','新竹縣/hsinchu_county_records.json'),('新竹市','新竹市/hsinchu_city_records.json')]:
    out.update(json.load(open(R+'raw/council/'+f)))
inc=json.load(open(R+'raw/council/incumbents_2.json'))
for k,v in out.items():
    assert set(v['members'])==set(inc[k]),k
    print(k,len(v['members']),'/',len(inc[k]))
json.dump(out,open(R+'records_council_2.json','w'),ensure_ascii=False,indent=1)
