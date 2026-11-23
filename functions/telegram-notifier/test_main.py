"""Unit tests for the Telegram notifier (stdlib unittest only, no network)."""

from __future__ import annotations

import base64
import json
import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Stub third-party modules so the tests run without installing anything.
_ff = types.ModuleType("functions_framework")
_ff.cloud_event = lambda func: func
sys.modules.setdefault("functions_framework", _ff)

if "requests" not in sys.modules:
    _requests = types.ModuleType("requests")

    class RequestException(Exception):
        """Stub of requests.RequestException."""

    _requests.RequestException = RequestException
    _requests.get = mock.MagicMock(name="requests.get")
    _requests.post = mock.MagicMock(name="requests.post")
    sys.modules["requests"] = _requests

import main  # noqa: E402

BOT_TOKEN = "123456:FAKE-BOT-TOKEN-xyz"
BB_TOKEN = "FAKE-BITBUCKET-REPO-TOKEN-abc"
SHA = "0123456789abcdef0123456789abcdef01234567"

BASE_ENV = {
    "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
    "TELEGRAM_CHAT_ID": "-1001234567890",
    "BITBUCKET_ACCESS_TOKEN": BB_TOKEN,
    "BITBUCKET_WORKSPACE": "example-workspace",
    "BITBUCKET_REPO_SLUG": "example-repo",
    "TARGET_TRIGGER_NAMES": "",
}


def make_data(status: str = "SUCCESS", trigger: str = "deploy-main", log_url: str = "https://example.com/log") -> dict:
    build = {"status": status, "substitutions": {"TRIGGER_NAME": trigger, "COMMIT_SHA": SHA}}
    if log_url:
        build["logUrl"] = log_url
    return {"message": {"data": base64.b64encode(json.dumps(build).encode()).decode()}}


def make_response(status_code: int = 200, payload: object = None) -> mock.Mock:
    response = mock.Mock(status_code=status_code)
    response.json.return_value = payload if payload is not None else {}
    return response


class ParseBuildEventTest(unittest.TestCase):
    def test_decodes_base64_payload(self) -> None:
        event = main.parse_build_event(make_data("WORKING", "build-pr"))
        self.assertEqual(event, main.BuildEvent("WORKING", "build-pr", SHA, "https://example.com/log"))

    def test_invalid_payload_returns_none(self) -> None:
        with self.assertLogs(main.logger, "ERROR"):
            self.assertIsNone(main.parse_build_event({"message": {"data": "%%%not-base64"}}))
            self.assertIsNone(main.parse_build_event({}))


class LoadConfigTest(unittest.TestCase):
    def test_missing_required_config(self) -> None:
        with self.assertLogs(main.logger, "ERROR") as logs:
            self.assertIsNone(main.load_config({"TELEGRAM_CHAT_ID": "1"}))
        self.assertIn("TELEGRAM_BOT_TOKEN", logs.output[0])

    def test_trigger_list_parsing(self) -> None:
        config = main.load_config({**BASE_ENV, "TARGET_TRIGGER_NAMES": " a, b ,,c "})
        self.assertEqual(config.target_trigger_names, frozenset({"a", "b", "c"}))

    def test_reads_environment_at_call_time(self) -> None:
        with mock.patch.dict(os.environ, BASE_ENV, clear=True):
            self.assertEqual(main.load_config().telegram_chat_id, "-1001234567890")


class ShouldNotifyTest(unittest.TestCase):
    def test_empty_filter_means_all_triggers(self) -> None:
        event = main.parse_build_event(make_data(trigger="anything"))
        self.assertTrue(main.should_notify(event, frozenset()))

    def test_filter_matches_only_listed_triggers(self) -> None:
        event = main.parse_build_event(make_data(trigger="other"))
        self.assertFalse(main.should_notify(event, frozenset({"deploy-main"})))
        self.assertTrue(main.should_notify(event, frozenset({"deploy-main", "other"})))

    def test_irrelevant_status_is_ignored(self) -> None:
        event = main.parse_build_event(make_data(status="STATUS_UNKNOWN"))
        self.assertFalse(main.should_notify(event, frozenset()))


class FormatMessageTest(unittest.TestCase):
    def test_running(self) -> None:
        text = main.format_message(main.parse_build_event(make_data("WORKING")), "feat: add thing\n\nbody")
        self.assertIn("running", text)
        self.assertIn("Trigger: deploy-main", text)
        self.assertIn("Commit: feat: add thing", text)
        self.assertNotIn("body", text)
        self.assertIn(f"SHA: {SHA[:7]}", text)
        self.assertIn("Logs: https://example.com/log", text)

    def test_success(self) -> None:
        text = main.format_message(main.parse_build_event(make_data("SUCCESS")), "fix: bug")
        self.assertIn("success", text)
        self.assertIn("SUCCESS", text)

    def test_failure_without_log_url(self) -> None:
        text = main.format_message(main.parse_build_event(make_data("FAILURE", log_url="")), "")
        self.assertIn("failure", text)
        self.assertIn(main.COMMIT_MESSAGE_FALLBACK, text)
        self.assertNotIn("Logs:", text)


