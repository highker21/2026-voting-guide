"""合併各縣市 records → crawler/records_council.json。資料截止日：2026-10-09（爬取日）。"""
import json
Rt='/Users/highker/claudecode/repos/2026-voting-guide/crawler/'
C=Rt+'raw/council/'
def L(p): return json.load(open(C+p))
cut='2026-10-09'
out={
 '高雄市':{'src_title':'高雄市議會議事資訊整合查詢系統（提案資料、議員市政總質詢）；提案數為系統列名之提案議員計，議長依規定不提市政總質詢',
   'src_url':'https://cissearch.kcc.gov.tw/System/Proposal/Default.aspx','period':'第4屆（2022-12-25～%s）；第8次定期大會進行中'%cut,'members':L('高雄市/kaohsiung_records.json')},
 '臺北市':{'src_title':'臺北市議會議案進階查詢系統（案號14開頭、提案者含該議員之議案；議員提案與市法規案）',
   'src_url':'https://ifddoc2.tcc.gov.tw/TCCMIS_Front/Adv_SearchInput.aspx','period':'第14屆（2022-12-25～%s）'%cut,'members':L('臺北市/taipei_records.json')},
 '臺中市':{'src_title':'臺中市議會議事資訊系統（議案查詢；提案人含共同提案、連署另計）',
   'src_url':'https://yishi.tccc.gov.tw/proposals','period':'第4屆（2022-12-25～%s）'%cut,'members':L('臺中市/taichung_records.json')},
 '臺南市':{'src_title':'臺南市議會議案查詢（議員提案、臨時動議；提案人含共同提案）',
   'src_url':'https://www.tncc.gov.tw/motion1.asp','period':'第4屆（2022-12-25～%s）'%cut,'members':L('臺南市/tainan_records.json')},
 '基隆市':{'src_title':'基隆市議會議案查詢（提案人含共同提案、連署另計；定期會/臨時會依會議種類區分）',
   'src_url':'https://www.kmc.gov.tw/kmcweb/#/motion','period':'第20屆（2022-12-25～%s）'%cut,'members':L('基隆市/keelung_records.json')},
}
json.dump(out,open(Rt+'records_council.json','w'),ensure_ascii=False,indent=1)
inc=L('incumbents.json')
for k,v in out.items(): print(k,len(v['members']),'/',len(inc[k]), set(inc[k])-set(v['members']))
