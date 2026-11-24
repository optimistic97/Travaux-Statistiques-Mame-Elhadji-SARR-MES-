/*******************************************************************************
  Script  : 03_indicateur_flou.do
  Objet   : Indice Flou de Pauvreté Multidimensionnelle (IFPM)
            Méthode de Dagum et Costa (2004), décompositions de Mussard et
            Pi Alperin (2005)
            1. Degrés de privation x_ij dans [0,1] pour 19 indicateurs
               (0 = non privé, 1 = totalement privé)
            2. Regroupement en 7 attributs (X1 à X7)
            3. Poids de Cerioli et Zani : w_j = ln(1 / mu_j), où mu_j est
               l'indice unidimensionnel de l'attribut j (privation moyenne)
            4. IFPM du ménage : mu_B(a_i) = somme_j x_ij w_j / somme_j w_j
            5. Contributions des attributs et décompositions par groupe
  Entrée  : $data/base_prep.dta
  Sorties : $output/ifpm_attributs.xlsx, $output/ifpm_groupes.xlsx
  Auteur  : Mame Elhadji SARR
*******************************************************************************/

version 16
use "$data/base_prep.dta", clear

* ---------------------------------------------------------------------------
* 1. Degrés de privation des indicateurs élémentaires
* ---------------------------------------------------------------------------

* Variables ordinales : échelle linéaire, de 1 (modalité la plus défavorable)
* à 0 (modalité la plus favorable)
gen d_quintile    = (5 - quintile) / 4             // Q1 = 1 ... Q5 = 0
gen d_instruction = (5 - niveau_instruction) / 4   // Aucun = 1 ... Supérieur = 0

* Statut d'occupation : propriétaire (avec ou sans titre) = 0,
* locataire = 0,5, autre = 1
gen d_logement = .
replace d_logement = 0   if inlist(logem, 1, 2)
replace d_logement = 0.5 if logem == 3
replace d_logement = 1   if logem == 4

* Variables binaires codées 1 = possède / a accès : privation = 1 - variable
local acces  alphab halfab  sol sol  mur mur  toit toit  ordures ordure ///
             toilettes toilet  eau eauboi_ss  electricite elec_ac       ///
             internet internet  tv tv  fer fer  frigo frigo             ///
             cuisiniere cuisin  telephone telpor  voiture car
while "`acces'" != "" {
    gettoken nom acces : acces
    gettoken var acces : acces
    gen d_`nom' = 1 - `var'
}
replace d_internet = 1 if missing(internet)   // non renseigné = pas d'accès

* Handicap majeur du chef de ménage (1 = handicap) : privation si handicap
gen d_handicap = hhandig

* Contrôle : tous les degrés de privation sont compris entre 0 et 1
foreach v of varlist d_* {
    assert inrange(`v', 0, 1) | missing(`v')
}
misstable summarize d_*

* ---------------------------------------------------------------------------
* 2. Les 7 attributs (moyenne simple des indicateurs qui les composent)
* ---------------------------------------------------------------------------
egen X1 = rowmean(d_telephone d_voiture d_cuisiniere d_tv d_fer d_frigo)
egen X2 = rowmean(d_instruction d_alphab)
gen  X3 = d_quintile
gen  X4 = d_handicap
gen  X5 = d_logement
egen X6 = rowmean(d_sol d_mur d_toit d_ordures d_toilettes d_eau)
egen X7 = rowmean(d_electricite d_internet)

label variable X1 "Biens de possession"
label variable X2 "Niveau d'instruction"
label variable X3 "Quintile de dépense par tête"
label variable X4 "Handicap majeur du CM"
label variable X5 "Statut d'occupation du logement"
label variable X6 "Habitat"
label variable X7 "Éléments de confort"

global attributs X1 X2 X3 X4 X5 X6 X7

* ---------------------------------------------------------------------------
* 3. Indices unidimensionnels et poids
* ---------------------------------------------------------------------------
matrix A = J(8, 4, .)
matrix colnames A = indice_unidim poids contrib_absolue contrib_relative
matrix rownames A = $attributs IFPM

local somme_w = 0
forvalues j = 1/7 {
    quietly summarize X`j' [aw = $pond]
    matrix A[`j', 1] = r(mean)
    matrix A[`j', 2] = ln(1 / r(mean))
    local somme_w = `somme_w' + ln(1 / r(mean))
}

* ---------------------------------------------------------------------------
* 4. IFPM du ménage et de la population
* ---------------------------------------------------------------------------
gen ifpm = 0
forvalues j = 1/7 {
    replace ifpm = ifpm + X`j' * A[`j', 2] / `somme_w'
}
label variable ifpm "Indice flou de pauvreté multidimensionnelle"
quietly summarize ifpm [aw = $pond]
scalar IFPM = r(mean)
di as result "IFPM national = " %6.4f IFPM

* Contributions des attributs (Dagum et Costa) : C_j = mu_j w_j / somme w
forvalues j = 1/7 {
    matrix A[`j', 3] = A[`j', 1] * A[`j', 2] / `somme_w'
    matrix A[`j', 4] = A[`j', 3] / IFPM
}
matrix A[8, 1] = IFPM
matrix A[8, 3] = IFPM
matrix A[8, 4] = 1
matlist A, format(%6.4f)

putexcel set "$output/ifpm_attributs.xlsx", replace
putexcel A1 = matrix(A), names nformat("0.0000")

* ---------------------------------------------------------------------------
* 5. Décompositions par groupe (Mussard et Pi Alperin)
*    IFPM du groupe et indices unidimensionnels par attribut et par groupe
* ---------------------------------------------------------------------------
foreach g in region milieu hgender groupe_age taille_men {
    di as text _n "===== Décomposition selon `g' ====="
    tabstat ifpm $attributs [aw = $pond], by(`g') stat(mean) format(%6.4f)

    preserve
    collapse (mean) ifpm $attributs [aw = $pond], by(`g')
    export excel using "$output/ifpm_groupes.xlsx", ///
        sheet("`g'", replace) firstrow(varlabels)
    restore
}

* Comparaison avec la pauvreté monétaire
tabstat ifpm [aw = $pond], by(p0) stat(mean) format(%6.4f)

save "$data/base_ifpm.dta", replace
