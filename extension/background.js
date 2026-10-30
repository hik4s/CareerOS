const API='http://127.0.0.1:8765';
chrome.runtime.onMessage.addListener((msg,sender,send)=>{
 if(msg.type==='assist'){chrome.scripting.executeScript({target:{tabId:msg.tabId},func:collectQuestions},async results=>{try{const qs=results?.[0]?.result||[];const r=await fetch(API+'/api/assistant/suggest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({questions:qs.map(x=>x.question)})});const answers=await r.json();chrome.scripting.executeScript({target:{tabId:msg.tabId},func:fillAnswers,args:[qs,answers]},()=>send({ok:true,filled:answers.filter(x=>x.answer).length,total:qs.length}));}catch(e){send({ok:false,error:String(e)})}});return true;}
 if(msg.type!=='capture')return;
 chrome.scripting.executeScript({target:{tabId:msg.tabId},func:extractJob},async results=>{
  if(chrome.runtime.lastError){send({ok:false,error:chrome.runtime.lastError.message});return}
  const job=results?.[0]?.result;
  try{const r=await fetch(API+'/api/import/browser',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(job)});const body=await r.json();send({ok:r.ok,...body,error:r.ok?null:(body.detail||'Falha')})}catch(e){send({ok:false,error:'Career OS não está aberto. Execute o aplicativo e tente novamente.'})}
 });return true;
});
function extractJob(){
 const text=(sel)=>document.querySelector(sel)?.innerText?.trim()||'';
 const meta=(name)=>document.querySelector(`meta[property="${name}"],meta[name="${name}"]`)?.content||'';
 const host=location.hostname;
 const adapters=[
  {test:/gupy\.io$/,title:['h1','[data-testid="job-title"]'],company:['[data-testid="company-name"]','.company-name'],description:['[data-testid="job-description"]','main']},
  {test:/indeed\.com$/,title:['h1','[data-testid="jobsearch-JobInfoHeader-title"]'],company:['[data-testid="inlineHeader-companyName"]','.jobsearch-InlineCompanyRating-companyHeader'],description:['#jobDescriptionText','main']},
  {test:/linkedin\.com$/,title:['h1','.job-details-jobs-unified-top-card__job-title'],company:['.job-details-jobs-unified-top-card__company-name','.topcard__org-name-link'],description:['.jobs-description__content','.show-more-less-html__markup']},
  {test:/solides\.jobs$/,title:['h1'],company:['.company-name','header'],description:['main','.job-description']},
  {test:/vagas\.com\.br$/,title:['h1','.job-shortdescription__title'],company:['.job-shortdescription__company'],description:['.job-description','main']}
 ];
 const a=adapters.find(x=>x.test.test(host))||{title:['h1'],company:['[class*=company]','header'],description:['main','article','[class*=description]']};
 const first=arr=>arr.map(text).find(Boolean)||'';
 const body=first(a.description).slice(0,45000)||document.body.innerText.slice(0,45000);
 const loc=(body.match(/(?:Local|Localidade|Location)\s*[:\-]?\s*([^\n]{2,80})/i)||[])[1]||'';
 const model=/remot[oa]/i.test(body)?'Remoto':/h[ií]brid[oa]/i.test(body)?'Híbrido':/presencial/i.test(body)?'Presencial':'';
 const benefits=[...new Set((body.match(/vale[- ]?(?:alimenta[cç][aã]o|refei[cç][aã]o)|VA|VR|auxílio alimentação/gi)||[]))];
 return {title:first(a.title)||meta('og:title')||document.title,company:first(a.company)||meta('og:site_name')||host,url:location.href.split('#')[0],location:loc,work_model:model,description:body,benefits,source:'browser-extension'};
}

function collectQuestions(){return [...document.querySelectorAll('textarea,input[type="text"]')].filter(e=>!e.value&&e.offsetParent!==null).map((e,i)=>{let label=e.labels?.[0]?.innerText||e.closest('label')?.innerText||e.parentElement?.innerText||e.getAttribute('placeholder')||'';return {index:i,question:label.trim().slice(0,500)}}).filter(x=>x.question)}
function fillAnswers(qs,answers){let fields=[...document.querySelectorAll('textarea,input[type="text"]')].filter(e=>!e.value&&e.offsetParent!==null);qs.forEach((q,i)=>{let a=answers[i]?.answer;if(a&&fields[q.index]){fields[q.index].value=a;fields[q.index].dispatchEvent(new Event('input',{bubbles:true}));fields[q.index].style.outline='2px solid #4361ee'}});alert('Career OS preencheu sugestões. Revise todas as respostas antes de enviar.');}
