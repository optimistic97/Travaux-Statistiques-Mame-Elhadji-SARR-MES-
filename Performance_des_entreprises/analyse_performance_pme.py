# %% [markdown]
# # Facteurs associés au niveau d'activité des PME au Sénégal
#
# Mémoire d'ingénieur (ENSAE Pierre Ndiaye, stage CCIAD, juillet 2026).
# Données : Recensement général des entreprises (RGE) 2016, ANSD.
# Méthode : logit ordonné, test de Brant, logit ordonné généralisé à cotes
# proportionnelles partielles (PPO), erreurs-types en grappes région x
# branche.
#
# Exécution complète : ``python analyse_performance_pme.py``
# Exécution par cellule : VS Code ou Jupyter (marqueurs ``# %%``).

# %% [markdown]
# ## 0. Paramètres et moteur d'estimation
#
# Objectif : fixer en un seul endroit le chemin racine, la graine aléatoire,
# les options d'affichage et les dossiers de sortie. Aucun chemin absolu :
# tout est relatif à l'emplacement de ce fichier.
#
# Pourquoi un moteur écrit dans le script : aucune bibliothèque Python
# n'implémente le logit ordonné généralisé à cotes proportionnelles
# partielles (équivalent de ``gologit2`` sous Stata) avec erreurs-types en
# grappes. L'estimation par maximum de vraisemblance est donc codée ici, avec
# gradient et hessienne analytiques, de façon transparente et auditable.

# %%
import os
import sys
import time
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from scipy.optimize import minimize

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")
pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", lambda v: f"{v:,.4f}")

# --- Chemins (relatifs à ce fichier) ---------------------------------------
try:
    RACINE = Path(__file__).resolve().parent
except NameError:  # exécution cellule par cellule dans Jupyter
    RACINE = Path.cwd()
DOSSIER_DONNEES = RACINE / "data"
DOSSIER_SORTIE = RACINE / "output"
DOSSIER_TABLEAUX = DOSSIER_SORTIE / "tableaux"
DOSSIER_FIGURES = DOSSIER_SORTIE / "figures"
for _dossier in (DOSSIER_TABLEAUX, DOSSIER_FIGURES):
    _dossier.mkdir(parents=True, exist_ok=True)

# Fichier de la base d'analyse : variable d'environnement PME_DATA, premier
# argument de la ligne de commande, ou fichier base_analyse.* dans data/.
EXTENSIONS_ACCEPTEES = (".dta", ".csv", ".parquet", ".pkl")

# --- Graine aléatoire (échantillon de retrait 70/30) -----------------------
GRAINE = 20260728

# --- Effectifs attendus (mémoire, chapitres 2 et 4) ------------------------
N_UNITES_ACTIVES = 406_408
N_ECHANTILLON = 292_589
DISTRIBUTION_Y = [85_935, 134_006, 48_014, 23_525, 1_109]
N_GRAPPES = 135

# --- Définition des variables ----------------------------------------------
VAR_DEP = "y"
GRAPPES = "cell_rb"
HYPOTHESES = ["formel", "banque_obt", "fin_informel", "femme"]
BLOC_SUBSTANTIEL = [
    "age",
    "age2",
    "educ2",
    "educ3",
    "educ4",
    "compta",
    "reseau",
    "urbain",
    "contraintes_rb",
]
REGIONS = [f"reg_{k}" for k in range(2, 15)]  # référence : Dakar (1)
BRANCHES = [f"br_{k}" for k in (1, 2, 3, 4, 5, 7, 8, 9, 10)]  # réf. : 6
FEMME_BRANCHE = [f"femme_br_{k}" for k in (1, 2, 3, 4, 5, 7, 8, 9, 10)]
# Variables contraintes (un seul coefficient pour les quatre seuils).
# La variable ``cuci`` est retirée : une seule unité cuci = 1 subsiste dans
# l'échantillon d'estimation (quasi-séparation).
CONTROLES = ["pers_morale"] + REGIONS + BRANCHES + FEMME_BRANCHE
X_LIBRES = HYPOTHESES + BLOC_SUBSTANTIEL  # 13 variables à coefficients/seuil
X_CONTRAINTES = CONTROLES  # 32 variables à coefficient commun
X_TOUS = X_LIBRES + X_CONTRAINTES  # 45 régresseurs
N_SEUILS = 4

COLONNES_REQUISES = [
    VAR_DEP,
    "formel",
    "banque_obt",
    "fin_informel",
    "femme",
    "age",
    "educ",
    "compta",
    "reseau",
    "urbain",
    "contraintes_rb",
    "pers_morale",
    "region",
    "branche",
]

ETIQUETTES = {
    "formel": "Formalité (H1)",
    "banque_obt": "Financement bancaire obtenu (H3)",
    "fin_informel": "Financement informel : tontine/famille (H3)",
    "femme": "Dirigeant femme (H2)",
    "age": "Âge de l'entreprise (années)",
    "age2": "Âge² / 100",
    "educ2": "Instruction : primaire",
    "educ3": "Instruction : moyen/secondaire",
    "educ4": "Instruction : supérieur",
    "compta": "Comptabilité écrite",
    "reseau": "Réseau professionnel",
    "urbain": "Milieu urbain",
    "contraintes_rb": "Contraintes région×branche",
    "pers_morale": "Personne morale",
}
NOMS_REGIONS = {
    1: "Dakar",
    2: "Ziguinchor",
    3: "Diourbel",
    4: "Saint-Louis",
    5: "Tambacounda",
    6: "Kaolack",
    7: "Thiès",
    8: "Louga",
    9: "Fatick",
    10: "Kolda",
    11: "Matam",
    12: "Kaffrine",
    13: "Kédougou",
    14: "Sédhiou",
}
NOMS_BRANCHES = {
    1: "Agriculture, élevage, pêche",
    2: "Industries alimentaires",
    3: "Industries textiles",
    4: "Autres industries",
    5: "Bâtiments et travaux publics",
    6: "Commerce",
    7: "Transport et télécoms",
    8: "Hôtels, bars, restaurants",
    9: "Services aux entreprises",
    10: "Services personnels, divers",
}
for _k, _v in NOMS_REGIONS.items():
    if _k > 1:
        ETIQUETTES[f"reg_{_k}"] = f"Région : {_v}"
for _k, _v in NOMS_BRANCHES.items():
    if _k != 6:
        ETIQUETTES[f"br_{_k}"] = f"Branche : {_v}"
        ETIQUETTES[f"femme_br_{_k}"] = f"Femme × {_v}"
CLASSES = {
    1: "C1 (<1M)",
    2: "C2 (1--5M)",
    3: "C3 (5--15M)",
    4: "C4 (15--200M)",
    5: "C5 (≥200M)",
}
# Bornes monétaires (FCFA) des classes de chiffre d'affaires.
BORNES_CLASSES = {
    1: (None, 1e6),
    2: (1e6, 5e6),
    3: (5e6, 15e6),
    4: (15e6, 200e6),
    5: (200e6, None),
}


def etiquette(variable):
    """Libellé de publication d'une variable."""
    return ETIQUETTES.get(variable, variable)


def controle(condition, message):
    """Contrôle qualité explicite : interrompt l'exécution si non vérifié."""
    if not condition:
        raise AssertionError(f"Contrôle qualité échoué : {message}")
    print(f"  [ok] {message}")


# --- Registre des tableaux exportés (CSV + classeur Excel final) ----------
TABLEAUX = {}


def exporter_tableau(df, nom, index=False):
    """Écrit un tableau en CSV (UTF-8 avec BOM, lisible sous Excel) et le
    garde en mémoire pour le classeur Excel de la cellule 8."""
    chemin = DOSSIER_TABLEAUX / f"{nom}.csv"
    df.to_csv(chemin, index=index, encoding="utf-8-sig")
    TABLEAUX[nom] = df.reset_index() if index else df
    return chemin


def style_graphique():
    """Style sobre (fond blanc, grille légère) pour tous les graphiques."""
    matplotlib.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.family": "serif",
            "font.size": 11,
            "axes.edgecolor": "#3b3b3b",
            "axes.linewidth": 0.8,
            "axes.grid": True,
            "grid.color": "#d9d9d9",
            "grid.linewidth": 0.6,
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": True,
            "legend.framealpha": 0.9,
            "legend.edgecolor": "#bbbbbb",
            "figure.dpi": 130,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
        }
    )
    return ["#1a476f", "#a50026", "#2e7d32", "#8c6d1f", "#5b5b5b"]


def enregistrer_figure(fig, nom):
    """Enregistre une figure en PNG dans output/figures/."""
    fig.savefig(DOSSIER_FIGURES / f"{nom}.png")
    plt.close(fig)


def etoiles(p):
    """Étoiles de significativité : * 10 %, ** 5 %, *** 1 %."""
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


PALETTE = style_graphique()


# %%
def _sigmoid(z):
    # stable
    out = np.empty_like(z, dtype=float)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def _lm_newton(nll, grad, hess, theta0, maxiter=100, tol=1e-7, verbose=False):
    """Newton amorti de Levenberg-Marquardt : pas = (H + λI)^{-1} g.
    Le terme λI
    ne sert qu'à régulariser l'INVERSION (Hessiennes singulières / directions
    plates dues aux quasi-séparations dans les classes rares) ; à convergence
    λ→0, de sorte que l'estimateur reste le MV exact. Robuste et rapide (~10-15
    itérations), avec Hessienne analytique."""
    theta = np.asarray(theta0, float)
    f0 = nll(theta)
    lam = 1e-3
    H = hess(theta)
    for it in range(maxiter):
        g = grad(theta)
        H = hess(theta)
        diag = np.diag(H).copy()
        diag[diag <= 0] = 1.0
        accepted = False
        for _ in range(40):
            try:
                step = np.linalg.solve(H + lam * np.diag(diag), g)
            except np.linalg.LinAlgError:
                lam *= 10
                continue
            new = theta - step
            fnew = nll(new)
            if np.isfinite(fnew) and fnew < f0 - 1e-12:
                accepted = True
                break
            lam = min(lam * 10, 1e12)
        if not accepted:
            break
        gnorm = np.max(np.abs(g))
        stepnorm = np.max(np.abs(step))
        if verbose:
            print(
                f"  it {it:2d} nll={fnew:.2f} lam={lam:.1e} "
                f"|step|={stepnorm:.2e} |g|={gnorm:.2e}",
                flush=True,
            )
        theta, f0 = new, fnew
        lam = max(lam / 10, 1e-10)
        if stepnorm < tol:
            break
    return theta, H, it + 1


