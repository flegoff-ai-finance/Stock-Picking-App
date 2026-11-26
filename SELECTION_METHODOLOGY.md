# Méthodologie de sélection en trois couches

## Paramètres validés

- Univers : titres dont l'éligibilité PEA est explicitement vérifiée et encore valide.
- Couche 1 : 150 candidats maximum par stratégie.
- Couche 2 : 25 titres maximum par stratégie.
- Couche 3 : score global sur 100 et signal indicatif.
- Seuils initiaux : achat à partir de 75 ; vente / éviter sous 40 ; conserver / surveiller entre 40 et 75.
- Les seuils sont provisoires : ils doivent être backtestés avant toute utilisation réelle.
- Aucune donnée manquante n'est imputée.

## Couche 1 — screening large

Le premier écran utilise des facteurs simples et relativement accessibles. Un titre doit avoir au moins deux facteurs disponibles sur trois pour être classable. Les facteurs sont transformés en rangs percentiles au sein de l'univers PEA vérifié ; les facteurs manquants ne contribuent pas au score et la couverture est affichée.

| Stratégie | Facteurs de screening | Sens favorable |
|---|---|---|
| Growth | CAGR du CA 3 ans ; croissance BPA estimée à 1 an ; Forward P/E | Plus élevé ; plus élevé ; plus faible |
| Growth Quality | CAGR du CA 3 ans ; marge opérationnelle ; ROIC | Plus élevé pour les trois |
| Growth Momentum | Performance 12-1 mois ; performance 6 mois ; cours vs MM200 | Plus élevé pour les trois |

La croissance BPA à un an n'est qu'un filtre initial de découverte. Elle ne remplace jamais la croissance BPA 3–5 ans utilisée dans le PEG classique.

## Couche 2 — sélection stratégique approfondie

Le moteur stratégique est appliqué uniquement aux candidats retenus en couche 1.

- Growth : PEG classique = Forward P/E / croissance annuelle anticipée du BPA en pourcentage. Croissance BPA pluriannuelle positive requise ; classement par PEG croissant.
- Growth Quality : score pondéré existant, fondé sur croissance CA et EBIT, marges opérationnelle et FCF, ROIC, dette nette/EBITDA, Sharpe 3 ans et drawdown 3 ans.
- Growth Momentum : score pondéré existant, fondé sur momentum 12-1, performance 6 mois, cours vs MM200, MM50 vs MM200, Sharpe 3 ans, drawdown 1 an, volatilité 1 an et performance relative à l'indice local.

Seuls les 25 premiers titres classables sont transmis à la couche 3. Les moteurs stratégiques conservent leurs exigences de données complètes.

## Couche 3 — score global et décision

Le score final est relatif au panel des finalistes de chaque stratégie. Chaque facteur disponible est transformé en rang percentile. Les poids disponibles sont renormalisés, sans inventer de valeur. Le score n'est calculé que si au moins quatre facteurs sont disponibles et si leur poids cumulé atteint au moins 75 %.

| Stratégie | Facteurs finaux | Poids |
|---|---|---:|
| Growth | PEG (plus faible = mieux) | 35 % |
|  | CAGR CA 3 ans | 20 % |
|  | Marge opérationnelle | 15 % |
|  | Momentum 12-1 mois | 15 % |
|  | Drawdown 3 ans (moins négatif = mieux) | 15 % |
| Growth Quality | Score Quality de couche 2 | 35 % |
|  | Forward P/E (plus faible = mieux) | 10 % |
|  | Marge FCF | 15 % |
|  | ROIC | 15 % |
|  | Dette nette / EBITDA (plus faible = mieux) | 10 % |
|  | Drawdown 3 ans (moins négatif = mieux) | 15 % |
| Growth Momentum | Score Momentum de couche 2 | 35 % |
|  | Forward P/E (plus faible = mieux) | 10 % |
|  | Croissance BPA estimée à 1 an | 10 % |
|  | Sharpe 3 ans | 15 % |
|  | Drawdown 1 an (moins négatif = mieux) | 15 % |
|  | Volatilité 1 an (plus faible = mieux) | 15 % |

### Interprétation

- Score >= 75 : signal d'achat à étudier.
- Score entre 40 et 75 : conserver / surveiller.
- Score < 40 : signal de vente pour une position détenue, ou éviter pour un titre non détenu.
- Score N/D : données insuffisantes ; aucune décision.

Les seuils sont des paramètres initiaux, pas des niveaux optimisés. Ils ne déclenchent aucun ordre. Toute décision doit tenir compte de la liquidité, des frais, de la taille de position, de la diversification, des événements récents et de la thèse d'investissement.

## État actuel et limites

Le registre de données contient encore sept titres pilotes. Il ne constitue pas un univers PEA exhaustif. La nouvelle architecture calcule des candidats uniquement sur les données présentes dans ce registre ; elle ne fabrique pas 150 lignes. L'étape suivante est d'élargir et de vérifier l'univers PEA, puis d'alimenter les champs par Yahoo Finance en priorité et de compléter / contrôler avec d'autres sources lorsque leurs conditions d'accès le permettent.

Le score final affiché est une mesure de classement relative, pas une probabilité de hausse ni une garantie de performance. Les données de fournisseurs gratuits peuvent être retardées, incomplètes ou soumises à des restrictions d'usage et de redistribution.
