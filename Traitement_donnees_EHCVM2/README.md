# Traitement de données – Pipeline de nettoyage de l'EHCVM2 (Sénégal)

Pipeline R reproductible qui transforme les microdonnées brutes de l'**Enquête Harmonisée sur les Conditions de Vie des Ménages (EHCVM2)** en une base propre, fusionnée et contrôlée. Il produit aussi un **rapport de qualité (QAQC)** pondéré selon le plan de sondage.

Projet réalisé dans le cadre du cours de *Traitement de données* à l'ENSAE Pierre Ndiaye de Dakar (2024).

---

## En bref

| Étape | Entrée | Sortie |
|---|---|---|
| 1. Dictionnaire initial | `ehcvm2_hh.dta`, `ehcvm2_ind.dta` | `dictionary_*_init.csv` |
| 2. Sélection et renommage | dictionnaires complétés (`*_filled.xlsx`) | `ehcvm2_*_renamed.csv` + dictionnaires de modalités |
| 3. Nettoyage | fichiers renommés | `ehcvm2_hh_clean.csv` (7 120 ménages × 46 var.), `ehcvm2_ind_clean.csv` (63 530 individus × 49 var.) |
| 4. Fusion ménages–individus | fichiers nettoyés | `ehcvm2_merged.csv` (63 530 lignes × 92 var.) |
| 5. Rapport QAQC | fichier fusionné | `data/output_qaqc/qaqc_ehcvm2_report.html` |

---

## Arborescence

```
Traitement_donnees_EHCVM2/
├── Requirements.R                     # Installation des packages
├── cleansurvey/
│   ├── config.R                       # Chemins des données (data/, data/aux_file/)
│   ├── utils.R                        # Fonctions génériques (renommage, nettoyage, fusion)
│   ├── run_all.R                      # Lance tout le pipeline en une fois
│   ├── 1_data_exploration/
│   │   ├── 1_get_initial_dict/        # Extraction des variables, labels et types
│   │   └── 2_select_and_label/        # Application du dictionnaire complété
│   ├── 2_clean_and_merge/
│   │   ├── 1_clean_hh_ind.R           # Nettoyage ménages et individus
│   │   └── 2_merge_hh_ind.R           # Fusion sur hhid
│   └── 9_qaqc/1_survey_data_qaqc/
│       ├── 1_qaqc_report.R            # Paramètres du rapport + rendu
│       └── qaqc_report.Rmd            # Modèle du rapport HTML
├── data/
│   ├── ehcvm2_hh.dta, ehcvm2_ind.dta  # Données brutes
│   ├── aux_file/                      # Dictionnaires de variables et de modalités
│   └── output_qaqc/                   # Rapport QAQC généré
└── readings/
    └── liens_utiles.md                # Ressources (imputation, ISLR, ISLP)
```

---

## Fonctionnement détaillé

### 1. Construction du dictionnaire de données
`1_get_hh_dict.R` et `2_get_ind_dict.R` lisent les fichiers Stata. Pour chaque variable, ils extraient le **nom d'origine**, le **label** et le **type** (labelled, factor, numeric, character). Le résultat est écrit dans `data/aux_file/dictionary_{hh,ind}_init.csv`.

➡️ **Étape manuelle** : on complète ce dictionnaire dans `dictionary_{hh,ind}_filled.xlsx`. On y indique les variables à garder (`keep`), leur nouveau nom et leur nouveau type (`type_new`).

### 2. Sélection et renommage
`1_apply_hh_dict.R` et `2_apply_ind_dict.R` vérifient d'abord que le dictionnaire complété couvre bien toutes les variables d'origine. Ils appliquent ensuite le dictionnaire avec `apply_var_dictionary()` : sélection, renommage et conversion des types. Ils génèrent enfin un **dictionnaire des modalités** pour les variables catégorielles.

### 3. Nettoyage (`1_clean_hh_ind.R`)
Toutes les règles sont réunies dans une seule liste, `CLEANING_PARAMS`. **Pour adapter le pipeline à une autre enquête, il suffit de modifier cette section.** La fonction `run_cleaning_pipeline()` applique ensuite les étapes suivantes, dans l'ordre :

1. **Suppression** des variables constantes ou redondantes (`vars_to_drop`).
2. **Bornes de domaine** pour les variables numériques : une valeur hors bornes devient NA (par exemple âge ∈ [0, 100], heures travaillées ≤ 4 380 par an).
3. **Imputation numérique** : moyenne, médiane, zéro, ou aucune imputation pour les variables à zéros structurels (salaires, heures).
4. **Imputation catégorielle** : mode, modalité « Unknown », ou aucune imputation.
5. **Règles de cohérence croisées**, qui mettent la valeur en NA ou créent une colonne `flag_*` :
   - âge au premier mariage supérieur à l'âge ;
   - moins de 15 ans et statut matrimonial autre que célibataire ;
   - moins de 5 ans avec un statut d'activité renseigné ;
   - salaire positif alors que l'individu est déclaré inactif.
