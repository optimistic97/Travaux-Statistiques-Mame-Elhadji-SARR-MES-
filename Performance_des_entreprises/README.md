# Facteurs associés au niveau d'activité des PME au Sénégal

Code Python du mémoire d'ingénieur de Mame Elhadji SARR (ENSAE Pierre
Ndiaye, Dakar), réalisé en stage à la Chambre de commerce, d'industrie et
d'agriculture de Dakar (CCIAD), juillet 2026.

## Question

Quels facteurs sont associés au niveau d'activité des petites et moyennes
entreprises sénégalaises, mesuré par cinq classes de chiffre d'affaires, et
ces associations changent-elles selon la position de l'entreprise dans la
distribution du chiffre d'affaires ?

## Données

Recensement général des entreprises (RGE) 2016, Agence nationale de la
Statistique et de la Démographie (ANSD) : bases anonymisées des personnes
physiques et des personnes morales, fusionnées (406 408 unités marchandes
actives). L'échantillon d'estimation, en cas complets, compte 292 589
unités.

**Les données ne sont pas publiées** (`data/` est vide et ignoré par git).
Pour les obtenir, adresser une demande à l'ANSD (www.ansd.sn). Le script
attend la base d'analyse issue de la fusion et de la préparation des
variables, dans `data/base_analyse.dta` (ou `.csv`, `.parquet`, `.pkl`), ou
à l'emplacement indiqué par la variable d'environnement `PME_DATA`. La
liste des colonnes requises figure dans la cellule 0 du script
(`COLONNES_REQUISES`). La préparation amont de cette base n'est pas
incluse.

## Méthode

1. Logit ordonné à cotes proportionnelles (modèle de référence).
2. Test de Brant : rejet de la proportionnalité (chi2 = 9 694, 135 degrés de
   liberté, p < 0,001).
3. Logit ordonné généralisé à cotes proportionnelles partielles (PPO) :
   `Pr(Y > j | x) = L(a_j + X'b_j + Z'g)`. Les variables d'hypothèse
   (formalité, financement, genre du dirigeant) et le bloc substantiel ont un
   coefficient propre à chaque seuil ; les contrôles (effets fixes de région
   et de branche, interactions femme x branche, personne morale) ont un
   coefficient commun. Erreurs-types agrégées en 135 grappes région x
   branche.
4. Robustesse : régression par intervalles sur le logarithme du chiffre
   d'affaires, probit ordonné, sous-échantillons (hors Dakar, hors classe
   supérieure, unités formelles seules), validation hors échantillon 70/30.
5. Interprétation : effets marginaux moyens et probabilités prédites pour des
   profils types.

Le PPO est préféré au logit ordonné par le test du rapport de
vraisemblance (4 364,5 ; 39 ddl), l'AIC et le BIC. Le modèle entièrement
généralisé n'est pas identifiable de façon stable (quasi-séparation dans les
cellules rares). Le PPO n'existe dans aucune bibliothèque Python usuelle :
il est estimé par maximum de vraisemblance dans le script (gradient et
hessienne analytiques, démarrage issu du logit ordonné).

## Résultats principaux (mémoire)

- La formalisation est le facteur le plus fortement associé au niveau
  d'activité : rapport de cotes de 2,4 au premier seuil et de 12,8 au
  dernier (franchir 200 millions de FCFA).
- Le financement bancaire est positivement associé (rapport de cotes de 1,3
  à 2,7 selon le seuil) ; le financement informel l'est aux seuils bas, puis
  son rapport de cotes passe sous 1 (0,78) au dernier seuil.
- Les entreprises dirigées par une femme ont des chances plus faibles
  d'atteindre les classes supérieures (rapport de cotes de 0,28 au premier
  seuil, 0,17 au dernier).
- À caractéristiques égales par ailleurs, la probabilité d'atteindre la
  classe supérieure (200 millions de FCFA et plus) passe de 15 % pour une PME
  formelle dirigée par un homme à 3 % pour une PME formelle dirigée par une
  femme.
- L'intensité des associations varie selon les seuils : un modèle à effet
  unique la masque.

## Exécution

```bash
pip install -r requirements.txt
python analyse_performance_pme.py            # utilise data/base_analyse.*
PME_DATA=/chemin/base.dta python analyse_performance_pme.py
```

Durée de l'ordre de quelques minutes. Le script est organisé en cellules `# %%`
(VS Code, Jupyter) : paramètres, chargement et contrôles qualité,
construction des variables, statistiques descriptives, logit ordonné et test
de Brant, PPO, robustesse, effets marginaux et profils, export. Les
tableaux (CSV et classeur Excel) et les graphiques (PNG) sont écrits dans
`output/`. Le fichier `output/tableaux/VERIF_memoire_contre_code.csv`
confronte les chiffres clés du mémoire aux valeurs recalculées.

## Limites

Données transversales : les coefficients mesurent des associations
conditionnelles, pas des effets causaux (la formalisation et le financement
sont probablement endogènes). La variable dépendante n'est observée que par
classes et manque pour 21,9 % des unités actives, plus souvent chez les
informelles : l'estimation en cas complets sous-représente les formelles
les mieux établies. Le recensement ne couvre que les unités disposant d'un
local fixe.

## Structure

```
Performance_des_entreprises/
├── analyse_performance_pme.py   # script unique, cellules # %%
├── requirements.txt
├── data/                        # vide (données non publiées)
└── output/                      # tableaux et graphiques générés
```
