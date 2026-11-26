import unittest

from scripts.discover_pea_candidates import parse_listing, parse_meqiri_listing


class CandidateDiscoveryTests(unittest.TestCase):
    def test_extracts_candidates_but_never_marks_them_eligible(self):
        html = """
        <table><tr><th>Code</th><th>Nom</th></tr>
        <tr><td>AI</td><td><a href="/fr/web/xpar-ai/air-liquide">AIR LIQUIDE</a></td></tr>
        <tr><td>ENX</td><td><a href="/fr/web/xpar-enx/euronext">EURONEXT</a></td></tr>
        </table>
        """
        rows = parse_listing(html, "france", "https://example.test/list")
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["pea_status"], "pending_verification")
        self.assertEqual(rows[0]["verification_status"], "not_verified")
        self.assertEqual(rows[0]["provisional_yahoo_ticker"], "AI.PA")
        self.assertIsNone(rows[0]["isin"])
        self.assertEqual(rows[0]["eligibility_evidence"], [])

    def test_maps_only_known_exchange_suffixes_as_provisional(self):
        html = """
        <table><tr><th>Code</th><th>Nom</th></tr>
        <tr><td>2GB</td><td><a href="/fr/web/xetr-2gb/2g-energy">2G ENERGY</a></td></tr>
        <tr><td>ADZ</td><td><a href="/fr/web/xmce-adz/a-dominguez">A. DOMINGUEZ</a></td></tr>
        <tr><td>ZZZ</td><td><a href="/fr/web/chix-zzz/company">UNKNOWN MARKET</a></td></tr>
        </table>
        """
        rows = parse_listing(html, "europe", "https://example.test/list")
        tickers = {row["name"]: row["provisional_yahoo_ticker"] for row in rows}
        self.assertEqual(tickers["2G ENERGY"], "2GB.DE")
        self.assertEqual(tickers["A. DOMINGUEZ"], "ADZ.MC")
        self.assertIsNone(tickers["UNKNOWN MARKET"])

    def test_meqiri_candidates_are_prequalified_but_not_eligible(self):
        html = """
        <table><tr><th>Rang</th><th>Action</th><th>Score</th><th>Siège</th></tr>
        <tr><td>1</td><td><a href="/fr/actions/euronext-athens">Euronext Athens Holding EXAE.AT</a></td><td>91</td><td>Grèce</td></tr>
        <tr><td>2</td><td><a href="/fr/actions/viel">VIEL &amp; Cie VIL.PA</a></td><td>86</td><td>France</td></tr>
        <tr><td>3</td><td><a href="/fr/actions/addtech">Addtech AB (publ.)ADDT-B.ST</a></td><td>68</td><td>Suède</td></tr>
        <tr><td>4</td><td><a href="/fr/actions/schott">SCHOTT Pharma 1SXP.F</a></td><td>70</td><td>Allemagne</td></tr>
        </table>
        """
        rows = parse_meqiri_listing(html, "https://meqiri.com/fr/actions/eligibles-pea")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["provisional_yahoo_ticker"], "EXAE.AT")
        self.assertEqual(rows[0]["issuer_country_hint_iso2"], "GR")
        self.assertEqual(rows[0]["pea_status"], "pending_verification")
        self.assertEqual(rows[0]["verification_status"], "prequalified_pending_legal_review")
        self.assertTrue(rows[0]["meqiri_pea_listed"])
        self.assertEqual(rows[2]["provisional_yahoo_ticker"], "ADDT-B.ST")
        self.assertEqual(rows[3]["provisional_yahoo_ticker"], "1SXP.F")

    def test_ignores_header_and_empty_rows(self):
        html = "<table><tr><td>Code</td><td>Nom</td></tr><tr><td></td><td></td></tr></table>"
        self.assertEqual(parse_listing(html, "france", "https://example.test/list"), [])


if __name__ == "__main__":
    unittest.main()
