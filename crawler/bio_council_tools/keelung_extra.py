import urllib.parse,json,os
EXTRA={}
def add(name,items,note=''): EXTRA[name]={'items':items,'note':note}
def U(d,f): return 'https://bulletin.cec.gov.tw/'+urllib.parse.quote(f'01選舉公報/06縣市議員/111年/20基隆市/第{d}選舉區/基隆市選舉公報_第{f}選區.pdf')
def S(d,f,dist): return ('official',f'中選會 基隆市議會第20屆議員選舉公報 {dist}（2022）',U(d,f),'2022-11-26')
s2=S('2','二','第2選區'); s4=S('4','四','第4選區'); s5=S('5','五','第5選區'); s6=S('6','六','第6選區')
add('李嘉濠',[('國立東華大學課程設計與潛能開發學系科學教育研究所理學碩士',)+s2,('學生會長、畢聯會長、學聯會理事長',)+s2,('管理顧問10年資歷',)+s2,('台灣人工智慧學校校友',)+s2])
add('莊敬聖',[('國立臺灣海洋大學航運管理碩士',)+s4,('基隆市議會第19屆市議員',)+s4,('基隆市中山社區發展協會理事長',)+s4,('基隆市救國團中山區團委會諮詢委員',)+s4])
add('劉韋巡',[('美國林肯大學商業管理學系碩士',)+s5,('台灣民眾黨安樂區主任；台灣民眾黨第一屆黨代表',)+s5,('立法委員邱臣遠服務處秘書',)+s5,('基隆市棒球委員會主任委員',)+s5],'2022年公報登記推薦政黨為台灣民眾黨')
add('莫璦緁',[('美國奧克拉荷馬大學畢業',)+s6,('臺東縣議會議政諮詢委員',)+s6,('全國報系暖暖分社社長兼記者',)+s6,('美國美中企業家商會台灣分會會長',)+s6,('臺灣國立海洋大學輪機工程學系博士班',)+s6])
add('拔耐',[('醒吾科技大學行銷與流通管理系畢業；同校行銷與流通系碩士在職專班研究生',)+s4,('基隆市議員王醒之辦公室主任',)+s4,('基隆市原住民族部落大學講師',)+s4,('勞動部勞資爭議獨任調解人',)+s4])
# 合併 subagent 新聞蒐集結果
_p='/private/tmp/claude-501/-Users-highker-claudecode/448a02b8-57b3-449e-a12d-74a66c9bd512/scratchpad/keelung_news.json'
if os.path.exists(_p):
    import re
    for n,v in json.load(open(_p)).items():
        k=re.sub(r'[A-Za-z．\.].*','',n)
        if k in EXTRA: continue
        EXTRA[k]={'items':[tuple(i) for i in v['items']],'note':v.get('note','')}
