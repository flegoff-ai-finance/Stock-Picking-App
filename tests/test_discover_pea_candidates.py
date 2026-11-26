import unittest

from scripts.discover_pea_candidates import parse_listing


class CandidateDiscoveryTests(unittest.TestCase):
    def test_extracts_candidates_but_never_marks_them_eligible(self):
        html = """
        <table><tr><th>Code</th><th>Nom</th></tr>
        <tr><td>AI</td><td><a href="/fr/web/xpar-ai/air-liquide">AIR LIQUIDE</a></td></tr>
        <tr><td>ENX</td><td><a href="/fr/web/xpar-enx/euronext">EURONEXT</a></td></tr>
        </table>
        """
        rows = parse_listing(html, "france", "https://example.test/list")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["pea_status"], "pending_verification")
        self.assertEqual(rows[0]["verification_status"], "not_verified")
        self.assertEqual(rows[0]["provisional_yahoo_ticker"], "AI.PA")
        self.assertIsNone(rows[0]["isin"])
        self.assertEqual(rows[0]["eligibility_evidence"], [])

    def test_ignores_header_and_empty_rows(self):
        html = "<table><tr><td>Code</td><td>Nom</td></tr><tr><td></td><td></td></tr></table>"
        self.assertEqual(parse_listing(html, "france", "https://example.test/list"), [])


if __name__ == "__main__":
    unittest.main()
