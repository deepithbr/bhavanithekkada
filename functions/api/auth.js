/*
 * Step one of the Decap sign-in: send the editor to GitHub.
 *
 * The CMS opens this endpoint in a popup. All it does is bounce the popup to
 * GitHub's authorisation page carrying our OAuth app's client id and a state
 * value; GitHub sends the user back to /api/callback with a one-time code.
 * The secret never appears here, and nothing about this endpoint is worth
 * caching.
 *
 * Requires two environment variables on the Pages project:
 *   GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET  (the OAuth app in SETUP-DECAP.md)
 */

export async function onRequestGet({ request, env }) {
  if (!env.GITHUB_CLIENT_ID) {
    return new Response("OAuth is not configured: set GITHUB_CLIENT_ID.", {
      status: 503,
    });
  }
  const url = new URL(request.url);
  const state = crypto.randomUUID();
  const target = new URL("https://github.com/login/oauth/authorize");
  target.searchParams.set("client_id", env.GITHUB_CLIENT_ID);
  target.searchParams.set("redirect_uri", `${url.origin}/api/callback`);
  target.searchParams.set("scope", "repo");
  target.searchParams.set("state", state);
  return Response.redirect(target.toString(), 302);
}
