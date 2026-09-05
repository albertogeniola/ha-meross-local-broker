"""Unit tests for timezone_utils (pure functions, no broker needed).

Run with: python3 -m unittest test_timezone_utils
"""
import unittest

from timezone_utils import build_time_rules, build_time_payload, needs_time_sync

# Independent oracle (not computed with the code under test):
# Europe/Rome switches to CEST on 2026-03-29 01:00 UTC and back to CET on 2026-10-25 01:00 UTC.
ROME_2026_DST_START = 1774746000
ROME_2026_DST_END = 1792890000
JAN_1_2026 = 1767225600  # 2026-01-01 00:00 UTC


class BuildTimeRulesTest(unittest.TestCase):
    def test_first_rule_is_next_dst_start_with_offset_and_dst_flag(self):
        rules = build_time_rules("Europe/Rome", start_ts=JAN_1_2026, years=1)
        self.assertEqual(rules[0], [ROME_2026_DST_START, 7200, 1])

    def test_second_rule_is_dst_end_back_to_standard_time(self):
        rules = build_time_rules("Europe/Rome", start_ts=JAN_1_2026, years=1)
        self.assertEqual(rules[1], [ROME_2026_DST_END, 3600, 0])

    def test_two_transitions_per_year_over_requested_horizon(self):
        rules = build_time_rules("Europe/Rome", start_ts=JAN_1_2026, years=3)
        self.assertEqual(len(rules), 6)
        self.assertEqual(rules, sorted(rules))

    def test_only_transitions_after_start_are_returned(self):
        after_dst_start = ROME_2026_DST_START + 3600
        rules = build_time_rules("Europe/Rome", start_ts=after_dst_start, years=1)
        self.assertEqual(rules[0], [ROME_2026_DST_END, 3600, 0])

    def test_timezone_without_dst_has_no_rules(self):
        self.assertEqual(build_time_rules("UTC", start_ts=JAN_1_2026, years=3), [])

    def test_unknown_timezone_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_time_rules("Mars/Olympus_Mons", start_ts=JAN_1_2026, years=1)


class BuildTimePayloadTest(unittest.TestCase):
    def test_payload_matches_appliance_system_time_format(self):
        payload = build_time_payload("Europe/Rome", now_ts=JAN_1_2026, years=1)
        self.assertEqual(payload["time"]["timestamp"], JAN_1_2026)
        self.assertEqual(payload["time"]["timezone"], "Europe/Rome")
        self.assertEqual(payload["time"]["timeRule"][0], [ROME_2026_DST_START, 7200, 1])


class NeedsTimeSyncTest(unittest.TestCase):
    def test_empty_timezone_needs_sync(self):
        self.assertTrue(needs_time_sync({"timestamp": 1, "timezone": "", "timeRule": []}, "Europe/Rome"))

    def test_missing_time_section_needs_sync(self):
        self.assertTrue(needs_time_sync(None, "Europe/Rome"))

    def test_same_timezone_does_not_need_sync(self):
        self.assertFalse(needs_time_sync({"timezone": "Europe/Rome", "timeRule": [[1, 2, 3]]}, "Europe/Rome"))

    def test_different_timezone_needs_sync(self):
        self.assertTrue(needs_time_sync({"timezone": "Europe/Zurich", "timeRule": [[1, 2, 3]]}, "Europe/Rome"))

    def test_no_configured_timezone_never_syncs(self):
        self.assertFalse(needs_time_sync({"timezone": "", "timeRule": []}, None))
        self.assertFalse(needs_time_sync({"timezone": "", "timeRule": []}, ""))


if __name__ == "__main__":
    unittest.main()
