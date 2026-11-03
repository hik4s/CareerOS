/* Shared by the popup, service worker, and contract tests. */
function careerOrigin(value) {
  const u = new URL(value.trim());
  const loopback = ['localhost', '127.0.0.1', '[::1]'].includes(u.hostname);
  if ((u.protocol !== 'https:' && !(u.protocol === 'http:' && loopback)) || u.username || u.password || u.pathname !== '/' || u.search || u.hash) {
    throw new Error('Use somente a origem HTTPS do CareerOS (sem caminho). HTTP apenas em localhost.');
  }
  return u.origin;
}
if (typeof module !== 'undefined') module.exports = {careerOrigin};
