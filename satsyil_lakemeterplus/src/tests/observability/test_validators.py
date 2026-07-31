"""Unit tests for app/observability/core/validators.py — the primary
SQL-injection defense for the observability module (its SQL is built via
f-strings against the Databricks SDK's Statement Execution API, which has
no parameterized-query mechanism for identifiers; see
docs/architecture-databricks-cost-observability.md). This had zero test
coverage in the source repo (its only test is a black-box HTTP smoke
test) — these tests exist specifically to pin the injection-relevant
rejection behavior.
"""
import pytest

from app.observability.core import validators


class TestValidateSqlIdentifier:
    def test_accepts_normal_identifier(self):
        assert validators.validate_sql_identifier("my_catalog-1") == "my_catalog-1"

    @pytest.mark.parametrize("payload", [
        "table; DROP TABLE users;--",
        "table`; DROP TABLE users; --",
        "table' OR '1'='1",
        'table" OR "1"="1',
        "table with spaces",
        "",
        "a" * 256,  # over the 255-char limit
    ])
    def test_rejects_injection_attempts(self, payload):
        with pytest.raises(ValueError):
            validators.validate_sql_identifier(payload)

    def test_rejects_non_string(self):
        with pytest.raises(ValueError):
            validators.validate_sql_identifier(123)  # type: ignore[arg-type]


class TestEscapeTagValue:
    def test_escapes_single_quotes(self):
        assert validators.escape_tag_value("O'Brien") == "O''Brien"

    def test_rejects_control_characters(self):
        with pytest.raises(ValueError):
            validators.escape_tag_value("value\x00withnull")

    def test_rejects_oversized_value(self):
        with pytest.raises(ValueError):
            validators.escape_tag_value("x" * 257)


class TestValidateDate:
    def test_accepts_valid_recent_date(self):
        import datetime
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        assert validators.validate_date(yesterday) == yesterday

    @pytest.mark.parametrize("payload", [
        "not-a-date",
        "2026-13-01",  # invalid month
        "2026-02-30",  # invalid day
        "2026/01/01",  # wrong separator
        "'; DROP TABLE billing;--",
    ])
    def test_rejects_invalid_or_malicious_input(self, payload):
        with pytest.raises(ValueError):
            validators.validate_date(payload)

    def test_rejects_far_future_date(self):
        with pytest.raises(ValueError):
            validators.validate_date("2099-01-01")

    def test_rejects_far_past_date(self):
        with pytest.raises(ValueError):
            validators.validate_date("1900-01-01")


class TestValidateEmailAddress:
    def test_accepts_and_lowercases_valid_email(self):
        assert validators.validate_email_address("Alice@Example.COM") == "alice@example.com"

    @pytest.mark.parametrize("payload", [
        "not-an-email",
        "alice@",
        "@example.com",
        "alice@example",  # no TLD
        "alice@example.com\r\nBcc: evil@example.com",  # header injection attempt
        "12345@67890",  # SP-style ID, rejected by the stricter email validator
    ])
    def test_rejects_invalid_email(self, payload):
        with pytest.raises(ValueError):
            validators.validate_email_address(payload)


class TestValidateUserIdentity:
    def test_accepts_email(self):
        assert validators.validate_user_identity("Bob@Example.com") == "bob@example.com"

    def test_accepts_service_principal_style_id(self):
        assert validators.validate_user_identity("12345@67890") == "12345@67890"

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError):
            validators.validate_user_identity("")


class TestValidateThresholdPct:
    @pytest.mark.parametrize("value", [1.0, 20.0, 100.0])
    def test_accepts_in_range(self, value):
        assert validators.validate_threshold_pct(value) == value

    @pytest.mark.parametrize("value", [0.0, 0.5, 100.1, -5, "not-a-number"])
    def test_rejects_out_of_range_or_non_numeric(self, value):
        with pytest.raises(ValueError):
            validators.validate_threshold_pct(value)


class TestValidateTabList:
    def test_none_returns_empty_list(self):
        assert validators.validate_tab_list(None) == []

    def test_dedupes_and_lowercases_known_tabs(self):
        assert validators.validate_tab_list(["Cost", "cost", "Executive"]) == ["cost", "cost", "executive"]

    def test_rejects_unknown_tab(self):
        with pytest.raises(ValueError):
            validators.validate_tab_list(["not-a-real-tab"])

    def test_rejects_oversized_list(self):
        with pytest.raises(ValueError):
            validators.validate_tab_list(["cost"] * 51)


class TestValidateWorkspaceList:
    def test_none_returns_empty_list(self):
        assert validators.validate_workspace_list(None) == []

    def test_accepts_valid_ids(self):
        assert validators.validate_workspace_list(["ws-123", "ws_456"]) == ["ws-123", "ws_456"]

    def test_rejects_invalid_id(self):
        with pytest.raises(ValueError):
            validators.validate_workspace_list(["ws with spaces"])

    def test_rejects_oversized_list(self):
        with pytest.raises(ValueError):
            validators.validate_workspace_list(["ws-1"] * 201)
