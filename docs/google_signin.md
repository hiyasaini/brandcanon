# Google sign-in and sign-up

BrandCanon can let people sign in or sign up with a Google account. It uses Streamlit's built-in OpenID Connect login
(`st.login`). **The Google buttons appear only when the deployment has Google credentials**, so nobody ever sees a button
that cannot work.

## How it behaves
- **Sign in with Google:** works for a person whose Google e-mail is already on a BrandCanon account (a Brand Manager adds
  it in Settings → Profile & people → *Google e-mail*, or the person created their workspace with Google).
- **Sign up with Google:** a Google e-mail BrandCanon has not seen asks for a brand name, creates the workspace and makes
  that person its Brand Manager. No password is stored for a Google-only account.
- An e-mail that Google has not verified is refused. An unknown e-mail never joins an existing workspace by itself; a Brand
  Manager must add it.
- **Sign out** asks for confirmation, then ends both the BrandCanon session and the Google session in that browser.

## One-time setup (about 10 minutes)
1. Google Cloud Console → *APIs & Services* → *OAuth consent screen*: choose *External*, give it a name, add yourself as a
   test user (or publish it).
2. *Credentials* → *Create credentials* → *OAuth client ID* → *Web application*.
   Under **Authorized redirect URIs** add `https://YOUR-APP-NAME.streamlit.app/oauth2callback`
   (and `http://localhost:8501/oauth2callback` for local use).
3. Copy the client ID and client secret.
4. In Streamlit Community Cloud → your app → *Settings* → *Secrets*, paste the `[auth]` block from
   `.streamlit/secrets.toml.example` with your values (locally, put it in `.streamlit/secrets.toml`).
5. `Authlib` is already in `requirements.txt`. Reboot the app. The "Continue with Google" button now shows on the sign-in page.

## Honest limits
- It was written against Streamlit's documented `st.login` API and checked with unit tests and a browser run with
  placeholder credentials (the button appears, and is absent without credentials). It has **not** been run against a real
  Google account in this repository's test runs, because that needs your own OAuth client.
- On Streamlit Community Cloud the per-visitor demo databases are temporary, so accounts created with Google there last as
  long as that visitor's copy does.
- Sign-in is still prototype-grade: no multi-factor control beyond what Google itself applies.
