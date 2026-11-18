# Méthodologie détaillée

Ce document décrit chaque étape de l'étude, les choix techniques et leurs justifications. Les paramètres « gisement réel » viennent du mémoire. Les paramètres « code » sont ceux du pipeline publié, appliqué au jeu synthétique.

---

## 1. Base de données

| Élément | Gisement réel | Jeu synthétique |
|---|---|---|
| Forages | 30 | 30 |
| Métrage | ~3 630 m | ~3 680 m |
| Échantillons analysés | 2 702 analyses XRF validées (2 705 brutes) | ~2 725 |
| Variables | Fe, SiO₂, Al₂O₃, P (analyses ALS) | Fe, SiO₂, Al₂O₃, P |
| Domaines | encaissant, itabirite fraîche, itabirite oxydée | idem |

Tables manipulées : collars (têtes de forage), surveys (déviations), assays (analyses), lithologie. Les contrôles de cohérence portent sur les intervalles qui se chevauchent, les trous sans analyse, les profondeurs supérieures à la longueur du trou et les doublons d'identifiants.

## 2. Contrôle qualité (QA/QC)

Le QA/QC a porté sur les quatre tables de la base (Collar, Survey, Geology, Assay) : les 2 705 analyses brutes ont été ramenées à 2 702 analyses exploitables, et les anomalies d'intervalles (chevauchements, lacunes) ont été corrigées. Il porte aussi sur la récupération des carottes (COR). Une faible récupération dans les zones altérées biaise les teneurs, parce que la fraction perdue n'est pas aléatoire. Un intervalle mal récupéré doit être signalé avant toute estimation.

## 3. Modèle géologique 3D

Sous Leapfrog Geo, trois domaines ont été modélisés à partir des logs lithologiques et des teneurs :

| Domaine | Volume |
|---|---|
| Encaissant | 45,6 Mm³ |
| Itabirite fraîche | 6,94 Mm³ |
| Itabirite oxydée | 0,81 Mm³ |

Le faciès oxydé, superficiel et peu volumineux, correspond à l'altération supergène. **Chaque domaine est estimé séparément**, afin de respecter l'hypothèse de stationnarité du krigeage et de ne pas faire « fuir » les teneurs d'un faciès vers l'autre.

## 4. Compositage et valeurs extrêmes

- **Compositage :** longueur fixe de 2 m, sans franchir une limite de domaine ; sur le gisement réel, 1 818 composites. On obtient un support homogène, condition nécessaire pour la variographie.
- **Écrêtage :** sur le gisement réel, teneurs aberrantes en Fe écrêtées entre les percentiles 1 et 99 (P01-P99) ; dans le code, quantile 99,5 %. Dans le mémoire, l'écrêtage global n'a pas complètement résorbé les extrêmes du phosphore. La recommandation est de l'appliquer **par domaine**.

## 5. Variographie

- Variogrammes expérimentaux par domaine, directionnels en plan (axe majeur et axe perpendiculaire) et le long du trou (pour l'effet de pépite).
- **Gisement réel (Isatis.neo) :** anisotropie commune aux deux faciès d'itabirite, orientée NW-SE (~135°), effet de pépite quasi nul, portées d'environ 150 m (itabirite fraîche) à 300 m (itabirite oxydée).
- **Code (jeu synthétique, orientation fictive de 60°) :** modèle sphérique, pépite fixée à 5 % du palier, rapports d'anisotropie de 1 / 0,5 / 0,25 (majeur / mineur / vertical).

## 6. Estimation

| Méthode | Entrées | Remarque |
|---|---|---|
| Krigeage ordinaire 3D | coordonnées + Fe des composites voisins | par domaine, ellipsoïde orienté selon la variographie |
| Random Forest | x, y, z, SiO₂, Al₂O₃, P, domaine | 400 arbres, feuille minimale 3 |
| XGBoost | idem | 600 arbres, profondeur 5, taux d'apprentissage 0,03 |
| Stacking | prédictions RF + XGB | méta-modèle Ridge, plis regroupés par forage |

**Point méthodologique important.** Le krigeage n'utilise que le fer des voisins. Les modèles ML utilisent aussi la chimie (SiO₂, Al₂O₃, P) **mesurée au point estimé**. Sur des échantillons, c'est légitime. Sur un modèle de blocs, ces covariables doivent d'abord être estimées en chaque bloc, et leur erreur se propage. Le gain du ML mesuré ici est donc une **borne haute** du gain attendu en production.

## 7. Validation

- **Jeu de test :** dans le mémoire, 20 % des composites (361), tirage stratifié par type de roche, et validation croisée à 5 plis pour régler les hyperparamètres. Dans le code de démonstration, 20 % des forages sont tenus à l'écart en entier : c'est plus strict, car des échantillons voisins d'un même trou sont fortement corrélés et un découpage aléatoire peut gonfler le score.
- **Métriques :** R², RMSE, MAE, biais moyen et pente de régression observé/estimé. Une pente de 1 signifie l'absence de biais conditionnel.
- **Biais conditionnel :** teneur moyenne estimée dans chaque classe de teneur observée. C'est le diagnostic direct de l'effet de lissage.
- **Importance des variables :** importance par permutation sur le jeu de test.

**Gisement réel :**

| Méthode | R² |
|---|---|
| Krigeage ordinaire | 0,606 (RMSE 5,34 % Fe ; Pearson 0,81 en validation croisée, pas de biais global ; pente 0,57) |
| Random Forest | 0,631 |
| XGBoost | 0,731 |
| Stacking RF + XGB | 0,825 (RMSE 3,54 % Fe, MAE 2,45 % Fe ; pente 0,83) |

## 8. Classification des ressources (JORC 2012)

Critères utilisés : efficacité de krigeage, densité d'échantillonnage et confiance géologique.

| Catégorie | Tonnage (coupure 25 % Fe) |
|---|---|
| Mesurée + Indiquée | 58,2 Mt |
| Inférée | 43,9 Mt |
| **Total** | **102,1 Mt à 31,4 % Fe** |

La courbe tonnage-teneur est continue, sans rupture nette entre minerai riche et minerai pauvre, ce qui est typique des itabirites.

*Une déclaration publique de ressources au sens du JORC exige la signature d'une Personne Compétente. La classification présentée ici est un exercice académique réalisé sous encadrement.*

## 9. Limites et suite

| Limite | Correction proposée |
|---|---|
| Densité uniforme de 3,5 t/m³ | Mesures par domaine sur carottes (déplacement d'eau) |
| Faible effectif du domaine oxydé | Forages ciblés en surface |
| Extrêmes du P mal traités par un top-cut global | Écrêtage par domaine |
| 43,9 Mt en Inférée, en profondeur | Densifier la maille profonde |
| ML dépendant des covariables au point | Krigeage des résidus RF/XGB, co-krigeage guidé par l'importance des variables |
