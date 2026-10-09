// 抽驗：用「案別」下拉分別查（議員提案／臨時動議案／自治條例(議提)），與全案別逐筆抓取的總數對照
const {chromium}=require('playwright-core');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const b=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 for(const name of process.argv.slice(2)) for(const kind of ['議員提案','臨時動議案','自治條例(議提)']){
  const p=await b.newPage({viewport:{width:1280,height:900}});
  await p.goto('https://bms1.ntp.gov.tw/billsystem/councilbillquery',{waitUntil:'networkidle'}); await sleep(1500);
  await p.click('text=全部屆別'); await sleep(700); await p.click('text=第4屆'); await sleep(1000);
  await p.click('text=全部案別'); await sleep(700); await p.click(`li:has-text("${kind}") >> nth=-1`).catch(async()=>{await p.click(`text=${kind}`)}); await sleep(800);
  const L=p.locator('input:not([type=radio]):not([type=checkbox])');
  await L.nth(5).click(); await L.nth(5).pressSequentially(name,{delay:30}); await L.nth(5).blur(); await sleep(500);
  await p.click('button:has-text("搜尋")'); await sleep(4000);
  const t=await p.innerText('body'); console.log(name,kind,(t.match(/查詢條件:[^\n]*/)||[''])[0],(t.match(/共\s*(\d+)\s*項/)||[])[1]);
  await p.close(); await sleep(1000);
 }
 await b.close();
})();
