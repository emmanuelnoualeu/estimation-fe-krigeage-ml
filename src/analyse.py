"""
Fonctions d'analyse : préparation des données, variographie, estimation
(krigeage ordinaire, Random Forest, XGBoost, stacking) et validation.
"""
import warnings
import numpy as np
import pandas as pd
from pykrige.ok3d import OrdinaryKriging3D
from sklearn.ensemble import RandomForestRegressor, StackingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")
SEED = 42
DOMAINES_MINERALISES = ["ITAB_FRAICHE", "ITAB_OXYDEE"]
VARIABLES = ["x", "y", "z", "SiO2", "Al2O3", "P", "dom_oxyde"]
AZIMUT = 60.0      # orientation fictive du jeu synthétique


# ----------------------------------------------------------------- préparation
def composites(df, longueur=2.0):
    """Composites de longueur fixe le long du trou, sans franchir une limite de domaine."""
    df = df.copy()
    df["bloc"] = (df["de"] // longueur).astype(int)
    agg = {c: "mean" for c in ["x", "y", "z", "Fe", "SiO2", "Al2O3", "P"]}
    agg["de"] = "min"
    out = df.groupby(["forage", "domaine", "bloc"], as_index=False).agg(agg)
    return out.drop(columns="bloc")


def top_cut(serie, quantile=0.995):
    """Écrêtage des valeurs extrêmes au quantile choisi. Renvoie (série écrêtée, seuil)."""
    seuil = serie.quantile(quantile)
    return serie.clip(upper=seuil), seuil


def separer_par_forage(df, part_test=0.2, seed=SEED):
    """Jeu de test = forages entiers tenus à l'écart (évite la fuite spatiale)."""
    forages = np.sort(df.forage.unique())
    rng = np.random.default_rng(seed)
    test_ids = rng.choice(forages, size=max(1, int(part_test * len(forages))), replace=False)
    test = df[df.forage.isin(test_ids)].reset_index(drop=True)
    train = df[~df.forage.isin(test_ids)].reset_index(drop=True)
    return train, test, sorted(test_ids)


# ------------------------------------------------------------------ variographie
def variogramme_directionnel(df, var, azimut, tol_angle=22.5, pas=30.0, n_pas=13, tol_vert=10.0):
    """Variogramme expérimental horizontal dans une direction donnée.
    Renvoie un DataFrame : distance moyenne, gamma, nombre de paires."""
    xyz = df[["x", "y", "z"]].to_numpy()
    v = df[var].to_numpy()
    i, j = np.triu_indices(len(df), k=1)
    dx, dy, dz = (xyz[j] - xyz[i]).T
    h = np.hypot(dx, dy)
    ang = (np.degrees(np.arctan2(dx, dy)) % 180.0)          # azimut géographique 0-180
    ecart = np.abs((ang - azimut % 180 + 90) % 180 - 90)
    garde = (ecart <= tol_angle) & (np.abs(dz) <= tol_vert) & (h > 0) & (h <= pas * n_pas)
    h, dv = h[garde], (v[j] - v[i])[garde]
    classe = np.floor(h / pas).astype(int)
    res = (pd.DataFrame({"classe": classe, "h": h, "g": 0.5 * dv ** 2})
             .groupby("classe").agg(distance=("h", "mean"), gamma=("g", "mean"), paires=("g", "size"))
             .reset_index(drop=True))
    return res[res.paires >= 30]


def variogramme_le_long_du_trou(df, var, pas=2.0, n_pas=15):
    """Variogramme expérimental vertical, paires prises dans un même forage.
    Les petits pas renseignent l'effet de pépite, invisible en horizontal (maille ~60-100 m)."""
    lignes = []
    for _, g in df.groupby("forage"):
        z, v = g.z.to_numpy(), g[var].to_numpy()
        i, j = np.triu_indices(len(g), k=1)
        h = np.abs(z[j] - z[i])
        garde = h <= pas * n_pas
        lignes.append(pd.DataFrame({"h": h[garde], "g": 0.5 * (v[j] - v[i])[garde] ** 2}))
    t = pd.concat(lignes)
    t["classe"] = np.round(t.h / pas).astype(int)
    res = (t.groupby("classe").agg(distance=("h", "mean"), gamma=("g", "mean"), paires=("g", "size"))
             .reset_index(drop=True))
    return res[res.paires >= 30]


# ------------------------------------------------------------------- estimation
PARAM_VARIOGRAMMES = {              # palier, portée majeure (m)
    "ITAB_FRAICHE": (14.0, 150.0),
    "ITAB_OXYDEE": (30.0, 300.0),
}


def krigeage_ordinaire(train, test):
    """Krigeage ordinaire 3D conduit séparément dans chaque domaine."""
    pred = pd.Series(np.nan, index=test.index)
    var_k = pd.Series(np.nan, index=test.index)
    for dom, (palier, portee) in PARAM_VARIOGRAMMES.items():
        tr, te = train[train.domaine == dom], test[test.domaine == dom]
        if te.empty or tr.empty:
            continue
        ok = OrdinaryKriging3D(
            tr.x, tr.y, tr.z, tr.Fe,
            variogram_model="spherical",
            variogram_parameters={"sill": palier, "range": portee, "nugget": 0.05 * palier},
            anisotropy_angle_z=90 - AZIMUT,   # PyKrige : angle trigonométrique de l'axe majeur
            anisotropy_scaling_y=0.5,
            anisotropy_scaling_z=0.25,
        )
        z, s2 = ok.execute("points", te.x.values, te.y.values, te.z.values)
        pred.loc[te.index] = np.asarray(z)
        var_k.loc[te.index] = np.asarray(s2)
    return pred.to_numpy(), var_k.to_numpy()


def modeles_ml(plis):
    rf = RandomForestRegressor(n_estimators=400, min_samples_leaf=3, random_state=SEED, n_jobs=-1)
    xgb = XGBRegressor(n_estimators=600, learning_rate=0.03, max_depth=5, subsample=0.8,
                       colsample_bytree=0.8, random_state=SEED, n_jobs=-1)
    stack = StackingRegressor([("rf", rf), ("xgb", xgb)], final_estimator=RidgeCV(), cv=plis)
    return {"Random Forest": rf, "XGBoost": xgb, "Stacking RF+XGB": stack}


def entrainer_et_predire(train, test):
    """Entraîne les 3 modèles ML (plis regroupés par forage) et renvoie prédictions + modèles."""
    plis = list(GroupKFold(n_splits=5).split(train, groups=train.forage))
    preds, ajustes = {}, {}
    for nom, m in modeles_ml(plis).items():
        m.fit(train[VARIABLES], train.Fe)
        preds[nom] = m.predict(test[VARIABLES])
        ajustes[nom] = m
    return preds, ajustes


# -------------------------------------------------------------------- validation
def metriques(y, yp):
    y, yp = np.asarray(y), np.asarray(yp)
    pente = np.polyfit(yp, y, 1)[0]          # pente de régression observé ~ estimé (1 = sans biais conditionnel)
    return {"R2": r2_score(y, yp),
            "RMSE": float(np.sqrt(mean_squared_error(y, yp))),
            "MAE": mean_absolute_error(y, yp),
            "Biais moyen": float(np.mean(yp - y)),
            "Pente de régression": float(pente)}


def biais_par_classe(y, preds, bornes=(0, 27, 30, 33, 36, 40, 100)):
    """Teneur moyenne estimée par classe de teneur observée (diagnostic du lissage)."""
    classes = pd.cut(y, bornes)
    tab = pd.DataFrame({"classe": classes, "Observé": y, **preds})
    return tab.groupby("classe", observed=True).mean()