6. **Harmonisation des libellés**, qui retire les espaces superflus et uniformise la casse.
7. **Dédoublonnage** sur la clé primaire (`hhid` pour les ménages, `hhid × numind` pour les individus).

### 4. Fusion (`2_merge_hh_ind.R`)
`run_merge_pipeline()` fusionne les ménages et les individus par une jointure `inner` sur `hhid`. Les colonnes présentes dans les deux fichiers (`milieu`, `region`) sont traitées selon une stratégie configurable : version ménage, version individu, ou les deux avec suffixes. La fonction produit aussi un rapport de jointure.

### 5. Rapport de qualité QAQC (`1_qaqc_report.R` → `qaqc_report.Rmd`)
Le rapport HTML tient compte du **plan de sondage** grâce au package `survey` : poids `hhweight`, strates `region` et grappes `grappe`. Il contient :
- une vue d'ensemble de la base et la répartition urbain/rural pondérée ;
- la **qualité des données** : valeurs manquantes et contrôles de cohérence (dont les doublons de clés) ;
- une **analyse univariée** des variables numériques et catégorielles ;
- les **indicateurs clés de l'EHCVM**, avec intervalles de confiance et ventilation par sexe, milieu et région : taux d'emploi et de chômage (15–64 ans), scolarisation nette (6–14 ans), alphabétisation, couverture maladie, possession d'un téléphone portable et accès à Internet ;
- une **analyse bivariée** : pyramide des âges, éducation selon le sexe et le milieu, activité selon l'âge, salaires et taille des ménages par région ;
- un diagnostic des poids de sondage.

Les indicateurs et les contrôles sont déclarés comme des expressions R dans `QAQC_PARAMS`. On peut donc en ajouter sans toucher au modèle `.Rmd`.

---

## Utilisation

### Prérequis
R (≥ 4.1) et les packages suivants. `pacman` installe automatiquement ceux qui manquent.

```r
install.packages("pacman")
pacman::p_load(haven, labelled, readxl, readr, data.table, dplyr, tidyr, purrr,
               stringr, forcats, tibble, glue, here, rmarkdown, knitr, kableExtra,
               ggplot2, scales, patchwork, survey, Hmisc)
```

### Exécution
Ouvrir R **à la racine du dossier** (les chemins sont relatifs), puis :

```r
source("cleansurvey/run_all.R")
```

Les scripts s'exécutent dans l'ordre des dossiers, chacun dans une session R propre (`Rscript --vanilla`). On peut aussi lancer chaque script séparément, dans l'ordre numéroté.

> ℹ️ Les fichiers intermédiaires (`*_renamed.csv`, `*_clean.csv`) et la base finale (`ehcvm2_merged.csv`) ne sont pas versionnés : `run_all.R` les régénère dans `data/` à partir des fichiers `.dta`. Le rapport QAQC produit est fourni dans `data/output_qaqc/`.

> ⚠️ Les étapes 1 et 2 demandent de compléter les dictionnaires à la main (`*_filled.xlsx`). Les versions complétées sont fournies dans `data/aux_file/`.

---

## Points forts de la conception
- **Paramétrage centralisé** : chaque étape a un seul bloc de paramètres (`CLEANING_PARAMS`, `MERGE_PARAMS`, `QAQC_PARAMS`), qu'il suffit de modifier pour une autre enquête.
- **Fonctions génériques et réutilisables** regroupées dans `utils.R`.
- **Traçabilité** : chaque étape écrit son propre fichier intermédiaire dans `data/`, ce qui permet de reprendre le pipeline à n'importe quel point.
- **Estimations pondérées** qui respectent le plan de sondage complexe de l'enquête.

## Données et ressources
- Les données EHCVM2 sont produites par l'**ANSD** (Sénégal) dans le cadre du programme régional EHCVM (UEMOA / Banque mondiale).
- Lectures du cours : voir `readings/liens_utiles.md`. Les manuels *An Introduction to Statistical Learning* (versions R et Python) se téléchargent gratuitement sur [statlearning.com](https://www.statlearning.com).

## Auteur
**Mame El Hadji Sarr** – Ingénieur Statisticien Économiste (ENSAE Pierre Ndiaye de Dakar)
