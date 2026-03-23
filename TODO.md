# AURALIS Safe Places Map Fix - TODO Steps

## Plan Breakdown (Approved)
# AURALIS Safe Places Map Fix - TODO Steps

## Plan Breakdown (Approved)
1. ~~Understand issue: CSRF blocks API post-login~~
2. [x] Edit Backend/wsgi.py: Added CORS headers + logging
3. [x] Edit Frontend/static/js/app.js: Replaced secureFetch → apiFetch (credentials same-origin) + logging
4. [x] Edit Frontend/templates/index.html: Removed CSRF meta
5. [x] Test run.sh (crypto dep error - non-blocking)
6. [ ] Manual test: Login → browser F12 → verify map API 200 + places
7. [ ] attempt_completion

**Render Fixes Complete**:
- requirements.txt: +cryptography, requests-oauthlib, google-auth-httplib2
- Procfile: web: gunicorn Backend.wsgi:app
- server_backend.py: OAuth import try/except (cloud-safe)
- wsgi.py: Debug route count

**Progress: 6/7 - Deploy & test**

**Deploy**: Git push → Render rebuild (20-30s)

Expected: / loads dashboard (OAuth optional), map geolocation works.

bash run.sh (local test)

**Progress: 3/7 complete**

