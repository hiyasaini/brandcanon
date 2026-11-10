# Share BrandCanon as a link

Two ways to give judges a link that opens on any device (laptop, tablet or phone), with nothing to install.

| | Streamlit Community Cloud (recommended) | Quick tunnel from your Mac |
|---|---|---|
| Link | Permanent, e.g. `https://brandcanon.streamlit.app` | Temporary `https://<random>.trycloudflare.com` |
| Needs your Mac running | No | Yes, with the Terminal window open |
| Set-up time | About 10 minutes, once | About 2 minutes |
| Cost | Free | Free, no account |

In both cases set `BRANDCANON_PUBLIC=1`. Every visitor then works on **their own private copy** of the NovaTech demo, so
one judge emptying the workspace or approving content never changes what another judge sees. The copy is kept for that
browser tab, including across page reloads (the link carries a private `?s=…` token); a new tab starts a fresh copy.

Gemini switches itself on when `GEMINI_API_KEY` is present, and the app checks the connection by itself at start-up:
the sidebar reads **Live Gemini · verified** without anyone pressing a test button. Every judge's requests use your
key's quota. If the key fails, every result says so and the deterministic checks still run.

## Option A — Streamlit Community Cloud (permanent link)

1. **Put the code on GitHub.** Create a free account at github.com, then a new repository called `brandcanon`
   (Public or Private both work). Upload the contents of the `BrandCanon` folder:
   - with Terminal (Git is offered by macOS the first time you type `git`):
     ```bash
     cd ~/Downloads/BrandCanon
     git init && git add . && git commit -m "BrandCanon"
     git branch -M main
     git remote add origin https://github.com/<your-user>/brandcanon.git
     git push -u origin main
     ```
     GitHub asks for your username and a personal access token as the password
     (github.com → Settings → Developer settings → Personal access tokens).
   - or in the browser: repository → **Add file → Upload files**, and drag in everything inside `BrandCanon`.
     In Finder press **Cmd + Shift + .** first so the hidden `.streamlit` folder (the theme) is included.
   `.gitignore` already keeps `.env`, `.venv` and the database out of GitHub. Never upload `.env`.
2. **Deploy.** Go to share.streamlit.io, sign in with GitHub → **Create app** → **Deploy a public app from GitHub**.
   Repository `<your-user>/brandcanon`, branch `main`, main file `app.py`, and choose an App URL such as `brandcanon`.
3. **Advanced settings** (before pressing Deploy):
   - Python version: **3.12**.
   - Secrets — paste, with your own key:
     ```toml
     GEMINI_API_KEY = "paste-your-key-here"
     GEMINI_MODEL = "gemini-3.5-flash-lite"
     BRANDCANON_PUBLIC = "1"
     ```
4. Press **Deploy**. The first build takes a few minutes. Open the link, sign in as Neha (`novatech-demo`) and check that
   the sidebar shows **Live Gemini · verified**.
5. Apps on the free tier go to sleep after a period without visitors. Open the link yourself shortly before judging;
   if you see "This app has gone to sleep", press the wake-up button and wait about a minute.

To update the live app later, push the new code to the same repository (or upload the changed files); it redeploys
by itself.

## Option B — Quick tunnel from your Mac (instant, temporary)

1. Start BrandCanon in public mode:
   ```bash
   cd ~/Downloads/BrandCanon
   source .venv/bin/activate
   BRANDCANON_PUBLIC=1 streamlit run app.py
   ```
2. In a **second** Terminal window, download Cloudflare's tunnel program once and start a tunnel
   (Apple silicon shown; on an Intel Mac use `cloudflared-darwin-amd64.tgz`):
   ```bash
   cd ~/Downloads
   curl -L -o cloudflared.tgz https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz
   tar -xzf cloudflared.tgz
   ./cloudflared tunnel --url http://localhost:8501
   ```
3. It prints a `https://….trycloudflare.com` address. Send that link to the judges. It works while both Terminal
   windows stay open and the Mac stays awake (System Settings → Lock Screen → never turn off the display while
   presenting). Each new tunnel gets a new address.

Quick tunnels need no account, have no uptime guarantee and allow up to 200 requests in flight at once — fine for a
judging session, not for permanent hosting.
