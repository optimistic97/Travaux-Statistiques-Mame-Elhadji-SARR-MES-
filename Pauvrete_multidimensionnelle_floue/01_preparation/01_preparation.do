/*******************************************************************************
  Script  : 01_preparation.do
  Objet   : Contrôles de la base et création des variables communes
            (groupes d'âge, taille du ménage, niveau d'instruction,
            dépense par tête, quintiles)
  Entrée  : $base
  Sortie  : $data/base_prep.dta
  Auteur  : Mame Elhadji SARR
*******************************************************************************/

version 16

use "$base", clear

* ---------------------------------------------------------------------------
* 1. Passage au niveau ménage et contrôles de qualité
*    La base EHCVM fusionnée contient une ligne par individu (66 120).
*    L'analyse porte sur les ménages : on garde la ligne du chef de ménage,
*    qui porte toutes les caractéristiques du ménage et du CM.
* ---------------------------------------------------------------------------
keep if lien == 1
isid hhid                                  // une seule ligne par ménage
count                                      // 7 156 ménages attendus

foreach v in hhid hhweight hhsize p0 dtot milieu region heduc hmstat {
    confirm variable `v'
    quietly count if missing(`v')
    if r(N) > 0 di as error "`v' : " r(N) " valeurs manquantes"
}
assert inlist(p0, 0, 1)
assert hhsize > 0 & hhweight > 0

* Distribution des variables utilisées
foreach v in hcsp hbranch hhandig hdiploma heduc hmstat halfab hgender ///
             toilet elec_ac eauboi_ss logem mur toit sol milieu region {
    tab `v', missing
}
summarize hage hhsize dtot

* ---------------------------------------------------------------------------
* 2. Variables dérivées
* ---------------------------------------------------------------------------
* Groupes d'âge du chef de ménage
recode hage (min/24 = 1 "Moins de 25 ans") (25/39 = 2 "25 à 39 ans")      ///
            (40/49  = 3 "40 à 49 ans")     (50/59 = 4 "50 à 59 ans")      ///
            (60/max = 5 "60 ans et plus"), gen(groupe_age)
label variable groupe_age "Groupe d'âge du chef de ménage"

* Taille du ménage en classes
recode hhsize (1/5 = 1 "1 à 5 personnes")   (6/11  = 2 "6 à 11 personnes")  ///
              (12/17 = 3 "12 à 17 personnes") (18/23 = 4 "18 à 23 personnes") ///
              (24/max = 5 "24 personnes et plus"), gen(taille_men)
label variable taille_men "Taille du ménage (classes)"

* Statut de pauvreté monétaire
label define pauv_lbl 0 "Non pauvre" 1 "Pauvre"
label values p0 pauv_lbl

* Niveau d'instruction du chef de ménage
recode heduc (1 = 1 "Aucun") (2 = 2 "Maternelle") (3 = 3 "Primaire") ///
               (4/8 = 4 "Secondaire") (9 = 5 "Supérieur"), gen(niveau_instruction)
label variable niveau_instruction "Niveau d'instruction du chef de ménage"

* Situation matrimoniale du chef de ménage (petites modalités regroupées)
recode hmstat (1 = 1 "Célibataire") (2 4 = 2 "Marié monogame ou union libre") ///
              (3 = 3 "Marié polygame") (5 = 4 "Veuf ou veuve")               ///
              (6 7 = 5 "Divorcé ou séparé"), gen(statut_mat)
label variable statut_mat "Situation matrimoniale du chef de ménage"

* Dépense par tête et quintiles (pondérés par la population)
gen dep_tete = dtot / hhsize
label variable dep_tete "Dépense annuelle par tête"
xtile quintile = dep_tete [pw = $pond], nq(5)
label define quint_lbl 1 "Q1 (plus pauvres)" 2 "Q2" 3 "Q3" 4 "Q4" 5 "Q5 (plus riches)"
label values quintile quint_lbl
tab quintile

save "$data/base_prep.dta", replace