def cluster_robust_vcov(scores, hess_inv, clusters):
    """Sandwich agrégé en grappes : V = H^{-1} (Σ_g u_g u_g') H^{-1}
    avec u_g = somme des scores de la grappe g. Correction petits échantillons
    à la Stata : c = G/(G-1) * (N-1)/(N-K)."""
    clusters = np.asarray(clusters)
    N, K = scores.shape
    # Agrégation des scores par grappe (vectorisée) : U (G x K)
    codes, uniq = pd.factorize(clusters)
    G = len(uniq)
    U = np.zeros((G, K))
    np.add.at(U, codes, scores)
    B = U.T @ U
    c = (G / (G - 1.0)) * ((N - 1.0) / (N - K))
    V = hess_inv @ (c * B) @ hess_inv
    return V


class GenOrderedLogit:
    """Pr(Y>j|x)=Λ(α_j + x_np'γ_j + x_pl'β), j=1..J-1.
       x_np : variables LIBÉRÉES (γ_j varie par seuil)
       x_pl : variables CONTRAINTES (β commun)
       Paramètres : [α_1..α_{J-1}] + [γ_j pour chaque var libérée, par seuil]
                    + [β pour chaque var contrainte].
    Scores analytiques -> SE OIM ou en grappes (sandwich)."""

    def __init__(self, y, Xnp, Xpl, names_np, names_pl):
        self.y = np.asarray(y, dtype=int)
        self.Xnp = np.asarray(Xnp, dtype=float)
        self.Xpl = np.asarray(Xpl, dtype=float)
        self.names_np = list(names_np)
        self.names_pl = list(names_pl)
        self.N = len(self.y)
        self.Knp = self.Xnp.shape[1]
        self.Kpl = self.Xpl.shape[1]
        self.J = int(self.y.max())
        self.ncut = self.J - 1
        # index des paramètres
        self.n_alpha = self.ncut
        self.n_gamma = self.Knp * self.ncut
        self.n_beta = self.Kpl
        self.nparam = self.n_alpha + self.n_gamma + self.n_beta

    def _eta(self, theta):
        alpha = theta[: self.n_alpha]
        gamma = theta[self.n_alpha : self.n_alpha + self.n_gamma].reshape(
            self.Knp, self.ncut
        )
        beta = theta[self.n_alpha + self.n_gamma :]
        xb_pl = self.Xpl @ beta  # N (commun à tous les seuils)
        xg = self.Xnp @ gamma  # N x ncut
        eta = alpha[None, :] + xg + xb_pl[:, None]  # N x ncut
        return eta, alpha, gamma, beta

    def _probs(self, theta):
        eta, *_ = self._eta(theta)
        G = _sigmoid(eta)  # Pr(Y>j)
        return G

    def negloglik(self, theta):
        G = self._probs(theta)
        Gpad = np.hstack([np.ones((self.N, 1)), G, np.zeros((self.N, 1))])
        p = (
            Gpad[np.arange(self.N), self.y - 1]
            - Gpad[np.arange(self.N), self.y]
        )
        p = np.clip(p, 1e-12, 1.0)
        return -np.sum(np.log(p))

    def scores(self, theta):
        G = self._probs(theta)
        lam = G * (1.0 - G)
        Gpad = np.hstack([np.ones((self.N, 1)), G, np.zeros((self.N, 1))])
        p = (
            Gpad[np.arange(self.N), self.y - 1]
            - Gpad[np.arange(self.N), self.y]
        )
        p = np.clip(p, 1e-12, 1.0)
        dl_deta = np.zeros((self.N, self.ncut))
        for j in range(1, self.ncut + 1):
            col = j - 1
            is_up = self.y - 1 == j  # Pr(Y>j) apparaît en +
            is_lo = self.y == j  # Pr(Y>j) apparaît en -
            dl_deta[is_up, col] += lam[is_up, col] / p[is_up]
            dl_deta[is_lo, col] -= lam[is_lo, col] / p[is_lo]
        # scores :
        # alpha_j : dη_j/dα_j = 1  -> score = dl_deta[:,j]
        s_alpha = dl_deta  # N x ncut
        # gamma_{k,j} : dη_j/dγ_{k,j} = Xnp[:,k]
        # -> score = dl_deta[:,j]*Xnp[:,k]
        s_gamma = np.einsum("nj,nk->nkj", dl_deta, self.Xnp).reshape(
            self.N, self.Knp * self.ncut
        )
        # beta_k : β commun -> dη_j/dβ_k = Xpl[:,k] pour tout j -> somme sur j
        s_beta = (dl_deta.sum(axis=1)[:, None]) * self.Xpl  # N x Kpl
        return np.hstack([s_alpha, s_gamma, s_beta])

    def _dl_deta(self, theta):
        """Dérivée du log-vraisemblance p/r aux indices η_j (N x ncut). Coeur
        commun au gradient (rapide, par produits matriciels) et aux scores."""
        G = self._probs(theta)
        lam = G * (1.0 - G)
        Gpad = np.hstack([np.ones((self.N, 1)), G, np.zeros((self.N, 1))])
        p = (
            Gpad[np.arange(self.N), self.y - 1]
            - Gpad[np.arange(self.N), self.y]
        )
        p = np.clip(p, 1e-12, 1.0)
        dl = np.zeros((self.N, self.ncut))
        for j in range(1, self.ncut + 1):
            col = j - 1
            is_up = self.y - 1 == j
            is_lo = self.y == j
            dl[is_up, col] += lam[is_up, col] / p[is_up]
            dl[is_lo, col] -= lam[is_lo, col] / p[is_lo]
        return dl

    def _grad(self, theta):
        # Gradient analytique par produits matriciels
        # (aucune matrice N x nparam).
        dl = self._dl_deta(theta)
        g_alpha = dl.sum(axis=0)
        g_gamma = (self.Xnp.T @ dl).reshape(-1)  # ordre [k*ncut + j]
        g_beta = self.Xpl.T @ dl.sum(axis=1)
        return -np.concatenate([g_alpha, g_gamma, g_beta])

    def _hessian(self, theta):
        """Hessienne analytique EXACTE de la log-vraisemblance NÉGATIVE.
        Exploite la structure : chaque observation ne fait intervenir que les
        deux seuils encadrant sa classe (matrice W_i, ncut x ncut, creuse)."""
        m = self.ncut
        G = self._probs(theta)  # N x m, Pr(Y>j)=Λ(η_j)
        lam = G * (1.0 - G)  # λ_j
        lamp = lam * (1.0 - 2.0 * G)  # λ'_j
        Gpad = np.hstack([np.ones((self.N, 1)), G, np.zeros((self.N, 1))])
        p = (
            Gpad[np.arange(self.N), self.y - 1]
            - Gpad[np.arange(self.N), self.y]
        )
        p = np.clip(p, 1e-12, 1.0)
        # Tenseur W (N x m x m) : ∂²logp/∂η_j∂η_k
        W = np.zeros((self.N, m, m))
        c = self.y  # classe (1..J)
        # a = seuil c-1 (col c-2), b = seuil c (col c-1)
        has_a = c >= 2
        has_b = c <= m
        ia = c - 2  # index colonne de η_{c-1}
        ib = c - 1  # index colonne de η_c
        rows = np.arange(self.N)
        # ∂²/∂a² = λ'_a/p - λ_a²/p²
        ra = rows[has_a]
        ja = ia[has_a]
        la = lam[ra, ja]
        lpa = lamp[ra, ja]
        pa = p[has_a]
        W[ra, ja, ja] += lpa / pa - la**2 / pa**2
        # ∂²/∂b² = -λ'_b/p - λ_b²/p²
        rb = rows[has_b]
        jb = ib[has_b]
        lb = lam[rb, jb]
        lpb = lamp[rb, jb]
        pb = p[has_b]
        W[rb, jb, jb] += -lpb / pb - lb**2 / pb**2
        # ∂²/∂a∂b = λ_a λ_b / p²  (obs de classe intérieure : a et b existent)
        both = has_a & has_b
        rboth = rows[both]
        jaa = ia[both]
        jbb = ib[both]
        lab = lam[rboth, jaa] * lam[rboth, jbb] / p[both] ** 2
        W[rboth, jaa, jbb] += lab
        W[rboth, jbb, jaa] += lab
        # ---- Assemblage des blocs (Hessienne de logp) ----
        na, ng = self.n_alpha, self.n_gamma
        H = np.zeros((self.nparam, self.nparam))
        Xnp, Xpl = self.Xnp, self.Xpl
        wrow = W.sum(axis=2)  # N x m : Σ_k W[:,j,k]
        wtot = wrow.sum(axis=1)  # N
        # (α,α)
        H[:na, :na] = W.sum(axis=0)
        # (α,β) et (β,β)
        H[:na, na + ng :] = wrow.T @ Xpl  # m x Kpl
        H[na + ng :, :na] = H[:na, na + ng :].T
        H[na + ng :, na + ng :] = Xpl.T @ (wtot[:, None] * Xpl)
        # (α,γ), (γ,γ), (γ,β)
        for j in range(m):
            for mm in range(m):
                wjm = W[:, j, mm]
                # (α_j, γ_{k,mm})
                vec = Xnp.T @ wjm  # Knp
                cols = na + np.arange(self.Knp) * m + mm
                H[j, cols] += vec
                # (γ_{k,j}, γ_{k',mm})
                M = Xnp.T @ (wjm[:, None] * Xnp)  # Knp x Knp
                rr = na + np.arange(self.Knp) * m + j
                cc = na + np.arange(self.Knp) * m + mm
                H[np.ix_(rr, cc)] += M
            # (α_j, β) déjà fait via wrow ; (γ_{k,j}, β_{k'})
            Mgb = Xnp.T @ (wrow[:, j][:, None] * Xpl)  # Knp x Kpl
            rr = na + np.arange(self.Knp) * m + j
            H[np.ix_(rr, np.arange(na + ng, self.nparam))] += Mgb
        # symétriser (α,γ) : compléter la partie basse
        H[na : na + ng, :na] = H[:na, na : na + ng].T
        H[na + ng :, na : na + ng] = H[na : na + ng, na + ng :].T
        return -H  # Hessienne de la nll

    def fit(
        self, clusters=None, maxiter=100, theta0=None, verbose=False, tol=1e-9
    ):
        if theta0 is None:
            freq = np.bincount(self.y, minlength=self.J + 1)[1:] / self.N
            cum = np.cumsum(freq)[:-1]
            alpha0 = np.log((1 - cum) / cum)  # α_j = logit(Pr(Y>j))
            theta0 = np.concatenate(
                [alpha0, np.zeros(self.n_gamma), np.zeros(self.n_beta)]
            )
        # Newton amorti (Levenberg-Marquardt) avec gradient + Hessienne
        # ANALYTIQUES : robuste aux quasi-séparations (classe C5 rare), rapide.
        theta, H_, nit = _lm_newton(
            self.negloglik,
            self._grad,
            self._hessian,
            theta0,
            maxiter=maxiter,
            tol=1e-6,
            verbose=verbose,
        )
        self.theta = theta
        self.loglik = -self.negloglik(theta)
        self.nit = nit
        self.res = type("R", (), {"nit": nit, "x": theta})()
        H = self._hessian(theta)  # Hessienne (somme) à l'optimum
        self.hess_inv = np.linalg.inv(H)
        S = self.scores(self.theta)
        self.vcov_oim = self.hess_inv
        if clusters is not None:
            self.vcov = cluster_robust_vcov(S, self.hess_inv, clusters)
        else:
            self.vcov = self.hess_inv
        self.se = np.sqrt(np.diag(self.vcov))
        self.se_oim = np.sqrt(np.diag(self.vcov_oim))
        self._build_names()
        return self

    def _numhess(self, theta, eps=1e-5):
        n = len(theta)
        H = np.zeros((n, n))
        g0 = self._grad(theta)
        for i in range(n):
            tp = theta.copy()
            tp[i] += eps
            H[:, i] = (self._grad(tp) - g0) / eps
        return 0.5 * (H + H.T)

    def _build_names(self):
        names = [f"alpha_{j}" for j in range(1, self.ncut + 1)]
        for k in range(self.Knp):
            for j in range(1, self.ncut + 1):
                names.append(f"{self.names_np[k]}::C{j}")
        names += [f"{v}::PL" for v in self.names_pl]
        self.names = names

    # ---- accès structuré aux coefficients ----
    def coef_by_threshold(self):
        """dict: var -> coefficients par seuil (γ pour libérées,
        β répété pour contraintes)."""
        alpha = self.theta[: self.n_alpha]
        gamma = self.theta[self.n_alpha : self.n_alpha + self.n_gamma].reshape(
            self.Knp, self.ncut
        )
        beta = self.theta[self.n_alpha + self.n_gamma :]
        out = {"_alpha": alpha}
        for k, v in enumerate(self.names_np):
            out[v] = gamma[k]
        for k, v in enumerate(self.names_pl):
            out[v] = np.repeat(beta[k], self.ncut)
        return out

    def se_by_threshold(self):
        se = self.se
        out = {"_alpha": se[: self.n_alpha]}
        p = self.n_alpha
        for k, v in enumerate(self.names_np):
            out[v] = se[p : p + self.ncut]
            p += self.ncut
        for k, v in enumerate(self.names_pl):
            out[v] = np.repeat(se[p], self.ncut)
            p += 1
        return out

    def summary_frame(self):
        import pandas as pd

        z = self.theta / self.se
        pval = 2 * (1 - stats.norm.cdf(np.abs(z)))
        return pd.DataFrame(
            {
                "param": self.names,
                "coef": self.theta,
                "se": self.se,
                "se_oim": self.se_oim,
                "z": z,
                "p": pval,
            }
        )

    # ---- probabilités prédites (N x J) ----
    def predict_proba(self, Xnp=None, Xpl=None, theta=None):
        theta = self.theta if theta is None else theta
        alpha = theta[: self.n_alpha]
        gamma = theta[self.n_alpha : self.n_alpha + self.n_gamma].reshape(
            self.Knp, self.ncut
        )
        beta = theta[self.n_alpha + self.n_gamma :]
        Xnp = self.Xnp if Xnp is None else np.asarray(Xnp, float)
        Xpl = self.Xpl if Xpl is None else np.asarray(Xpl, float)
        n = Xnp.shape[0]
        eta = alpha[None, :] + Xnp @ gamma + (Xpl @ beta)[:, None]
        G = _sigmoid(eta)
        Gpad = np.hstack([np.ones((n, 1)), G, np.zeros((n, 1))])
        P = Gpad[:, :-1] - Gpad[:, 1:]  # n x J  (Pr(Y=1..J))
        return np.clip(P, 0, 1)


