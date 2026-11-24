# Questionnaire ODK : enquête sur l'inclusion financière (EIFIS)

Questionnaire d'enquête ménages au format **XLSForm**, utilisable avec ODK Collect et KoboToolbox.

## Contenu du fichier

Le classeur `Questionnaire_Gestion_des_controles_ODK.xlsx` suit la structure standard XLSForm.

| Feuille | Rôle |
|---|---|
| `survey` | Questions, types de réponse, sauts et contrôles |
| `choices` | Listes de modalités |
| `settings` | Paramètres du formulaire |

## Sections du questionnaire

| Section | Thème |
|---|---|
| 0 | Identification du ménage |
| I | Situation socioéconomique |
| II | Connaissance des services financiers, éducation financière |
| III | Accès physique aux services financiers |
| IV | Accès et utilisation des moyens de paiement |
| V | Accès et utilisation de l'épargne |
| VI | Accès et utilisation du crédit |
| VII | Accès et utilisation du transfert d'argent |
| VIII | Accès et utilisation de la monnaie électronique (mobile banking) |
| IX | Accès et utilisation des assurances |
| X | Accès et utilisation des services financiers informels |
| XI | Besoins de financement |

## Contrôles de qualité intégrés à la saisie

- **Sauts conditionnels** (colonne `relevant`) : une question ne s'affiche que si elle concerne le répondant.
- **Listes en cascade** (colonne `choice_filter`) : la liste des départements dépend de la région choisie.
- **Contraintes de format** (colonne `constraint`) : par exemple, les numéros de téléphone doivent commencer par 77, 78 ou 70 et compter 9 chiffres ; les identifiants numériques doivent être des entiers positifs.
- **Contrôles de cohérence entre questions** : certaines combinaisons de réponses incompatibles sont bloquées directement à la saisie.
- **Questions obligatoires** (colonne `required`) et **messages d'erreur** explicites pour l'enquêteur (colonne `constraint_message`).

## Utilisation

Importer le fichier dans KoboToolbox (*Nouveau projet > Importer un XLSForm*) ou le convertir avec ODK Build ou pyxform, puis déployer le formulaire sur les tablettes des enquêteurs.
