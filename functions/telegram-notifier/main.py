"""Cloud Function (2nd gen) that relays Cloud Build status changes to Telegram.

Triggered by the ``cloud-builds`` Pub/Sub topic. Configuration comes entirely
from environment variables, read at invocation time (never at import time).
"""

from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Mapping, Optional

import functions_framework
import requests

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SECONDS = 10
BITBUCKET_API_URL = "https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/commit/{sha}"
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
COMMIT_MESSAGE_FALLBACK = "commit message unavailable"

RUNNING_STATUSES = frozenset({"QUEUED", "WORKING"})
FINAL_STATUSES = frozenset({"SUCCESS", "FAILURE", "TIMEOUT", "CANCELLED", "INTERNAL_ERROR"})
STATUS_ICONS = {
    "QUEUED": "⏳",
    "WORKING": "🔄",
    "SUCCESS": "✅",
    "FAILURE": "❌",
    "TIMEOUT": "⌛",
    "CANCELLED": "🚫",
    "INTERNAL_ERROR": "⚠️",
}


@dataclass(frozen=True)
class Config:
    """Runtime configuration loaded from environment variables."""

    telegram_bot_token: str
    telegram_chat_id: str
    bitbucket_access_token: str
    bitbucket_workspace: str
    bitbucket_repo_slug: str
    target_trigger_names: frozenset[str]


@dataclass(frozen=True)
class BuildEvent:
    """Fields of a Cloud Build notification relevant to the notifier."""

    status: str
    trigger_name: str
    commit_sha: str
    log_url: str


def load_config(env: Optional[Mapping[str, str]] = None) -> Optional[Config]:
    """Build a Config from the environment; return None if required values are missing."""
    env = os.environ if env is None else env
    missing = [name for name in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID") if not env.get(name, "").strip()]
    if missing:
        logger.error("Missing required configuration: %s", ", ".join(missing))
        return None
    triggers = frozenset(t.strip() for t in env.get("TARGET_TRIGGER_NAMES", "").split(",") if t.strip())
    return Config(
        telegram_bot_token=env["TELEGRAM_BOT_TOKEN"].strip(),
        telegram_chat_id=env["TELEGRAM_CHAT_ID"].strip(),
        bitbucket_access_token=env.get("BITBUCKET_ACCESS_TOKEN", "").strip(),
        bitbucket_workspace=env.get("BITBUCKET_WORKSPACE", "").strip(),
        bitbucket_repo_slug=env.get("BITBUCKET_REPO_SLUG", "").strip(),
        target_trigger_names=triggers,
    )


def parse_build_event(data: Mapping[str, Any]) -> Optional[BuildEvent]:
    """Decode the base64 Pub/Sub payload of a CloudEvent into a BuildEvent."""
    try:
        raw = base64.b64decode(data["message"]["data"]).decode("utf-8")
        build = json.loads(raw)
    except (KeyError, TypeError, ValueError) as exc:
        logger.error("Could not decode Pub/Sub message: %s", type(exc).__name__)
        return None
    if not isinstance(build, dict):
        logger.error("Unexpected Pub/Sub payload type: %s", type(build).__name__)
        return None
    substitutions = build.get("substitutions") or {}
    return BuildEvent(
        status=str(build.get("status", "")),
        trigger_name=str(substitutions.get("TRIGGER_NAME", "")),
        commit_sha=str(substitutions.get("COMMIT_SHA", "")),
        log_url=str(build.get("logUrl", "")),
    )


def should_notify(event: BuildEvent, target_trigger_names: frozenset[str]) -> bool:
    """Return True for relevant statuses of watched triggers (empty set = all triggers)."""
    if event.status not in RUNNING_STATUSES | FINAL_STATUSES:
        return False
    return not target_trigger_names or event.trigger_name in target_trigger_names


def format_message(event: BuildEvent, commit_message: str) -> str:
    """Render the Telegram message text for a build event."""
    state = "running" if event.status in RUNNING_STATUSES else event.status.lower()
    first_line = (commit_message or COMMIT_MESSAGE_FALLBACK).strip().splitlines()
    lines = [
        f"{STATUS_ICONS.get(event.status, '')} Build {state} ({event.status})".strip(),
        f"Trigger: {event.trigger_name or 'unknown'}",
        f"Commit: {first_line[0] if first_line else COMMIT_MESSAGE_FALLBACK}",
        f"SHA: {event.commit_sha[:7] or 'unknown'}",
    ]
    if event.log_url:
        lines.append(f"Logs: {event.log_url}")
    return "\n".join(lines)


def get_commit_message(config: Config, commit_sha: str) -> str:
    """Fetch the commit message from Bitbucket Cloud using a repository access token."""
    if not (config.bitbucket_access_token and config.bitbucket_workspace and config.bitbucket_repo_slug and commit_sha):
        logger.info("Bitbucket lookup skipped: token, workspace, repo slug or SHA not configured")
        return COMMIT_MESSAGE_FALLBACK
    url = BITBUCKET_API_URL.format(
        workspace=config.bitbucket_workspace, repo_slug=config.bitbucket_repo_slug, sha=commit_sha
    )
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {config.bitbucket_access_token}", "Accept": "application/json"},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.warning("Bitbucket request failed: %s", type(exc).__name__)
        return COMMIT_MESSAGE_FALLBACK
    if response.status_code != 200:
        logger.warning("Bitbucket returned HTTP %s for commit lookup", response.status_code)
        return COMMIT_MESSAGE_FALLBACK
    try:
        message = response.json().get("message")
    except (ValueError, AttributeError):
        logger.warning("Bitbucket returned an unparseable response")
        return COMMIT_MESSAGE_FALLBACK
    return message or COMMIT_MESSAGE_FALLBACK


def send_telegram_message(config: Config, text: str) -> bool:
    """Send a message via the Telegram Bot API; never logs the URL (it contains the token)."""
    url = TELEGRAM_API_URL.format(token=config.telegram_bot_token)
    try:
        response = requests.post(
            url, json={"chat_id": config.telegram_chat_id, "text": text}, timeout=HTTP_TIMEOUT_SECONDS
        )
    except requests.RequestException as exc:
        logger.error("Telegram request failed: %s", type(exc).__name__)
        return False
    if response.status_code != 200:
        logger.error("Telegram returned HTTP %s", response.status_code)
        return False
    return True


@functions_framework.cloud_event
def cloud_build_pubsub(cloud_event: Any) -> None:
    """Entry point: handle a Cloud Build notification from the cloud-builds topic."""
    config = load_config()
    if config is None:
        return
    event = parse_build_event(cloud_event.data)
    if event is None or not should_notify(event, config.target_trigger_names):
        return
    commit_message = get_commit_message(config, event.commit_sha)
    if send_telegram_message(config, format_message(event, commit_message)):
        logger.info("Notification sent for trigger %s (%s)", event.trigger_name, event.status)