def brant_test(y, X, xnames, clusters=None):
    """Test de Brant par régressions logistiques binaires cumulées.
    Pour chaque seuil j : d_j = 1[Y>j] ; on ajuste un logit d_j ~ X.
    H0 : β_1 = ... = β_{J-1} (droites parallèles) pour chaque régresseur.
    Renvoie le chi2 global, ddl, p, et le détail par variable (test de Wald
    sur l'égalité des coefficients entre seuils, méthode de Brant 1990)."""
    import statsmodels.api as sm

    y = np.asarray(y, int)
    X = np.asarray(X, float)
    N, K = X.shape
    J = int(y.max())
    m = J - 1
    Xc = sm.add_constant(X, has_constant="add")
    betas, Vs, pis = [], [], []
    for j in range(1, m + 1):
        dj = (y > j).astype(int)
        res = sm.Logit(dj, Xc).fit(disp=0, maxiter=100)
        b = res.params[1:]  # sans constante
        V = res.cov_params()[1:, 1:]
        betas.append(np.asarray(b))
        Vs.append(np.asarray(V))
        pis.append(res.predict(Xc))
    betas = np.array(betas)  # m x K
    # matrice de covariance conjointe des m estimations (Brant)
    # Var(beta_j)=Vs[j]; Cov(beta_j,beta_l) via formule Brant utilisant les pi
    # Construit la covariance du vecteur empilé (m*K)
    Wjl = {}
    for j in range(m):
        for l_ in range(m):
            pj = pis[j]
            if j == l_:
                w = pj * (1 - pj)
            else:
                jj, ll = min(j, l_), max(j, l_)
                w = pis[ll] - pis[jj] * pis[ll]  # Brant: π_max - π_min*π_max
            W = (Xc.T * w) @ Xc
            Wjl[(j, l_)] = W

    # cov(beta_j, beta_l) = (Xc'W_jj Xc)^-1 (Xc'W_jl Xc) (Xc'W_ll Xc)^-1,
    # sans constante
    def inv(j):
        return np.linalg.inv(Wjl[(j, j)])

    bigcov = np.zeros((m * K, m * K))
    for j in range(m):
        for l_ in range(m):
            full = inv(j) @ Wjl[(j, l_)] @ inv(l_)
            block = full[1:, 1:]
            bigcov[j * K : (j + 1) * K, l_ * K : (l_ + 1) * K] = block
    # Contrast D : (m-1)*K contraintes β_j - β_{j+1} = 0
    beta_stack = betas.reshape(-1)  # m*K
    D = np.zeros(((m - 1) * K, m * K))
    r = 0
    for j in range(m - 1):
        for k in range(K):
            D[r, j * K + k] = 1.0
            D[r, (j + 1) * K + k] = -1.0
            r += 1
    Db = D @ beta_stack
    DVD = D @ bigcov @ D.T
    chi2 = float(Db.T @ np.linalg.pinv(DVD) @ Db)
    dfree = (m - 1) * K
    pval = 1 - stats.chi2.cdf(chi2, dfree)
    # détail par variable : contraste sur les m coefficients d'une
    # même variable
    detail = []
    for k in range(K):
        Dk = np.zeros((m - 1, m * K))
        for j in range(m - 1):
            Dk[j, j * K + k] = 1.0
            Dk[j, (j + 1) * K + k] = -1.0
        dbk = Dk @ beta_stack
        vdk = Dk @ bigcov @ Dk.T
        c2 = float(dbk.T @ np.linalg.pinv(vdk) @ dbk)
        detail.append((xnames[k], c2, m - 1, 1 - stats.chi2.cdf(c2, m - 1)))
    return {
        "chi2": chi2,
        "df": dfree,
        "p": pval,
        "detail": detail,
        "betas": betas,
        "xnames": xnames,
    }


# %% [markdown]
# ## 1. Chargement et contrôles qualité
#
# Objectif : charger la base d'analyse et vérifier qu'elle correspond bien
# à celle du mémoire avant toute estimation (effectifs, bornes, identifiants).
#
# Pourquoi des ``assert`` explicites : une base mal chargée ou modifiée
# donnerait des résultats plausibles mais faux. Les contrôles échouent
# bruyamment plutôt que de laisser passer une erreur silencieuse.
#
# Les bases brutes RGE (personnes physiques et personnes morales) ne sont
# pas publiées. Leur fusion et la construction de la base d'analyse ont été
# réalisées en amont (voir README). Le script part de
# cette base d'analyse, à placer dans data/ (ou à indiquer via PME_DATA).

# %%


def localiser_base():
    """Trouve le fichier de la base d'analyse (variable PME_DATA, argument
    de la ligne de commande ou data/base_analyse.*)."""
    candidats = []
    if os.environ.get("PME_DATA"):
        candidats.append(Path(os.environ["PME_DATA"]))
    candidats += [
        Path(arg)
        for arg in sys.argv[1:]
        if Path(arg).suffix.lower() in EXTENSIONS_ACCEPTEES
    ]
    candidats += sorted(DOSSIER_DONNEES.glob("base_analyse.*"))
    for chemin in candidats:
        if chemin.exists():
            return chemin
    raise FileNotFoundError(
        "Base d'analyse introuvable. Placez data/base_analyse.(dta|csv|"
        "parquet|pkl) ou définissez la variable d'environnement PME_DATA."
    )


def lire_base(chemin):
    """Lit la base d'analyse selon son extension."""
    extension = chemin.suffix.lower()
    if extension == ".dta":
        return pd.read_stata(chemin, convert_categoricals=False)
    if extension == ".csv":
        return pd.read_csv(chemin)
    if extension == ".parquet":
        return pd.read_parquet(chemin)
    return pd.read_pickle(chemin)


def controles_base(base):
    """Contrôles qualité sur la base complète des unités actives."""
    print("Contrôles qualité de la base d'analyse :")
    manquantes = [c for c in COLONNES_REQUISES if c not in base.columns]
    controle(not manquantes, f"colonnes requises présentes {manquantes}")
    if "ID" in base.columns:
        controle(base["ID"].is_unique, "identifiants uniques")
    else:
        print("  [info] pas de colonne ID : unicité non vérifiable")
    controle(
        len(base) == N_UNITES_ACTIVES,
        f"{len(base):,} unités actives (attendu {N_UNITES_ACTIVES:,})",
    )
    controle(
        set(base[VAR_DEP].dropna().unique()) <= {1, 2, 3, 4, 5},
        "classes de chiffre d'affaires dans {1,...,5}",
    )
    for var in [
        "formel",
        "banque_obt",
        "fin_informel",
        "femme",
        "compta",
        "reseau",
        "urbain",
        "pers_morale",
    ]:
        controle(set(base[var].dropna().unique()) <= {0, 1}, f"{var} binaire")
    controle(
        base["age"].dropna().between(0, 120).all(),
        "âge compris entre 0 et 120 ans",
    )
    controle(
        base["contraintes_rb"].dropna().between(0, 1).all(),
        "taux de contraintes compris entre 0 et 1",
    )
    controle(
        base["region"].dropna().between(1, 14).all()
        and base["branche"].dropna().between(1, 10).all(),
        "région dans 1-14 et branche dans 1-10",
    )


