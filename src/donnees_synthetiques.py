"""
Génère une base de forages SYNTHÉTIQUE imitant la géométrie d'un gisement
d'itabirite (BIF) : 30 forages, ~3 600 m, ~2 700 échantillons.

Les données réelles sont confidentielles et ne sont pas publiées. Ce jeu est
entièrement fictif : coordonnées locales, orientation, teneurs et géométrie
ne correspondent à aucun gisement réel. Il sert uniquement à rendre le
pipeline exécutable par n'importe qui.
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
AZIMUT_DIRECTION = 60.0           # direction fictive de la formation (degrés)
LONG_ECH = 1.35                   # longueur moyenne d'un échantillon (m)


def _champ_anisotrope(x, y, z, portee_maj, portee_min, portee_v, n=300):
    """Champ gaussien approché par fonctions de Fourier aléatoires,
    anisotrope selon l'azimut AZIMUT_DIRECTION."""
    a = np.deg2rad(90 - AZIMUT_DIRECTION)
    u = x * np.cos(a) + y * np.sin(a)        # axe majeur
    v = -x * np.sin(a) + y * np.cos(a)       # axe mineur
    k = RNG.normal(size=(n, 3)) / np.array([portee_maj, portee_min, portee_v])
    phi = RNG.uniform(0, 2 * np.pi, n)
    p = np.c_[u, v, z]
    return np.sqrt(2 / n) * np.cos(p @ k.T + phi).sum(axis=1)


def generer(n_forages=30):
    # Maille irrégulière ~ 100 x 60 m, allongée selon la direction
    a = np.deg2rad(90 - AZIMUT_DIRECTION)
    lignes = []
    for i in range(n_forages):
        u = (i % 10) * 100 + RNG.normal(0, 15)
        v = (i // 10) * 60 + RNG.normal(0, 10)
        x0 = 1_000 + u * np.cos(a) - v * np.sin(a)
        y0 = 2_000 + u * np.sin(a) + v * np.cos(a)
        z0 = 250 + RNG.normal(0, 5)
        prof = RNG.uniform(95, 147)
        n_ech = int(prof / LONG_ECH)
        de = np.arange(n_ech) * LONG_ECH
        for d in de:
            lignes.append((f"DH{i+1:03d}", x0, y0, z0 - d - LONG_ECH / 2, d, d + LONG_ECH, v))
    df = pd.DataFrame(lignes, columns=["forage", "x", "y", "z", "de", "a", "v_local"])

    # Toit / mur de la couche d'itabirite (pendage vers le NE)
    toit = 215 - 0.25 * df["v_local"] + 6 * _champ_anisotrope(df.x, df.y, 0 * df.z, 400, 150, 1e9, 50)
    mur = toit - 55
    dans_itab = (df.z < toit) & (df.z > mur)
    oxyde = dans_itab & (df.z > toit - 12)
    df["domaine"] = np.where(oxyde, "ITAB_OXYDEE", np.where(dans_itab, "ITAB_FRAICHE", "ENCAISSANT"))

    g = _champ_anisotrope(df.x.values, df.y.values, df.z.values, 300, 150, 40)
    bruit = RNG.normal(0, 1, len(df))

    # SiO2 contrôle la dilution du fer (relation inverse propre aux BIF)
    sio2 = np.select(
        [df.domaine == "ITAB_OXYDEE", df.domaine == "ITAB_FRAICHE"],
        [33 - 6 * g + 2.0 * bruit, 43 - 6 * g + 2.0 * bruit],
        61 - 3 * g + 2.0 * bruit,
    )
    sio2 = np.clip(sio2, 5, 80)
    al2o3 = np.clip(np.where(df.domaine == "ENCAISSANT", 13, 2.5) + 1.5 * RNG.normal(size=len(df)), 0.2, 25)
    p = np.clip(RNG.lognormal(np.log(0.06), 0.6, len(df)), 0.005, 1.2)
    fe_max = 0.699 * (100 - sio2 - al2o3 - 4)            # Fe porté par la magnétite/hématite
    fe = np.where(df.domaine == "ENCAISSANT", 0.12, 1.0) * fe_max
    # Composante non linéaire : enrichissement supergène dans le faciès oxydé
    fe = fe + np.where(df.domaine == "ITAB_OXYDEE", 4 * np.tanh(g), 0) + 1.5 * RNG.normal(size=len(df))
    df["Fe"] = np.clip(fe, 1, 66).round(2)
    df["SiO2"] = sio2.round(2)
    df["Al2O3"] = al2o3.round(2)
    df["P"] = p.round(3)
    return df.drop(columns="v_local")


if __name__ == "__main__":
    d = generer()
    d.to_csv("data/forages_synthetiques.csv", index=False)  # lancer depuis la racine du dépôt
    long_tot = d.groupby("forage").a.max().sum()
    print(f"{d.forage.nunique()} forages, {long_tot:.0f} m, {len(d)} échantillons")
    print(d.groupby("domaine").Fe.describe().round(2))
