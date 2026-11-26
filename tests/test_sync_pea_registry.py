import unittest

from scripts.sync_pea_registry import merge_registry


class SyncPeaRegistryTests(unittest.TestCase):
    def test_only_verified_rows_are_added(self):
        document = {"instruments": [{"name": "Pilot", "isin": "FR0000000001", "ticker": "PIL.PA"}]}
        audit = {
            "verified_instruments": [{
                "name": "NewCo", "isin": "DE0000000001", "ticker": "NEW.DE",
                "pea_status": "eligible", "pea_checked_at": "2026-11-26",
                "issuer_country_iso2": "DE", "corporate_tax_status": "confirmed",
                "instrument_type": "ordinary_share", "eligibility_evidence": ["https://example.com/pea"],
                "verified_by": "reviewer",
            }],
            "pending_review": [{"name": "Unverified", "isin": "FR0000000002", "ticker": "NO.PA"}],
        }
        merged = merge_registry(document, audit)
        self.assertEqual(merged["universe_count"], 2)
        self.assertEqual(merged["pea_verified_universe_count"], 1)
        self.assertEqual(merged["registry_sync_added_count"], 1)
        self.assertEqual(merged["instruments"][1]["pea_status"], "eligible")

    def test_existing_isin_is_updated_not_duplicated(self):
        document = {"instruments": [{"name": "Old Name", "isin": "FR0000000001", "ticker": "OLD.PA"}]}
        audit = {"verified_instruments": [{
            "name": "Correct Name", "isin": "FR0000000001", "ticker": "NEW.PA",
            "pea_status": "eligible", "pea_checked_at": "2026-11-26",
        }]}
        merged = merge_registry(document, audit)
        self.assertEqual(len(merged["instruments"]), 1)
        self.assertEqual(merged["instruments"][0]["name"], "Correct Name")
        self.assertEqual(merged["registry_sync_updated_count"], 1)


if __name__ == "__main__":
    unittest.main()
