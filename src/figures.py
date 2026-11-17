"""Figures du dépôt. Palette : bleu marine (données), orange (méthode retenue), gris (référence)."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLEU, ORANGE, GRIS, GRIS_CLAIR = "#1f4e79", "#c55a11", "#8c96a0", "#d5dae0"
COUL_DOM = {"ENCAISSANT": GRIS_CLAIR, "ITAB_FRAICHE": BLEU, "ITAB_OXYDEE": ORANGE}
COUL_METH = {"Krigeage ordinaire": GRIS, "Random Forest": "#6b8fb3", "XGBoost": BLEU, "Stacking RF+XGB": ORANGE}
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
                     "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left"})
MENTION = "Données synthétiques de démonstration (structure identique au jeu réel)"


def _signer(fig):
    fig.text(0.995, 0.005, MENTION, ha="right", va="bottom", fontsize=7.5, color=GRIS, style="italic")


def carte_forages(brut, test_ids, chemin):
    tetes = brut.groupby("forage").agg(x=("x", "first"), y=("y", "first"), prof=("a", "max")).reset_index()
    fig = plt.figure(figsize=(13, 5.4))
    ax = fig.add_subplot(1, 2, 1)
    est_test = tetes.forage.isin(test_ids)
    ax.scatter(tetes.x[~est_test], tetes.y[~est_test], s=45, color=BLEU, label="Forages d'entraînement (24)")
    ax.scatter(tetes.x[est_test], tetes.y[est_test], s=70, marker="D", color=ORANGE, label="Forages de test (6)")
    for _, r in tetes.iterrows():
        ax.annotate(r.forage[-2:], (r.x, r.y), xytext=(4, 4), textcoords="offset points", fontsize=7, color="#444")
    ax.set_aspect("equal")
    ax.set_xlabel("X local (m)"); ax.set_ylabel("Y local (m)")
    ax.set_title("Plan d'implantation : 30 forages (grille locale fictive)")
    ax.legend(loc="lower left", fontsize=8, frameon=False)
    ax.ticklabel_format(useOffset=False, style="plain")
    ax.tick_params(axis="x", labelrotation=30)

    ax3 = fig.add_subplot(1, 2, 2, projection="3d")
    sous = brut[brut.domaine != "ENCAISSANT"]
    ax3.scatter(brut.x, brut.y, brut.z, s=1, color=GRIS_CLAIR, alpha=0.4)
    sc = ax3.scatter(sous.x, sous.y, sous.z, c=sous.Fe, s=4, cmap="viridis")
    ax3.set_title("Vue 3D : teneurs Fe dans l'itabirite", pad=0)
    ax3.set_xticklabels([]); ax3.set_yticklabels([]); ax3.set_zlabel("Z (m)")
    ax3.view_init(elev=22, azim=-60)
    fig.colorbar(sc, ax=ax3, shrink=0.6, pad=0.08, label="Fe (%)")
    _signer(fig); fig.tight_layout(); fig.savefig(chemin, dpi=160); plt.close(fig)


def exploration(brut, chemin):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.3))
    ordre = ["ENCAISSANT", "ITAB_FRAICHE", "ITAB_OXYDEE"]
    for dom in ordre:
        axes[0].hist(brut.Fe[brut.domaine == dom], bins=40, alpha=0.85, color=COUL_DOM[dom],
                     label=f"{dom} (n={int((brut.domaine == dom).sum())})")
    axes[0].set_xlabel("Fe (%)"); axes[0].set_ylabel("Échantillons")
    axes[0].set_title("Distribution du fer par domaine"); axes[0].legend(fontsize=8, frameon=False)

    data = [brut.Fe[brut.domaine == d] for d in ordre]
    bp = axes[1].boxplot(data, patch_artist=True, widths=0.55, showfliers=False,
                         medianprops={"color": "black", "lw": 1.5})
    for patch, d in zip(bp["boxes"], ordre):
        patch.set_facecolor(COUL_DOM[d]); patch.set_alpha(0.85)
    axes[1].set_xticks([1, 2, 3], ["Encaissant", "Itab. fraîche", "Itab. oxydée"])
    axes[1].set_ylabel("Fe (%)"); axes[1].set_title("Contraste entre domaines")

    it = brut[brut.domaine != "ENCAISSANT"]
    for dom in ordre[1:]:
        s = it[it.domaine == dom]
        axes[2].scatter(s.SiO2, s.Fe, s=6, alpha=0.5, color=COUL_DOM[dom], label=dom)
    r = np.corrcoef(it.SiO2, it.Fe)[0, 1]
    axes[2].set_xlabel("SiO₂ (%)"); axes[2].set_ylabel("Fe (%)")
    axes[2].set_title(f"Dilution par la silice (r = {r:.2f})"); axes[2].legend(fontsize=8, frameon=False)
    _signer(fig); fig.tight_layout(); fig.savefig(chemin, dpi=160); plt.close(fig)


def variogrammes(vg_trou, vg_maj, vg_min, variance, chemin):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.4), gridspec_kw={"width_ratios": [1, 1.6]})
    a1.plot(vg_trou.distance, vg_trou.gamma, "o-", color=BLEU)
    a1.set_xlim(0, None); a1.set_ylim(0, variance * 1.3)
    a1.axhline(variance, color=GRIS, lw=1, ls=":")
    a1.set_xlabel("Distance le long du trou (m)"); a1.set_ylabel("γ(h)  (% Fe)²")
    a1.set_title("Le long des forages : effet de pépite")
    a2.plot(vg_maj.distance, vg_maj.gamma, "o-", color=ORANGE, label="Axe majeur (60°)")
    a2.plot(vg_min.distance, vg_min.gamma, "s--", color=BLEU, label="Axe mineur (150°)")
    a2.axhline(variance, color=GRIS, lw=1, ls=":", label="Variance des composites")
    a2.set_xlim(0, None); a2.set_ylim(0, None)
    a2.set_xlabel("Distance horizontale h (m)")
    a2.set_title("En plan : continuité anisotrope")
    a2.legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle("Variographie du fer, itabirite fraîche", x=0.01, ha="left", fontweight="bold")
    _signer(fig); fig.tight_layout(); fig.savefig(chemin, dpi=160); plt.close(fig)


def observe_vs_estime(y, preds, resultats, chemin):
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.3), sharex=True, sharey=True)
    lim = [np.min(y) - 2, np.max(y) + 2]
    for ax, (nom, p) in zip(axes, preds.items()):
        ax.scatter(y, p, s=11, alpha=0.6, color=COUL_METH[nom])
        ax.plot(lim, lim, "--", color="#333", lw=0.8)
        ax.set_title(f"{nom}\nR² = {resultats[nom]['R2']:.2f}   RMSE = {resultats[nom]['RMSE']:.2f}", fontsize=10)
        ax.set_xlabel("Fe observé (%)")
    axes[0].set_ylabel("Fe estimé (%)")
    _signer(fig); fig.tight_layout(); fig.savefig(chemin, dpi=160); plt.close(fig)


def biais_conditionnel(tab, chemin):
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    x = np.arange(len(tab))
    ax.plot(x, tab["Observé"], "k-", lw=2, label="Teneur observée (référence)")
    for nom in [c for c in tab.columns if c != "Observé"]:
        ax.plot(x, tab[nom], "o-", color=COUL_METH[nom], label=nom, lw=1.6 if "Stacking" in nom else 1.1)
    ax.set_xticks(x, [str(c).replace("(", "").replace("]", "").replace(", ", "–") for c in tab.index])
    ax.set_xlabel("Classe de teneur observée (% Fe)"); ax.set_ylabel("Teneur moyenne (% Fe)")
    ax.set_title("Effet de lissage : qui suit les teneurs extrêmes ?")
    ax.legend(frameon=False, fontsize=8)
    _signer(fig); fig.tight_layout(); fig.savefig(chemin, dpi=160); plt.close(fig)


def importance(imp, chemin):
    imp = imp.sort_values()
    fig, ax = plt.subplots(figsize=(7.5, 4))
    couleurs = [ORANGE if i == imp.index[-1] else BLEU for i in imp.index]
    ax.barh(imp.index, imp.values, color=couleurs)
    ax.set_xlabel("Perte de R² quand la variable est permutée")
    ax.set_title("Ce qui pilote la prédiction du fer (stacking)")
    _signer(fig); fig.tight_layout(); fig.savefig(chemin, dpi=160); plt.close(fig)


def resultats_memoire(chemin):
    """Synthèse des performances RÉELLES publiées dans le mémoire.
    Seules les métriques de méthode sont montrées : aucun nom, tonnage, teneur ou coordonnée."""
    methodes = ["Krigeage\nordinaire", "Random\nForest", "XGBoost", "Stacking\nRF + XGB"]
    r2 = [0.606, 0.631, 0.731, 0.825]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    b = ax.bar(methodes, r2, color=[GRIS, GRIS, GRIS, ORANGE], width=0.6)
    ax.bar_label(b, labels=[f"{v:.3f}".replace(".", ",") for v in r2], padding=3)
    ax.set_ylim(0, 1); ax.set_ylabel("R² sur forages de test indépendants")
    ax.set_title("Précision de l'estimation de Fe % par méthode (gisement réel, 30 forages)")
    fig.tight_layout(); fig.savefig(chemin, dpi=170); plt.close(fig)
