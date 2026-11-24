# Analyse multidimensionnelle de la pauvreté au Sénégal par l'approche des sous-ensembles flous

**Auteur** : Mame Elhadji SARR
**Cadre** : mémoire de fin d'études d'Analyste Statisticien, ENSAE Pierre Ndiaye (juin 2023), stage à l'ANSD
**Données** : EHCVM 2018/2019, Sénégal. Base individuelle fusionnée (66 120 individus) ; l'analyse est menée au niveau des 7 156 ménages.
**Logiciel** : Stata 16 ou plus récent

## Objectif

Mesurer la pauvreté au-delà de la seule dépense de consommation, en construisant un **Indice Flou de Pauvreté Multidimensionnelle (IFPM)**. L'étude identifie ensuite les groupes et les dimensions qui contribuent le plus à la pauvreté, ainsi que les déterminants de la pauvreté des ménages.

## Méthode

1. **Degrés de privation** : 19 indicateurs de conditions de vie sont transformés en degrés de privation compris entre 0 (non privé) et 1 (totalement privé). Les variables ordinales (quintile de dépense, niveau d'instruction, statut d'occupation du logement) reçoivent des valeurs intermédiaires.
2. **Attributs** : les indicateurs sont regroupés en 7 attributs. Ce sont les biens possédés, le niveau d'instruction, le quintile de dépense, le handicap majeur du chef de ménage, le statut d'occupation du logement, l'habitat et les éléments de confort.
3. **Pondération** : chaque attribut reçoit le poids w = ln(1/μ), où μ est sa privation moyenne (Cerioli et Zani). Une privation rare pèse donc davantage.
4. **Indice** : l'IFPM suit Dagum et Costa (2004). Il est décomposé par attribut et par groupe de population (région, milieu, sexe et âge du chef de ménage, taille du ménage), selon Mussard et Pi Alperin (2005).
5. **Déterminants** : un modèle logit estime les déterminants de la pauvreté monétaire des ménages. Il utilise une sélection descendante et des erreurs-types robustes. Sa validation repose sur la matrice de confusion, le test de Hosmer-Lemeshow, la courbe ROC et les effets marginaux.

## Organisation et ordre d'exécution

| Fichier | Rôle |
|---|---|
| `00_master.do` | Chemins, pondération, lancement de tous les scripts |
| `01_preparation/01_preparation.do` | Contrôles de la base, création des variables communes |
| `02_analyse_descriptive/02_analyse_descriptive.do` | Caractéristiques des ménages, profil de pauvreté |
| `03_indicateur_flou/03_indicateur_flou.do` | Calcul de l'IFPM, contributions, décompositions |
| `04_modele_logit/04_modele_logit.do` | Modèle logit et validation |
| `data/` | Emplacement de la base (non fournie) |
| `output/` | Tableaux Excel et graphiques produits |

## Utilisation

1. Placer la base dans `data/` sous le nom `BASE.dta`.
2. Modifier la ligne `global root` dans `00_master.do`.
3. Exécuter `00_master.do`.

## Données

Les microdonnées EHCVM 2018/2019 ne sont pas incluses. Elles sont diffusées par l'ANSD et la Banque mondiale (Microdata Library).
