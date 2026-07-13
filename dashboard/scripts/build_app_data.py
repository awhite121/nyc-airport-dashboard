from __future__ import annotations

import json
import math
import os
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor, LGBMClassifier
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get('NYC_TAXI_PROJECT_ROOT', str(Path(__file__).resolve().parents[2])))
OUT = DASHBOARD_ROOT / 'data/app_data.json'
OUT_JS = DASHBOARD_ROOT / 'data/app_data.js'
CSV = ROOT / 'data/processed/taxi_clean_for_modeling.csv'
BENCHMARKS = ROOT / 'models/model_results.json'

# Published taxi-zone centroids for the 63 Manhattan pickup zones in the project.
CENTROIDS = {
4:(-73.97696825691767,40.72375214158478),12:(-74.01556351255896,40.702945834984696),13:(-74.01607915192938,40.712038157074545),24:(-73.96547951516968,40.80197049389964),41:(-73.9512920024351,40.8043339497946),42:(-73.9407716675627,40.81825786111926),43:(-73.96555356545912,40.78247809974788),45:(-73.99815149899052,40.71245931177951),48:(-73.98984464313301,40.76225275531936),50:(-73.99513522075519,40.7662377250419),68:(-73.99991742024714,40.74842755506573),74:(-73.93734560812489,40.80116948058649),75:(-73.94575026755159,40.79001075149541),79:(-73.98593745682462,40.72762019590953),87:(-74.00749598562427,40.70680845166583),88:(-74.01151502922319,40.703357903236146),90:(-73.99697141558369,40.7422786290123),100:(-73.9887865991153,40.75351275872571),107:(-73.98405213268914,40.73682405761896),113:(-73.99430477051165,40.73257907302701),114:(-73.99738026020042,40.72834039137229),116:(-73.94852173020878,40.827012654925355),125:(-74.0074858180095,40.72629041028122),127:(-73.91930823586206,40.86607500072785),137:(-73.97649472376762,40.74043897859643),140:(-73.95473878380501,40.76548408788982),141:(-73.95963474149167,40.76694821638321),142:(-73.9815322063918,40.77363329302705),143:(-73.98764554944394,40.775965228761),144:(-73.99691854183827,40.72088889344528),148:(-73.9908962618473,40.718938359380246),151:(-73.96816833309244,40.79796199310005),152:(-73.95378223705626,40.81797514762945),158:(-74.0089841047853,40.73503540069665),161:(-73.97769793122403,40.75802804352627),162:(-73.97235594352033,40.75668765218885),163:(-73.97756868222719,40.76442140578679),164:(-73.9851563946768,40.748574629356725),166:(-73.96176359682933,40.8094569611253),170:(-73.97849159965224,40.74774579364388),186:(-73.9924375369761,40.748497181405014),194:(-73.92459630024567,40.79100078171126),202:(-73.94995171169585,40.76189974995509),209:(-74.00366456329894,40.709072742793076),211:(-74.00153756565634,40.72388811004175),224:(-73.97659767323339,40.731820636016785),229:(-73.96514579918423,40.75672894163307),230:(-73.98419648907567,40.759817617191835),231:(-74.00787970866403,40.717772736265175),232:(-73.98302455833492,40.71473250693941),233:(-73.97044256869235,40.74991407790215),234:(-73.99045782354735,40.74033744175702),236:(-73.9570116983574,40.78043643718996),237:(-73.9656345353807,40.76861518381156),238:(-73.97304890061594,40.791704934427074),239:(-73.97863194845081,40.78396143031376),243:(-73.93283148761283,40.85710828331433),244:(-73.9413991057364,40.84170877111966),246:(-74.00401512528674,40.75330906598342),249:(-74.00287495910834,40.73457600733173),261:(-74.01302277174901,40.70913894067186),262:(-73.94651035601467,40.77593240314995),263:(-73.951009874818,40.77876585543437),
}
AIRPORT_COORDS = {
    'JFK': {'id':132, 'name':'John F. Kennedy International Airport', 'lon':-73.78653298335013, 'lat':40.64698489239527},
    'LGA': {'id':138, 'name':'LaGuardia Airport', 'lon':-73.87362864289081, 'lat':40.77437570593239},
}
MODEL_FEATURES = ['trip_distance','passenger_count','pickup_hour','pickup_dow','payment_type','airport_code','PULocationID']
DISPLAY_FEATURES = ['Trip distance','Passenger count','Pickup hour','Day of week','Payment type','Airport','Pickup zone']


