"""
Unit tests for NVIDIA Free Endpoint Monitor safety guards and override behavior.
"""

import io
import unittest
from unittest.mock import patch

from src.monitor import (
    MAX_DROP_RATIO,
    MIN_VALID_MODEL_COUNT,
    compare_models,
    main,
    parse_args,
)


def _make_models(count: int, prefix: str = "vendor/model") -> list[dict]:
    return [
        {"id": f"{prefix}-{i:03d}", "owned_by": "vendor", "created": 1700000000}
        for i in range(count)
    ]


class TestMonitorSafetyGuards(unittest.TestCase):
    """Tests for MIN_VALID_MODEL_COUNT, MAX_DROP_RATIO, and --allow-large-drop override."""

    def test_01_min_valid_model_count_blocks_even_with_override(self):
        """1. Responses below MIN_VALID_MODEL_COUNT are always blocked, even when allow_large_drop=True."""
        self.assertEqual(MIN_VALID_MODEL_COUNT, 20)
        too_few = _make_models(MIN_VALID_MODEL_COUNT - 1)
        baseline = {"checked_at": "2026-11-12T17:05:21Z", "models": _make_models(33)}

        with self.assertRaises(RuntimeError) as ctx_default:
            compare_models(baseline, too_few, allow_large_drop=False)
        self.assertIn("below the minimum threshold", str(ctx_default.exception))

        with self.assertRaises(RuntimeError) as ctx_override:
            compare_models(baseline, too_few, allow_large_drop=True)
        self.assertIn("below the minimum threshold", str(ctx_override.exception))

    def test_02_stable_33_models_passes_without_error(self):
        """2. A steady catalog of 33 models passes safety guards cleanly."""
        models_33 = _make_models(33)
        baseline = {"checked_at": "2026-11-16T10:00:00Z", "models": models_33}

        diff = compare_models(baseline, models_33)
        self.assertFalse(diff["has_changes"])
        self.assertEqual(diff["current_count"], 33)
        self.assertEqual(diff["previous_count"], 33)
        self.assertEqual(diff["added"], [])
        self.assertEqual(diff["removed"], [])

    def test_03_large_drop_blocked_by_default(self):
        """3. Dropping from 83 to 33 models (>50%) raises Safety Guard error by default."""
        baseline = {"checked_at": "2026-11-12T17:05:21Z", "models": _make_models(83)}
        current_33 = _make_models(33)

        self.assertGreater(50 / 83, MAX_DROP_RATIO)
        with self.assertRaises(RuntimeError) as ctx:
            compare_models(baseline, current_33)
        self.assertIn("Safety Guard Triggered", str(ctx.exception))
        self.assertIn("50/83", str(ctx.exception))

    def test_04_large_drop_allowed_when_override_enabled(self):
        """4. allow_large_drop=True permits verified >50% drop and reports exact added/removed."""
        baseline = {"checked_at": "2026-11-12T17:05:21Z", "models": _make_models(83)}
        current_33 = _make_models(33)

        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            diff = compare_models(baseline, current_33, allow_large_drop=True)
            out_text = fake_out.getvalue()

        self.assertTrue(diff["has_changes"])
        self.assertEqual(diff["previous_count"], 83)
        self.assertEqual(diff["current_count"], 33)
        self.assertEqual(diff["added"], [])
        self.assertEqual(len(diff["removed"]), 50)
        self.assertIn("Large drop override enabled", out_text)

    def test_05_parse_args_allow_large_drop_flag(self):
        """5. CLI parser defaults allow_large_drop to False and enables it with --allow-large-drop."""
        self.assertFalse(parse_args([]).allow_large_drop)
        self.assertTrue(parse_args(["--allow-large-drop"]).allow_large_drop)

    def test_06_main_respects_override_and_default_guard(self):
        """6. main() blocks write/notify on large drop without flag, and updates when flag is passed."""
        payload_33 = {
            "object": "list",
            "data": _make_models(33),
        }
        baseline_83 = {"checked_at": "2026-11-12T17:05:21Z", "models": _make_models(83)}

        with (
            patch("src.monitor.fetch_models", return_value=payload_33),
            patch("src.monitor.load_baseline", return_value=baseline_83),
            patch("src.monitor.save_baseline") as mock_save,
            patch("src.monitor.send_telegram_notification") as mock_notify,
        ):
            with self.assertRaises(RuntimeError):
                main([])
            mock_save.assert_not_called()
            mock_notify.assert_not_called()

            with patch("sys.stdout", new=io.StringIO()):
                main(["--allow-large-drop"])
            mock_save.assert_called_once()
            mock_notify.assert_called_once()


if __name__ == "__main__":
    unittest.main()
