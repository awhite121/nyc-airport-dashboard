# How to Update the Existing GitHub Repo

Your existing repo is:

```text
https://github.com/awhite121/NYC-Taxi-Trip-Duration-Late-Risk-Prediction
```

## Option A — Replace the repo contents with this cleaned version

```bash
cd ~/Downloads
unzip nyc-taxi-airport-risk-github.zip
cd NYC-Taxi-Trip-Duration-Late-Risk-Prediction

# backup old repo locally first if you want
# then copy the cleaned files into the cloned repo
```

## Recommended terminal flow

```bash
git clone https://github.com/awhite121/NYC-Taxi-Trip-Duration-Late-Risk-Prediction.git
cd NYC-Taxi-Trip-Duration-Late-Risk-Prediction

# copy the cleaned package contents into this folder, then:
git status
git add .
git commit -m "Upgrade project structure, notebooks, docs, and website assets"
git push origin main
```

## Before pushing

Confirm the 367MB raw `taxi_data.csv` is not committed:

```bash
find . -type f -size +50M
```

The raw file is intentionally excluded from `.gitignore`.
