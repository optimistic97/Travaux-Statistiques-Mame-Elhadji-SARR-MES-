/*******************************************************************************
  Projet  : Analyse multidimensionnelle de la pauvreté par l'approche
            des indicateurs flous (Sénégal, données EHCVM)
  Script  : 00_master.do  (exécute l'ensemble du projet dans l'ordre)
  Auteur  : Mame Elhadji SARR
  Cadre   : Mémoire d'Analyste Statisticien, ENSAE Pierre Ndiaye (juin 2023)
  Logiciel: Stata 16 ou plus récent
*******************************************************************************/

version 16
clear all
set more off

* ---------------------------------------------------------------------------
* 1. Chemin racine : SEULE ligne à modifier pour exécuter le projet
* ---------------------------------------------------------------------------
global root "C:/Users/VotreNom/Documents/Pauvrete_multidimensionnelle_floue"

global data   "$root/data"
global output "$root/output"
capture mkdir "$output"

* Base de données (non fournie : voir README)
global base "$data/BASE.dta"

* ---------------------------------------------------------------------------
* 2. Pondération : poids de sondage des ménages (analyse au niveau ménage)
* ---------------------------------------------------------------------------
global pond "hhweight"

* Variable dépendante du modèle logit : p0 = pauvreté monétaire du ménage
global ydep "p0"

* ---------------------------------------------------------------------------
* 3. Exécution
* ---------------------------------------------------------------------------
do "$root/01_preparation/01_preparation.do"
do "$root/02_analyse_descriptive/02_analyse_descriptive.do"
do "$root/03_indicateur_flou/03_indicateur_flou.do"
do "$root/04_modele_logit/04_modele_logit.do"
