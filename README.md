# Travaux statistiques : Mame Elhadji SARR (MES)

Recueil de travaux d'analyse statistique réalisés à partir d'enquêtes auprès des ménages au Sénégal (EHCVM, inclusion financière) et des entreprises (RGE), en R, Stata, Python et XLSForm.

**Auteur** : Mame Elhadji SARR, Ingénieur Statisticien Économiste (ENSAE Pierre Ndiaye de Dakar)

## Projets

| Dossier | Description | Outils |
|---|---|---|
| [`Traitement_donnees_EHCVM2`](Traitement_donnees_EHCVM2) | Pipeline reproductible de nettoyage de l'EHCVM2 : dictionnaire de données, nettoyage paramétré, fusion ménages et individus, rapport de qualité pondéré (QAQC). | R, R Markdown |
| [`Pauvrete_multidimensionnelle_floue`](Pauvrete_multidimensionnelle_floue) | Mémoire d'Analyste Statisticien (ENSAE, 2023) : indice flou de pauvreté multidimensionnelle (IFPM) sur l'EHCVM 2018/2019, décompositions et modèle logit des déterminants de la pauvreté. | Stata |
| [`Performance_des_entreprises`](Performance_des_entreprises) | Mémoire d'ingénieur (ENSAE, stage CCIAD, 2026) : facteurs associés au niveau d'activité des PME au Sénégal à partir du RGE 2016. Logit ordonné, test de Brant et logit ordonné généralisé à cotes proportionnelles partielles (PPO), estimé par maximum de vraisemblance dans le script. | Python |
| [`Questionnaire_ODK`](Questionnaire_ODK) | Questionnaire XLSForm de l'enquête sur l'inclusion financière, avec sauts conditionnels, listes en cascade et contraintes de saisie. | XLSForm, KoboToolbox |

Chaque dossier contient son propre README, qui détaille son fonctionnement et la manière de l'exécuter.

## Fil conducteur

Ces travaux couvrent la chaîne de production statistique, de la collecte à l'analyse :

1. **Collecte** : conception d'un questionnaire électronique avec contrôles intégrés (`Questionnaire_ODK`).
2. **Traitement** : nettoyage, fusion et contrôle qualité de microdonnées d'enquête (`Traitement_donnees_EHCVM2`).
3. **Analyse** : mesure multidimensionnelle de la pauvreté (`Pauvrete_multidimensionnelle_floue`) et modélisation économétrique de la performance des entreprises (`Performance_des_entreprises`).

## Données

Les données EHCVM sont produites par l'ANSD (Sénégal) dans le cadre du programme régional EHCVM (UEMOA, Banque mondiale). Les microdonnées du Recensement général des entreprises (RGE 2016, ANSD) ne sont pas publiées dans ce dépôt.
