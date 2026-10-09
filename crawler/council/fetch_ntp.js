// 新北市議會 議案查詢（Blazor Server）：第4屆，按提案人／連署人逐人查詢，Playwright 無頭；每次動作間隔 >= 1 秒
// 用法：NODE_PATH=/Users/highker/.claude/skills/course2notes/node_modules node fetch_ntp.js [姓名...]
const {chromium}=require('playwright-core'); const fs=require('fs');
const R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/新北市/';
const inc=JSON.parse(fs.readFileSync(R+'../incumbents_2.json','utf8'))['新北市'];
const only=process.argv.slice(2);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function total(p){ const t=await p.innerText('body'); const m=t.match(/共\s*(\d+)\s*項/); return m?+m[1]:null; }
async function rowsOf(p){
  return await p.evaluate(()=>[...document.querySelectorAll('table.k-grid-table tbody tr, .k-grid-table tr')].map(tr=>[...tr.querySelectorAll('td')].map(td=>td.innerText.replace(/\s+/g,' ').trim())).filter(r=>r.length>=8));
}
async function query(b,name,field,countOnly){ // field: 5=提案人, 6=連署人
  const p=await b.newPage({viewport:{width:1280,height:900}});
  await p.goto('https://bms1.ntp.gov.tw/billsystem/councilbillquery',{waitUntil:'networkidle'}); await sleep(1500);
  await p.click('text=全部屆別'); await sleep(700); await p.click('text=第4屆'); await sleep(1000);
  const L=p.locator('input:not([type=radio]):not([type=checkbox])');
  await L.nth(field).click(); await L.nth(field).pressSequentially(name,{delay:30}); await L.nth(field).blur(); await sleep(500);
  await p.click('button:has-text("搜尋")'); await sleep(4000);
  const n=await total(p); let rows=[];
  if(n===null){ await p.close(); return {n:0,rows:[],cond:null}; }
  const cond=(await p.innerText('body')).match(/查詢條件:[^\n]*/)?.[0];
  const seen=new Set(); let stall=0;
  for(let pg=1;pg<=Math.ceil(n/10)+30;pg++){
    const cur=await rowsOf(p); let added=0;
    for(const r of cur){ const k=[r[1],r[2],r[3],r[4],r[5],r[8]].join('|'); if(!seen.has(k)){ seen.add(k); rows.push(r); added++; } }
    if(countOnly||rows.length>=n) break;
    if(added===0){ stall++; if(stall>=4) break; await sleep(1500); continue; } else stall=0;
    const nx=p.locator('button[title="下一頁"]'); await nx.click(); await sleep(1500);
  }
  await p.close(); return {n,rows,cond};
}
(async()=>{
 const b=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 for(const full of inc){
  if(only.length&&!only.includes(full)) continue;
  const name=(process.env.NTP_NAME&&only.length===1)?process.env.NTP_NAME:full.match(/^[一-鿿]+/)[0];
  for(const [kind,field] of [['pp',5],['pc',6]]){
    const f=R+`m/${full}_${kind}.json`; fs.mkdirSync(R+'m',{recursive:true});
    if(fs.existsSync(f)) continue;
    let r; try{ r=await query(b,name,field,kind==='pc');}catch(e){ console.log('ERR',full,kind,e.message.slice(0,100)); continue; }
    fs.writeFileSync(f,JSON.stringify({full,name,kind,...r},null,0));
    console.log(full,kind,r.n,r.rows.length);
    await sleep(1000);
  }
 }
 await b.close();
})();