chemin_base = localiser_base()
print(f"Lecture de {chemin_base.name}")
base = lire_base(chemin_base)
controles_base(base)

manquants = base[COLONNES_REQUISES].isna().sum().rename("manquants").to_frame()
manquants["part_%"] = (100 * manquants["manquants"] / len(base)).round(2)
exporter_tableau(manquants, "D0_valeurs_manquantes", index=True)
print(manquants)


# %% [markdown]
# ## 2. Construction des variables
#
# Objectif : reconstruire toutes les variables dérivées du modèle (carré de
# l'âge, indicatrices de région, de branche, d'instruction, interactions
# femme x branche) et construire l'échantillon d'estimation.
#
# Pourquoi : si la base fournit déjà ces colonnes, on vérifie qu'elles
# coïncident avec la recomposition ; sinon on les crée. Les modalités
# manquantes de région, de branche et d'instruction restent codées 0 sur
# toutes les indicatrices, c'est-à-dire rattachées à la modalité de
# référence (Dakar, Commerce, aucune instruction), comme dans l'estimation
# du mémoire.
#
# Échantillon d'estimation : cas complets sur la variable dépendante et sur
# l'ensemble des régresseurs (406 408 -> 317 627 -> 292 589 unités).

# %%


def ajouter_ou_verifier(df, nom, valeurs):
    """Ajoute la colonne ``nom`` ou, si elle existe, vérifie qu'elle
    coïncide avec la recomposition (tolérance numérique)."""
    valeurs = pd.Series(valeurs, index=df.index)
    if nom in df.columns:
        existant = df[nom].astype(float)
        ecart = (existant - valeurs.astype(float)).abs().max(skipna=True)
        memes_nan = (existant.isna() == valeurs.isna()).all()
        controle(
            bool(memes_nan) and (pd.isna(ecart) or ecart < 1e-4),
            f"{nom} conforme à la recomposition",
        )
    else:
        df[nom] = valeurs


def construire_variables(base_brute):
    """Variables dérivées du modèle (voir cellule d'introduction)."""
    d = base_brute.copy()
    ajouter_ou_verifier(d, "age2", d["age"] ** 2 / 100)
    for k in range(2, 15):
        ajouter_ou_verifier(d, f"reg_{k}", (d["region"] == k).astype("int8"))
    for k in (1, 2, 3, 4, 5, 7, 8, 9, 10):
        ajouter_ou_verifier(d, f"br_{k}", (d["branche"] == k).astype("int8"))
        ajouter_ou_verifier(
            d, f"femme_br_{k}", d["femme"] * (d["branche"] == k)
        )
    for k in (2, 3, 4):
        ajouter_ou_verifier(d, f"educ{k}", (d["educ"] == k).astype("int8"))
    if GRAPPES not in d.columns:
        d[GRAPPES] = (
            d.groupby(["region", "branche"]).ngroup().replace(-1, np.nan)
        )
    return d


print("Construction des variables :")
base = construire_variables(base)

masque = base[[VAR_DEP] + X_TOUS].notna().all(axis=1)
d = base.loc[masque].reset_index(drop=True).copy()
y = d[VAR_DEP].astype(int).to_numpy()
grappes = d[GRAPPES].to_numpy()

print("Échantillon d'estimation (cas complets) :")
n_avec_y = int(base[VAR_DEP].notna().sum())
controle(n_avec_y == 317_627, f"{n_avec_y:,} unités avec classe de CA")
controle(len(d) == N_ECHANTILLON, f"{len(d):,} unités d'estimation")
controle(
    np.bincount(y, minlength=6)[1:].tolist() == DISTRIBUTION_Y,
    "distribution de la variable dépendante conforme au mémoire",
)
controle(
    len(np.unique(grappes[~pd.isna(grappes)])) == N_GRAPPES,
    f"{N_GRAPPES} grappes région x branche",
)
n_sans_grappe = int(pd.isna(grappes).sum())
print(
    f"  [info] unités sans grappe (région ou branche manquante) : "
    f"{n_sans_grappe}"
)


# %% [markdown]
# ## 3. Statistiques descriptives
#
# Objectif : décrire l'échantillon d'estimation (chapitre 3 du mémoire),
# puis croiser chaque caractéristique avec le niveau d'activité.
#
# Pourquoi le même échantillon que l'estimation : chaque tableau totalise
# exactement 292 589 unités, de sorte que la description prépare directement
# le modèle. Les associations sont mesurées par le Khi-deux, le V de Cramér
# (qui guide l'interprétation, car le Khi-deux est significatif presque
# partout à cette taille d'échantillon) et le rho de Spearman pour les
# variables binaires ou ordonnées. Ce sont des associations brutes.

# %%
LIBELLES_SEXE = {0: "Homme", 1: "Femme"}
LIBELLES_INSTRUCTION = {
    1: "Aucune instruction / alphabétisé",
    2: "Primaire",
    3: "Moyen / secondaire",
    4: "Supérieur",
}
LIBELLES_OUI_NON = {1: "Oui", 0: "Non"}

# Modalités manquantes rattachées à la modalité de référence du modèle.
d["region_m"] = d["region"].fillna(1).astype(int)
d["branche_m"] = d["branche"].fillna(6).astype(int)
d["educ_m"] = d["educ"].fillna(1).astype(int)


def tableau_univarie(serie, libelles, nom, trier=False):
    """Effectifs et pourcentages d'une variable, avec ligne de total."""
    effectifs = serie.value_counts().reindex(list(libelles)).fillna(0)
    effectifs = effectifs.astype(int)
    if trier:
        effectifs = effectifs.sort_values(ascending=False)
    controle(
        int(effectifs.sum()) == len(d),
        f"{nom} : total = {len(d):,} unités",
    )
    tableau = pd.DataFrame(
        {
            "Modalité": [libelles[k] for k in effectifs.index],
            "Effectif": effectifs.to_numpy(),
            "%": (100 * effectifs / effectifs.sum()).round(1).to_numpy(),
        }
    )
    tableau.loc[len(tableau)] = ["Ensemble", int(effectifs.sum()), 100.0]
    return tableau


def association(x, y_cls):
    """Khi-deux, V de Cramér et rho de Spearman entre x et la classe."""
    croisement = pd.crosstab(x, y_cls)
    chi2, p, _, _ = stats.chi2_contingency(croisement)
    n = croisement.to_numpy().sum()
    dim = min(croisement.shape) - 1
    rho, _ = stats.spearmanr(x, y_cls)
    return {
        "khi2": chi2,
        "p": p,
        "V_Cramer": np.sqrt(chi2 / (n * dim)),
        "rho_Spearman": rho,
    }


def tableau_bivarie(variable, libelles, nom):
    """Pourcentages en ligne du niveau d'activité par modalité."""
    croisement = pd.crosstab(d[variable], d[VAR_DEP])
    croisement = croisement.reindex(list(libelles))
    pct = 100 * croisement.div(croisement.sum(axis=1), axis=0)
    pct.columns = [CLASSES[c] for c in pct.columns]
    tableau = pct.round(1)
    tableau.insert(0, "Effectif", croisement.sum(axis=1).astype(int))
    tableau.index = [libelles[k] for k in tableau.index]
    ensemble = d[VAR_DEP].value_counts(normalize=True).sort_index() * 100
    tableau.loc["Ensemble"] = [len(d)] + ensemble.round(1).tolist()
    controle(
        int(croisement.to_numpy().sum()) == len(d),
        f"{nom} : croisement sur {len(d):,} unités",
    )
    return tableau


# --- 3.1 Profil univarié ---------------------------------------------------
vc = d[VAR_DEP].value_counts().sort_index()
distribution = pd.DataFrame(
    {
        "Classe": [CLASSES[c] for c in vc.index],
        "Effectif": vc.to_numpy(),
        "%": (100 * vc / len(d)).round(2).to_numpy(),
    }
)
distribution["% cumulé"] = distribution["%"].cumsum().round(2)
exporter_tableau(distribution, "D1_distribution_niveau_activite")

univaries = {
    "T3_01_categorie_juridique": tableau_univarie(
        d["pers_morale"],
        {0: "Personne physique", 1: "Personne morale"},
        "catégorie juridique",
    ),
    "T3_03a_sexe_dirigeant": tableau_univarie(
        d["femme"].astype(int), LIBELLES_SEXE, "sexe du dirigeant"
    ),
    "T3_03b_instruction": tableau_univarie(
        d["educ_m"], LIBELLES_INSTRUCTION, "niveau d'instruction"
    ),
    "T3_04_region": tableau_univarie(
        d["region_m"], NOMS_REGIONS, "région", trier=True
    ),
    "T3_05_branche": tableau_univarie(
        d["branche_m"], NOMS_BRANCHES, "branche d'activité", trier=True
    ),
    "T3_06_formalisation": tableau_univarie(
        d["formel"], {0: "Informelle", 1: "Formelle"}, "formalisation"
    ),
    "T3_07a_financement_bancaire": tableau_univarie(
        d["banque_obt"], LIBELLES_OUI_NON, "financement bancaire"
    ),
    "T3_07b_financement_informel": tableau_univarie(
        d["fin_informel"], LIBELLES_OUI_NON, "financement informel"
    ),
    "T3_16a_comptabilite": tableau_univarie(
        d["compta"].astype(int), LIBELLES_OUI_NON, "comptabilité écrite"
    ),
    "T3_16b_reseau": tableau_univarie(
        d["reseau"].astype(int), LIBELLES_OUI_NON, "réseau professionnel"
    ),
    "T3_17_milieu": tableau_univarie(
        d["urbain"], {1: "Urbain", 0: "Rural"}, "milieu"
    ),
}
for nom_tableau, tableau in univaries.items():
    exporter_tableau(tableau, nom_tableau)

resume_age = d["age"].describe(percentiles=[0.25, 0.5, 0.75]).to_frame("age")
exporter_tableau(resume_age, "T3_08_age_resume", index=True)
print(distribution.to_string(index=False))
print(
    f"Âge : moyenne {d['age'].mean():.1f}, médiane {d['age'].median():.0f}"
    f", maximum {d['age'].max():.0f}"
)

# --- 3.2 Analyse bivariée --------------------------------------------------
variables_croisees = {
    "formel": ("Formalisation", {0: "Informelle", 1: "Formelle"}),
    "femme": ("Sexe du dirigeant", LIBELLES_SEXE),
    "banque_obt": ("Financement bancaire", LIBELLES_OUI_NON),
    "fin_informel": ("Financement informel", LIBELLES_OUI_NON),
    "branche_m": ("Branche d'activité", NOMS_BRANCHES),
    "urbain": ("Milieu urbain", {1: "Urbain", 0: "Rural"}),
    "educ_m": ("Niveau d'instruction", LIBELLES_INSTRUCTION),
    "compta": ("Comptabilité écrite", LIBELLES_OUI_NON),
    "reseau": ("Réseau professionnel", LIBELLES_OUI_NON),
}
lignes_assoc = []
for variable, (intitule, libelles) in variables_croisees.items():
    d[f"_{variable}"] = d[variable].astype(int)
    tab = tableau_bivarie(f"_{variable}", libelles, intitule)
    exporter_tableau(tab, f"T3_biv_{variable}_niveau_activite", index=True)
    stat = association(d[f"_{variable}"], d[VAR_DEP])
    stat["Variable"] = intitule
    lignes_assoc.append(stat)
