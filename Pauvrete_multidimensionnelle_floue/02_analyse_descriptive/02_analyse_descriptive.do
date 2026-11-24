/*******************************************************************************
  Script  : 02_analyse_descriptive.do
  Objet   : Caractéristiques des ménages et profil de la pauvreté monétaire
  Entrée  : $data/base_prep.dta
  Auteur  : Mame Elhadji SARR
*******************************************************************************/

version 16

use "$data/base_prep.dta", clear

* ---------------------------------------------------------------------------
* 1. Caractéristiques des ménages selon le milieu de résidence
* ---------------------------------------------------------------------------
foreach v in hgender niveau_instruction groupe_age statut_mat taille_men ///
             halfab logem sol mur hcsp hbranch {
    di as text _n "===== `v' selon le milieu de résidence ====="
    tab `v' milieu [aw = hhweight], nofreq col
}

* ---------------------------------------------------------------------------
* 2. Profil de la pauvreté
*    Pour chaque caractéristique :
*    - incidence (part de pauvres dans chaque groupe)
*    - contribution (répartition des pauvres entre les groupes)
*    - test d'indépendance du khi-deux et V de Cramér
* ---------------------------------------------------------------------------
foreach v in hgender groupe_age taille_men milieu region niveau_instruction ///
             statut_mat hcsp hbranch halfab hhandig hdiploma {
    di as text _n "===== Pauvreté selon `v' ====="
    table `v' [pw = $pond], c(mean p0) format(%5.3f)            // incidence
    tab `v' if p0 == 1 [aw = $pond]                              // contribution
    tab `v' p0, chi2 V                                           // test
}
