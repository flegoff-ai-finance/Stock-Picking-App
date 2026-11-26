# Méthodologie de sélection en trois couches

## Paramètres validés

- Univers de découverte : actions européennes candidates, sans filtre PEA préalable.
- Contrôle PEA : appliqué en couche 2, après le premier classement ; seuls les ISIN présents dans le registre vérifié et dont la vérification date de moins de 90 jours sont admis.
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

## Couche 2 — vérification PEA et sélection stratégique approfondie

Le moteur classe d'abord l'univers de découverte complet. Il prend ensuite les candidats dans l'ordre de classement et les rapproche du registre PEA vérifié par ISIN. Les candidats sans preuve PEA récente sont écartés ; le moteur poursuit dans la liste classée pour les remplacer, jusqu'à 150 titres vérifiés maximum par stratégie. La vérification exige un statut `eligible`, un ISIN valide, un ticker confirmé et une date de contrôle de moins de 90 jours. Les informations légales du registre priment sur les métadonnées de découverte.

Le moteur stratégique est appliqué uniquement aux candidats retenus après ce contrôle PEA.

- Growth : PEG classique = Forward P/E / croissance annuelle anticipée du BPA en pourcentage. Croissance BPA pluriannuelle positive requise ; classement par PEG croissant.
- Growth Quality : score pondéré existant, fondé sur croissance CA et EBIT, marges opérationnelle et FCF, ROIC, dette nette/EBITDA, Sharpe 3 ans et drawdown 3 ans.
- Growth Momentum : score pondéré existant, fondé sur momentum 12-1, performance 6 mois, cours vs MM200, MM50 vs MM200, Sharpe 3 ans, drawdown 1 an, volatilité 1 an et performance relative à l'indice local.

Seuls les 25 premiers titres classables sont transmis à la couche 3. Les moteurs stratégiques n'imputent aucune donnée. Un score de couche 2 n'est calculé que si au moins quatre facteurs sont disponibles et si leur poids cumulé atteint 75 % du poids total ; les poids absents sont renormalisés sur les seuls facteurs documentés. La couverture en nombre de facteurs et en poids doit rester visible.

## Couche 3 — score global et décision

Le score final est relatif au panel des finalistes de chaque stratégie. Chaque facteur disponible est transformé en rang percentile. Les poids disponibles sont renormalisés, sans inventer de valeur. Le score n'est calculé que si au moins quatre facteurs sont disponibles et si leur poids cumulé atteint au moins 75 %. La même règle minimale s'applique aux scores stratégiques de couche 2.

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

Le registre technique contient encore sept titres pilotes et ne constitue pas un univers PEA exhaustif. Le code de sélection accepte désormais séparément un univers de découverte et le registre PEA : le premier screening est réalisé sans filtre PEA, puis la vérification PEA intervient en couche 2 avec remplacement par les candidats suivants. L'application est prête à charger `data/discovery_financials.json`, mais ce fichier n'est pas encore produit ; tant qu'il est absent, l'interface reste explicitement en mode pilote et utilise les sept titres existants. Aucun screening élargi ni classement sur 3 691 sociétés ne doit être considéré comme exécuté à ce stade. L'étape suivante est d'alimenter ce fichier avec des données financières et de marché documentées, sans scraper les sites dont les conditions interdisent l'extraction.

Le score final affiché est une mesure de classement relative, pas une probabilité de hausse ni une garantie de performance. Les données de fournisseurs gratuits peuvent être retardées, incomplètes ou soumises à des restrictions d'usage et de redistribution.