stat_age = stats.spearmanr(d["age"], d[VAR_DEP])
lignes_assoc.append(
    {
        "Variable": "Âge (variable continue)",
        "khi2": np.nan,
        "p": stat_age[1],
        "V_Cramer": np.nan,
        "rho_Spearman": stat_age[0],
    }
)
associations = pd.DataFrame(lignes_assoc)[
    ["Variable", "khi2", "p", "V_Cramer", "rho_Spearman"]
]
exporter_tableau(associations, "T3_associations_bivariees")
print(associations.to_string(index=False))

age_par_classe = d.groupby(VAR_DEP)["age"].agg(["mean", "median", "count"])
age_par_classe.index = [CLASSES[c] for c in age_par_classe.index]
exporter_tableau(age_par_classe, "T3_biv_age_niveau_activite", index=True)

# --- 3.3 Diagnostics préliminaires de l'estimation -------------------------
# Non-réponse sur la variable dépendante (base des unités actives).
base["y_manquant"] = base[VAR_DEP].isna().astype(int)
non_reponse = (
    base.groupby("formel")["y_manquant"].agg(["mean", "size"]).reset_index()
)
non_reponse.columns = ["Formelle", "Taux de non-réponse", "N"]
non_reponse["Taux de non-réponse"] = (
    100 * non_reponse["Taux de non-réponse"]
).round(2)
exporter_tableau(non_reponse, "D2_non_reponse_niveau_activite")

# Unités incluses et exclues de l'estimation (sélection sur observables).
base["dans_echantillon"] = masque.astype(int)
selection = pd.DataFrame(
    [
        (etiquette(v), base.loc[masque, v].mean(), base.loc[~masque, v].mean())
        for v in [
            "formel",
            "femme",
            "urbain",
            "pers_morale",
            "age",
            "compta",
            "banque_obt",
        ]
    ],
    columns=["Variable", "Incluses", "Exclues"],
)
selection["Écart"] = selection["Incluses"] - selection["Exclues"]
exporter_tableau(selection.round(3), "D3_selection_observables")

# Statistiques descriptives des régresseurs.
variables_desc = HYPOTHESES + BLOC_SUBSTANTIEL + ["pers_morale"]
descriptives = pd.DataFrame(
    {
        "Variable": [etiquette(v) for v in variables_desc],
        "Moyenne": [d[v].astype(float).mean() for v in variables_desc],
        "Écart-type": [d[v].astype(float).std() for v in variables_desc],
        "Min": [d[v].astype(float).min() for v in variables_desc],
        "Max": [d[v].astype(float).max() for v in variables_desc],
    }
).round(3)
exporter_tableau(descriptives, "D4_descriptives_regresseurs")

# Corrélations et facteurs d'inflation de la variance (VIF).
corr_vars = [
    "formel",
    "banque_obt",
    "fin_informel",
    "femme",
    "age",
    "educ",
    "compta",
    "reseau",
    "urbain",
    "pers_morale",
    "contraintes_rb",
]
exporter_tableau(
    d[corr_vars].astype(float).corr().round(2), "D6_correlations", index=True
)
# VIF_i = i-ème terme diagonal de l'inverse de la matrice de corrélation.
inverse_corr = np.linalg.pinv(
    np.corrcoef(d[X_TOUS].astype(float).to_numpy(), rowvar=False)
)
vif = pd.DataFrame(
    {
        "Variable": [etiquette(v) for v in X_TOUS],
        "VIF": np.diag(inverse_corr).round(2),
    }
).sort_values("VIF", ascending=False)
exporter_tableau(vif, "D7_vif")
print(vif.head(5).to_string(index=False))

# Séparation : formalité x classe, et femmes par branche.
separation = pd.crosstab(d["formel"], d[VAR_DEP])
separation.index = ["Informelle", "Formelle"]
separation.columns = [CLASSES[c] for c in separation.columns]
exporter_tableau(separation, "D8_separation_formalite_classe", index=True)
femmes_branche = d.groupby("branche_m")["femme"].agg(["sum", "size"])
femmes_branche.columns = ["Femmes", "Total"]
femmes_branche = femmes_branche.astype(int)
femmes_branche.index = [NOMS_BRANCHES[k] for k in femmes_branche.index]
exporter_tableau(femmes_branche, "D9_femmes_par_branche", index=True)

# --- 3.4 Graphiques descriptifs --------------------------------------------
fig, axe = plt.subplots(figsize=(7.5, 4.2))
ages = d["age"].to_numpy()
axe.hist(
    ages,
    bins=np.arange(0, ages.max() + 2) - 0.5,
    color=PALETTE[0],
    edgecolor="white",
    linewidth=0.3,
)
axe.axvline(
    ages.mean(),
    color=PALETTE[1],
    ls="--",
    lw=1.4,
    label=f"Moyenne : {ages.mean():.1f} ans",
)
axe.axvline(
    np.median(ages),
    color=PALETTE[2],
    ls=":",
    lw=1.6,
    label=f"Médiane : {np.median(ages):.0f} ans",
)
axe.set_xlabel("Âge de l'entreprise (années, sans troncature)")
axe.set_ylabel("Nombre d'unités")
axe.legend()
enregistrer_figure(fig, "G3_1_histogramme_age")

formalisation = pd.crosstab(d["formel"], d[VAR_DEP], normalize="index") * 100
formalisation.loc["Ensemble"] = (
    d[VAR_DEP].value_counts(normalize=True).sort_index() * 100
)
formalisation.index = ["Informelle", "Formelle", "Ensemble"]
fig, axe = plt.subplots(figsize=(7.5, 3.6))
gauche = np.zeros(3)
teintes = ["#c6dbef", "#6baed6", "#3182bd", "#08519c", "#08306b"]
for classe in range(1, 6):
    valeurs = formalisation[classe].to_numpy()
    axe.barh(
        formalisation.index,
        valeurs,
        left=gauche,
        color=teintes[classe - 1],
        edgecolor="white",
        label=CLASSES[classe],
    )
    gauche += valeurs
axe.set_xlim(0, 100)
axe.invert_yaxis()
axe.set_xlabel("Répartition du niveau d'activité (%)")
axe.legend(ncol=5, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.22))
enregistrer_figure(fig, "G3_2_formalisation_niveau_activite")

# Même périmètre que le mémoire (sept variables, sans comptabilité ni réseau).
hierarchie = associations.dropna(subset=["V_Cramer"])
hierarchie = hierarchie[
    ~hierarchie["Variable"].isin(
        ["Comptabilité écrite", "Réseau professionnel"]
    )
].sort_values("V_Cramer")
fig, axe = plt.subplots(figsize=(7.5, 4.2))
axe.barh(
    hierarchie["Variable"],
    hierarchie["V_Cramer"],
    color=PALETTE[0],
    height=0.6,
)
for position, valeur in enumerate(hierarchie["V_Cramer"]):
    axe.text(
        valeur + 0.004,
        position,
        f"{valeur:.3f}".replace(".", ","),
        va="center",
        fontsize=9,
    )
axe.set_xlabel("V de Cramér (intensité de l'association brute)")
enregistrer_figure(fig, "G3_3_hierarchie_associations")


# %% [markdown]
# ## 4. Logit ordonné et test de Brant
#
# Objectif : estimer le modèle de référence (logit ordonné à cotes
# proportionnelles : un seul coefficient par variable pour les quatre
# seuils), puis tester cette hypothèse par le test de Brant.
#
# Pourquoi : la démarche suit l'ordre logit ordonné, test de Brant, puis
# modèle généralisé. Le rejet de la proportionnalité (chi2 global de
# l'ordre de 9 694, 135 degrés de liberté) justifie de relâcher la
# contrainte. Le logit ordonné est estimé avec le même moteur, toutes les
# variables étant placées dans le bloc contraint.

# %%
X_matrice = d[X_TOUS].to_numpy(dtype=float)

debut = time.time()
logit_ordonne = GenOrderedLogit(
    y, np.empty((len(d), 0)), X_matrice, [], X_TOUS
).fit(clusters=grappes)
print(
    f"[logit ordonné] {time.time() - debut:.1f} s, "
    f"log-vraisemblance = {logit_ordonne.loglik:,.1f}"
)

debut = time.time()
brant = brant_test(y, X_matrice, X_TOUS)
print(
    f"[Brant] {time.time() - debut:.1f} s, chi2 = {brant['chi2']:,.1f}, "
    f"ddl = {brant['df']}, p = {brant['p']:.3g}"
)

detail_brant = pd.DataFrame(
    brant["detail"], columns=["var", "chi2", "ddl", "p"]
)
detail_brant["Variable"] = detail_brant["var"].map(etiquette)
detail_brant["signif"] = detail_brant["p"].map(etoiles)
detail_brant = detail_brant.sort_values("chi2", ascending=False)
exporter_tableau(detail_brant, "D10_brant_detail_par_variable")
global_brant = pd.DataFrame(
    [{"chi2": brant["chi2"], "ddl": brant["df"], "p": brant["p"]}]
)
exporter_tableau(global_brant, "T4_brant_global")
print(
    detail_brant[detail_brant["var"].isin(X_LIBRES)][
        ["Variable", "chi2", "p", "signif"]
    ].to_string(index=False)
)


# %% [markdown]
# ## 5. Logit ordonné généralisé à cotes proportionnelles partielles
#
# Objectif : estimer le modèle retenu,
# Pr(Y > j | x) = L(alpha_j + X'beta_j + Z'gamma), j = 1,...,4, où les
# treize variables d'hypothèse et du bloc substantiel (X) ont un
# coefficient propre à chaque seuil, et les contrôles (Z : personne morale,
# effets fixes de région et de branche, interactions femme x branche) un
# coefficient commun.
#
# Pourquoi : le test de Brant rejette la proportionnalité. Le point de
# départ de l'optimisation est issu du logit ordonné (probabilités
# cumulées monotones par construction), ce qui évite les zones
# infaisables liées à la classe rare C5. Les erreurs-types sont agrégées
# en grappes région x branche. Le modèle entièrement généralisé n'est pas
# identifiable de façon stable (quasi-séparation) : le PPO est donc le
# modèle le moins contraint identifiable.

# %%


