import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import analyse as an
import donnees_synthetiques as ds


def test_base_synthetique_a_la_bonne_taille():
    d = ds.generer()
    assert d.forage.nunique() == 30
    assert 2500 < len(d) < 2900
    assert set(d.domaine) == {"ENCAISSANT", "ITAB_FRAICHE", "ITAB_OXYDEE"}


def test_composites_ne_franchissent_pas_les_domaines():
    d = pd.DataFrame({"forage": ["A"] * 4, "domaine": ["X", "X", "Y", "Y"],
                      "de": [0.0, 1.0, 2.0, 3.0], "x": 0.0, "y": 0.0, "z": [10, 9, 8, 7],
                      "Fe": [10, 20, 30, 40], "SiO2": 1.0, "Al2O3": 1.0, "P": 0.1})
    c = an.composites(d, longueur=2.0)
    assert len(c) == 2
    assert sorted(c.Fe) == [15, 35]


def test_separation_par_forage_sans_fuite():
    d = ds.generer()
    train, test, ids = an.separer_par_forage(d)
    assert set(train.forage).isdisjoint(test.forage)
    assert len(ids) == 6


def test_top_cut():
    s, seuil = an.top_cut(pd.Series(np.arange(1000.0)), 0.99)
    assert s.max() == seuil


def test_metriques_parfaites():
    y = np.array([25.0, 30.0, 35.0, 40.0])
    m = an.metriques(y, y)
    assert m["R2"] == 1 and m["RMSE"] == 0 and abs(m["Pente de régression"] - 1) < 1e-9
