# Her journal editor: the one-time setup

The code is in place: `/admin` is the editor, and `/api/auth` plus
`/api/callback` handle sign-in. Four steps remain, all yours, all one-time.
After them, Bhavani opens `https://<site>/admin`, signs in with her own
GitHub account, writes, presses **Publish**, and the site rebuilds itself
with her entry live. Total time: about fifteen minutes.

## 1. Give Bhavani a login

She needs a free GitHub account (github.com/join — username and password,
nothing else). Then, on the repo:

- github.com/deepithbr/bhavanithekkada → **Settings → Collaborators →
  Add people** → her username → role **Write**.
- She accepts the email invitation.

That account is her login for the editor, hers alone, and it can be removed
any time.

## 2. Create the OAuth app

github.com → your profile → **Settings → Developer settings → OAuth Apps →
New OAuth App**:

- Application name: `Bhavani journal editor`
- Homepage URL: the live site, e.g. `https://bhavanithekkada.pages.dev`
- Authorization callback URL: `https://bhavanithekkada.pages.dev/api/callback`

Register, then **Generate a new client secret**. Keep the Client ID and the
secret for step 3; the secret is shown once.

## 3. Give Cloudflare the keys

Cloudflare dashboard → the Pages project → **Settings → Environment
variables → Production**:

- `GITHUB_CLIENT_ID` = the Client ID
- `GITHUB_CLIENT_SECRET` = the secret (mark it as a secret)

Redeploy once so the functions pick them up. The secret lives only here;
it is never in the repository and never reaches a browser.

## 4. Point the editor at the site

In `admin/config.yml`, set `base_url` to the same live origin used in
step 2, commit, push. Done.

## How publishing works after that

She writes at `/admin`. The **Draft** switch is on by default; while it is
on, the entry is saved in the repo but stays off the site. Switching it off
and pressing Publish makes the entry live on the next build, about a minute
later. Every entry is an ordinary file in `content/journal`, so nothing she
writes can be lost, and you can always edit or roll back from the repo.

## If sign-in ever fails

- A 503 from `/api/auth` means the environment variables are missing.
- A GitHub error page means the callback URL in the OAuth app does not
  match the site origin exactly.
- "Not Found" after sign-in means her account has not accepted the
  collaborator invitation.
