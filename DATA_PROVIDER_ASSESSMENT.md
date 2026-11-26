# Évaluation des fournisseurs de données — novembre 2026

## Décision de conception

Ne pas lancer un scraping de portails boursiers ni publier de données financières dérivées d'une source sans droits d'accès et de redistribution vérifiés. Le code de l'application est public ; publier un fichier JSON de données brutes dans le dépôt rendrait ces données accessibles à tous. Une licence d'utilisation personnelle ne suffit donc pas nécessairement à autoriser cette publication.

Le pipeline doit distinguer :
1. le référentiel de découverte (identité, ISIN, place, secteur, taille) ;
2. les données de prix et d'historique ;
3. les états financiers et estimations ;
4. les preuves d'éligibilité PEA, qui restent indépendantes des fournisseurs de données financières.

## Sources examinées

| Source | Couverture / quota gratuit | Fondamentaux | Limite principale | Décision |
|---|---|---|---|---|
| FinanceDatabase | Univers de 3 691 lignes dans le snapshot actuel | Non | Référentiel de symboles et métadonnées, pas une source financière à jour | Conserver pour la découverte uniquement |
| EODHD | 20 appels API/jour ; 1 an de cours EOD en gratuit | Non dans l'offre gratuite | Les fondamentaux nécessitent le forfait Fundamentals ; l'historique EOD est un autre forfait | Meilleur candidat pour un pilote européen si le coût et les droits d'affichage sont acceptables |
| Financial Modeling Prep (FMP) | 250 appels/jour sur Basic | Limité aux données US dans l'offre gratuite | Les données européennes nécessitent une offre payante ; les droits d'affichage/redistribution nécessitent un accord spécifique | Ne pas retenir comme source gratuite pour notre univers européen |
| Yahoo Finance / yfinance | Pas d'API Finance publique officielle documentée pour ce cas | Champs variables selon le titre | Les conditions Yahoo interdisent la collecte automatisée sans permission préalable et la redistribution des données | Retirer comme source automatisée du pipeline public, sauf autorisation écrite |
| Stooq | Téléchargements historiques disponibles | Non | Usage personnel uniquement et restrictions de redistribution | Ne pas utiliser dans le dépôt public |

## Coûts observés (à confirmer avant souscription)

- EODHD Fundamentals Data Feed : 59,99 USD/mois en paiement mensuel.
- EODHD EOD Historical All-World : 19,99 USD/mois en paiement mensuel.
- EODHD All-in-One : 99,99 USD/mois en paiement mensuel.
- FMP Basic : gratuit, mais couverture US ; Starter annoncé à 19 USD/mois en facturation annuelle et ne couvre pas notre univers européen complet ; Premium annoncé à 49 USD/mois en facturation annuelle avec couverture UK/Canada ; Ultimate annoncé à 99 USD/mois en facturation annuelle avec couverture globale.

Ces tarifs sont ceux affichés au moment de la recherche et peuvent évoluer. Les offres personnelles et les licences d'affichage public sont deux sujets distincts : demander une confirmation écrite au fournisseur avant de publier les données dans l'application.

## Couverture de l'univers actuel

Le fichier `data/discovery_universe.csv` contient 3 691 ISIN uniques. La répartition de taille déclarée par la source est :
- Nano Cap : 1 113
- Micro Cap : 851
- Small Cap : 767
- Mid Cap : 482
- Large Cap : 430
- Mega Cap : 10
- Non renseigné : 38

Soit 2 731 titres classés Nano/Micro/Small. Cette composition est très large et comprend de nombreuses valeurs peu liquides. Le premier filtre devra donc intégrer une règle de liquidité documentée (volume moyen en valeur, fréquence de cotation, flottant si disponible) ou au minimum afficher un avertissement. La capitalisation déclarée par FinanceDatabase est une catégorie, pas une capitalisation chiffrée suffisamment précise pour calculer un filtre quantitatif.

## Besoin de données par stratégie

| Stratégie | Données requises pour couche 1 | Enrichissement indispensable ensuite |
|---|---|---|
| Growth | Forward P/E et croissance BPA estimée explicite | Croissance BPA prévisionnelle 3–5 ans pour calculer le PEG classique ; ne jamais la remplacer par une croissance historique |
| Growth Quality | CAGR CA 3 ans, marge opérationnelle, ROIC | Marge FCF, dette nette/EBITDA, croissance EBIT et qualité des comptes |
| Momentum | Prix ajustés sur au moins 12 mois, volume et benchmark local | Historique 3 ans, volatilité, drawdown, Sharpe et performance relative |

Un titre ne doit être classé dans une stratégie que si au moins deux facteurs de couche 1 sont réellement disponibles. Les données manquantes restent nulles et leur couverture est mesurée.

## Proposition opérationnelle

1. Ne pas acheter d'abonnement à ce stade.
2. Demander à EODHD une confirmation écrite couvrant : places européennes précises, mapping ISIN/ticker, champs de consensus EPS +5y, droits d'affichage sur une application web publique, stockage/cache des réponses et redistribution des scores calculés.
3. Si la réponse est satisfaisante, faire un pilote limité à 30–50 sociétés européennes de tailles et de pays variés, puis contrôler manuellement les comptes et les données de consensus.
4. Mesurer les taux de disponibilité par indicateur, les erreurs de mapping et la cohérence des calculs avant de traiter les 3 691 titres.
5. N'activer le fichier `data/discovery_financials.json` dans le moteur que lorsque le pilote et les règles de fraîcheur/qualité sont validés.

## Sources officielles consultées

- EODHD plans et prix : https://eodhd.com/pricing/
- EODHD détail des plans : https://eodhd.com/help/plans
- FMP plans : https://site.financialmodelingprep.com/pricing-plans
- FMP périmètre Basic : https://site.financialmodelingprep.com/how-to/how-to-create-a-financial-modeling-prep-account
- Yahoo Terms of Service : https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html
- Yahoo Finance data and redistribution notice : https://in.help.yahoo.com/kb/SLN2310.html
- Stooq data terms should be checked directly before any use.
