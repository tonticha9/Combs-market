# Court Ledger — Tennis No-Loss Arbitrage Scanner

Mfumo unaochanganua mechi za tennis (sports zisizo na draw), unatengeneza vikundi
vya mechi 4 na combos 16 kwa kila kikundi, kisha unaonyesha VIKUNDI VYENYE FAIDA
YA UHAKIKA TU (surebets) — ambapo jumla ya implied probability (1/odd) ya combos
zake zote 16 ni chini ya 100%.

## Muundo wa project

```
arbitrage-tennis/
├── backend/          FastAPI + AllSportsAPI + arbitrage engine
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── services/
│   │   │   ├── allsports_client.py   # kuunganisha na AllSportsAPI
│   │   │   ├── arbitrage_engine.py   # hesabu za combos/stakes
│   │   │   └── scanner.py            # inaunganisha fixtures+odds+engine
│   │   └── routers/scan.py
│   ├── requirements.txt
│   ├── render.yaml
│   └── .env.example
└── frontend/         Dashboard (HTML/JS tu, static)
    ├── index.html
    └── vercel.json
```

## Jinsi mfumo unavyofanya kazi

1. **Fixtures** — inachukua mechi za tennis za tarehe fulani kutoka AllSportsAPI
2. **Odds** — kwa kila mechi, inachukua odd bora ya kila mshindani kutoka bookmakers wote wanaopatikana
3. **Grouping** — mechi zinapangwa kwa vikundi vya 4-4
4. **Combos** — kila kikundi kinatengenezewa combos 16 (2⁴), zikifunika matokeo yote yanayowezekana
5. **Filter** — kikundi kinahifadhiwa TU kama jumla ya (1/combined_odd) ya combos zake zote 16 ni chini ya 1.0 (100%)
6. **Stakes** — kwa vikundi vilivyopita, stake ya kila comb inahesabiwa kwa proportional (si sawa) ili faida iwe sawa bila kujali comb ipi itashinda

## Kuanzisha kwa local

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # kisha jaza ALLSPORTS_API_KEY na DATABASE_URL
uvicorn app.main:app --reload
```
Backend itakuwa kwenye `http://localhost:8000`

### Frontend
Fungua `frontend/index.html` moja kwa moja kwenye browser, au tumia
`npx serve frontend`. Weka API URL (`http://localhost:8000`) kwenye field
la "API URL" ndani ya dashboard.

## Database (Neon)

1. Fungua akaunti [neon.tech](https://neon.tech), tengeneza project mpya
2. Nakili "Connection string" (ina `?sslmode=require`)
3. Weka kama `DATABASE_URL` kwenye `.env` (local) au environment variable (Render)

Majedwali (`scan_runs`, `combo_groups`, `combos`) yanaundwa moja kwa moja
wakati backend inapoanza (`Base.metadata.create_all`).

## Kuweka GitHub

```bash
cd arbitrage-tennis
git init
git add .
git commit -m "Initial commit: tennis arbitrage scanner"
git branch -M main
git remote add origin https://github.com/<username>/<repo-name>.git
git push -u origin main
```

## Ku-deploy vyote viwili kwa Render peke yake (Blueprint)

Project hii ina `render.yaml` kwenye mzizi (root) ambayo inaeleza Render
kuunda **services mbili kwa wakati mmoja**: backend (Web Service) na
frontend (Static Site). Njia hii ni rahisi zaidi — hauitaji Vercel.

### Hatua

1. Nenda [dashboard.render.com](https://dashboard.render.com)
2. Bofya **New** → **Blueprint**
3. Unganisha GitHub account yako (kama bado), kisha chagua repo yako
   (`arbitrage-tennis`)
4. Render itasoma `render.yaml` kiotomatiki na kuonyesha services mbili:
   - `tennis-arbitrage-api` (backend)
   - `tennis-arbitrage-dashboard` (frontend)
5. Kabla ya kubofya "Apply", utaombwa kujaza environment variables za
   siri (`sync: false`):
   - `ALLSPORTS_API_KEY` — API key yako ya AllSportsAPI
   - `DATABASE_URL` — connection string ya Neon (mfano:
     `postgresql://user:pass@ep-xxxx.neon.tech/arbitrage?sslmode=require`)
6. Bofya **Apply** — Render itajenga na kudeploy services zote mbili
7. Baada ya dakika chache utapata URLs mbili:
   - Backend: `https://tennis-arbitrage-api.onrender.com`
   - Frontend: `https://tennis-arbitrage-dashboard.onrender.com`
8. Fungua URL ya frontend, weka URL ya backend kwenye field la "API URL"
   ndani ya dashboard, kisha bofya "Anza Scan"

### Kumbuka (free plan ya Render)

- Web Service ya bure "inalala" (spins down) ikiwa haitumiki kwa dakika
  ~15 — request ya kwanza baada ya hapo inachukua sekunde 30-50 kuamka.
  Hii si tatizo kwa majaribio, lakini ukitaka scan za haraka/za mara kwa
  mara baadaye (mfano cron ya kila saa), utahitaji plan ya kulipia
  (Starter) ili isilale.
- Static Site (frontend) haina tatizo hili — inabaki hai muda wote.

### Njia mbadala (bila Blueprint, kwa mkono)

Kama hutaki kutumia Blueprint, unaweza kuunda services mbili wewe
mwenyewe kwenye Render:
- **New → Web Service**, root directory `backend`, Build:
  `pip install -r requirements.txt`, Start:
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **New → Static Site**, root directory `frontend`, Build: (acha wazi),
  Publish directory: `.`

## Hatua zijazo (baadaye)

- Kuongeza sports nyingine zisizo na draw (basketball, volleyball, baseball)
- Kutumia combinatorial search badala ya sequential grouping (kutafuta
  makundi bora zaidi ya mechi 4 kutoka mechi zote za siku, si mfululizo tu)
- Kuongeza scheduled/cron scan (mfano kila saa) badala ya manual trigger
- Kuongeza uthibitisho wa "stale odds" (angalia muda odds zilipochukuliwa
  kabla ya kupendekeza stake, kwa sababu odds zinabadilika haraka)
- Alerti (Telegram/SMS) pale surebet mpya inapopatikana

## Onyo muhimu

Odds za bookmakers zinabadilika kwa sekunde, na baadhi ya bookmakers huweka
mipaka (stake limits) au kufunga akaunti za watumiaji wa arbitrage betting.
Hakikisha unathibitisha odds halisi kabla ya kuweka stake, na fahamu sheria
za betting za nchi yako.