def clean_float(x, digits=4):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return None
    return round(float(x), digits)


def metrics_reg(y, p):
    return {
        'mae': clean_float(mean_absolute_error(y,p),3),
        'rmse': clean_float(mean_squared_error(y,p) ** .5,3),
        'r2': clean_float(r2_score(y,p),4),
    }


def metrics_clf(y, prob, threshold=.5):
    pred=(prob>=threshold).astype(int)
    return {
        'threshold':threshold,
        'accuracy':clean_float(accuracy_score(y,pred),4),
        'precision':clean_float(precision_score(y,pred,zero_division=0),4),
        'recall':clean_float(recall_score(y,pred,zero_division=0),4),
        'f1':clean_float(f1_score(y,pred,zero_division=0),4),
        'roc_auc':clean_float(roc_auc_score(y,prob),4),
    }


def group_importance(model):
    vals = np.maximum(model.feature_importances_.astype(float), 0)
    total = vals.sum() or 1
    rows = [
        {'feature': label, 'importance': clean_float(val / total, 5)}
        for label, val in zip(DISPLAY_FEATURES, vals)
    ]
    return sorted(rows, key=lambda r: r['importance'], reverse=True)


def main():
    df = pd.read_csv(CSV)
    df['tpep_pickup_datetime'] = pd.to_datetime(df['tpep_pickup_datetime'])
    df['is_late'] = df['is_late'].astype(int)
    df = df.sort_values('tpep_pickup_datetime').reset_index(drop=True)
    split = int(len(df)*.8)
    train, test = df.iloc[:split], df.iloc[split:]

    df['airport_code'] = df['airport'].map({'JFK': 0, 'LGA': 1}).astype(int)
    train, test = df.iloc[:split].copy(), df.iloc[split:].copy()
    reg = LGBMRegressor(
        objective='regression_l1', n_estimators=320, learning_rate=.045, num_leaves=31,
        min_child_samples=24, subsample=.9, colsample_bytree=.9, reg_lambda=.4, random_state=42, n_jobs=1, verbosity=-1
    )
    q80 = LGBMRegressor(
        objective='quantile', alpha=.80, n_estimators=280, learning_rate=.05, num_leaves=31,
        min_child_samples=26, subsample=.9, colsample_bytree=.9, reg_lambda=.45, random_state=42, n_jobs=1, verbosity=-1
    )
    q90 = LGBMRegressor(
        objective='quantile', alpha=.90, n_estimators=280, learning_rate=.05, num_leaves=31,
        min_child_samples=26, subsample=.9, colsample_bytree=.9, reg_lambda=.45, random_state=42, n_jobs=1, verbosity=-1
    )
    clf = LGBMClassifier(
        objective='binary', n_estimators=320, learning_rate=.045, num_leaves=31,
        min_child_samples=24, subsample=.9, colsample_bytree=.9, reg_lambda=.45,
        random_state=42, n_jobs=1, verbosity=-1
    )
    print('Training duration and uncertainty models...')
    reg.fit(train[MODEL_FEATURES], train['duration_min'])
    q80.fit(train[MODEL_FEATURES], train['duration_min'])
    q90.fit(train[MODEL_FEATURES], train['duration_min'])
    print('Training risk model...')
    clf.fit(train[MODEL_FEATURES], train['is_late'])
    pred_reg = reg.predict(test[MODEL_FEATURES])
    prob = clf.predict_proba(test[MODEL_FEATURES])[:,1]

    thresholds=[]
    for t in np.arange(.2,.71,.05):
        m=metrics_clf(test['is_late'].to_numpy(),prob,float(round(t,2)))
        thresholds.append(m)

    # Typical values to complete an inference request before a taxi is booked.
    default_passengers = int(round(df['passenger_count'].median()))
    default_payment = int(df['payment_type'].mode().iloc[0])
    airport_distance = df.groupby('airport')['trip_distance'].median().to_dict()
    zone_air_distance = df.groupby(['PULocationID','airport'])['trip_distance'].median().to_dict()
    zone_air_count = df.groupby(['PULocationID','airport']).size().to_dict()
    exact_count = df.groupby(['PULocationID','airport','pickup_dow','pickup_hour']).size().to_dict()
    exact_actual = df.groupby(['PULocationID','airport','pickup_dow','pickup_hour']).agg(
        actual_mean=('duration_min','mean'),actual_p80=('duration_min',lambda s:s.quantile(.8)),actual_late=('is_late','mean')
    ).to_dict('index')

    zones_base = df[['PULocationID','PU_Zone']].drop_duplicates().sort_values('PU_Zone')
    scenarios=[]
    for row in zones_base.itertuples(index=False):
        zid=int(row.PULocationID)
        for airport, ap in AIRPORT_COORDS.items():
            dist=float(zone_air_distance.get((zid,airport),airport_distance[airport]))
            for dow in range(7):
                for hour in range(24):
                    scenarios.append({
                        'PULocationID':zid,
                        'airport':airport,
                        'trip_distance':dist,
                        'passenger_count':default_passengers,
                        'pickup_hour':hour,
                        'pickup_dow':dow,
                        'payment_type':default_payment,
                    })
    scen=pd.DataFrame(scenarios)
    scen['airport_code'] = scen['airport'].map({'JFK':0,'LGA':1}).astype(int)
    print('Scoring',len(scen),'departure scenarios...')
    scen['predicted_duration']=reg.predict(scen[MODEL_FEATURES])
    scen['late_probability']=clf.predict_proba(scen[MODEL_FEATURES])[:,1]
    scen['p80']=np.maximum(q80.predict(scen[MODEL_FEATURES]), scen['predicted_duration'])
    scen['p90']=np.maximum(q90.predict(scen[MODEL_FEATURES]), scen['p80'])

    pred_lookup={}
    for r in scen.itertuples(index=False):
        key=f'{int(r.PULocationID)}|{r.airport}|{int(r.pickup_dow)}|{int(r.pickup_hour)}'
        exact=exact_actual.get((int(r.PULocationID),r.airport,int(r.pickup_dow),int(r.pickup_hour)),{})
        cnt=int(exact_count.get((int(r.PULocationID),r.airport,int(r.pickup_dow),int(r.pickup_hour)),0))
        support=int(zone_air_count.get((int(r.PULocationID),r.airport),0))
        pred_lookup[key]=[
            clean_float(r.predicted_duration,2),clean_float(max(r.p80,r.predicted_duration),2),
            clean_float(max(r.p90,r.p80),2),clean_float(r.late_probability,4),clean_float(r.trip_distance,2),
            cnt,support,clean_float(exact.get('actual_mean'),2),clean_float(exact.get('actual_p80'),2),clean_float(exact.get('actual_late'),4)
        ]

    zone_stats=[]
    for (zid,name),g in df.groupby(['PULocationID','PU_Zone']):
        lon,lat=CENTROIDS[int(zid)]
        apstats={}
        for ap,ga in g.groupby('airport'):
            apstats[ap]={
                'trips':int(len(ga)), 'avg':clean_float(ga.duration_min.mean(),2),
                'p80':clean_float(ga.duration_min.quantile(.8),2),'lateRate':clean_float(ga.is_late.mean(),4),
                'distance':clean_float(ga.trip_distance.median(),2)
            }
        zone_stats.append({
            'id':int(zid),'name':name,'lon':lon,'lat':lat,'trips':int(len(g)),
            'avg':clean_float(g.duration_min.mean(),2),'p80':clean_float(g.duration_min.quantile(.8),2),
            'lateRate':clean_float(g.is_late.mean(),4),'airports':apstats,
        })
    zone_stats.sort(key=lambda z:z['name'])

    hourly=[]
    for (airport,hour),g in df.groupby(['airport','pickup_hour']):
        hourly.append({'airport':airport,'hour':int(hour),'trips':int(len(g)),'avg':clean_float(g.duration_min.mean(),2),'p80':clean_float(g.duration_min.quantile(.8),2),'lateRate':clean_float(g.is_late.mean(),4)})
    weekdays=[]
    for (airport,dow),g in df.groupby(['airport','pickup_dow']):
        weekdays.append({'airport':airport,'dow':int(dow),'trips':int(len(g)),'avg':clean_float(g.duration_min.mean(),2),'p80':clean_float(g.duration_min.quantile(.8),2),'lateRate':clean_float(g.is_late.mean(),4)})
    airport_stats=[]
    for airport,g in df.groupby('airport'):
        airport_stats.append({'airport':airport,'trips':int(len(g)),'avg':clean_float(g.duration_min.mean(),2),'median':clean_float(g.duration_min.median(),2),'p80':clean_float(g.duration_min.quantile(.8),2),'p90':clean_float(g.duration_min.quantile(.9),2),'lateRate':clean_float(g.is_late.mean(),4),'distance':clean_float(g.trip_distance.median(),2)})

    peak_matrix=[]
    for (dow,hour),g in df.groupby(['pickup_dow','pickup_hour']):
        peak_matrix.append({'dow':int(dow),'hour':int(hour),'avg':clean_float(g.duration_min.mean(),2),'lateRate':clean_float(g.is_late.mean(),4),'trips':int(len(g))})

    with open(BENCHMARKS) as f:
        benchmarks=json.load(f)

    payload={
        'meta':{
            'generatedAt':datetime.now(timezone.utc).isoformat(),
            'source':'NYC yellow taxi airport-trip modeling dataset supplied with the project',
            'tripCount':int(len(df)),
            'zoneCount':int(df.PULocationID.nunique()),
            'dateStart':df.tpep_pickup_datetime.min().isoformat(),
            'dateEnd':df.tpep_pickup_datetime.max().isoformat(),
            'lateRate':clean_float(df.is_late.mean(),4),
            'lateDefinition':'More than 1.2× the typical duration for the same airport, pickup hour, and weekday.',
            'scope':'Manhattan pickups to JFK or LaGuardia; August 2025 historical trips.',
            'mapNote':'Map points are official TLC taxi-zone centroids, not polygon boundaries.',
        },
        'model':{
            'name':'Airport Timing LightGBM ensemble',
            'durationMetrics':metrics_reg(test.duration_min,pred_reg),
            'riskMetrics50':metrics_clf(test.is_late.to_numpy(),prob,.5),
            'riskMetrics40':metrics_clf(test.is_late.to_numpy(),prob,.4),
            'thresholds':thresholds,
            'durationImportance':group_importance(reg),
            'riskImportance':group_importance(clf),
            'holdoutRows':int(len(test)),
            'trainingRows':int(len(train)),
            'split':'Chronological 80/20 holdout',
            'benchmarks':benchmarks,
        },
        'airports':AIRPORT_COORDS,
        'zones':zone_stats,
        'predictions':pred_lookup,
        'analytics':{'hourly':hourly,'weekdays':weekdays,'airports':airport_stats,'matrix':peak_matrix},
        'defaults':{'passengers':default_passengers,'paymentType':default_payment},
    }
    compact = json.dumps(payload,separators=(',',':'))
    OUT.write_text(compact)
    OUT_JS.write_text('window.APP_DATA=' + compact + ';')
    print('Wrote',OUT,OUT.stat().st_size/1024/1024,'MB')
    print(json.dumps(payload['model'],indent=2)[:1800])

if __name__=='__main__':
    main()
