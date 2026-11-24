/*******************************************************************************
  Script  : 04_modele_logit.do
  Objet   : Déterminants de la pauvreté des ménages (modèle logit binaire)
            Variable dépendante : $ydep (définie dans 00_master.do)
  Entrée  : $data/base_prep.dta
  Sorties : $output/courbes_roc_sensibilite.png
  Auteur  : Mame Elhadji SARR
*******************************************************************************/

version 16

use "$data/base_prep.dta", clear

global X taille_men statut_mat groupe_age niveau_instruction region milieu ///
         hgender halfab hhandig

keep $ydep hage hhsize hhweight $X
misstable summarize $ydep $X

* ---------------------------------------------------------------------------
* 1. Analyse bivariée
* ---------------------------------------------------------------------------
* Variables qualitatives : khi-deux et V de Cramér
foreach v of global X {
    tab $ydep `v', chi2 V nofreq
}

* Variables quantitatives : comparaison des moyennes
ttest hhsize, by($ydep)
ttest hage,   by($ydep)

* Association entre variables explicatives (indicatif)
pwcorr $X

* ---------------------------------------------------------------------------
* 2. Estimation
* ---------------------------------------------------------------------------
* Modèle sans variable explicative (référence)
logit $ydep

* Modèle complet (variables qualitatives en indicatrices)
logit $ydep i.taille_men i.statut_mat i.groupe_age i.niveau_instruction i.region ///
         i.milieu i.hgender i.halfab i.hhandig
estimates store complet

* Sélection descendante (seuil de sortie 5 %)
stepwise, pr(.05): logit $ydep (i.taille_men) (i.statut_mat) (i.groupe_age)       ///
          (i.niveau_instruction) (i.region) (i.milieu) (i.hgender)        ///
          (i.halfab) (i.hhandig)
estimates store selection

* Modèle retenu, erreurs-types robustes
logit $ydep i.taille_men i.statut_mat i.groupe_age i.niveau_instruction i.region ///
         i.milieu i.hgender i.halfab i.hhandig, vce(robust)
estimates store retenu

estimates table complet selection retenu, star stats(N r2_p ll aic bic)

* ---------------------------------------------------------------------------
* 3. Qualité d'ajustement (modèle retenu)
* ---------------------------------------------------------------------------
* Les coefficients sont identiques au modèle complet (seule la variance change) :
* les tests d'ajustement sont faits sur l'estimation standard.
estimates restore complet
estat classification                       // taux de bonne classification
estat gof, group(10)                       // test de Hosmer-Lemeshow

lroc, title("Courbe ROC") saving("$output/roc.gph", replace)
lsens, title("Sensibilité et spécificité") saving("$output/sens.gph", replace)
graph combine "$output/roc.gph" "$output/sens.gph", ///
    title("Qualité de prédiction du modèle", size(medium))
graph export "$output/courbes_roc_sensibilite.png", replace

* ---------------------------------------------------------------------------
* 4. Interprétation
* ---------------------------------------------------------------------------
estimates restore retenu
logit, or                                  // rapports de cotes
margins, dydx(*)                           // effets marginaux moyens
