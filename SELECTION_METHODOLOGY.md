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

Le premier écran est appliqué à l'univers de découverte complet, avant la vérification PEA. Un titre qui ne respecte pas le socle minimal de données de sa stratégie est exclu immédiatement. Les données manquantes ne sont ni imputées ni remplacées par zéro. Les candidats classables sont rangés par percentiles et le moteur conserve au maximum 150 candidats par stratégie.

| Stratégie | Indicateurs du filtre | Règle minimale de passage |
|---|---|---|
| Growth | CAGR du CA 3 ans ; croissance BPA annualisée estimée à 5 ans ; Forward P/E | Les 3 disponibles ; Forward P/E et croissance BPA strictement positifs pour calculer le PEG |
| Growth Quality | CAGR du CA 3 ans ; marge opérationnelle ; ROIC ; marge FCF ; dette nette / EBITDA | Au moins 4 sur 5, avec croissance du CA obligatoire et ROIC ou marge FCF obligatoire |
| Growth Momentum | Performance 12-1 mois ; performance 6 mois ; cours vs MM200 ; volatilité 1 an ; drawdown 1 an | Au moins 4 sur 5, avec les performances 12-1 mois et 6 mois obligatoires |

Les candidats écartés sont comptabilisés par stratégie avec un motif d'exclusion. Les raisons incluent notamment l'absence de données financières, un historique de cours trop court ou l'absence d'un indicateur indispensable.

## Couche 2 — vérification PEA et sélection stratégique approfondie

Le moteur classe d'abord l'univers de découverte complet. Il prend ensuite les candidats dans l'ordre de classement et les rapproche du registre PEA vérifié par ISIN. Les candidats sans preuve PEA récente sont écartés ; le moteur poursuit dans la liste classée pour les remplacer, jusqu'à 150 titres vérifiés maximum par stratégie. La vérification exige un statut `eligible`, un ISIN valide, un ticker confirmé et une date de contrôle de moins de 90 jours. Les informations légales du registre priment sur les métadonnées de découverte.

Le moteur stratégique est appliqué uniquement aux candidats retenus après ce contrôle PEA.

- Growth : PEG classique = Forward P/E / croissance annuelle anticipée du BPA à 5 ans en pourcentage. Les quatre données (Forward P/E, croissance BPA 5 ans, PEG calculable et CAGR du CA 3 ans) sont indispensables ; la croissance BPA doit être positive. Classement par PEG croissant.
- Growth Quality : au moins 4 indicateurs sur 5 doivent être présents : CAGR du CA, marge opérationnelle, ROIC, marge FCF et dette nette / EBITDA. La croissance du CA est obligatoire, ainsi que le ROIC ou la marge FCF.
- Growth Momentum : au moins 4 indicateurs sur 5 doivent être présents : performance 12-1 mois, performance 6 mois, cours vs MM200, volatilité 1 an et drawdown 1 an. Les performances 12-1 mois et 6 mois sont obligatoires.

Seuls les 25 premiers titres classables sont transmis à la couche 3. Les titres qui échouent aux règles minimales sont exclus du classement de la stratégie concernée, même si d'autres indicateurs sont disponibles. Les motifs d'exclusion sont comptabilisés. Les scores ne reposent que sur des données observées ; aucune donnée manquante n'est imputée.

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
