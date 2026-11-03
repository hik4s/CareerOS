import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import { GoogleIcon, GitHubIcon } from './icons';

const modes = {
  login: ['Bem-vindo de volta', 'Entre para continuar de onde parou.', 'Entrar'],
  signup: ['Crie sua conta', 'Comece a organizar seu próximo passo.', 'Criar conta'],
  reset: ['Recupere seu acesso', 'Enviaremos um link para você escolher outra senha.', 'Enviar link'],
  recover: ['Defina uma nova senha', 'Use pelo menos 8 caracteres.', 'Salvar senha'],
};

const messages = {
  invalid_credentials: 'E-mail ou senha inválidos.',
  email_not_confirmed: 'Confirme seu e-mail antes de entrar.',
  weak_password: 'Escolha uma senha mais forte.',
  email_address_not_authorized: 'O envio de e-mails ainda está restrito neste ambiente.',
  over_email_send_rate_limit: 'Aguarde antes de solicitar outro e-mail.',
};

function Auth({ client, redirectTo, bridge, startupError }) {
  const [mode, setMode] = useState('login');
  const [providers, setProviders] = useState([]);
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [visible, setVisible] = useState(false);
  const [pending, setPending] = useState(false);
  const [feedback, setFeedback] = useState(null);

  function changeMode(next) {
    setMode(next);
    setPassword('');
    setVisible(false);
    setFeedback(null);
  }

  bridge.providers = setProviders;
  bridge.recover = () => { if (mode !== 'recover') changeMode('recover'); };

  async function submit(event) {
    event.preventDefault();
    setPending(true);
    setFeedback(null);
    try {
      let result;
      if (mode === 'login') result = await client.auth.signInWithPassword({email: email.trim(), password});
      if (mode === 'signup') result = await client.auth.signUp({email: email.trim(), password, options: {emailRedirectTo: redirectTo}});
      if (mode === 'reset') result = await client.auth.resetPasswordForEmail(email.trim(), {redirectTo});
      if (mode === 'recover') result = await client.auth.updateUser({password});
      if (result.error) throw result.error;
      setPassword('');
      if (mode === 'recover') {
        changeMode('login');
        await bridge.recovered();
      }
      if (mode === 'signup' && !result.data.session) setFeedback({text: 'Confira seu e-mail para confirmar a conta.'});
      if (mode === 'reset') setFeedback({text: 'Se houver uma conta para esse endereço, você receberá um link.'});
    } catch (error) {
      setFeedback({error: true, text: messages[error.code] || 'Não foi possível concluir. Tente novamente em instantes.'});
    } finally {
      setPending(false);
    }
  }

  async function social(provider) {
    setPending(true);
    setFeedback(null);
    try {
      const {error} = await client.auth.signInWithOAuth({provider, options: {redirectTo}});
      if (error) throw error;
    } catch {
      setPending(false);
      setFeedback({error: true, text: 'Não foi possível iniciar o login social.'});
    }
  }

  const [heading, description, action] = modes[mode];
  return (
    <div className="auth-layout">
      <aside className="auth-story">
        <a className="brand" href="/"><span className="brand-icon">C</span>Career<span>OS</span></a>
        <div className="auth-story-copy">
          <span className="auth-kicker">SUA CARREIRA, COM DIREÇÃO</span>
          <h1>Organize seu próximo <em>grande passo.</em></h1>
          <p>Vagas, currículo e preparação em um só lugar.</p>
          <div className="auth-preview" aria-hidden="true">
            <span className="auth-preview-icon">↗</span>
            <div><strong>Seu espaço de evolução</strong><small>Perfil · Vagas · Preparação</small></div>
          </div>
        </div>
        <small>CAREEROS / ESPAÇO PESSOAL</small>
      </aside>
      <main className="auth-panel">
        <div className="auth-card">
          {['login','signup'].includes(mode) && (
            <div className="auth-switch" role="group" aria-label="Tipo de acesso">
              <button type="button" disabled={pending} aria-pressed={mode === 'login'} onClick={() => changeMode('login')}>Entrar</button>
              <button type="button" disabled={pending} aria-pressed={mode === 'signup'} onClick={() => changeMode('signup')}>Criar conta</button>
            </div>
          )}
          <div className="auth-copy" key={mode}>
            <h2>{heading}</h2>
            <p>{description}</p>
          </div>
          {startupError ? <p role="alert">{startupError}</p> : (
            <form onSubmit={submit} aria-busy={pending}>
              {mode !== 'recover' && <label htmlFor="auth-email">E-mail<input id="auth-email" type="email" autoComplete="email" placeholder="voce@exemplo.com" value={email} onChange={e => setEmail(e.target.value)} required /></label>}
              {mode !== 'reset' && (
                <label htmlFor="auth-password">Senha
                  <span className="auth-password">
                    <input id="auth-password" type={visible ? 'text' : 'password'} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={mode === 'login' ? undefined : 8} value={password} onChange={e => setPassword(e.target.value)} required />
                    <button type="button" className="auth-link" aria-pressed={visible} onClick={() => setVisible(!visible)}>{visible ? 'Ocultar' : 'Mostrar'}</button>
                  </span>
                </label>
              )}
              {mode === 'login' && <button type="button" className="auth-link auth-forgot" disabled={pending} onClick={() => changeMode('reset')}>Esqueci a senha</button>}
              {mode === 'signup' && <small className="auth-hint">Use pelo menos 8 caracteres.</small>}
              <button className="auth-primary" type="submit" disabled={pending}>{pending ? 'Aguarde…' : action}<span aria-hidden="true">→</span></button>
            </form>
          )}
          {feedback && <p className={feedback.error ? 'auth-feedback auth-error' : 'auth-feedback'} role={feedback.error ? 'alert' : 'status'}>{feedback.text}</p>}
          {mode === 'reset' && <button type="button" className="auth-link" disabled={pending} onClick={() => changeMode('login')}>← Voltar para entrar</button>}
          {providers.length > 0 && ['login','signup'].includes(mode) && (
            <>
              <div className="auth-divider">ou continue com</div>
              <div className="auth-social">
                {providers.includes('google') && <button type="button" disabled={pending} onClick={() => social('google')}><GoogleIcon /> Google</button>}
                {providers.includes('github') && <button type="button" disabled={pending} onClick={() => social('github')}><GitHubIcon /> GitHub</button>}
              </div>
            </>
          )}
          <p className="auth-hint auth-footer">Seu espaço é privado e vinculado à sua conta.</p>
        </div>
      </main>
    </div>
  );
}

const root = createRoot(document.getElementById('auth-root'));
window.mountCareerAuth = (client, redirectTo) => {
  const bridge = {onRecovered: handler => { bridge.recovered = handler; }};
  flushSync(() => root.render(<Auth client={client} redirectTo={redirectTo} bridge={bridge} />));
  return bridge;
};
window.showCareerAuthError = startupError => root.render(<Auth bridge={{}} startupError={startupError} />);
