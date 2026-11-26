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
- ProRealTime : découverte large des candidats France, Europe et EEE. MEQIRI : liste complémentaire préfiltrée selon les critères légaux annoncés, avec exclusions SIIC et indications de pays. Ces sources ne remplacent pas la confirmation du courtier ni notre contrôle documentaire.

## Univers PEA — état du pilote

- 7 titres pilotes actuellement admis dans l'univers de scoring.
- 3 621 candidats détectés dans les répertoires de découverte.
- 1 451 tickers Yahoo provisoires identifiés ; aucun candidat nouvellement découvert n'est admis automatiquement.
- Les nouveaux titres restent en attente jusqu'à vérification de l'ISIN, de la nature du titre, du siège UE/EEE, de l'assujettissement fiscal et des sources probantes.
- La revue est tracée dans `data/pea_verification.csv` ; le contrôle est automatisé par `scripts/build_pea_registry.py`.

## Limites actuelles

- Growth reste N/D tant que les estimations de croissance BPA à cinq ans nécessaires au PEG ne sont pas disponibles.
- Les classements Quality et Momentum reposent encore sur les sept titres pilotes ; ils ne sont pas représentatifs de tout le PEA.
- Un diagnostic historique du signal Momentum est disponible sur les sept pilotes (snapshots mensuels, horizons 1/3/6 mois, frais aller-retour simulés sur le Top 2). Il reste exploratoire et ne valide pas les seuils de décision ni la construction des portefeuilles.
- Growth et Growth Quality ne sont pas backtestés faute de fondamentaux historiques point-in-time.
- Les portefeuilles sont virtuels : aucun ordre réel n'est transmis.
- Les conditions d'accès et de redistribution des données de marché doivent être respectées avant tout usage public élargi.

## Workflows GitHub Actions

- `Refresh Yahoo Finance market data` : actualisation en semaine.
- `Discover PEA equity candidates` : actualisation hebdomadaire des candidats et audit des preuves.
- `Backtest Growth Momentum signal` : diagnostic historique mensuel du classement Momentum.
- `Validate data pipeline` et `Validate selection JavaScript` : tests automatisés.
