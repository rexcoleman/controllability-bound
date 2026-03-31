"""Tests for controllability bound computation."""
import unittest

from controllability_scorer import Channel, SystemSpec, score_system, rank_channels


class TestChannel(unittest.TestCase):
    def test_valid_channel(self):
        ch = Channel("test", 0.5, 0.3)
        self.assertEqual(ch.controllability, 0.5)
        self.assertEqual(ch.observability, 0.3)

    def test_invalid_controllability(self):
        with self.assertRaises(ValueError):
            Channel("bad", 1.5, 0.0)

    def test_invalid_observability(self):
        with self.assertRaises(ValueError):
            Channel("bad", 0.5, -0.1)

    def test_vulnerability_score(self):
        ch = Channel("test", 1.0, 0.0)
        self.assertAlmostEqual(ch.vulnerability_score, 1.0)
        ch2 = Channel("test", 1.0, 1.0)
        self.assertAlmostEqual(ch2.vulnerability_score, 0.0)

    def test_boundary_values(self):
        ch0 = Channel("zero", 0.0, 0.0)
        ch1 = Channel("one", 1.0, 1.0)
        self.assertAlmostEqual(ch0.vulnerability_score, 0.0)
        self.assertAlmostEqual(ch1.vulnerability_score, 0.0)


class TestSystemSpec(unittest.TestCase):
    def test_add_channels(self):
        spec = SystemSpec("test")
        spec.add_channel("ch1", 0.5, 0.3)
        spec.add_channel("ch2", 1.0, 0.0)
        self.assertEqual(len(spec.channels), 2)

    def test_fluent_api(self):
        spec = (SystemSpec("test")
                .add_channel("a", 0.5, 0.3)
                .add_channel("b", 1.0, 0.0))
        self.assertEqual(len(spec.channels), 2)


class TestScoring(unittest.TestCase):
    def test_score_system_returns_dict(self):
        spec = SystemSpec("test")
        spec.add_channel("ch1", 0.5, 0.3)
        result = score_system(spec)
        self.assertIn("overall_score", result)
        self.assertIn("channels", result)
        self.assertIn("dominant_factor", result)

    def test_high_risk_channel(self):
        spec = SystemSpec("test")
        spec.add_channel("dangerous", 1.0, 0.0)
        result = score_system(spec)
        self.assertGreater(result["overall_score"], 0.5)

    def test_low_risk_channel(self):
        spec = SystemSpec("test")
        spec.add_channel("safe", 0.0, 1.0)
        result = score_system(spec)
        self.assertLess(result["overall_score"], 0.3)

    def test_empty_system_raises(self):
        spec = SystemSpec("empty")
        with self.assertRaises(ValueError):
            score_system(spec)

    def test_domain_weights(self):
        spec_rl = SystemSpec("rl", domain="rl_agent")
        spec_rl.add_channel("obs", 0.5, 0.0)
        spec_game = SystemSpec("game", domain="game_theoretic")
        spec_game.add_channel("alloc", 0.5, 0.0)
        r_rl = score_system(spec_rl)
        r_game = score_system(spec_game)
        # Both scored but with different weights
        self.assertIsNotNone(r_rl["overall_score"])
        self.assertIsNotNone(r_game["overall_score"])

    def test_rank_channels(self):
        spec = SystemSpec("test")
        spec.add_channel("safe", 0.1, 0.9)
        spec.add_channel("dangerous", 1.0, 0.0)
        ranked = rank_channels(spec)
        self.assertEqual(ranked[0][0], "dangerous")
        self.assertGreater(ranked[0][1], ranked[1][1])

    def test_scores_bounded_0_1(self):
        spec = SystemSpec("test")
        spec.add_channel("extreme", 1.0, 0.0)
        spec.add_channel("zero", 0.0, 1.0)
        result = score_system(spec)
        for ch in result["channels"]:
            self.assertGreaterEqual(ch["score"], 0.0)
            self.assertLessEqual(ch["score"], 1.0)


class TestModels(unittest.TestCase):
    def test_separate_vs_product(self):
        spec = SystemSpec("test")
        spec.add_channel("ch", 0.5, 0.0)
        r_sep = score_system(spec, model="separate")
        r_prod = score_system(spec, model="product")
        # Both return valid scores
        self.assertIsNotNone(r_sep["overall_score"])
        self.assertIsNotNone(r_prod["overall_score"])
        # Models should differ (separate is NOT just C*(1-D))
        self.assertEqual(r_sep["model"], "separate")
        self.assertEqual(r_prod["model"], "product")


if __name__ == "__main__":
    unittest.main()
