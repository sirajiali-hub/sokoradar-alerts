# SokoRadar app: food price alerts for Kenyan markets

The app shows which Kenyan markets have unusually high prices for maize, beans, sorghum and potatoes, explains why in plain words, and lets county teams download a list of markets to act on. It is built around the decisions of county governments, NDMA and NGOs.

## Pages (in the order of the demo)

| Page | Question it answers | Main users |
|---|---|---|
| 1. This month | Where are prices unusually high now, and where will they be in the next 3 months? Map, action list with suggested actions, county bulletin | County governments, NDMA, NGOs |
| 2. Market check | Why is this market flagged, what does it cost a household, what should people be told? Reasons, bag price, household cost, SMS in English and Kiswahili, rainfall what-if | County officers, NGOs |
| 3. Does it work? | How early did SokoRadar warn in the 2011, 2017 and 2022 droughts, and how does it compare with simple rules? | Judges, analysts, World Bank and WFP |
| 4. About & limits | Data, method, patterns in the data and honest limits | Everyone |

## Folder layout

```
alerts_app/
├── app.py                 # entry point and menu
├── app_pages/             # one file per page
│   ├── overview.py        # This month: headline, cards, map, action list, county bulletin
│   ├── market.py          # Market check: reasons, cost, SMS, price chart, rainfall what-if
│   ├── proof.py           # Does it work?: drought replay with lead time, results, threshold, groups, calibration, drivers
│   └── about.py           # data, method, patterns in the data, limits, feedback
├── src/
│   ├── loaders.py         # cached data loaders
│   ├── alerts.py          # ALPS phases, normal price line, reasons, rainfall what-if
│   ├── actions.py         # suggested actions, bag prices, household cost, SMS (English and Kiswahili), bulletin
│   ├── views.py           # shared tables (ranked list, county summary, warning shares)
│   ├── charts.py          # Plotly charts (the map is drawn as plain shapes, so it works offline)
│   └── style.py           # header, headline banner, badges and cards
├── data/                  # filled by prepare_data.py
├── prepare_data.py        # copies the small data files the app needs into data/
├── requirements.txt       # pinned app dependencies
└── .streamlit/config.toml # theme; hides stack traces from users
```

## Run locally

1. Run `notebooks/modelling/01_eda_review.ipynb`, then all of `05_alerts.ipynb` (Steps 1 to 8 save the alert labels and early warning results).
2. From the `alerts_app` folder:

```bash
pip install -r requirements.txt
python prepare_data.py
python -m streamlit run app.py
```

## Connecting the forecasting model

When the modelling notebook saves `forecasts.csv` to the handoff folder with the columns `admin2, market, crop, pricetype, month, forecast, lower, upper`, run `python prepare_data.py` again. The forecast and its 80% range then appear on the Market check page automatically.

## Deploy to Streamlit Community Cloud

1. Make sure `data/` holds the files from `prepare_data.py` (all small enough for GitHub).
2. Push to GitHub.
3. At share.streamlit.io choose the repo, the branch and the file `alerts_app/app.py`. Under Advanced settings choose Python 3.12.
4. Every push redeploys the app.