class GetCommitMessageTest(unittest.TestCase):
    def test_success_uses_bearer_token(self) -> None:
        config = main.load_config(BASE_ENV)
        with mock.patch.object(main.requests, "get", return_value=make_response(200, {"message": "feat: x"})) as get:
            self.assertEqual(main.get_commit_message(config, SHA), "feat: x")
        _, kwargs = get.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {BB_TOKEN}")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertIn(f"example-workspace/example-repo/commit/{SHA}", get.call_args[0][0])

    def test_missing_token_falls_back_without_request(self) -> None:
        config = main.load_config({**BASE_ENV, "BITBUCKET_ACCESS_TOKEN": ""})
        with mock.patch.object(main.requests, "get") as get:
            self.assertEqual(main.get_commit_message(config, SHA), main.COMMIT_MESSAGE_FALLBACK)
        get.assert_not_called()

    def test_http_error_falls_back(self) -> None:
        config = main.load_config(BASE_ENV)
        with mock.patch.object(main.requests, "get", return_value=make_response(401)):
            with self.assertLogs(main.logger, "WARNING"):
                self.assertEqual(main.get_commit_message(config, SHA), main.COMMIT_MESSAGE_FALLBACK)

    def test_network_error_falls_back(self) -> None:
        config = main.load_config(BASE_ENV)
        with mock.patch.object(main.requests, "get", side_effect=main.requests.RequestException("boom")):
            with self.assertLogs(main.logger, "WARNING"):
                self.assertEqual(main.get_commit_message(config, SHA), main.COMMIT_MESSAGE_FALLBACK)


class EntryPointTest(unittest.TestCase):
    def run_entry(self, env: dict, data: dict, post_response: mock.Mock | None = None, get_response: mock.Mock | None = None):
        cloud_event = mock.Mock(data=data)
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(main.requests, "get", return_value=get_response or make_response(200, {"message": "feat: x"})) as get, \
                mock.patch.object(main.requests, "post", return_value=post_response or make_response(200)) as post, \
                self.assertLogs(main.logger, "DEBUG") as logs:
            main.logger.debug("start")
            main.cloud_build_pubsub(cloud_event)
        return get, post, "\n".join(logs.output)

    def test_sends_json_body_to_telegram(self) -> None:
        _, post, _ = self.run_entry(BASE_ENV, make_data("SUCCESS"))
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertTrue(args[0].endswith("/sendMessage"))
        self.assertEqual(kwargs["json"]["chat_id"], "-1001234567890")
        self.assertIn("feat: x", kwargs["json"]["text"])
        self.assertEqual(kwargs["timeout"], 10)
        self.assertNotIn("params", kwargs)

    def test_missing_config_does_not_raise_or_send(self) -> None:
        _, post, logs = self.run_entry({"TELEGRAM_CHAT_ID": "1"}, make_data())
        post.assert_not_called()
        self.assertIn("Missing required configuration", logs)

    def test_unwatched_trigger_is_skipped(self) -> None:
        _, post, _ = self.run_entry({**BASE_ENV, "TARGET_TRIGGER_NAMES": "only-this"}, make_data(trigger="other"))
        post.assert_not_called()

    def test_no_secrets_in_logs(self) -> None:
        for get_resp, post_resp in (
            (make_response(200, {"message": "feat: x"}), make_response(200)),
            (make_response(403), make_response(401)),
        ):
            _, _, logs = self.run_entry(BASE_ENV, make_data(), post_resp, get_resp)
            self.assertNotIn(BOT_TOKEN, logs)
            self.assertNotIn(BB_TOKEN, logs)
            self.assertNotIn("api.telegram.org", logs)

    def test_telegram_network_error_does_not_raise(self) -> None:
        cloud_event = mock.Mock(data=make_data())
        with mock.patch.dict(os.environ, {**BASE_ENV, "BITBUCKET_ACCESS_TOKEN": ""}, clear=True), \
                mock.patch.object(main.requests, "post", side_effect=main.requests.RequestException(BOT_TOKEN)), \
                self.assertLogs(main.logger, "ERROR") as logs:
            main.cloud_build_pubsub(cloud_event)
        self.assertNotIn(BOT_TOKEN, "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