def theta_initial(modele_ref, libres, contraintes):
    """Point de départ du PPO : seuils et coefficients du logit ordonné."""
    coefficients = modele_ref.coef_by_threshold()
    alpha = coefficients["_alpha"]
    gamma = np.concatenate([coefficients[v][:N_SEUILS] for v in libres])
    beta = np.array([coefficients[v][0] for v in contraintes])
    return np.concatenate([alpha, gamma, beta])


def table_ppo(modele, ordre, en_rapports_de_cotes):
    """Coefficients (ou rapports de cotes) par seuil, erreurs-types
    entre parenthèses (méthode delta pour les rapports de cotes)."""
    coefs = modele.coef_by_threshold()
    ses = modele.se_by_threshold()
    lignes = []
    for variable in ordre:
        ligne_valeur = {"Variable": etiquette(variable)}
        ligne_se = {"Variable": ""}
        for j in range(modele.ncut):
            c, s = coefs[variable][j], ses[variable][j]
            z = c / s if s > 0 else 0.0
            p = 2 * (1 - stats.norm.cdf(abs(z)))
            valeur = np.exp(c) if en_rapports_de_cotes else c
            se_aff = valeur * s if en_rapports_de_cotes else s
            ligne_valeur[f"Pr(Y>{j + 1})"] = f"{valeur:.3f}{etoiles(p)}"
            ligne_se[f"Pr(Y>{j + 1})"] = f"({se_aff:.3f})"
        lignes += [ligne_valeur, ligne_se]
    alpha, se_alpha = coefs["_alpha"], ses["_alpha"]
    lignes.append(
        {
            "Variable": "Constante (alpha_j)",
            **{
                f"Pr(Y>{j + 1})": f"{alpha[j]:.3f}" for j in range(modele.ncut)
            },
        }
    )
    lignes.append(
        {
            "Variable": "",
            **{
                f"Pr(Y>{j + 1})": f"({se_alpha[j]:.3f})"
                for j in range(modele.ncut)
            },
        }
    )
    return pd.DataFrame(lignes)


X_np = d[X_LIBRES].to_numpy(dtype=float)
X_pl = d[X_CONTRAINTES].to_numpy(dtype=float)
theta0 = theta_initial(logit_ordonne, X_LIBRES, X_CONTRAINTES)

debut = time.time()
ppo = GenOrderedLogit(y, X_np, X_pl, X_LIBRES, X_CONTRAINTES).fit(
    clusters=grappes, theta0=theta0
)
print(
    f"[PPO] {time.time() - debut:.1f} s, {ppo.nit} itérations, "
    f"log-vraisemblance = {ppo.loglik:,.1f}, {ppo.nparam} paramètres"
)

# Pseudo-R2 de McFadden global (modèle nul = entropie des fréquences).
frequences = np.bincount(y, minlength=6)[1:] / ppo.N
ll_nul = ppo.N * np.sum(frequences * np.log(frequences))
mcfadden = 1 - ppo.loglik / ll_nul
print(f"Pseudo-R2 de McFadden : {mcfadden:.4f}")

ordre_affichage = HYPOTHESES + BLOC_SUBSTANTIEL + ["pers_morale"]
exporter_tableau(
    table_ppo(ppo, ordre_affichage, True), "T4_7_ppo_rapports_de_cotes"
)
exporter_tableau(table_ppo(ppo, ordre_affichage, False), "T4_ppo_coefficients")
coefs_ppo = ppo.coef_by_threshold()
effets_fixes = ppo.summary_frame()
exporter_tableau(effets_fixes, "T4_ppo_tous_parametres")

# Du logit ordonné au PPO : coefficient commun contre coefficients/seuil.
coefs_ologit = logit_ordonne.coef_by_threshold()
comparaison = pd.DataFrame(
    [
        [etiquette(v), coefs_ologit[v][0], *coefs_ppo[v]]
        for v in ordre_affichage
    ],
    columns=[
        "Variable",
        "Ordonné (commun)",
        "PPO s1",
        "PPO s2",
        "PPO s3",
        "PPO s4",
    ],
).round(3)
exporter_tableau(comparaison, "T4_comparaison_ologit_ppo")

# Emboîtement et critères d'information.
k_ologit = len(X_TOUS) + N_SEUILS
k_ppo = ppo.nparam
rapport_vrais = 2 * (ppo.loglik - logit_ordonne.loglik)
ddl_rv = k_ppo - k_ologit
p_rv = 1 - stats.chi2.cdf(rapport_vrais, ddl_rv)
criteres = pd.DataFrame(
    [
        (
            "Logit ordonné",
            k_ologit,
            logit_ordonne.loglik,
            -2 * logit_ordonne.loglik + 2 * k_ologit,
            -2 * logit_ordonne.loglik + k_ologit * np.log(ppo.N),
        ),
        (
            "PPO (retenu)",
            k_ppo,
            ppo.loglik,
            -2 * ppo.loglik + 2 * k_ppo,
            -2 * ppo.loglik + k_ppo * np.log(ppo.N),
        ),
    ],
    columns=["Modèle", "k", "logLik", "AIC", "BIC"],
).round(1)
exporter_tableau(criteres, "T4_emboitement_criteres_information")
print(criteres.to_string(index=False))
print(
    f"LR (ordonné -> PPO) = {rapport_vrais:,.1f}, ddl = {ddl_rv}, "
    f"p = {p_rv:.3g}"
)

# Pseudo-R2 de McFadden par seuil (logits binaires cumulés).
pseudo_r2 = []
X_const = sm.add_constant(d[X_TOUS].to_numpy(dtype=float))
for j in range(1, N_SEUILS + 1):
    indicatrice = (y > j).astype(int)
    complet = sm.Logit(indicatrice, X_const).fit(disp=0, maxiter=100)
    nul = sm.Logit(indicatrice, np.ones((len(y), 1))).fit(disp=0)
    pseudo_r2.append((j, indicatrice.mean(), 1 - complet.llf / nul.llf))
pseudo_r2 = pd.DataFrame(pseudo_r2, columns=["seuil", "part", "pseudoR2"])
exporter_tableau(pseudo_r2.round(3), "T4_pseudo_R2_par_seuil")
print(pseudo_r2.round(3).to_string(index=False))


# %% [markdown]
# ## 6. Robustesse
#
# Objectif : vérifier que les conclusions ne dépendent ni du lien, ni de
# la mesure, ni de l'échantillon.
#
# Pourquoi chaque volet :
# - régression par intervalles sur le logarithme du chiffre d'affaires : elle
#   exploite les bornes monétaires connues des classes (1, 5, 15 et 200
#   millions de FCFA) et donne des semi-élasticités ;
# - probit ordonné : même modèle avec un lien normal au lieu de logistique ;
# - sous-échantillons (hors Dakar, hors C5, unités formelles seules) : les
#   signes et ordres de grandeur doivent rester stables ;
# - validation hors échantillon (70/30) : un modèle explicatif doit
#   tout de même avoir un pouvoir prédictif non nul, évalué classe par
#   classe et comparé à la règle majoritaire.

# %%
PHI, PHI_DENSITE = stats.norm.cdf, stats.norm.pdf


def standardiser(X):
    """Régresseurs centrés-réduits (bon conditionnement de l'optimisation)."""
    moyenne, ecart = X.mean(0), X.std(0)
    ecart[ecart == 0] = 1.0
    return (X - moyenne) / ecart, moyenne, ecart


def regression_par_intervalles(X, y_cls, grappes_):
    """Régression par intervalles sur log(CA). Renvoie (coefficients à
    l'échelle d'origine, erreurs-types en grappes, sigma)."""
    n = len(y_cls)
    Xs, moyenne, ecart = standardiser(X)
    Xc = np.hstack([np.ones((n, 1)), Xs])
    borne_inf = np.full(n, -np.inf)
    borne_sup = np.full(n, np.inf)
    for classe, (bas, haut) in BORNES_CLASSES.items():
        sel = y_cls == classe
        borne_inf[sel] = np.log(bas) if bas else -np.inf
        borne_sup[sel] = np.log(haut) if haut else np.inf

    def composantes(theta):
        beta, s = theta[:-1], np.exp(theta[-1])
        xb = Xc @ beta
        a, b = (borne_inf - xb) / s, (borne_sup - xb) / s
        Fa = np.where(np.isneginf(a), 0.0, PHI(a))
        Fb = np.where(np.isposinf(b), 1.0, PHI(b))
        p = np.clip(Fb - Fa, 1e-300, 1.0)
        fa = np.where(np.isfinite(a), PHI_DENSITE(a), 0.0)
        fb = np.where(np.isfinite(b), PHI_DENSITE(b), 0.0)
        aa, bb = (
            np.where(np.isfinite(a), a, 0.0),
            np.where(np.isfinite(b), b, 0.0),
        )
        return s, p, fa, fb, aa, bb

    def fonction_gradient(theta):
        s, p, fa, fb, aa, bb = composantes(theta)
        g_beta = ((-(fb - fa) / s / p)[:, None] * Xc).sum(0)
        g_lns = np.sum(-(bb * fb - aa * fa) / p)
        return (-np.sum(np.log(p)) / n, -np.concatenate([g_beta, [g_lns]]) / n)

    def scores(theta):
        s, p, fa, fb, aa, bb = composantes(theta)
        s_beta = (-(fb - fa) / s / p)[:, None] * Xc
        s_lns = (-(bb * fb - aa * fa) / p)[:, None]
        return np.hstack([s_beta, s_lns])

    milieu = np.where(
        np.isfinite(borne_inf) & np.isfinite(borne_sup),
        (borne_inf + borne_sup) / 2,
        np.where(np.isfinite(borne_sup), borne_sup - 1, borne_inf + 1),
    )
    b0 = np.linalg.lstsq(Xc, milieu, rcond=None)[0]
    theta0_ = np.concatenate([b0, [np.log(np.std(milieu - Xc @ b0))]])
    res = minimize(
        fonction_gradient,
        theta0_,
        jac=True,
        method="BFGS",
        options={"maxiter": 500, "gtol": 1e-7},
    )
    sigma = np.exp(res.x[-1])
    beta_s = res.x[:-1]
    beta = beta_s.copy()
    beta[1:] = beta_s[1:] / ecart
    beta[0] = beta_s[0] - np.sum(beta_s[1:] * moyenne / ecart)
    # Hessienne numérique du critère, puis sandwich en grappes.
    g0 = fonction_gradient(res.x)[1] * n
    hess = np.zeros((len(res.x),) * 2)
    for i in range(len(res.x)):
        tp = res.x.copy()
        tp[i] += 1e-5
        hess[:, i] = (fonction_gradient(tp)[1] * n - g0) / 1e-5
    hess = 0.5 * (hess + hess.T)
    vcov = cluster_robust_vcov(scores(res.x), np.linalg.inv(hess), grappes_)
    se_s = np.sqrt(np.diag(vcov))
    se = se_s[: X.shape[1] + 1].copy()
    se[1:] = se_s[1 : X.shape[1] + 1] / ecart
    return beta, se, sigma


