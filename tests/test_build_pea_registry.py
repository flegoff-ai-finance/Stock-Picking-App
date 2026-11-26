import unittest
from datetime import date

from scripts.build_pea_registry import is_recently_verified_pilot, validate_review


class PeaRegistryAuditTests(unittest.TestCase):
    def valid_review(self):
        return {
            "candidate_id": "abc123",
            "isin": "FR0000120271",
            "ticker": "TOTF.PA",
            "issuer_country_iso2": "FR",
            "corporate_tax_status": "confirmed",
            "instrument_type": "ordinary_share",
            "pea_eligibility_source_url": "https://example.com/pea",
            "issuer_source_url": "https://example.com/investors",
            "verified_by": "reviewer",
            "verified_at": "2026-11-26",
        }

    def test_recent_verified_pilot_is_counted_but_stale_one_is_not(self):
        row = {"pea_status": "eligible", "isin": "FR0000120271",
               "ticker": "TTE.PA", "pea_checked_at": "2026-11-26"}
        self.assertTrue(is_recently_verified_pilot(row, date(2026, 11, 26)))
        row["pea_checked_at"] = "2026-01-01"
        self.assertFalse(is_recently_verified_pilot(row, date(2026, 11, 26)))

    def test_complete_recent_evidence_is_accepted(self):
        self.assertEqual(validate_review(self.valid_review(), {"abc123"}, date(2026, 11, 26)), [])

    def test_missing_legal_or_instrument_evidence_is_rejected(self):
        row = self.valid_review()
        row["issuer_country_iso2"] = "US"
        row["corporate_tax_status"] = "unknown"
        row["instrument_type"] = "warrant"
        errors = validate_review(row, {"abc123"}, date(2026, 11, 26))
        self.assertGreaterEqual(len(errors), 3)

    def test_expired_review_is_rejected(self):
        row = self.valid_review()
        row["verified_at"] = "2026-01-01"
        self.assertIn("vérification PEA expirée ou datée dans le futur",
                      validate_review(row, {"abc123"}, date(2026, 11, 26)))

    def test_unknown_candidate_is_rejected(self):
        self.assertIn("candidate_id absent du référentiel de découverte",
                      validate_review(self.valid_review(), set(), date(2026, 11, 26)))


if __name__ == "__main__":
    unittest.main()
