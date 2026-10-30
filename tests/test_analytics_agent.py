import unittest

from analytics_agent import AnalyticsAgent, aggregate_metric, detect_anomalies, profile_dataset


ROWS = [
    {"date": "2025-01-01", "region": "East", "channel": "web", "orders": "10", "revenue": "100.00"},
    {"date": "2025-01-02", "region": "West", "channel": "direct", "orders": "20", "revenue": "200.00"},
    {"date": "2025-02-01", "region": "East", "channel": "web", "orders": "15", "revenue": "150.00"},
]


class AnalyticsAgentTests(unittest.TestCase):
    def test_profile_reports_shape(self):
        profile = profile_dataset(ROWS)
        self.assertEqual(profile["rows"], 3)
        self.assertEqual(profile["missing_values"]["region"], 0)

    def test_aggregate_by_region(self):
        result = aggregate_metric(ROWS, "revenue", "region")
        self.assertEqual(result[0], {"region": "East", "revenue": 250.0})

    def test_aggregate_by_month(self):
        result = aggregate_metric(ROWS, "orders", "month")
        self.assertEqual(result[0]["orders"], 30.0)

    def test_invalid_metric_is_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_metric(ROWS, "profit", "region")

    def test_constant_values_have_no_anomalies(self):
        rows = [{**row, "revenue": "10"} for row in ROWS]
        self.assertEqual(detect_anomalies(rows), [])

    def test_guardrail_blocks_side_effects(self):
        result = AnalyticsAgent(ROWS).run("Delete and email this dataset")
        self.assertEqual(result.status, "blocked")
        self.assertIsNone(result.tool_call)

    def test_empty_question_is_blocked(self):
        self.assertEqual(AnalyticsAgent(ROWS).run(" ").status, "blocked")

    def test_agent_selects_profile_tool(self):
        result = AnalyticsAgent(ROWS).run("Profile the columns and missing values")
        self.assertEqual(result.tool_call.name, "profile_dataset")

    def test_agent_selects_anomaly_tool(self):
        result = AnalyticsAgent(ROWS).run("Find unusual revenue rows")
        self.assertEqual(result.tool_call.name, "detect_anomalies")

    def test_result_has_audit_trace(self):
        result = AnalyticsAgent(ROWS).run("Compare revenue by region").to_dict()
        self.assertEqual(result["trace"][-1]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
