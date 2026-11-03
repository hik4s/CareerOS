importScripts('origin.js');
// Session storage is unavailable to content scripts by default; never widen access.
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (sender.id !== chrome.runtime.id || sender.tab || message.type !== 'capture') return;
  capture(message.tabId).then(sendResponse).catch(() => sendResponse({ok:false,error:'Falha ao capturar. Confira a conexão e tente novamente.'}));
  return true;
});
async function capture(tabId) {
  const {careerOrigin: configured} = await chrome.storage.local.get('careerOrigin');
  const origin = careerOrigin(configured || '');
  const {careerToken: token,careerTokenOrigin: tokenOrigin} = await chrome.storage.session.get(['careerToken','careerTokenOrigin']);
  if (!token || tokenOrigin !== origin) return {ok:false,error:'Conecte com um token atual do painel JobsFinder.'};
  if (!await chrome.permissions.contains({origins:[origin+'/*']})) return {ok:false,error:'Conecte novamente para autorizar esta origem.'};
  const results = await chrome.scripting.executeScript({target:{tabId},func:extractJob});
  const extracted = results?.[0]?.result;
  if (!extracted?.title || !extracted?.description) return {ok:false,error:'Não foi possível ler esta vaga. Use uma página de detalhes.'};
  const job = Object.fromEntries(['title','company','description','url','location','work_model'].map(k => [k, extracted[k] || '']));
  job.status='saved';
  const response = await fetch(origin+'/api/jobs',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},body:JSON.stringify(job),redirect:'error'});
  if (response.status === 401 || response.status === 403) {
    await chrome.storage.session.remove(['careerToken','careerTokenOrigin']);
    return {ok:false,error:'A sessão expirou ou não tem acesso. Copie um novo token no painel e conecte novamente.'};
  }
  return {ok:response.ok,error:response.ok ? null : 'Não foi possível salvar a vaga. Confira o painel e tente novamente.'};
}
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

