"""
Unit tests for log sanitization and token redaction (S1.1 Security Fix)
"""

import io
import os
import unittest
from unittest.mock import patch

from src.monitor import sanitize_log_message, send_telegram_notification


class TestLogSanitization(unittest.TestCase):
    """Tests for defensive redaction of sensitive tokens in error logs."""

    def test_01_redact_telegram_bot_token_in_url(self):
        """1. Telegram bot token in full URL is replaced with ***REDACTED***."""
        raw_msg = "urllib.error.HTTPError: HTTP Error 401: Unauthorized for url: https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567/sendMessage"
        sanitized = sanitize_log_message(raw_msg)
        
        self.assertNotIn("123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567", sanitized)
        self.assertIn("https://api.telegram.org/bot***REDACTED***/sendMessage", sanitized)

    def test_02_redact_telegram_http_url_variant(self):
        """2. Handles http scheme variations and trailing paths."""
        raw_msg = "Failed to connect to http://api.telegram.org/bot987654321:XYZ123_abcDEF/getMe (Connection refused)"
        sanitized = sanitize_log_message(raw_msg)
        
        self.assertNotIn("987654321:XYZ123_abcDEF", sanitized)
        self.assertIn("http://api.telegram.org/bot***REDACTED***/getMe", sanitized)

    def test_03_preserve_non_sensitive_error_messages(self):
        """3. Standard network and runtime error messages remain unchanged and clear."""
        normal_msg = "urllib.error.URLError: <urlopen error [Errno 11001] getaddrinfo failed>"
        sanitized = sanitize_log_message(normal_msg)
        self.assertEqual(sanitized, normal_msg)

    def test_04_empty_and_falsy_inputs(self):
        """4. Falsy inputs return empty string without error."""
        self.assertEqual(sanitize_log_message(""), "")
        self.assertEqual(sanitize_log_message(None), "")

    def test_05_send_telegram_notification_exception_output_is_sanitized(self):
        """5. send_telegram_notification catches exception and prints sanitized error."""
        fake_token = "111222333:SECRET_TOKEN_VALUE_ABCXYZ12345"
        diff_with_changes = {
            "is_initial": False,
            "has_changes": True,
            "current_count": 100,
            "previous_count": 99,
            "added": ["meta/llama-3.3-70b-instruct"],
            "removed": [],
        }

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": fake_token, "TELEGRAM_CHAT_ID": "12345678"}):
            with patch("urllib.request.urlopen", side_effect=RuntimeError(f"Error on https://api.telegram.org/bot{fake_token}/sendMessage: Request failed")):
                with patch("sys.stdout", new=io.StringIO()) as fake_out:
                    send_telegram_notification(diff_with_changes, "2026-08-29T12:00:00Z")
                    output = fake_out.getvalue()
                    
                    self.assertNotIn(fake_token, output)
                    self.assertIn("bot***REDACTED***/sendMessage", output)
                    self.assertIn("[WARN] Failed to send Telegram notification", output)


if __name__ == "__main__":
    unittest.main()
