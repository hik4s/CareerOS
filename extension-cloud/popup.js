const status = document.getElementById('status');
const originInput = document.getElementById('origin');
const tokenInput = document.getElementById('token');
chrome.storage.local.get('careerOrigin').then(v => {originInput.value = v.careerOrigin || '';});
function show(text) { status.textContent = text; }
document.getElementById('connect').addEventListener('click', async () => {
  try {
    const origin = careerOrigin(originInput.value);
    const token = tokenInput.value.trim();
    if (!token || token.length > 16000 || /\s/.test(token)) throw new Error('Cole o token de acesso copiado no painel.');
    // Request only this origin, directly from the user's click gesture.
    const allowed = await chrome.permissions.request({origins: [origin + '/*']});
    if (!allowed) throw new Error('Permita acesso ao endereço do seu JobsFinder para conectar.');
    const previous = await chrome.storage.local.get('careerOrigin');
    await chrome.storage.session.remove(['careerToken', 'careerTokenOrigin']);
    await chrome.storage.local.set({careerOrigin: origin});
    await chrome.storage.session.set({careerToken: token, careerTokenOrigin: origin});
    tokenInput.value = '';
    if (previous.careerOrigin && previous.careerOrigin !== origin) await chrome.permissions.remove({origins:[previous.careerOrigin+'/*']});
    show('Conectado nesta sessão. Abra uma vaga e clique em Capturar.');
  } catch (e) { show(e.message); }
});
document.getElementById('capture').addEventListener('click', async () => {
  try {
    const [tab] = await chrome.tabs.query({active:true,currentWindow:true});
    if (!tab?.id) throw new Error('Abra uma página de vaga.');
    const result = await chrome.runtime.sendMessage({type:'capture',tabId:tab.id});
    show(result.ok ? 'Vaga salva. Revise o conteúdo no painel JobsFinder.' : result.error);
  } catch (e) { show(e.message); }
});
document.getElementById('logout').addEventListener('click', async () => {
  const previous = await chrome.storage.local.get('careerOrigin');
  await chrome.storage.session.remove(['careerToken','careerTokenOrigin']);
  await chrome.storage.local.remove('careerOrigin');
  if (previous.careerOrigin) await chrome.permissions.remove({origins:[previous.careerOrigin+'/*']});
  tokenInput.value=''; originInput.value=''; show('Desconectado.');
});
