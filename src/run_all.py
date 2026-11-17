"""
Exécute l'étude complète de bout en bout et régénère toutes les figures.

    python src/run_all.py
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

sys.path.insert(0, str(Path(__file__).parent))
import donnees_synthetiques as ds
import analyse as an
import figures as fg

RACINE = Path(__file__).resolve().parents[1]
DATA, FIG = RACINE / "data", RACINE / "figures"


def main():
    DATA.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
    brut = ds.generer()
    brut.to_csv(DATA / "forages_synthetiques.csv", index=False)
    print(f"[1/6] Base : {brut.forage.nunique()} forages, {brut.groupby('forage').a.max().sum():.0f} m, {len(brut)} échantillons")

    comp = an.composites(brut)
    comp = comp[comp.domaine.isin(an.DOMAINES_MINERALISES)].reset_index(drop=True)
    comp["dom_oxyde"] = (comp.domaine == "ITAB_OXYDEE").astype(int)
    comp["P"], seuil_p = an.top_cut(comp["P"])
    train, test, test_ids = an.separer_par_forage(comp)
    print(f"[2/6] {len(comp)} composites de 2 m ; top-cut P = {seuil_p:.3f} % ; test = {', '.join(test_ids)}")

    fraiche = comp[comp.domaine == "ITAB_FRAICHE"]
    vg_trou = an.variogramme_le_long_du_trou(fraiche, "Fe")
    vg_maj = an.variogramme_directionnel(fraiche, "Fe", an.AZIMUT)
    vg_min = an.variogramme_directionnel(fraiche, "Fe", an.AZIMUT + 90)
    print("[3/6] Variogrammes directionnels calculés")

    preds = {"Krigeage ordinaire": an.krigeage_ordinaire(train, test)[0]}
    ml, modeles = an.entrainer_et_predire(train, test)
    preds.update(ml)
    resultats = {n: an.metriques(test.Fe, p) for n, p in preds.items()}
    tab = pd.DataFrame(resultats).T.round(3)
    tab.to_csv(DATA / "metriques_test.csv")
    print("[4/6] Performances sur les 6 forages de test :\n" + tab.to_string())

    perm = permutation_importance(modeles["Stacking RF+XGB"], test[an.VARIABLES], test.Fe,
                                  n_repeats=20, random_state=an.SEED, scoring="r2")
    noms = {"x": "X (est)", "y": "Y (nord)", "z": "Z (altitude)", "SiO2": "SiO₂", "Al2O3": "Al₂O₃",
            "P": "P", "dom_oxyde": "Domaine oxydé"}
    imp = pd.Series(perm.importances_mean, index=[noms[v] for v in an.VARIABLES])
    bc = an.biais_par_classe(test.Fe.to_numpy(), preds)
    print("[5/6] Importance des variables et biais conditionnel calculés")

    fg.resultats_memoire(FIG / "00_resultats_memoire.png")
    fg.carte_forages(brut, test_ids, FIG / "01_implantation_forages.png")
    fg.exploration(brut, FIG / "02_exploration_donnees.png")
    fg.variogrammes(vg_trou, vg_maj, vg_min, fraiche.Fe.var(), FIG / "03_variogrammes.png")
    fg.observe_vs_estime(test.Fe.to_numpy(), preds, resultats, FIG / "04_observe_vs_estime.png")
    fg.biais_conditionnel(bc, FIG / "05_biais_conditionnel.png")
    fg.importance(imp, FIG / "06_importance_variables.png")
    print(f"[6/6] Figures écrites dans {FIG.relative_to(RACINE)}/")
    return tab


if __name__ == "__main__":
    main()
