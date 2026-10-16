"""Environment-only application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from .utils import debug


@dataclass(frozen=True)
class Settings:
    public_base_url: str
    work_root: Path
    checks_repository_url: str
    maximum_parallel_tests: int
    git_timeout_seconds: int
    default_test_timeout_seconds: int
    azure_account_url: str
    azure_container: str
    excel_rows_per_sheet: int
    excel_findings_per_file: int
    json_findings_per_file: int
    git_token: str | None


def required_environment(name: str) -> str:
    debug(f"environment lookup started name={name}")
    value = os.getenv(name, "").strip()

    if not value:
        debug(f"environment lookup failed name={name}")
        raise RuntimeError(
            f"Required environment variable is not set: {name}"
        )

    debug(f"environment lookup completed name={name}")
    return value


def positive_integer(name: str, default: int) -> int:
    debug(f"integer setting lookup started name={name} default={default}")
    raw_value = os.getenv(name, str(default))

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            f"{name} must be an integer. Received: {raw_value}"
        ) from exc

    if value < 1:
        raise RuntimeError(
            f"{name} must be greater than zero"
        )

    debug(f"integer setting lookup completed name={name} value={value}")
    return value


def load_settings() -> Settings:
    debug("settings load started")
    value=Settings(
        public_base_url=os.getenv(
            "CSTOOL_PUBLIC_BASE_URL",
            "http://localhost:8000",
        ).rstrip("/"),

        work_root=Path(
            os.getenv(
                "CSTOOL_WORK_ROOT",
                "./data/workspaces",
            )
        ).resolve(),

        checks_repository_url=required_environment(
            "CSTOOL_CHECKS_REPOSITORY_URL"
        ),

        maximum_parallel_tests=positive_integer(
            "CSTOOL_MAX_PARALLEL_TESTS",
            4,
        ),

        git_timeout_seconds=positive_integer(
            "CSTOOL_GIT_TIMEOUT_SECONDS",
            300,
        ),

        default_test_timeout_seconds=positive_integer(
            "CSTOOL_TEST_TIMEOUT_SECONDS",
            300,
        ),

        azure_account_url=required_environment(
            "CSTOOL_AZURE_ACCOUNT_URL"
        ).rstrip("/"),

        azure_container=os.getenv(
            "CSTOOL_AZURE_CONTAINER",
            "code-standards-results",
        ),

        excel_rows_per_sheet=min(
            positive_integer(
                "CSTOOL_EXCEL_ROWS_PER_SHEET",
                900000,
            ),
            1048575,
        ),

        excel_findings_per_file=positive_integer(
            "CSTOOL_EXCEL_FINDINGS_PER_FILE",
            1800000,
        ),

        json_findings_per_file=positive_integer(
            "CSTOOL_JSON_FINDINGS_PER_FILE",
            250000,
        ),

        git_token=os.getenv("CSTOOL_GIT_TOKEN") or None,
    )
    debug(f"settings loaded work_root={value.work_root} max_parallel={value.maximum_parallel_tests} git_token_configured={bool(value.git_token)}")
    return value