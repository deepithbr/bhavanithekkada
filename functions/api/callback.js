/*
 * Step two of the Decap sign-in: trade the code for a token, hand it back.
 *
 * GitHub returns the popup here with a one-time code. This function swaps it
 * for an access token server-side, where the client secret lives, and then
 * serves a small page that performs Decap's postMessage handshake with the
 * editor window that opened the popup: the popup announces itself, the CMS
 * answers, the popup delivers the token and closes. The token goes to the
 * CMS in the browser and nowhere else; this function stores nothing.
 */

const escapeJs = (s) => String(s).replace(/[\\'"<>]/g, (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));

export async function onRequestGet({ request, env }) {
  if (!env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET) {
    return new Response("OAuth is not configured.", { status: 503 });
  }
  const code = new URL(request.url).searchParams.get("code");
  if (!code) {
    return new Response("Missing code.", { status: 400 });
  }

  const r = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      client_id: env.GITHUB_CLIENT_ID,
      client_secret: env.GITHUB_CLIENT_SECRET,
      code,
    }),
  });
  const data = await r.json();

  const ok = Boolean(data.access_token);
  const payload = ok
    ? `authorization:github:success:${JSON.stringify({
        token: data.access_token,
        provider: "github",
      })}`
    : `authorization:github:error:${JSON.stringify({
        error: data.error || "no_token",
      })}`;

  const html = `<!doctype html>
<meta charset="utf-8">
<title>Signing in…</title>
<script>
  (function () {
    // Decap's handshake: the popup says hello, the editor answers, the popup
    // delivers the result. The wildcard origin on the hello is part of the
    // published protocol; the payload itself only goes to the window that
    // answers, and this page closes immediately after.
    function deliver(e) {
      window.removeEventListener("message", deliver);
      e.source.postMessage('${escapeJs(payload)}', e.origin);
      window.close();
    }
    window.addEventListener("message", deliver);
    (window.opener || window.parent).postMessage("authorizing:github", "*");
  })();
</script>
<p>Signing in&hellip; you can close this window.</p>`;

  return new Response(html, {
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}
