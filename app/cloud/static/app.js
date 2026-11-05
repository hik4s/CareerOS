'use strict';
const $ = id => document.getElementById(id);
const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stages={saved:'Salva',skip:'Não priorizar',new:'Nova',review:'Em análise',ready:'Pronta para candidatura',applied:'Candidatura enviada',interview:'Entrevista',offer:'Proposta',rejected:'Encerrada',archived:'Arquivada'};
const titles={overview:'Visão geral',jobs:'Minhas vagas',discover:'Buscar vagas',profile:'Meu perfil',resumes:'Currículos',ai:'Assistente IA',capture:'Capturar vagas',data:'Meus dados'};
let client,session,profile={},jobs=[],resumes=[],history=[],apiKey='',tab='overview',estimate=null,estimatePayload=null,aiResult='',loadGeneration=0;
let aiDraft={provider:'heuristic',model:'',task:'evaluate',job_id:'',resume_id:'',instruction:'',previous_text:'',max_output_tokens:512,input_price_per_million:'',output_price_per_million:''};
function toast(message,error=false){$('toast').textContent=message;$('toast').className=error?'error':'';clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').textContent='',6000)}
async function api(path,options={},expectedOwner){const {data,error}=await client.auth.getSession();if(error||!data.session||(expectedOwner && data.session.user.id!==expectedOwner))throw Error('Sua sessão expirou. Entre novamente.');const headers={Authorization:`Bearer ${data.session.access_token}`,...options.headers};if(options.body&&!(options.body instanceof FormData))headers['Content-Type']='application/json';const response=await fetch(path,{...options,headers});if(!response.ok){let body;try{body=await response.json()}catch{}throw Error(typeof body?.detail==='string'?body.detail:`Não foi possível concluir a operação (${response.status}).`)}return response.status===204?null:response.json()}
async function busy(button,fn){const original=button?.textContent;if(button){button.disabled=true;button.textContent='Aguarde…'}try{return await fn()}catch(e){toast(e.message||'Ocorreu um erro.',true)}finally{if(button){button.disabled=false;button.textContent=original}}}
function empty(title,text){return `<div class="empty"><div class="empty-icon">◇</div><h3>${title}</h3><p>${text}</p></div>`}
function safeURL(url){try{const u=new URL(url);return ['https:','http:'].includes(u.protocol)?u.href:''}catch{return ''}}
function date(value){return value?new Date(value).toLocaleDateString('pt-BR'):''}
async function reload(){const generation=++loadGeneration;$('loading').classList.remove('hidden');try{const data=await Promise.all([api('/api/profile'),api('/api/jobs'),api('/api/resumes'),api('/api/ai/history')]);if(generation!==loadGeneration||!session)return;[profile,jobs,resumes,history]=data;render()}catch(e){if(generation===loadGeneration)toast(e.message,true)}finally{if(generation===loadGeneration)$('loading').classList.add('hidden')}}
function clearAccount(){loadGeneration++;pendingJobUpdates.clear();jobFilters={query:'',stage:'',mode:'list'};apiKey='';profile={};jobs=[];resumes=[];history=[];estimate=null;estimatePayload=null;aiResult='';aiDraft={provider:'heuristic',model:'',task:'evaluate',job_id:'',resume_id:'',instruction:'',previous_text:'',max_output_tokens:512,input_price_per_million:'',output_price_per_million:''};$('view').replaceChildren();$('accountName').textContent='Minha conta';$('accountEmail').textContent='';$('avatar').textContent='C';$('jobForm').reset();$('jobDialog').close();$('jobDetailsDialog').close()}
function showSession(next){if(next&&session?.user.id===next.user.id&&$('view').childElementCount){session=next;return}if(session?.user?.id!==next?.user?.id)clearAccount();session=next;const path=next?'/':'/auth';if(location.pathname!==path)window.history.replaceState(null,'',path+location.search+location.hash);$('gate').classList.toggle('hidden',!!next);$('shell').classList.toggle('hidden',!next);if(!next){clearAccount();return}const user=next.user;$('accountName').textContent=user.user_metadata?.full_name||user.email?.split('@')[0]||'Minha conta';$('accountEmail').textContent=user.email||'';$('avatar').textContent=($('accountName').textContent[0]||'C').toUpperCase();reload()}
function setTab(){const next=location.hash.slice(1);tab=Object.hasOwn(titles,next)?next:'overview';render()}
function render(){if(!session)return;$('pageTitle').textContent=titles[tab];document.querySelectorAll('[data-tab]').forEach(a=>a.classList.toggle('active',a.dataset.tab===tab));({overview:renderOverview,jobs:renderJobs,discover:renderDiscovery,profile:renderProfile,resumes:renderResumes,ai:renderAI,capture:renderCapture,data:renderData})[tab]()}
function renderOverview(){const active=jobs.filter(j=>!['archived','rejected'].includes(j.status));const first=profile.full_name?.split(' ')[0];$('view').innerHTML=`<div class="hero"><span class="eyebrow">UM PASSO DE CADA VEZ</span><h2>${first?`Olá, ${esc(first)}. `:''}Sua próxima oportunidade<br>merece um bom plano.</h2><p>Acompanhe suas candidaturas e prepare materiais com base no que você realmente sabe e já construiu.</p><a class="button" href="#jobs">Explorar minhas vagas <span>→</span></a></div><div class="metrics">${[[jobs.length,'Vagas salvas','Seu repertório de oportunidades','▣'],[jobs.filter(j=>j.status==='applied').length,'Candidaturas enviadas','Etapa marcada por você','↗'],[jobs.filter(j=>j.status==='interview').length,'Em entrevista','Conversas em andamento','◎'],[resumes.length,'Currículos','Arquivos na sua conta','▤']].map(([n,l,d,i],index)=>`<a class="metric metric-link" href="${index===3?'#resumes':'#jobs'}" data-metric-filter="${['','applied','interview',''][index]}"><span class="metric-icon">${i}</span><span class="metric-label">${l}</span><strong>${n}</strong><small>${d}</small></a>`).join('')}</div><div class="grid-two"><div class="card"><div class="section-head"><div><h2>No seu radar</h2><p>Suas oportunidades em andamento.</p></div><a class="inline-link" href="#jobs">Ver todas →</a></div>${active.length?active.slice(0,3).map(j=>`<div class="file-row"><div><h3><button type="button" class="job-title-button" data-job-details="${esc(j.id)}">${esc(j.title)}</button></h3><small>${esc(j.company)} · ${stages[j.status]||esc(j.status)}</small></div><span class="badge">${j.fit_score==null?'Sem análise':`${esc(j.fit_score)}% de aderência`}</span></div>`).join(''):empty('Seu radar está pronto','Salve sua primeira vaga para começar a acompanhar as possibilidades.')}</div><div class="card"><div class="section-head"><h2>Construa sua base</h2></div><div class="steps"><div class="step"><span class="step-number">01</span><div><a href="#profile">Dê contexto ao seu perfil →</a><p>Habilidades, projetos e experiências reais.</p></div></div><div class="step"><span class="step-number">02</span><div><a href="#resumes">Organize seus currículos →</a><p>Seus arquivos sempre à mão.</p></div></div><div class="step"><span class="step-number">03</span><div><a href="#ai">Prepare o próximo passo →</a><p>Revise seus materiais com assistência.</p></div></div></div></div></div>`;bindJobActions();document.querySelectorAll('[data-metric-filter]').forEach(link=>{link.onclick=()=>{jobFilters={query:'',stage:link.dataset.metricFilter,mode:'list'};rememberJobFilters()}})}
function jobCard(j){const a=j.analysis||{};const url=safeURL(j.url);return `<article class="job"><div class="job-top"><div><h3><button type="button" class="job-title-button" data-job-details="${esc(j.id)}">${esc(j.title)}</button></h3><p>${esc(j.company)}${j.location?' · '+esc(j.location):''}${j.work_model?' · '+esc(j.work_model):''}</p></div><span class="score">${j.fit_score==null?'Sem análise':`${esc(j.fit_score)}% aderência`}</span></div><div>${(a.matched_skills||[]).map(s=>`<span class="badge">${esc(s)}</span>`).join('')}</div>${(a.blockers||[]).map(s=>`<p>${esc(s)}</p>`).join('')}<div class="job-actions"><select aria-label="Etapa de ${esc(j.title)}" data-stage="${esc(j.id)}">${Object.entries(stages).map(([v,l])=>`<option value="${v}" ${j.status===v?'selected':''}>${l}</option>`).join('')}</select><button class="small secondary" data-analyze="${esc(j.id)}">Analisar perfil</button><button class="small secondary" data-edit="${esc(j.id)}">Editar</button>${url?`<a class="button secondary small" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Abrir ↗</a>`:''}<button class="small danger" data-delete="${esc(j.id)}">Excluir</button></div></article>`}
const workModelLabels = {remote: 'Remoto', hybrid: 'Híbrido', onsite: 'Presencial'};
const jobSectionHeadings = [
  ['Objetivos da vaga', /^(objetivos?( da vaga| do cargo)?|missao( do cargo| da vaga)?|role overview|role purpose|about the role|the role)$/],
  ['Responsabilidades', /^(principais )?(responsabilidades( e atribuicoes)?|atribuicoes|atividades( do cargo| do dia a dia)?|what you('ll| will) do|responsibilities|key responsibilities|duties)$/],
  ['Requisitos', /^(principais )?(requisitos( obrigatorios| e qualificacoes)?|pre[- ]requisitos|qualificacoes|o que (buscamos|esperamos)|requirements|what you('ll| will) need|qualifications|minimum qualifications|preferred qualifications|what you bring)$/],
  ['Formação', /^(formacao( academica| exigida)?|escolaridade|educacao|education|educational requirements)$/],
  ['Salário', /^(salario|faixa salarial|remuneracao|bolsa([- ]auxilio)?|salary|salary range|compensation|pay range)$/],
  ['Benefícios', /^(beneficios|o que oferecemos|benefits|perks|what we offer)$/],
  ['Sobre a empresa', /^(empresa|sobre a empresa|sobre nos|quem somos|about us|about the company|company overview)$/],
];

function jobReadingSections(description) {
  const sections = [];
  let current = {title: 'Sobre a vaga', lines: []};
  for (const raw of (description || '').split(/\r?\n/)) {
    const line = raw.trim();
    const [heading] = line.split(':', 1);
    const key = heading.replace(/^[#•*\s]+|[•*\s]+$/g, '').normalize('NFD')
      .replace(/\p{M}/gu, '').replace(/[‘’]/g, "'").toLowerCase();
    const section = jobSectionHeadings.find(([, pattern]) => pattern.test(key));
    if (section) {
      if (current.lines.some(Boolean)) sections.push(current);
      const inline = line.slice(heading.length + 1).trim();
      current = {title: section[0], lines: inline ? [inline] : []};
    } else {
      current.lines.push(line);
    }
  }
  if (current.lines.some(Boolean)) sections.push(current);
  const grouped = new Map();
  for (const section of sections) {
    const existing = grouped.get(section.title);
    if (existing) existing.lines.push('', ...section.lines);
    else grouped.set(section.title, section);
  }
  return [...grouped.values()];
}

function jobReadingBlocks(lines) {
  const blocks = [];
  let bullets = [];
  const flush = () => {
    if (bullets.length) blocks.push({bullets});
    bullets = [];
  };
  for (const line of lines) {
    const bullet = line.match(/^(?:[•●▪*-]|\d+[.)])\s+(.+)/);
    if (bullet) {
      bullets.push(bullet[1]);
      continue;
    }
    flush();
    if (!line) continue;
    const sentences = line.length > 400 && typeof Intl.Segmenter === 'function'
      ? [...new Intl.Segmenter(undefined, {granularity: 'sentence'}).segment(line)].map(item => item.segment)
      : [line];
    let paragraph = '';
    for (const sentence of sentences) {
      if (paragraph && paragraph.length + sentence.length > 400) {
        blocks.push({text: paragraph.trim()});
        paragraph = '';
      }
      paragraph += sentence;
    }
    if (paragraph.trim()) blocks.push({text: paragraph.trim()});
  }
  flush();
  return blocks;
}

function renderJobReading(sections, missing) {
  const body = $('jobDetailsBody');
  body.innerHTML = (sections.length > 1 ? `<nav class="job-reading-index" aria-label="Seções da vaga">
    ${sections.map((section, index) => `<button type="button" class="secondary small" data-reading-section="${index}">${esc(section.title)}</button>`).join('')}
  </nav>` : '') + (sections.length ? sections.map((section, index) =>
    `<section id="job-reading-section-${index}"><h3>${esc(section.title)}</h3>${jobReadingBlocks(section.lines).map(block =>
      block.bullets ? `<ul>${block.bullets.map(text => `<li>${esc(text)}</li>`).join('')}</ul>`
        : `<p>${esc(block.text)}</p>`
    ).join('')}</section>`
  ).join('') : '<p>A fonte não informou a descrição desta vaga.</p>') +
    (missing?.length ? `<section><h3>A desenvolver</h3><p>${missing.map(esc).join(', ')}</p></section>` : '');
  body.querySelectorAll('[data-reading-section]').forEach(button => {
    button.onclick = () => $('job-reading-section-' + button.dataset.readingSection).scrollIntoView({block: 'start'});
  });
}

let jobTranslation;
async function translateJobReading(job, sections, language) {
  jobTranslation?.abort();
  const controller = new AbortController();
  jobTranslation = controller;
  const {signal} = controller;
  const status = $('jobTranslationStatus');
  const retry = $('retryJobTranslation');
  const missing = job.analysis?.missing_skills;
  $('jobDetailsTitle').textContent = job.title;
  renderJobReading(sections, missing);
  retry.hidden = true;
  status.textContent = '';
  if (language === 'original' || !sections.length) return;
  if (!globalThis.Translator || !globalThis.LanguageDetector) {
    status.textContent = 'Tradução integrada indisponível neste navegador. Exibindo o original.';
    return;
  }
  let detector, translator;
  try {
    status.textContent = 'Identificando idioma…';
    detector = await LanguageDetector.create({signal});
    const [detected] = await detector.detect(job.description.slice(0, 3500), {signal});
    signal.throwIfAborted();
    const sourceLanguage = detected?.detectedLanguage;
    if (!sourceLanguage || sourceLanguage === 'und' || detected.confidence < 0.5) {
      status.textContent = 'Idioma do anúncio não identificado. Exibindo o original.';
      return;
    }
    if (sourceLanguage.split('-')[0] === 'pt') {
      status.textContent = 'Anúncio original em português.';
      return;
    }
    let options = {sourceLanguage, targetLanguage: language};
    if (await Translator.availability(options) === 'unavailable') {
      options = {sourceLanguage, targetLanguage: 'pt'};
      if (await Translator.availability(options) === 'unavailable') {
        status.textContent = 'Tradução indisponível para o idioma deste anúncio.';
        return;
      }
    }
    status.textContent = 'Preparando tradução neste dispositivo…';
    translator = await Translator.create({...options, signal});
    status.textContent = 'Traduzindo anúncio…';
    const title = await translator.translate(job.title, {signal});
    const translated = [];
    for (const section of sections) {
      const lines = [];
      for (const block of jobReadingBlocks(section.lines)) {
        if (block.bullets) {
          for (const text of block.bullets) lines.push('• ' + await translator.translate(text, {signal}));
        } else {
          lines.push(await translator.translate(block.text, {signal}));
        }
      }
      translated.push({title: section.title, lines});
    }
    signal.throwIfAborted();
    $('jobDetailsTitle').textContent = title;
    renderJobReading(translated, missing);
    status.textContent = 'Tradução automática para português.';
  } catch {
    if (signal.aborted) return;
    retry.hidden = false;
    status.textContent = 'A tradução não ficou pronta. Você pode tentar novamente.';
  } finally {
    detector?.destroy?.();
    translator?.destroy?.();
  }
}

function openJobDetails(job, {onSave, saved = false} = {}) {
  const dialog = $('jobDetailsDialog');
  const url = safeURL(job.url);
  const model = workModelLabels[job.work_model] || job.work_model || (job.remote ? 'Remoto' : '');
  $('jobDetailsTitle').textContent = job.title;
  $('jobDetailsMeta').textContent = [job.company || 'Empresa não informada', job.location, model, job.source]
    .filter(Boolean).join(' · ');
  const sections = jobReadingSections(job.description);
  const language = $('jobReadingLanguage');
  const preference = 'careeros.job-reading-language.' + session?.user.id;
  let stored = 'pt-BR';
  try { stored = localStorage.getItem(preference) || stored; } catch {}
  language.value = stored === 'original' ? 'original' : 'pt-BR';
  const translate = () => translateJobReading(job, sections, language.value);
  language.onchange = () => {
    try { localStorage.setItem(preference, language.value); } catch {}
    translate();
  };
  $('retryJobTranslation').onclick = translate;
  $('jobDetailsActions').innerHTML = `
    ${onSave ? `<button type="button" id="saveJobFromDetails" ${saved ? 'disabled' : ''}>${saved ? 'Já salva' : 'Revisar e salvar'}</button>` : ''}
    ${url ? `<a class="button secondary" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Abrir candidatura ↗</a>` : ''}
  `;
  if (onSave) $('saveJobFromDetails').onclick = () => { dialog.close(); onSave(); };
  $('jobDetailsBody').scrollTop = 0;
  dialog.showModal();
  translate();
}

const jobDetailsDialog = $('jobDetailsDialog');
$('closeJobDetails').onclick = () => jobDetailsDialog.close();
jobDetailsDialog.onclose = () => jobTranslation?.abort();
let jobBackdropPressed = false;
jobDetailsDialog.onpointerdown = event => { jobBackdropPressed = event.target === jobDetailsDialog; };
jobDetailsDialog.onclick = event => {
  if (jobBackdropPressed && event.target === jobDetailsDialog) jobDetailsDialog.close();
  jobBackdropPressed = false;
};

function renderDiscovery() {
  $('view').innerHTML = `<div class="hero">
    <span class="eyebrow">EXPLORE OPORTUNIDADES</span><h2>Encontre sua próxima vaga</h2>
    <p>Pesquise, leia as descrições e salve oportunidades em Minhas vagas.</p>
  </div>
  <div class="card"><form id="discoverForm" class="discover-form">
    <label>Cargo ou palavra-chave<input name="q" maxlength="120" placeholder="Ex.: estágio Python, estágio em TI"><small>Use vírgulas para separar alternativas. Palavras sem vírgula são buscadas juntas.</small></label>
    <label>Cidade, região ou país<input name="location" maxlength="100" placeholder="Ex.: São Paulo"></label>
    <label>Distância da cidade<select name="radius_km"><option value="0">Sem raio</option><option value="10">Até 10 km</option><option value="25">Até 25 km</option><option value="50">Até 50 km</option><option value="100">Até 100 km</option></select><small>Com raio, informe uma cidade brasileira. Use cidade e UF se houver ambiguidade.</small></label>
    <label>Modalidade<select name="work_model"><option value="">Todas</option><option value="remote">Remoto</option><option value="hybrid">Híbrido</option><option value="onsite">Presencial</option></select></label>
    <label>Nível<select name="level"><option value="">Todos</option><option value="intern">Estágio ou aprendizagem</option><option value="trainee">Trainee</option><option value="junior">Júnior</option><option value="mid">Pleno</option><option value="senior">Sênior</option></select></label>
    <label class="discover-check"><input type="checkbox" name="title_only"> Buscar palavras-chave somente no título</label>
    <button type="submit">Buscar vagas</button>
    <button type="button" id="clearDiscoveryFilters" class="secondary">Limpar filtros</button>
  </form></div>
  <div class="card"><form id="discoverImport" class="discover-form">
    <label>Link de uma vaga<input name="url" type="url" maxlength="4096" placeholder="https://…" required></label>
    <button type="submit" class="secondary">Importar link</button>
  </form><p class="fine">Confira os dados encontrados ou complete a vaga manualmente antes de salvar.</p></div>
  <div id="discoverStatus" role="status"></div><div id="discoverResults"></div>`;
  const form = $('discoverForm');
  const owner = session.user.id;
  const storageKey = 'careeros.discovery.' + owner;
  $('clearDiscoveryFilters').onclick = () => {
    try { sessionStorage.removeItem(storageKey); } catch {}
    renderDiscovery();
    $('discoverForm').elements.q.focus();
  };
  let state = {};
  try { state = JSON.parse(sessionStorage.getItem(storageKey)) || {}; } catch {}
  const remember = () => {
    try { sessionStorage.setItem(storageKey, JSON.stringify(state)); } catch {}
  };
  const draft = state.draft ?? {};
  form.elements.q.value = draft.q ?? '';
  form.elements.location.value = draft.location ?? '';
  form.elements.radius_km.value = draft.radius_km ?? '0';
  form.elements.work_model.value = draft.work_model ?? (draft.remote === 'true' ? 'remote' : '');
  form.elements.level.value = draft.level ?? '';
  form.elements.title_only.checked = draft.title_only === 'true';
  const filters = () => ({
    q: form.elements.q.value.trim(),
    location: form.elements.location.value.trim(),
    radius_km: form.elements.radius_km.value,
    work_model: form.elements.work_model.value,
    level: form.elements.level.value,
    title_only: String(form.elements.title_only.checked),
  });
  form.oninput = () => {
    state.draft = filters();
    remember();
  };
  let searching = false;
  let retry;
  $('discoverImport').onsubmit = event => {
    event.preventDefault();
    const importForm = event.currentTarget;
    const query = new URLSearchParams({url: importForm.elements.url.value.trim()});
    busy(event.submitter, async () => {
      const job = await api('/api/discovery/import?' + query, {}, owner);
      if (importForm.isConnected && session?.user.id === owner) {
        openJob({...job, work_model: workModelLabels[job.work_model] || (job.remote ? 'Remoto' : '')});
      }
    });
  };
  const search = (query, page, button, attempt = 0) => {
    if (searching || !form.isConnected) return;
    clearTimeout(retry);
    searching = true;
    busy(button, async () => {
      query.set('page', page);
      state.query = query.toString();
      state.page = page;
      remember();
      $('discoverStatus').textContent = 'Consultando fontes de vagas…';
      const submit = form.querySelector('[type="submit"]');
      submit.disabled = true;
      try {
        const result = await api('/api/discovery/jobs?' + query, {}, owner);
        if (!form.isConnected || session?.user.id !== owner) return;
        const refreshing = result.sources?.some(source => source.refreshing);
        if (!refreshing || !state.result?.jobs?.length || (result.page === page && result.jobs?.length)) {
          renderDiscoveryResults(result, (next, control) => search(query, next, control));
          state.result = result;
        }
        state.page = refreshing ? page : (result.page ?? page);
        remember();
        if (refreshing && attempt < 7) {
          retry = setTimeout(() => search(query, page, null, attempt + 1), 4000);
        }
      } finally {
        if (form.isConnected) $('discoverStatus').textContent = '';
        submit.disabled = false;
        searching = false;
      }
    });
  };
  form.onsubmit = event => {
    event.preventDefault();
    const values = filters();
    state = {draft: values, query: new URLSearchParams(values).toString(), page: 1};
    remember();
    search(new URLSearchParams(values), 1, event.submitter);
  };
  if (typeof state.query === 'string') {
    const query = new URLSearchParams(state.query);
    if (Array.isArray(state.result?.jobs)) {
      renderDiscoveryResults(state.result, (page, button) => search(query, page, button));
    }
    search(query, state.page || 1, null);
  }
}

function renderDiscoveryResults(result, goToPage) {
  const {jobs: found, total = 0, sources = [], page = 1, page_size: pageSize = 20} = result ?? {};
  if (!Array.isArray(found) || !Array.isArray(sources)) {
    throw Error('A busca retornou uma resposta inesperada. Tente novamente.');
  }
  const sourceStatus = sources.map(source => {
    const updated = source.updated_at && new Date(source.updated_at).toLocaleString('pt-BR');
    const status = source.refreshing ? 'atualizando' : source.partial ? 'atualização parcial' :
      source.available ? 'disponível' : updated ? 'exibindo última coleta' : 'temporariamente indisponível';
    const count = Number.isInteger(source.unique_matches) ? ' · ' + source.unique_matches + ' vagas nos filtros' : '';
    return `<li>${esc(source.name)} · ${status}${count}${updated ? ' · Atualizada em ' + esc(updated) : ''}</li>`;
  }).join('');
  const cards = found.map((job, index) => {
    const url = safeURL(job.url);
    if (!url) return '';
    const saved = jobs.some(item => item.url === job.url);
    return `<article class="job">
      <div class="job-top"><div><h3><button type="button" class="job-title-button" data-discover-details="${index}">${esc(job.title)}</button></h3><p>${esc(job.company)} · ${esc(job.location || 'Local não informado')}</p></div>
      <span class="badge">${esc(job.source)}</span></div>
      ${job.work_model || job.remote ? `<span class="badge">${esc(workModelLabels[job.work_model] || 'Remoto')}</span>` : ''}
      ${job.match_scope === 'title' ? '<span class="badge">Termos no título</span>' : ''}
      ${job.match_scope === 'details' ? '<span class="badge">Termos nos detalhes</span>' : ''}
      ${job.match_scope === 'provider' ? '<span class="badge">Sugestão da fonte</span>' : ''}
      ${Number.isFinite(job.distance_km) ? `<span class="badge">≈ ${job.distance_km.toLocaleString('pt-BR')} km</span>` : ''}
      ${job.unconfirmed ? '<span class="badge">Abertura ainda não reconfirmada</span>' : ''}
      <div class="job-actions">
        <a class="button secondary small" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Candidatar-se no site da vaga ↗</a>
        <button class="small" type="button" data-discover-save="${index}" data-url="${esc(job.url)}" ${saved ? 'disabled' : ''}>${saved ? 'Já salva' : 'Revisar e salvar'}</button>
      </div></article>`;
  }).join('');
  $('discoverResults').innerHTML = `
    <section class="card"><h2>Resultados integrados</h2><details><summary>Atualização das fontes</summary><ul class="fine">${sourceStatus}</ul></details>
    <p>${total ? `${total} vagas encontradas. Página ${page} de ${Math.ceil(total / pageSize)}.` :
      sources.some(source => source.refreshing) ? 'Carregando o catálogo. Os resultados aparecerão aqui.' :
      'Nenhuma vaga encontrada nas fontes disponíveis. Tente outros termos ou filtros.'}</p>
    ${cards}<div class="job-actions">
      ${page > 1 ? '<button class="small secondary" id="discoverPrevious">Página anterior</button>' : ''}
      ${page * pageSize < total ? '<button class="small secondary" id="discoverNext">Próxima página</button>' : ''}
    </div></section>`;
  if ($('discoverPrevious')) $('discoverPrevious').onclick = event => goToPage(page - 1, event.currentTarget);
  if ($('discoverNext')) $('discoverNext').onclick = event => goToPage(page + 1, event.currentTarget);
  const saveDiscovery = job => openJob({
    ...job, work_model: workModelLabels[job.work_model] || (job.remote ? 'Remoto' : ''),
  });
  $('discoverResults').querySelectorAll('[data-discover-details]').forEach(button => {
    button.onclick = () => {
      const job = found[Number(button.dataset.discoverDetails)];
      openJobDetails(job, {
        onSave: () => saveDiscovery(job),
        saved: jobs.some(item => item.url === job.url),
      });
    };
  });
  $('discoverResults').querySelectorAll('[data-discover-save]').forEach(button => {
    button.onclick = () => saveDiscovery(found[Number(button.dataset.discoverSave)]);
  });
}
const jobBoardColumns = [
  {title: 'No radar', stage: 'saved', statuses: ['new', 'saved', 'skip']},
  {title: 'Preparação', stage: 'review', statuses: ['review', 'ready']},
  {title: 'Candidaturas', stage: 'applied', statuses: ['applied']},
  {title: 'Entrevistas', stage: 'interview', statuses: ['interview']},
  {title: 'Propostas', stage: 'offer', statuses: ['offer']},
  {title: 'Encerradas', stage: 'rejected', statuses: ['rejected', 'archived']},
];
let jobFilters = {query: '', stage: '', mode: 'list'};
const pendingJobUpdates = new Set();

function jobBoardCard(job) {
  return `<article class="job-board-card" draggable="${!pendingJobUpdates.has(job.id)}" data-drag-job="${esc(job.id)}">
    <span class="badge">${esc(stages[job.status] || job.status)}</span>
    <h3><button type="button" class="job-title-button" data-job-details="${esc(job.id)}">${esc(job.title)}</button></h3>
    <p>${esc(job.company)}${job.location ? ' · ' + esc(job.location) : ''}</p>
    <label>Mover para<select data-stage="${esc(job.id)}" aria-label="Etapa de ${esc(job.title)}" ${pendingJobUpdates.has(job.id) ? 'disabled' : ''}>
      ${Object.entries(stages).map(([value, label]) => `<option value="${value}" ${job.status === value ? 'selected' : ''}>${label}</option>`).join('')}
    </select></label>
  </article>`;
}

function rememberJobFilters() {
  if (!session) return;
  try { sessionStorage.setItem('careeros.jobs.' + session.user.id, JSON.stringify(jobFilters)); } catch {}
}

function renderJobs() {
  try {
    const stored = JSON.parse(sessionStorage.getItem('careeros.jobs.' + session.user.id));
    if (stored && ['list', 'board'].includes(stored.mode)) jobFilters = stored;
  } catch {}
  $('view').innerHTML = `<div class="section-head"><div><h2>Seu próximo passo, à vista</h2><p>Organize suas oportunidades e acompanhe cada candidatura.</p></div>
    <button id="newJob">＋ Nova vaga</button></div>
    <div class="jobs-workspace-toolbar">
      <div class="view-switch" role="group" aria-label="Visualização das vagas">
        <button type="button" data-job-mode="list">Lista</button><button type="button" data-job-mode="board">Quadro de etapas</button>
      </div>
      <span id="jobCount" role="status"></span>
      <button type="button" id="refreshJobs" class="secondary small">Atualizar vagas</button>
      <a class="button secondary small" href="#discover">Encontrar vagas ↗</a>
    </div>
    <div class="toolbar">
      <input id="jobSearch" placeholder="Buscar por título ou empresa" aria-label="Buscar vagas salvas" value="${esc(jobFilters.query || '')}">
      <select id="stageFilter" aria-label="Filtrar por etapa"><option value="">Todas as etapas</option>
        ${Object.entries(stages).map(([value, label]) => `<option value="${value}" ${jobFilters.stage === value ? 'selected' : ''}>${label}</option>`).join('')}
      </select>
      <button id="clearJobFilters" type="button" class="secondary small">Limpar filtros</button>
    </div><div id="jobList"></div>`;
  $('jobSearch').oninput = () => {
    jobFilters.query = $('jobSearch').value;
    rememberJobFilters();
    renderJobResults();
  };
  $('stageFilter').onchange = () => {
    jobFilters.stage = $('stageFilter').value;
    rememberJobFilters();
    renderJobResults();
  };
  $('clearJobFilters').onclick = () => {
    jobFilters = {...jobFilters, query: '', stage: ''};
    rememberJobFilters();
    renderJobs();
    $('jobSearch').focus();
  };
  document.querySelectorAll('[data-job-mode]').forEach(button => {
    button.onclick = () => {
      jobFilters.mode = button.dataset.jobMode;
      rememberJobFilters();
      renderJobResults();
    };
  });
  $('newJob').onclick = () => openJob();
  $('refreshJobs').onclick = event => busy(event.currentTarget, reload);
  renderJobResults();
}

function renderJobResults() {
  if (tab !== 'jobs' || !$('jobList')) return;
  const query = (jobFilters.query || '').normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
  const filtered = jobs.filter(job => {
    const text = `${job.title} ${job.company}`.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
    return (!jobFilters.stage || job.status === jobFilters.stage) && text.includes(query);
  });
  $('jobCount').textContent = `${filtered.length} de ${jobs.length} oportunidades`;
  $('refreshJobs').disabled = pendingJobUpdates.size > 0;
  document.querySelectorAll('[data-job-mode]').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.jobMode === jobFilters.mode));
  });
  if (!filtered.length) {
    $('jobList').innerHTML = empty('Seu radar está pronto para o próximo passo',
      jobs.length ? 'Ajuste ou limpe os filtros para encontrar suas vagas.' : 'Encontre oportunidades na busca ou adicione uma vaga para começar.');
  } else if (jobFilters.mode === 'board') {
    $('jobList').innerHTML = `<p class="fine">Arraste um cartão para mudar a etapa ou use “Mover para”. A mudança fica salva na sua conta.</p>
      <div class="job-board" aria-label="Quadro de candidaturas">
      ${jobBoardColumns.map(column => {
        const items = filtered.filter(job => column.statuses.includes(job.status));
        return `<section class="job-board-column" data-drop-stage="${column.stage}" aria-label="${column.title}">
          <div class="job-board-column-head"><h3>${column.title}</h3><span class="badge">${items.length}</span></div>
          ${items.map(jobBoardCard).join('') || '<p class="job-board-empty">Mova uma vaga para esta etapa.</p>'}
        </section>`;
      }).join('')}</div>`;
  } else {
    $('jobList').innerHTML = filtered.map(jobCard).join('');
  }
  bindJobActions();
  document.querySelectorAll('[data-drag-job]').forEach(card => {
    card.ondragstart = event => {
      if (pendingJobUpdates.has(card.dataset.dragJob)) { event.preventDefault(); return; }
      event.dataTransfer.setData('text/plain', card.dataset.dragJob);
      event.dataTransfer.effectAllowed = 'move';
    };
  });
  document.querySelectorAll('[data-drop-stage]').forEach(column => {
    column.ondragover = event => { event.preventDefault(); column.classList.add('is-drop-target'); };
    column.ondragleave = event => {
      if (!column.contains(event.relatedTarget)) column.classList.remove('is-drop-target');
    };
    column.ondrop = event => {
      event.preventDefault();
      column.classList.remove('is-drop-target');
      const id = event.dataTransfer.getData('text/plain');
      const job = jobs.find(item => item.id === id);
      const group = jobBoardColumns.find(item => item.stage === column.dataset.dropStage);
      if (job && group && !group.statuses.includes(job.status)) updateJobStage(id, group.stage);
    };
  });
}

async function updateJobStage(id, stage) {
  const job = jobs.find(item => item.id === id);
  if (!job || !Object.hasOwn(stages, stage) || pendingJobUpdates.has(id) || job.status === stage) return;
  const owner = session?.user.id;
  const previous = job.status;
  pendingJobUpdates.add(id);
  job.status = stage;
  renderJobResults();
  try {
    const updated = await api('/api/jobs/' + encodeURIComponent(id), {
      method: 'PATCH', body: JSON.stringify({status: stage}),
    }, owner);
    if (session?.user.id !== owner) return;
    const index = jobs.findIndex(item => item.id === id);
    if (index >= 0) jobs[index] = updated;
    toast('Etapa atualizada para ' + stages[stage] + '.');
  } catch (error) {
    if (session?.user.id === owner) {
      const current = jobs.find(item => item.id === id);
      if (current) current.status = previous;
      toast(error.message || 'Não foi possível salvar a etapa. Tente novamente.', true);
    }
  } finally {
    pendingJobUpdates.delete(id);
    if (session?.user.id === owner) renderJobResults();
  }
}

function bindJobActions() {
  document.querySelectorAll('[data-job-details]').forEach(button => {
    button.onclick = () => {
      const job = jobs.find(item => item.id === button.dataset.jobDetails);
      if (job) openJobDetails(job);
    };
  });
  document.querySelectorAll('[data-edit]').forEach(button => {
    button.disabled = pendingJobUpdates.has(button.dataset.edit);
    button.onclick = () => openJob(jobs.find(job => job.id === button.dataset.edit));
  });
  document.querySelectorAll('[data-delete]').forEach(button => {
    button.disabled = pendingJobUpdates.has(button.dataset.delete);
    button.onclick = () => {
      if (confirm('Excluir esta vaga da sua conta?')) busy(button, async () => {
        await api('/api/jobs/' + encodeURIComponent(button.dataset.delete), {method: 'DELETE'});
        await reload();
        toast('Vaga excluída.');
      });
    };
  });
  document.querySelectorAll('[data-stage]').forEach(select => {
    select.disabled = pendingJobUpdates.has(select.dataset.stage);
    select.onchange = () => updateJobStage(select.dataset.stage, select.value);
  });
  document.querySelectorAll('[data-analyze]').forEach(button => {
    button.disabled = pendingJobUpdates.has(button.dataset.analyze);
    button.onclick = () => busy(button, async () => {
      await api('/api/jobs/' + encodeURIComponent(button.dataset.analyze) + '/analyze', {method: 'POST'});
      await reload();
      toast('Análise local atualizada.');
    });
  });
}
function openJob(j){$('jobForm').reset();for(const name of ['id','title','company','location','work_model','url','description'])$('jobForm').elements.namedItem(name).value=j?.[name]||'';$('jobDialogTitle').textContent=j?.id?'Editar vaga':'Nova vaga';$('jobDialog').showModal()}
function profilePhoto(value) {
  return typeof value === 'string' && value.length <= 50000 &&
    /^data:image\/jpeg;base64,[A-Za-z0-9+/]+={0,2}$/.test(value) ? value : '';
}

async function resizeProfilePhoto(file) {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
    throw Error('Escolha uma foto JPEG, PNG ou WebP de até 5 MiB.');
  }
  const bitmap = await createImageBitmap(file);
  try {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 160;
    const side = Math.min(bitmap.width, bitmap.height);
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, 160, 160);
    ctx.drawImage(bitmap, (bitmap.width-side)/2, (bitmap.height-side)/2, side, side, 0, 0, 160, 160);
    const result = profilePhoto(canvas.toDataURL('image/jpeg', .78));
    if (!result) throw Error('Não foi possível preparar a foto.');
    return result;
  } finally {
    bitmap.close();
  }
}

function renderProfile(){const fields=[['full_name','Nome completo'],['email','E-mail'],['phone','Telefone'],['city','Cidade'],['course','Curso'],['term','Semestre / termo'],['graduation_date','Previsão de conclusão'],['linkedin','LinkedIn'],['github','GitHub']];
const owner = session?.user.id;
let avatar = profilePhoto(profile.avatar);
const sections = [
  ['Identificação', profile.full_name],
  ['Contato', profile.email || profile.phone],
  ['Formação', profile.course],
  ['Resumo profissional', profile.summary],
  ['Habilidades', profile.skills?.length],
  ['Projetos e evidências', profile.evidence?.length],
  ['Currículo anexado', resumes.length],
];
const status = sections.filter(([, filled]) => filled).length;
$('view').innerHTML=`<div class="card"><div class="section-head"><div><h2>Meu perfil</h2><p>Use informações reais. Este perfil orienta a análise de vagas e os textos assistidos.</p></div></div><div class="profile-overview"><div id="profileAvatar" class="profile-avatar"></div><div><h3>${esc(profile.full_name || 'Minha conta')}</h3><p>${esc(session?.user.email || '')}</p><p>${status} de ${sections.length} áreas preenchidas</p></div></div>
<div class="profile-checklist">${sections.map(([label,filled])=>`<span class="badge">${filled?'✓':'○'} ${label}</span>`).join('')}</div>
<form id="profileForm"><div class="row"><label>Foto de perfil<input id="profilePhoto" type="file" accept="image/jpeg,image/png,image/webp"></label><button type="button" id="removeProfilePhoto" class="secondary small">Remover foto</button></div><small>A foto será atualizada ao salvar o perfil.</small><div class="form-grid">${fields.map(([n,l])=>`<label>${l}<input name="${n}" value="${esc(profile[n])}" ${n==='term'?'type="number" min="1" max="20" required':n==='email'?'type="email"':''}></label>`).join('')}</div><label>Resumo profissional<textarea name="summary" rows="4" maxlength="10000">${esc(profile.summary || '')}</textarea></label><label>Cargos de interesse<input name="target_roles" value="${esc((profile.target_roles||[]).join(', '))}" placeholder="Ex.: estágio em desenvolvimento, analista júnior"><small>Separe por vírgulas.</small></label><label>Habilidades<input name="skills" value="${esc((profile.skills||[]).join(', '))}" placeholder="Ex.: Python, SQL, comunicação"><small>Inclua apenas competências que você consegue demonstrar. Separe por vírgulas.</small></label><label>Projetos e evidências (JSON)<textarea name="evidence" rows="7" spellcheck="false">${esc(JSON.stringify(profile.evidence||[],null,2))}</textarea><small>Lista de objetos. Exemplo de estrutura: [{"name": "Nome do projeto", "description": "O que você fez", "url": "https://..."}]. Não invente experiências.</small></label><button type="submit">Salvar perfil</button></form></div>
<div class="card"><h2>Seções do currículo</h2><p>Confira as seções e os contatos identificados no texto do arquivo.</p>
${resumes.length ? `<div class="row"><select id="profileResume" aria-label="Currículo para analisar">${resumes.map(r=>`<option value="${esc(r.id)}">${esc(r.filename)}</option>`).join('')}</select><button id="inspectResume" type="button" class="secondary">Analisar currículo</button></div><div id="resumeSections" class="profile-checklist" role="status"></div>` : '<a href="#resumes">Adicionar currículo</a>'}</div>
<div class="card"><h2>Dados da conta</h2><p>Baixe uma cópia dos seus dados antes de excluir a conta.</p><a href="#data">Exportar meus dados</a>
<details class="account-delete"><summary>Excluir conta</summary><p>A exclusão é permanente e remove o perfil, as vagas, os currículos e o histórico de IA desta conta.</p>
<form id="deleteAccountForm"><label>Digite EXCLUIR para confirmar<input name="confirmation" autocomplete="off" required pattern="EXCLUIR"></label><button class="danger" type="submit">Excluir minha conta</button></form></details></div>`;
const updateAvatar = () => {
  const slot = $('profileAvatar');
  slot.replaceChildren();
  if (avatar) {
    const img = document.createElement('img');
    img.src = avatar;
    img.alt = 'Foto de perfil';
    slot.append(img);
  } else {
    slot.textContent = (profile.full_name || session?.user.email || 'C').charAt(0).toUpperCase();
  }
};
updateAvatar();
const inspect = $('inspectResume');
if (inspect) inspect.onclick = () => busy(inspect, async () => {
  const selected = $('profileResume').value;
  const report = await api('/api/resumes/' + encodeURIComponent(selected) + '/sections', {}, owner);
  const output = $('resumeSections');
  if (!output || session?.user.id !== owner || $('profileResume').value !== selected) return;
  if (!report.has_text) {
    output.textContent = 'Não foi encontrado texto legível neste arquivo.';
    return;
  }
  const labels = {resumo:'Resumo',experiencia:'Experiência ou projetos',formacao:'Formação',habilidades:'Habilidades',email:'E-mail',phone:'Telefone',linkedin:'LinkedIn',github:'GitHub'};
  const found = {...report.sections, ...report.contacts};
  output.innerHTML = Object.entries(labels).map(([key,label]) =>
    `<span class="badge">${found[key] ? '✓' : '○'} ${label}</span>`).join('');
});
if (inspect) $('profileResume').onchange = () => $('resumeSections').replaceChildren();
$('removeProfilePhoto').onclick = () => { avatar = ''; $('profilePhoto').value = ''; updateAvatar(); };
$('deleteAccountForm').onsubmit = event => {
  event.preventDefault();
  if (session?.user.id !== owner) return;
  const confirmation = new FormData(event.currentTarget).get('confirmation');
  busy(event.submitter, async () => {
    await api('/api/account/delete', {method:'POST', body:JSON.stringify({confirmation})}, owner);
    await client.auth.signOut({scope:'local'});
    showSession(null);
    toast('Conta excluída.');
  });
};
$('profileForm').onsubmit=e=>{e.preventDefault();busy(e.submitter,async()=>{const f=new FormData(e.target);let evidence;try{evidence=JSON.parse(f.get('evidence'));if(!Array.isArray(evidence)||evidence.some(v=>!v||typeof v!=='object'||Array.isArray(v)))throw Error()}catch{throw Error('Revise o JSON de evidências: use uma lista de objetos.')}const photo = $('profilePhoto').files[0];
const next={...profile,evidence,avatar:photo ? await resizeProfilePhoto(photo) : avatar};
if(session?.user.id!==owner)return;for(const [key,value]of f){if(['skills','target_roles'].includes(key))next[key]=value.split(',').map(x=>x.trim()).filter(Boolean);else if(key==='term'){if(!value)throw Error('Informe seu semestre ou termo.');next[key]=Number(value);}else if(key!=='evidence')next[key]=value}await api('/api/profile',{method:'PUT',body:JSON.stringify(next)}, owner);await reload();toast('Perfil salvo.')})}}
function renderResumes(){$('view').innerHTML=`<div class="card"><div class="section-head"><div><h2>Seus materiais, organizados</h2><p>Guarde e consulte os currículos da sua conta.</p></div></div><form id="uploadForm" class="upload"><h3>Adicione seu currículo</h3><p>Envie um arquivo PDF ou DOCX.</p><input type="file" id="resumeFile" accept=".pdf,.docx" required aria-label="Arquivo de currículo"><button type="submit">↑ Enviar arquivo</button></form><div>${resumes.length?resumes.map(r=>`<div class="file-row"><div><h3>▤ ${esc(r.filename)}</h3><small>Adicionado em ${date(r.created_at)}</small></div><div class="row"><button class="small secondary" data-download="${esc(r.id)}">Baixar</button><button class="small danger" data-remove-resume="${esc(r.id)}">Excluir</button></div></div>`).join(''):empty('Nenhum currículo salvo','Seus arquivos enviados aparecerão aqui.')}</div></div>`;$('uploadForm').onsubmit=e=>{e.preventDefault();busy(e.submitter,async()=>{const form=new FormData();form.append('file',$('resumeFile').files[0]);await api('/api/resumes',{method:'POST',body:form});await reload();toast('Arquivo enviado.')})};document.querySelectorAll('[data-download]').forEach(b=>b.onclick=()=>busy(b,async()=>{const data=await api(`/api/resumes/${b.dataset.download}/download`);const url=safeURL(data.url);if(!url)throw Error('Link de download inválido.');const a=document.createElement('a');a.href=url;a.rel='noopener noreferrer';a.download='';document.body.append(a);a.click();a.remove()}));document.querySelectorAll('[data-remove-resume]').forEach(b=>b.onclick=()=>{if(confirm('Excluir este currículo e seu arquivo?'))busy(b,async()=>{await api(`/api/resumes/${b.dataset.removeResume}`,{method:'DELETE'});await reload();toast('Currículo excluído.')})})}
function captureDraft(){const f=$('aiForm');if(!f)return;for(const name of Object.keys(aiDraft))aiDraft[name]=f.elements.namedItem(name).value}
function aiPayload(){captureDraft();const p={provider:aiDraft.provider,model:aiDraft.model.trim(),task:aiDraft.task,max_output_tokens:Number(aiDraft.max_output_tokens),instruction:aiDraft.instruction,previous_text:aiDraft.previous_text};if(aiDraft.job_id)p.job_id=aiDraft.job_id;if(aiDraft.resume_id)p.resume_id=aiDraft.resume_id;for(const k of ['input_price_per_million','output_price_per_million'])if(aiDraft[k]!=='')p[k]=Number(aiDraft[k]);return p}
function renderAI(){const external=aiDraft.provider!=='heuristic';$('view').innerHTML=`<div class="notice">A IA usa seu perfil e a vaga selecionada para preparar um rascunho. Confira cada afirmação antes de usar. A análise local não chama provedores externos.</div><div class="grid-two"><div class="card"><div class="section-head"><div><h2>Seu parceiro de preparação</h2><p>Você escolhe o contexto, o modelo e o limite.</p></div><span class="badge">✧ IA sob seu controle</span></div><form id="aiForm"><div class="form-grid"><label>Provedor<select name="provider">${[['heuristic','Local · sem API'],['openai','OpenAI'],['anthropic','Anthropic'],['deepseek','DeepSeek']].map(([v,l])=>`<option value="${v}" ${aiDraft.provider===v?'selected':''}>${l}</option>`).join('')}</select></label><label>Modelo exato<input name="model" value="${esc(aiDraft.model)}" placeholder="Identificador do provedor" ${external?'required':''}><small>Consulte o identificador disponível na sua conta do provedor.</small></label></div><label>O que vamos preparar?<select name="task">${[['evaluate','Avaliar aderência à vaga'],['summary','Resumo profissional'],['cover_letter','Carta de apresentação'],['revise','Revisar um texto']].map(([v,l])=>`<option value="${v}" ${aiDraft.task===v?'selected':''}>${l}</option>`).join('')}</select></label><label>Vaga de contexto<select name="job_id"><option value="">Sem vaga selecionada</option>${jobs.map(j=>`<option value="${esc(j.id)}" ${j.id===aiDraft.job_id?'selected':''}>${esc(j.title)} · ${esc(j.company)}</option>`).join('')}</select></label><label>Currículo de contexto (opcional)<select name="resume_id"><option value="">Usar apenas perfil e vaga</option>${resumes.map(r=>`<option value="${esc(r.id)}" ${r.id===aiDraft.resume_id?'selected':''}>${esc(r.filename)}</option>`).join('')}</select><small>O texto extraído pode ser limitado a 6.000 caracteres pelo servidor. PDF digitalizado pode não conter texto legível.</small></label><label>Orientações adicionais<textarea name="instruction" rows="3" placeholder="Ex.: destaque meus projetos e mantenha o tom objetivo">${esc(aiDraft.instruction)}</textarea></label><label>Texto para revisão (quando aplicável)<textarea name="previous_text" rows="4">${esc(aiDraft.previous_text)}</textarea></label><label>Limite de tokens de saída<input name="max_output_tokens" type="number" min="128" max="2048" step="1" value="${esc(aiDraft.max_output_tokens)}" required><small>Entre 128 e 2.048 tokens. Um limite menor pode cortar a resposta.</small></label><details><summary>Preços para estimativa (opcional)</summary><p class="fine">Preencha os preços atuais do seu provedor em USD por milhão de tokens. A estimativa não representa cobrança nem garante custo máximo real.</p><div class="form-grid"><label>Entrada · USD / 1M<input name="input_price_per_million" type="number" min="0" step="any" value="${esc(aiDraft.input_price_per_million)}"></label><label>Saída · USD / 1M<input name="output_price_per_million" type="number" min="0" step="any" value="${esc(aiDraft.output_price_per_million)}"></label></div></details><button type="submit">1. Estimar antes de gerar</button></form><div id="estimateArea"></div>${aiResult?`<div class="section-head output-head"><h3>Seu rascunho</h3><button id="copyResult" class="small secondary">Copiar texto</button></div><div class="result">${esc(aiResult)}</div>`:''}</div><div><div class="card"><h2>Conexão de IA</h2><p class="muted">Sua chave fica somente na memória desta página. Ela é apagada ao sair ou atualizar a página e enviada ao servidor apenas ao gerar uma resposta.</p><form id="keyForm"><label>Chave de API<input id="apiKeyInput" type="password" autocomplete="off" placeholder="Cole sua chave aqui"></label><div class="row"><button type="submit" class="secondary small">Guardar nesta sessão</button><button id="clearKey" type="button" class="secondary small">Apagar</button></div></form><p class="ai-status" id="keyStatus">${apiKey?'Chave em memória · não validada':'Nenhuma chave nesta sessão'}</p><p class="fine">Guardar a chave não testa nem valida a conexão. Não há tentativas automáticas em caso de falha.</p></div><div class="card"><h2>Histórico</h2><p class="muted">Rascunhos e execuções da sua conta.</p>${history.length?history.slice(0,20).map(h=>`<div class="history-item"><h3>${esc(h.task||'Preparação')} <span class="badge">${esc(h.provider)}</span></h3><p>${date(h.created_at)} · ${esc(h.model||'Local')}${h.cached?' · cache':''}</p><p>Tokens de entrada: ${esc(h.input_tokens??'não informado')} · saída: ${esc(h.output_tokens??'não informado')}<br>Custo estimado: ${h.estimated_cost_usd==null?'não informado':'US$ '+Number(h.estimated_cost_usd).toFixed(6)}${h.estimated_input_tokens!=null?' · entrada estimada: '+esc(h.estimated_input_tokens):''}</p><details><summary>Ver resultado</summary><div class="result">${esc(typeof h.result==='string'?h.result:JSON.stringify(h.result??{},null,2))}</div></details></div>`).join(''):empty('Nenhuma execução ainda','Seus rascunhos aparecerão aqui.')}</div></div></div>`;$('keyForm').onsubmit=e=>{e.preventDefault();apiKey=$('apiKeyInput').value.trim();$('apiKeyInput').value='';$('keyStatus').textContent=apiKey?'Chave em memória · não validada':'Nenhuma chave nesta sessão';toast(apiKey?'Chave guardada apenas nesta página.':'Nenhuma chave informada.')};$('clearKey').onclick=()=>{apiKey='';$('apiKeyInput').value='';$('keyStatus').textContent='Nenhuma chave nesta sessão';toast('Chave apagada.')};$('aiForm').elements.provider.onchange=()=>{captureDraft();estimate=null;estimatePayload=null;renderAI()};$('aiForm').oninput=()=>{estimate=null;estimatePayload=null;$('estimateArea').replaceChildren()};$('aiForm').onsubmit=e=>{e.preventDefault();busy(e.submitter,async()=>{const p=aiPayload();const snapshot=JSON.stringify(p);const owner=session?.user?.id;const data=await api('/api/ai/estimate',{method:'POST',body:snapshot});if(!session||session.user.id!==owner||tab!=='ai'||JSON.stringify(aiPayload())!==snapshot)return;estimate=data;estimatePayload=p;showEstimate()})};if($('copyResult'))$('copyResult').onclick=e=>busy(e.currentTarget,async()=>{await navigator.clipboard.writeText(aiResult);toast('Texto copiado.')})}
function showEstimate(){if(!estimate)return;const cost=estimate.estimated_max_cost_usd;const external=estimatePayload.provider!=='heuristic';$('estimateArea').innerHTML=`<div class="consent-area notice ${external?'warning':''}"><strong>Estimativa antes de gerar</strong><p>Entrada aproximada: ${esc(estimate.estimated_input_tokens)} tokens · saída limitada a ${esc(estimate.max_output_tokens)} tokens.<br>${cost==null?'Custo não calculado: informe os preços para uma estimativa.':`Custo estimado: até US$ ${Number(cost).toFixed(6)} com os preços informados.`}${estimate.cached?'<br>Resultado disponível em cache.':''}</p><p>${esc(estimate.notice||'Contagens e custos são estimativas; a cobrança real é definida pelo provedor.')}</p><label class="check"><input type="checkbox" id="aiConsent"> <span>${external?`Autorizo enviar meu perfil, a vaga selecionada, o currículo selecionado (texto extraído limitado) e os textos acima ao provedor ${esc(estimatePayload.provider)} para esta execução. Entendo que podem existir cobranças.`:'Confirmo que o contexto selecionado pode ser usado para gerar este rascunho local.'}</span></label><button id="generateAI" disabled>2. Gerar rascunho</button></div>`;$('aiConsent').onchange=()=>{$('generateAI').disabled=!$('aiConsent').checked};$('generateAI').onclick=e=>busy(e.currentTarget,async()=>{if(!estimatePayload||!$('aiConsent').checked)throw Error('Faça uma nova estimativa e confirme o envio.');if(external&&!apiKey)throw Error('Guarde sua chave de API nesta sessão antes de gerar.');const owner=session?.user?.id;const data=await api('/api/ai/run',{method:'POST',body:JSON.stringify({...estimatePayload,...(external?{api_key:apiKey}:{})})});if(!session||session.user.id!==owner)return;const nextResult=typeof data.result==='string'?data.result:JSON.stringify(data.result,null,2);const nextHistory=await api('/api/ai/history');if(!session||session.user.id!==owner)return;aiResult=nextResult;estimate=null;estimatePayload=null;history=nextHistory;if(tab==='ai')renderAI();toast(data.cached?'Rascunho recuperado do cache.':'Rascunho gerado. Revise antes de usar.')})}
function renderCapture(){$('view').innerHTML=`<div class="hero"><span class="eyebrow">LEVE SEU RADAR COM VOCÊ</span><h2>Encontrou uma boa vaga?<br>Guarde no CareerOS.</h2><p>Capture oportunidades durante sua pesquisa e organize as próximas etapas no seu espaço pessoal.</p><a class="button" href="/api/extension.zip" download>↓ Baixar extensão Chrome</a></div><div class="card"><h2>Instalar e conectar</h2><div class="steps" style="margin-top:24px"><div class="step"><span class="step-number">01</span><div><h3>Extraia o arquivo baixado</h3><p>Mantenha a pasta da extensão no seu computador.</p></div></div><div class="step"><span class="step-number">02</span><div><h3>Abra chrome://extensions</h3><p>Ative o modo de desenvolvedor, escolha “Carregar sem compactação” e selecione a pasta.</p></div></div><div class="step"><span class="step-number">03</span><div><h3>Conecte à sua conta</h3><p>Informe na extensão o endereço deste site: <strong>${esc(location.origin)}</strong>. Copie abaixo seu token de sessão e cole no campo indicado na extensão.</p></div></div></div><div class="notice warning" style="margin-top:24px">O token concede acesso à sua conta. Mantenha-o privado e cole somente na extensão CareerOS instalada por você. Ele expira; copie um novo token quando precisar reconectar. A extensão mantém o token apenas durante a sessão do navegador.</div><button id="copyToken" class="secondary">Copiar token da sessão</button><p class="fine">Abra uma página de vaga, revise os campos capturados e salve. Você também pode cadastrar vagas manualmente.</p></div>`;$('copyToken').onclick=e=>busy(e.currentTarget,async()=>{const {data,error}=await client.auth.getSession();if(error||!data.session)throw Error('Sessão indisponível. Entre novamente.');await navigator.clipboard.writeText(data.session.access_token);toast('Token copiado. Cole somente na extensão CareerOS.')})}
$('closeJob').onclick = $('cancelJob').onclick = () => $('jobDialog').close();
$('jobForm').onsubmit = event => {
  event.preventDefault();
  const owner = session?.user.id;
  const data = Object.fromEntries(new FormData(event.currentTarget));
  const id = data.id;
  delete data.id;
  if (!owner) return;
  busy(event.submitter, async () => {
    const saved = await api(id ? `/api/jobs/${id}` : '/api/jobs', {
      method: id ? 'PATCH' : 'POST', body: JSON.stringify(data),
    }, owner);
    if (session?.user.id !== owner) return;
    $('jobDialog').close();
    if (tab === 'discover' && !id) {
      jobs = [saved, ...jobs];
      document.querySelectorAll('[data-discover-save]').forEach(button => {
        if (button.dataset.url === saved.url) {
          button.disabled = true;
          button.textContent = 'Já salva';
        }
      });
    } else {
      await reload();
    }
    toast('Vaga salva.');
  });
};
$('logout').onclick=e=>busy(e.currentTarget,async()=>{apiKey='';aiResult='';const {error}=await client.auth.signOut();if(error)throw error;showSession(null);toast('Você saiu da conta.')});$('mobileLogout').onclick=()=>$('logout').click();window.addEventListener('hashchange',setTab);
const authReturn = new URLSearchParams(location.hash.slice(1));
let recovery = authReturn.get('type') === 'recovery';
const signupReturn = authReturn.get('type') === 'signup' && authReturn.has('access_token');

function finishAuthTransition() {
  $('auth-transition').classList.add('hidden');
}

function showSignupWelcome(openDashboard) {
  const transition = $('auth-transition');
  transition.classList.add('auth-transition-success');
  $('auth-transition-title').textContent = 'E-mail confirmado!';
  $('auth-transition-description').textContent = 'Sua conta está pronta. Boas-vindas ao CareerOS.';
  const button = $('auth-transition-continue');
  button.classList.remove('hidden');
  button.onclick = () => busy(button, openDashboard);
  button.focus();
}

(async () => {
  if (signupReturn) {
    $('auth-transition-title').textContent = 'Confirmando seu e-mail';
    $('auth-transition-description').textContent = 'Estamos verificando o link e preparando sua conta.';
  }
  try {
    const response = await fetch('/api/config');
    if (!response.ok) throw Error('Não foi possível carregar a configuração.');
    const config = await response.json();
    if (!config.configured || !window.supabase) throw Error('Login indisponível neste ambiente.');
    const redirectTo = location.origin + '/';
    client = window.supabase.createClient(config.supabase_url, config.supabase_anon_key, {
      auth: {persistSession: true, autoRefreshToken: true, detectSessionInUrl: true},
    });
    const authView = window.mountCareerAuth(client, redirectTo);
    const applySession = next => {
      if (recovery && next) {
        showSession(null);
        authView.recover();
      } else {
        recovery = false;
        showSession(next);
      }
    };
    authView.onRecovered(async () => {
      recovery = false;
      const {data} = await client.auth.getSession();
      showSession(data.session);
      toast('Senha atualizada.');
    });
    let initializing = true;
    let awaitingWelcome = false;
    client.auth.onAuthStateChange((event, next) => {
      if (event === 'PASSWORD_RECOVERY') recovery = true;
      if (initializing || awaitingWelcome) return;
      if (['PASSWORD_RECOVERY', 'SIGNED_IN', 'INITIAL_SESSION', 'SIGNED_OUT'].includes(event)) {
        setTimeout(() => applySession(next), 0);
      } else if (event === 'TOKEN_REFRESHED' && !recovery) {
        session = next;
      }
    });
    setTab();
    const {data, error} = await client.auth.getSession();
    if (error) throw error;
    if (signupReturn && data.session && !recovery) {
      const verified = await client.auth.getUser();
      if (verified.error || verified.data.user?.id !== data.session.user.id ||
          !verified.data.user.email_confirmed_at) {
        throw Error('Não foi possível confirmar a conta.');
      }
      awaitingWelcome = true;
      showSignupWelcome(async () => {
        const {data: latest, error: sessionError} = await client.auth.getSession();
        awaitingWelcome = false;
        finishAuthTransition();
        const next = !sessionError && latest.session?.user.id === verified.data.user.id
          ? latest.session : null;
        showSession(next);
        if (next) {
          $('pageTitle').setAttribute('tabindex', '-1');
          $('pageTitle').focus();
        } else {
          toast('Sua sessão expirou. Entre novamente.', true);
        }
      });
    } else {
      finishAuthTransition();
      applySession(data.session);
      if (!data.session && (signupReturn || authReturn.has('error'))) {
        toast('O link não pôde ser validado. Entre ou solicite um novo link.', true);
      }
    }
    initializing = false;
    const availability = await fetch('/api/auth/providers').then(r => r.json()).catch(() => null);
    authView.providers(Array.isArray(availability?.providers) ? availability.providers : []);
  } catch {
    finishAuthTransition();
    $('gate').classList.remove('hidden');
    window.showCareerAuthError('Não foi possível iniciar o login. Atualize a página e tente novamente.');
  }
})();


function renderData(){
 $('view').innerHTML=`<div class="card"><h2>Uma cópia dos seus dados</h2><p>Exporte o perfil, todas as vagas, o histórico de IA e os currículos armazenados na sua conta.</p><p>O ZIP contém os arquivos originais, registros em JSON e um manifesto de integridade SHA-256. Chaves de IA e tokens de acesso não são incluídos.</p><div class="notice">O arquivo contém dados pessoais e não é criptografado. Guarde-o em um dispositivo seu e não o publique. Evite editar a conta em outras abas durante a exportação.</div><p class="fine">Limite: 64 MiB e 10.000 registros por categoria. A exportação é manual e não substitui backup automático do servidor. A importação/restauração cloud ainda não está disponível.</p><button id="exportAccount">Baixar minha cópia em ZIP</button></div>`;
 $('exportAccount').onclick=e=>busy(e.currentTarget,async()=>{
  const owner=session?.user.id;
  const {data,error}=await client.auth.getSession();
  if(error||!data.session||data.session.user.id!==owner)throw Error('Entre novamente na sua conta antes de exportar.');
  const response=await fetch('/api/workspace/export.zip',{headers:{Authorization:`Bearer ${data.session.access_token}`}});
  if(!response.ok){const problem=await response.json().catch(()=>({}));throw Error(typeof problem.detail==='string'?problem.detail:'Não foi possível exportar os dados.');}
  const blob=await response.blob();
  if(session?.user.id!==owner)return;
  const url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;link.download='CareerOS-workspace.zip';document.body.append(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),10000);toast('Cópia preparada. Confira o download no seu navegador.');
 });
}