def probit_ordonne(X, y_cls):
    """Probit ordonné à cotes proportionnelles (lien normal). Renvoie les
    coefficients à l'échelle d'origine et la log-vraisemblance."""
    n = len(y_cls)
    Xs, _, ecart = standardiser(X)
    n_classes = int(y_cls.max())
    n_seuils = n_classes - 1

    def fonction_gradient(theta):
        beta, kappa = theta[: Xs.shape[1]], theta[Xs.shape[1] :]
        xb = Xs @ beta
        z = np.concatenate([[-np.inf], kappa, [np.inf]])
        Z = z[None, :] - xb[:, None]
        F = np.where(
            np.isneginf(Z), 0.0, np.where(np.isposinf(Z), 1.0, PHI(Z))
        )
        rang = np.arange(n)
        p = np.clip(F[rang, y_cls] - F[rang, y_cls - 1], 1e-300, 1.0)
        ph = np.where(np.isfinite(Z), PHI_DENSITE(Z), 0.0)
        dpi = ph[rang, y_cls] - ph[rang, y_cls - 1]
        g_beta = (-(dpi / p)[:, None] * Xs).sum(0)
        g_kappa = np.zeros(n_seuils)
        for m in range(1, n_seuils + 1):
            ajout = np.where(y_cls == m, ph[:, m] / p, 0.0)
            ajout -= np.where(y_cls - 1 == m, ph[:, m] / p, 0.0)
            g_kappa[m - 1] = ajout.sum()
        return (-np.sum(np.log(p)) / n, -np.concatenate([g_beta, g_kappa]) / n)

    freq = np.bincount(y_cls, minlength=n_classes + 1)[1:] / n
    kappa0 = stats.norm.ppf(np.cumsum(freq)[:-1])
    res = minimize(
        fonction_gradient,
        np.concatenate([np.zeros(Xs.shape[1]), kappa0]),
        jac=True,
        method="BFGS",
        options={"maxiter": 500, "gtol": 1e-7},
    )
    return res.x[: Xs.shape[1]] / ecart, -fonction_gradient(res.x)[0] * n


# --- 6.1 Régression par intervalles et probit ordonné ----------------------
debut = time.time()
beta_int, se_int, sigma_int = regression_par_intervalles(X_matrice, y, grappes)
noms_int = ["const"] + X_TOUS
print(f"[intervalles] {time.time() - debut:.1f} s, sigma = {sigma_int:.4f}")
debut = time.time()
beta_probit, ll_probit = probit_ordonne(X_matrice, y)
print(
    f"[probit ordonné] {time.time() - debut:.1f} s, "
    f"log-vraisemblance = {ll_probit:,.1f}"
)

variables_cles = [
    "formel",
    "banque_obt",
    "fin_informel",
    "femme",
    "age",
    "compta",
    "reseau",
    "urbain",
    "pers_morale",
]
lignes = []
for variable in variables_cles:
    b_int = beta_int[noms_int.index(variable)]
    s_int = se_int[noms_int.index(variable)]
    p_int = 2 * (1 - stats.norm.cdf(abs(b_int / s_int)))
    lignes.append(
        (
            etiquette(variable),
            b_int,
            s_int,
            etoiles(p_int),
            beta_probit[X_TOUS.index(variable)],
            coefs_ppo[variable][1],
        )
    )
robustesse_mesure = pd.DataFrame(
    lignes,
    columns=[
        "Variable",
        "intervalles_b",
        "intervalles_se",
        "signif",
        "probit_ordonne_b",
        "ppo_seuil2_b",
    ],
).round(4)
exporter_tableau(robustesse_mesure, "T4_robustesse_mesure_et_lien")
print(robustesse_mesure.to_string(index=False))

# --- 6.2 Sous-échantillons -------------------------------------------------


def ajuster_sous_echantillon(masque_sous, nom):
    """Réestime le PPO sur un sous-échantillon (démarrage à chaud issu du
    PPO principal, classes recodées si l'une disparaît)."""
    ds = d.loc[masque_sous]
    y_sous = ds[VAR_DEP].astype(int).to_numpy()
    classes = np.sort(np.unique(y_sous))
    y_sous = np.searchsorted(classes, y_sous) + 1
    n_seuils = len(classes) - 1
    alpha = coefs_ppo["_alpha"][:n_seuils]
    gamma = np.concatenate([coefs_ppo[v][:n_seuils] for v in X_LIBRES])
    beta = np.array([coefs_ppo[v][0] for v in X_CONTRAINTES])
    debut_ = time.time()
    modele = GenOrderedLogit(
        y_sous,
        ds[X_LIBRES].to_numpy(float),
        ds[X_CONTRAINTES].to_numpy(float),
        X_LIBRES,
        X_CONTRAINTES,
    ).fit(
        clusters=ds[GRAPPES].to_numpy(),
        theta0=np.concatenate([alpha, gamma, beta]),
    )
    print(
        f"[{nom}] N = {len(ds):,}, {time.time() - debut_:.1f} s, "
        f"log-vraisemblance = {modele.loglik:,.1f}"
    )
    return modele


sous_echantillons = {
    "Hors Dakar": d["region_m"] != 1,
    "Hors classe C5": d[VAR_DEP] < 5,
    "Formelles seules": d["formel"] == 1,
}
modeles_sous = {
    nom: ajuster_sous_echantillon(masque_s, nom)
    for nom, masque_s in sous_echantillons.items()
}
variables_stabilite = [
    "formel",
    "femme",
    "banque_obt",
    "fin_informel",
    "compta",
    "urbain",
]
lignes = []
for variable in variables_stabilite:
    ligne = {
        "Variable": etiquette(variable).split(" (")[0],
        "Principal (seuil 1)": coefs_ppo[variable][0],
    }
    for nom, modele in modeles_sous.items():
        ligne[f"{nom} (seuil 1)"] = modele.coef_by_threshold()[variable][0]
    lignes.append(ligne)
stabilite = pd.DataFrame(lignes).round(3)
exporter_tableau(stabilite, "T4_stabilite_sous_echantillons")
print(stabilite.to_string(index=False))

# --- 6.3 Validation hors échantillon (70/30) -------------------------------
generateur = np.random.default_rng(GRAINE)
apprentissage = generateur.random(len(d)) < 0.70
idx_app, idx_test = np.where(apprentissage)[0], np.where(~apprentissage)[0]
modele_app = GenOrderedLogit(
    y[idx_app],
    d.loc[idx_app, X_LIBRES].to_numpy(float),
    d.loc[idx_app, X_CONTRAINTES].to_numpy(float),
    X_LIBRES,
    X_CONTRAINTES,
).fit(clusters=None, theta0=ppo.theta)
probabilites = modele_app.predict_proba(
    d.loc[idx_test, X_LIBRES].to_numpy(float),
    d.loc[idx_test, X_CONTRAINTES].to_numpy(float),
)
y_predit = probabilites.argmax(1) + 1
y_test = y[idx_test]
classe_modale = np.bincount(y[idx_app]).argmax()
lignes = []
for classe in range(1, 6):
    sel = y_test == classe
    lignes.append(
        (
            CLASSES[classe],
            int(sel.sum()),
            round(100 * (y_predit[sel] == classe).mean(), 1),
            100.0 if classe == classe_modale else 0.0,
        )
    )
taux_modele = 100 * (y_predit == y_test).mean()
taux_majoritaire = 100 * (y_test == classe_modale).mean()
lignes.append(
    ("Global", len(y_test), round(taux_modele, 1), round(taux_majoritaire, 1))
)
validation = pd.DataFrame(
    lignes, columns=["Classe", "N_test", "PPO (%)", "Règle majoritaire (%)"]
)
exporter_tableau(validation, "T4_validation_hors_echantillon")
print(validation.to_string(index=False))


# %% [markdown]
# ## 7. Effets marginaux et probabilités par profil
#
# Objectif : traduire les coefficients du PPO, qui ne se lisent pas
# directement, en effets sur la probabilité d'appartenir à chaque classe.
#
# Pourquoi : dans un modèle non linéaire, seuls le signe et la
# significativité d'un coefficient brut sont interprétables. On calcule
# (i) les effets marginaux moyens (dérivée de Pr(Y = j) par rapport à chaque
# variable, moyennée sur l'échantillon, écart-type par méthode delta avec
# la matrice de covariance en grappes) et (ii) les probabilités prédites
# pour des profils types, les autres variables étant fixées à leur moyenne
# d'échantillon.

# %%
na, ng, Knp = ppo.n_alpha, ppo.n_gamma, ppo.Knp
J = ppo.J
noms_all = X_LIBRES + X_CONTRAINTES


def matrice_coefficients(theta):
    """Coefficients par seuil, ordre [X_LIBRES, X_CONTRAINTES]."""
    gamma = theta[na : na + ng].reshape(Knp, N_SEUILS)
    beta = theta[na + ng :]
    return np.vstack([gamma, np.repeat(beta[:, None], N_SEUILS, axis=1)])


def effets_marginaux_moyens(theta):
    """Dérivées moyennes de Pr(Y = j) pour chaque variable (K x J).
    dP(Y=j)/dx = lambda(eta_{j-1}) c_{j-1} - lambda(eta_j) c_j, avec
    lambda = Lambda (1 - Lambda) et lambda(eta_0) = lambda(eta_J) = 0."""
    alpha = theta[:na]
    gamma = theta[na : na + ng].reshape(Knp, N_SEUILS)
    beta = theta[na + ng :]
    eta = alpha[None, :] + X_np @ gamma + (X_pl @ beta)[:, None]
    cumulee = 1 / (1 + np.exp(-eta))
    lambda_moyen = (cumulee * (1 - cumulee)).mean(axis=0)
    coefs = matrice_coefficients(theta)
    ame = np.zeros((coefs.shape[0], J))
    for k in range(coefs.shape[0]):
        for j in range(1, J + 1):
            valeur = 0.0
            if j >= 2:
                valeur += lambda_moyen[j - 2] * coefs[k, j - 2]
            if j <= N_SEUILS:
                valeur -= lambda_moyen[j - 1] * coefs[k, j - 1]
            ame[k, j - 1] = valeur
    return ame


variables_ame = HYPOTHESES + ["compta", "reseau", "urbain", "age", "educ4"]
ame0 = effets_marginaux_moyens(ppo.theta)
jacobien = np.zeros((len(noms_all) * J, ppo.nparam))
for p in range(ppo.nparam):
    theta_pert = ppo.theta.copy()
    theta_pert[p] += 1e-6
    jacobien[:, p] = (
        (effets_marginaux_moyens(theta_pert) - ame0) / 1e-6
    ).reshape(-1)
