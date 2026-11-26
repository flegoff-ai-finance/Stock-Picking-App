# PEA LAB — Stock Picking App

Application de recherche et de simulation de trois portefeuilles PEA indépendants : **Growth**, **Growth Quality** et **Growth Momentum**.

## Architecture de sélection

- Couche 1 : screening interne, jusqu'à 150 candidats par stratégie. Les noms et les rangs de cette couche ne sont pas affichés dans l'application.
- Couche 2 : analyse stratégique, jusqu'à 25 valeurs par stratégie, avec indicateurs détaillés et couverture des données.
- Couche 3 : score global /100 et signal indicatif. Seuils provisoires : achat à étudier ≥75, conserver/surveiller entre 40 et 75, vente/éviter <40.
- Données manquantes : jamais imputées. Les scores partiels exigent au moins quatre facteurs et 75 % du poids documenté.

## Données

- Yahoo Finance via `yfinance` : cours ajustés, indicateurs techniques, états financiers disponibles et estimations de croissance BPA.
- Banque centrale européenne : €STR quotidien pour le Sharpe excédentaire.
- CAC 40 : proxy de marché pour la performance relative des titres pilotes cotés à Paris.
- Les sources de listes PEA ne sont pas aspirées automatiquement lorsqu'elles interdisent l'extraction. Le référentiel élargi doit provenir d'un export du courtier ou d'un fournisseur dûment licencié.

## Univers PEA — état du pilote

- 7 titres pilotes actuellement admis dans l'univers de scoring.
- Un vivier de découverte de 3 691 candidats européens est maintenant généré depuis FinanceDatabase (référentiel MIT), sur 19 places de cotation. Ce vivier n'est pas assimilé à l'univers PEA éligible : seuls les titres passés par le contrôle documentaire peuvent rejoindre le scoring.
- Le vivier exploratoire est dans `data/discovery_universe.csv` (rafraîchi chaque semaine). Sa méthode et ses limites sont documentées dans `DISCOVERY_UNIVERSE.md`. Il reste distinct du modèle d'import et de contrôle PEA dans `data/pea_verification.csv`. Le contrôle documentaire est automatisé par `scripts/build_pea_registry.py`, puis `scripts/sync_pea_registry.py` ajoute uniquement les titres validés ; Yahoo les enrichit par lots de 50.
- Chaque nouvelle ligne doit documenter l'ISIN, le ticker, le siège UE/EEE, l'assujettissement fiscal, la nature d'action ordinaire, une source d'éligibilité PEA et une source émetteur. La vérification expire après 90 jours.

## Limites actuelles

- Growth reste N/D tant que les estimations de croissance BPA à cinq ans nécessaires au PEG ne sont pas disponibles.
- Les classements Quality et Momentum reposent encore sur les sept titres pilotes ; ils ne sont pas représentatifs de tout le PEA.
- Un diagnostic historique du signal Momentum est disponible sur les sept pilotes (snapshots mensuels, horizons 1/3/6 mois, frais aller-retour simulés sur le Top 2). Il reste exploratoire et ne valide pas les seuils de décision ni la construction des portefeuilles.
- Growth et Growth Quality ne sont pas backtestés faute de fondamentaux historiques point-in-time.
- Les portefeuilles sont virtuels : aucun ordre réel n'est transmis.
- Yahoo Finance via yfinance est une interface non officielle ; les droits d'usage et de redistribution doivent être confirmés avant tout usage public élargi.

## Workflows GitHub Actions

- `Refresh Yahoo Finance market data` : actualisation en semaine.
- `Backtest Growth Momentum signal` : diagnostic historique mensuel du classement Momentum.
- `Validate PEA registry import` : audit manuel des fichiers d'import.
- `Validate data pipeline` et `Validate selection JavaScript` : tests automatisés.
