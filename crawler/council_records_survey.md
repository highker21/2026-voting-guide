# 22 縣市議會「現任議員任內紀錄」可行性調查

調查日：2026-10-09。範圍：第4屆（2022-12-25 起；臺北為第14屆、基隆/嘉義縣/花蓮/屏東/南投等縣市依各自屆次編號）。
來源只限議會官網議事系統與公開資料。難度：易＝純 GET/POST 取得結構化資料；中＝ASP.NET postback 或需解析 HTML；難＝Blazor/PDF/需瀏覽器自動化；做不到＝官網無可按議員查的資料。

總結：
- **全 22 縣市都查不到「大會出席率／出席次數」**（議事錄只有 PDF 或全文檢索，無按議員統計）。
- **「自治條例提案數」只有臺北能獨立取得**（案別「市法規」）；其餘縣市要從案由字串另行判斷，未做。
- 可量化且已完成：提案數（高雄、臺北、臺中、臺南、基隆）、市政總質詢次數（僅高雄）。
- 已實作並輸出到 `records_council.json` 的 5 縣市，現任涵蓋 227 位（占約 665 位的 34%）。

| 縣市 | 現任人數 | 有哪些指標 | 網址 | 難度 | 建議做法／狀態 |
|---|---|---|---|---|---|
| 高雄市 | 53 | 議員提案、臨時提案、市政總質詢次數、質詢答復列名（譯文稿）、公聽會 | https://cissearch.kcc.gov.tw/Frame_Councilor.aspx?cname=<姓名> ；總質詢 https://cissearch.kcc.gov.tw/System/MunicipalQuestion/DealData.aspx?councilorfullname=<姓名> ；全部提案 https://cissearch.kcc.gov.tw/System/Proposal/Default.aspx | 易 | **已完成**。個人頁 GET 即得提案數；總質詢頁列出日期（含已排定未進行者，需依日期切）。提案清單另用 postback（LinkButton1 + 每頁筆數 3000）抓 10,196 件交叉驗證，53 人數字與個人頁完全一致。議長不提總質詢。無出席率。SSL 憑證鏈缺 Subject Key Identifier，python 需 verify=False |
| 臺北市 | 50 | 議員提案、市法規案（含自治條例）；書面質詢（gaz.tcc.gov.tw，未做） | https://ifddoc2.tcc.gov.tw/TCCMIS_Front/Adv_SearchInput.aspx | 中 | **已完成**。ASP.NET postback：取 VIEWSTATE 後 POST，`councilorSelect=姓名`、`useMen=on`、`sele_DETR=14`（結案屆次）＋另查 `useunFi=on`，取聯集並以案號開頭「14」篩出本屆提案。案別「臨時提案」在結果中未出現，故未列。日期篩選欄位會觸發伺服器錯誤，未使用 |
| 新北市 | 52 | 議案查詢（提案）；議事錄全文檢索 | https://bms1.ntp.gov.tw/billsystem/councilbillquery ；https://ntpbook.ntp.gov.tw/Home/Home/IndexByMJ | 難 | 議案查詢為 Blazor Server（SignalR），curl 抓不到內容，需 Playwright 類瀏覽器自動化；議事錄僅發言全文檢索，無統計欄位。未做 |
| 桃園市 | 55 | 無（僅會議紀錄 PDF） | https://www.tycc.gov.tw/TC/meeting.aspx?mid=41 | 做不到 | 官網無議案、質詢、出席查詢系統，只有 PDF 議事錄，解析成本高且不可靠。建議標「官網未提供」 |
| 臺中市 | 55 | 議員提案、臨時動議、連署 | https://yishi.tccc.gov.tw/proposals ；API `https://yishi.tccc.gov.tw/api/Proposal/FrontList?PageNumber=1&PageSize=5000` | 易 | **已完成**。公開 JSON，全部 15,417 筆 4 次請求；`sponsor` 欄以頓號/逗號分隔多位提案人，`jointSignatory` 為連署。質詢只有影音，無統計 |
| 臺南市 | 46 | 議員提案、臨時動議 | https://www.tncc.gov.tw/motion1.asp ；API `https://bill.tncc.gov.tw/NoPaperMeeting_TNCC/api/WEB014_GetProposalList.ashx?grdno=4&kidno=4`（4=議員提案、5=臨時動議） | 易 | **已完成**。GET JSON，`pagerow=1500` 分頁；`OrgTitle` 為全部提案人。以 `orgtitle=` 單人查詢驗證（余柷青 435 件）與全抓一致。連署需另用 `orgtitle2`，未做。原住民族姓名含空格，比對前要去空白 |
| 基隆市 | 23 | 提案（含定期會/臨時會區分）、連署 | https://www.kmc.gov.tw/kmcweb/#/motion ；API POST `https://www.kmc.gov.tw/kmcwebapi/motion/getlist`（`expkd=20`） | 易 | **已完成**。一次 POST 取第20屆 3,408 筆；`sm1_1c` 提案人（附「議員／副議長」職稱需清洗）、`sm1_2c` 連署。`seqkd` 1＝定期會、2＝臨時會（非「臨時動議」）。無質詢、出席 |
| 新竹市 | 27 | 質詢（市政總質詢／單位業務）、提案 | https://www.hsinchu-cc.gov.tw/tc/question.aspx?mid=41 ；https://www.hsinchu-cc.gov.tw/tc/proposal.aspx?mid=42 | 中 | ASP.NET postback：先 `ddlClass=11` 載入議員下拉，再 `ddlCouncilor=<id>` 查詢，逐頁數筆數；約 5–10 次請求/人。未做（工作量） |
| 嘉義市 | 17 | 議決案檢索（提案人勾選）；質詢僅影音 | https://www.cycc.gov.tw/web/Expect_Search/listExpect_Search.aspx?c0=3672 | 中 | postback 勾選提案人，但結果集合涵蓋範圍未驗證（抽測 69 件偏少）。未做，需先對照確認 |
| 新竹縣 | 4 | 提案（含連署）、質詢（每會期有質詢議員名單） | https://www.hcc.gov.tw/porposal?lang=&program=197 ；https://www.hcc.gov.tw/question?lang=&program=198 | 易 | 伺服器端渲染 HTML，GET 即可；議員 id 由 `getCouncilor.php` 取得。現任僅 4 人，優先度低。未做 |
| 苗栗縣 | 25 | 無（會議記錄 PDF） | https://www.mcc.gov.tw/iframcirculated_list.php?menu=1765&typeid=2626 | 做不到 | 無按議員資料，議事錄數位化站連不上。建議標「官網未提供」 |
| 彰化縣 | 37 | 無（議事錄 PDF 冊別、議員基本資料） | https://www.chcc.gov.tw/proceedings/index.aspx?Parser=99,7,171,168 | 做不到 | 議員頁僅基本資料，無提案/質詢統計 |
| 南投縣 | 25 | 提案單（PDF 連結，可按提案人篩） | https://www.ntcc.gov.tw/tw/proposal/index.aspx | 中 | postback（`session1=20` 後載入 `proposer`）。抽測張婉慈僅 4 筆，涵蓋範圍存疑（可能只收部分提案單），未驗證故未做 |
| 雲林縣 | 27 | 議事影音（發言議員為影片標籤） | http://msr.ylcc.gov.tw/portal/video_G.php | 做不到 | 後端 API 回 403，標籤非官方次數；數位議事錄只到 2018。建議標「官網未提供」 |
| 嘉義縣 | 29 | 議員提案、臨時動議 | https://api.cyscc.gov.tw/1/News/114?handler=News（`NewWWWDynamiSettingService_Category=[505]`、`[507]`） | 易（但資料不完整） | **實測後棄用**：第20屆僅收 293 件議員提案，缺第4次定期會（僅「變更」案）與第8次定期會，且各會期筆數明顯偏少，無法保證每位議員口徑一致，故不輸出 |
| 屏東縣 | 39 | 議決議案一覽表（提案人欄） | https://www.ptcc.gov.tw/index.php?Page=Resolution&Guid=341d32e8-611e-d50b-da48-ad99548baca3 | 中（未成功） | POST `keyword_ptr_proposer=<姓名>`；實測以現任議員姓名查詢回傳空表，需另帶議案別（`prc_guid`）才可能有結果，未解決，未做 |
| 宜蘭縣 | 24 | 政府提案（議員提案查得 0 筆） | https://www.ilcc.gov.tw/CSource/C06/C0601Q01.aspx?System_work=4&AP=true&Sysno=C0601 | 做不到 | Big5 舊式 ASP.NET，議員提案類別在第20屆查無資料，無質詢/出席查詢 |
| 花蓮縣 | 21 | 議員提案（含提案人/連署人）、書面質詢（僅部分） | https://www.hlcc.gov.tw/proposal_data_search2.php（POST `proposal_section=20&keyword=&search=y`） | 易（但資料不完整） | **實測後棄用**：第20屆共 1,809 件，但第2次定期大會完全沒有資料、第1次定期大會僅 1 件，與其他會期落差過大，不能當全期統計 |
| 臺東縣 | 21 | 議案（含縣府提案與議員提案） | https://www.taitungcc.gov.tw/api/bill?limit=100&page=1&lg=1&kind=2&desk=front&search=num01:20; | 易（但資料不完整） | **實測後棄用**：第20屆全部議案僅 209 筆，其中議員提案 33 件，`kind` 參數無篩選效果，顯然非完整提案資料 |
| 澎湖縣 | 15 | 無（議事錄為掃描 PDF） | https://www.phcouncil.gov.tw/councildata2.php?id=20 | 做不到 | 單檔 80MB、需 OCR，無查詢系統 |
| 金門縣 | 12 | 縣政總質詢列名場次（第8屆）；提案僅收到第7屆 | https://agenda.kmcc.gov.tw/CouncilManage/AgendaGovMinutes | 中 | ASP.NET MVC，需 cookie 與兩個 token，POST `/Search`（`SeNumber=8`）可取 72 筆。第8屆議案不在系統內，只能做總質詢場次。未做 |
| 連江縣 | 8 | 提案全文（依議員發布）、質詢影音（依議員） | https://www.mtcc.gov.tw/ch/news/7178 ；https://www.mtcc.gov.tw/ch/news/7176?clid=N | 中 | 純 GET 解析 HTML，約 100 次請求；提案以議員發文方式發布，需自行切案計數。未做（現任僅 8 人） |

## 口徑備註（已輸出縣市）

- 提案數都以系統列名「提案人」計（含共同提案）；高雄、臺北、臺中、臺南、基隆的列名口徑略有差異（見 records_council.json 各縣市 src_title）。跨縣市不可直接比較。
- 資料截止日皆為爬取日 2026-10-09；高雄第8次定期大會進行中，該會期提案與市政總質詢（排定至 10/15）尚未完整。
- 原始資料在 `crawler/raw/council/<縣市>/`，處理腳本在 `crawler/council/`。