lignes = []
for variable in variables_ame:
    k = noms_all.index(variable)
    for j in range(J):
        gradient = jacobien[k * J + j]
        se = np.sqrt(max(gradient @ ppo.vcov @ gradient, 0.0))
        z = ame0[k, j] / se if se > 0 else 0.0
        p = 2 * (1 - stats.norm.cdf(abs(z)))
        lignes.append(
            (
                etiquette(variable),
                CLASSES[j + 1],
                ame0[k, j],
                se,
                p,
                etoiles(p),
            )
        )
effets_marginaux = pd.DataFrame(
    lignes, columns=["Variable", "Classe", "AME", "Écart-type", "p", "signif"]
)
exporter_tableau(effets_marginaux.round(5), "T4_effets_marginaux_moyens")
print(
    effets_marginaux[
        effets_marginaux["Variable"].str.startswith(("Formalité", "Dirigeant"))
    ]
    .round(4)
    .to_string(index=False)
)

# --- Probabilités prédites par profil (autres variables aux moyennes) ------
moyenne_np, moyenne_pl = X_np.mean(0), X_pl.mean(0)


def probabilites_profil(**valeurs):
    """Distribution prédite de la classe pour un profil donné."""
    xn, xp = moyenne_np.copy(), moyenne_pl.copy()
    for variable, valeur in valeurs.items():
        if variable in X_LIBRES:
            xn[X_LIBRES.index(variable)] = valeur
        else:
            xp[X_CONTRAINTES.index(variable)] = valeur
    return ppo.predict_proba(xn[None, :], xp[None, :])[0]


profils = {
    "Micro informelle féminine (rurale)": probabilites_profil(
        formel=0, femme=1, urbain=0, compta=0, banque_obt=0, age=3
    ),
    "Micro informelle masculine (urbaine)": probabilites_profil(
        formel=0, femme=0, urbain=1, compta=0, banque_obt=0, age=8
    ),
    "PME formelle masculine (comptabilité, banque)": probabilites_profil(
        formel=1, femme=0, urbain=1, compta=1, banque_obt=1, age=15
    ),
    "PME formelle féminine (comptabilité, banque)": probabilites_profil(
        formel=1, femme=1, urbain=1, compta=1, banque_obt=1, age=15
    ),
}
table_profils = pd.DataFrame(
    {nom: np.round(p, 4) for nom, p in profils.items()},
    index=[CLASSES[c] for c in range(1, J + 1)],
).T
exporter_tableau(table_profils, "T4_profils_types", index=True)
print(table_profils.to_string())

lignes = []
for formel in (0, 1):
    for femme in (0, 1):
        p = probabilites_profil(formel=formel, femme=femme)
        lignes += [(formel, femme, CLASSES[j + 1], p[j]) for j in range(J)]
exporter_tableau(
    pd.DataFrame(
        lignes, columns=["formel", "femme", "Classe", "probabilité"]
    ).round(4),
    "T4_probabilites_formel_femme",
)

# --- Figures ---------------------------------------------------------------
classes_axe = np.arange(1, J + 1)
etiq_axe = [CLASSES[j] for j in classes_axe]

p_informel = probabilites_profil(formel=0)
p_formel = probabilites_profil(formel=1)
fig, axe = plt.subplots(figsize=(7, 4.3))
axe.plot(classes_axe, p_informel, "-o", color=PALETTE[0], label="Informelle")
axe.plot(classes_axe, p_formel, "--D", color=PALETTE[1], label="Formelle")
axe.set_xticks(classes_axe)
axe.set_xticklabels(etiq_axe, fontsize=9)
axe.set_xlabel("Classe de niveau d'activité")
axe.set_ylabel("Probabilité prédite")
axe.legend()
enregistrer_figure(fig, "G4_1_probabilites_formalisation")

sous = effets_marginaux[effets_marginaux["Variable"] == etiquette("formel")]
fig, axe = plt.subplots(figsize=(7, 4.3))
axe.bar(
    classes_axe,
    sous["AME"],
    yerr=1.96 * sous["Écart-type"],
    color=PALETTE[0],
    alpha=0.85,
    capsize=4,
    width=0.6,
)
axe.axhline(0, color="#3b3b3b", lw=0.8)
axe.set_xticks(classes_axe)
axe.set_xticklabels(etiq_axe, fontsize=9)
axe.set_xlabel("Classe de niveau d'activité")
axe.set_ylabel("Effet marginal moyen de la formalité")
enregistrer_figure(fig, "G4_2_effet_marginal_formalite")

fig, axe = plt.subplots(figsize=(7.2, 4.5))
seuils = np.arange(1, N_SEUILS + 1)
for i, variable in enumerate(
    ["formel", "femme", "fin_informel", "banque_obt", "compta"]
):
    axe.plot(
        seuils,
        np.exp(coefs_ppo[variable]),
        "-o",
        color=PALETTE[i % len(PALETTE)],
        label=etiquette(variable).split(" (")[0],
    )
axe.axhline(1, color="#3b3b3b", lw=0.8, ls=":")
axe.set_xticks(seuils)
axe.set_xticklabels([f"Seuil {s}\n(Y>{s})" for s in seuils], fontsize=9)
axe.set_ylabel("Rapport de cotes")
axe.legend(fontsize=8.5, ncol=2)
enregistrer_figure(fig, "G4_3_rapports_de_cotes_par_seuil")

fig, axe = plt.subplots(figsize=(8.2, 4.6))
gauche = np.zeros(len(profils))
matrice = np.array(list(profils.values()))
for j in range(J):
    axe.barh(
        range(len(profils)),
        matrice[:, j],
        left=gauche,
        color=teintes[j],
        edgecolor="white",
        label=CLASSES[j + 1],
    )
    gauche += matrice[:, j]
axe.set_yticks(range(len(profils)))
axe.set_yticklabels(list(profils), fontsize=8.5)
axe.set_xlim(0, 1)
axe.set_xlabel("Probabilité prédite")
axe.legend(ncol=5, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12))
enregistrer_figure(fig, "G4_4_profils_types")


# %% [markdown]
# ## 8. Export des tableaux et vérification contre le mémoire
#
# Objectif : regrouper tous les tableaux dans un classeur Excel unique
# (en plus des CSV déjà écrits dans output/tableaux/) et confronter les
# chiffres clés calculés à ceux publiés dans le mémoire.
#
# Pourquoi : la reproductibilité se démontre. Le tableau de vérification
# indique, pour chaque chiffre du mémoire, la valeur retrouvée par le code
# et l'écart toléré (arrondi de la dernière décimale publiée).

# %%
or_formel = np.exp(coefs_ppo["formel"])
or_femme = np.exp(coefs_ppo["femme"])
or_banque = np.exp(coefs_ppo["banque_obt"])
p_c5 = {nom: profils[nom][4] for nom in profils}
lig_assoc = associations.set_index("Variable")
femmes_formelles_s1 = modeles_sous["Formelles seules"].coef_by_threshold()[
    "femme"
][0]
indice_femme = noms_int.index("femme")

verifications = [
    ("Échantillon d'estimation (N)", N_ECHANTILLON, ppo.N, 0),
    (
        "Grappes région x branche",
        N_GRAPPES,
        len(np.unique(grappes[~pd.isna(grappes)])),
        0,
    ),
    ("Test de Brant : chi2 global", 9694, brant["chi2"], 1),
    ("Test de Brant : ddl", 135, brant["df"], 0),
    ("RC formalité, seuil 1 (≈ 2,4)", 2.404, or_formel[0], 0.002),
    ("RC formalité, seuil 2", 2.088, or_formel[1], 0.002),
    ("RC formalité, seuil 3", 3.407, or_formel[2], 0.002),
    ("RC formalité, seuil 4 (≈ 13)", 12.846, or_formel[3], 0.002),
    ("RC dirigeant femme, seuil 1", 0.276, or_femme[0], 0.002),
    ("RC dirigeant femme, seuil 4", 0.165, or_femme[3], 0.002),
    ("RC financement bancaire, seuil 4", 2.659, or_banque[3], 0.002),
    ("Log-vraisemblance du PPO", -319_976.5, ppo.loglik, 0.5),
    (
        "Log-vraisemblance du logit ordonné",
        -322_158.8,
        logit_ordonne.loglik,
        0.5,
    ),
    ("LR (ordonné -> PPO)", 4364.5, rapport_vrais, 0.5),
    (
        "Pr(C5), PME formelle masculine (≈ 15 %)",
        0.148,
        p_c5["PME formelle masculine (comptabilité, banque)"],
        0.0005,
    ),
    (
        "Pr(C5), PME formelle féminine (≈ 3 %)",
        0.028,
        p_c5["PME formelle féminine (comptabilité, banque)"],
        0.0005,
    ),
    (
        "Pr(C1), micro informelle féminine rurale (≈ 62 %)",
        0.619,
        profils["Micro informelle féminine (rurale)"][0],
        0.0005,
    ),
    (
        "Khi-deux formalisation x niveau d'activité",
        24_445,
        lig_assoc.loc["Formalisation", "khi2"],
        1,
    ),
    (
        "V de Cramér, formalisation",
        0.289,
        lig_assoc.loc["Formalisation", "V_Cramer"],
        0.0005,
    ),
    (
        "Spearman, formalisation",
        0.122,
        lig_assoc.loc["Formalisation", "rho_Spearman"],
        0.0005,
    ),
    (
        "Régression par intervalles : coefficient femme",
        -0.92,
        beta_int[noms_int.index("femme")],
        0.005,
    ),
    (
        "Sous-échantillon formelles : coef. femme, seuil 1",
        -0.40,
        femmes_formelles_s1,
        0.005,
    ),
    (
        "Validation hors échantillon : taux global PPO (%)",
        52.8,
        taux_modele,
        0.05,
    ),
    (
        "Validation hors échantillon : règle majoritaire (%)",
        45.8,
        taux_majoritaire,
        0.05,
    ),
]
tableau_verification = pd.DataFrame(
    verifications,
    columns=["Chiffre du mémoire", "Mémoire", "Code", "Tolérance"],
)
tableau_verification["Écart"] = (
    tableau_verification["Code"] - tableau_verification["Mémoire"]
)
tableau_verification["Concordance"] = np.where(
    tableau_verification["Écart"].abs()
    <= tableau_verification["Tolérance"] + 1e-12,
    "oui",
    "NON",
)
exporter_tableau(tableau_verification.round(4), "VERIF_memoire_contre_code")
print(tableau_verification.round(4).to_string(index=False))

chemin_classeur = DOSSIER_SORTIE / "tableaux_complets.xlsx"
with pd.ExcelWriter(chemin_classeur, engine="openpyxl") as classeur:
    for nom_tableau, tableau in TABLEAUX.items():
        tableau.to_excel(classeur, sheet_name=nom_tableau[:31], index=False)
print(f"{len(TABLEAUX)} tableaux exportés dans {DOSSIER_SORTIE.name}/")
