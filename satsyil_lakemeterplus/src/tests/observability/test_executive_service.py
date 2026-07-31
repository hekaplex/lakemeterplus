"""Unit tests for the pure-logic pieces of ExecutiveService
(app/observability/services/executive_service.py) — the largest, most
logic-heavy file in the observability module (1,055 lines) after
cost_service.py, and previously at zero test coverage. Covers
`_contract_year_start()` (the Aug 1 - Jul 31 fiscal-year boundary math
behind the executive dashboard's annual spend forecast — exactly the kind
of date-boundary logic prone to off-by-one bugs) and `_safe_future()` (the
error-swallowing helper used to keep one failed parallel fetch from
breaking the whole executive scorecard). Does not cover the SQL-fetching
methods themselves — see docs/TODO.md for what's still untested.
"""
import datetime

import pytest

from app.observability.services.executive_service import ExecutiveService, _safe_future


class TestContractYearStart:
    def test_date_in_august_starts_that_years_contract(self):
        assert ExecutiveService._contract_year_start(datetime.date(2026, 8, 1)) == datetime.date(2026, 8, 1)

    def test_date_in_december_stays_in_same_contract_year(self):
        assert ExecutiveService._contract_year_start(datetime.date(2026, 12, 15)) == datetime.date(2026, 8, 1)

    def test_date_in_january_belongs_to_prior_years_contract(self):
        assert ExecutiveService._contract_year_start(datetime.date(2027, 1, 15)) == datetime.date(2026, 8, 1)

    def test_date_in_july_is_the_last_month_of_prior_contract_year(self):
        assert ExecutiveService._contract_year_start(datetime.date(2027, 7, 31)) == datetime.date(2026, 8, 1)

    def test_boundary_july_to_august_transition(self):
        # July 31 and August 1 of the same calendar year must fall into
        # *different* contract years — this is the exact boundary a
        # month->quarter-style off-by-one bug would get wrong.
        july_31 = ExecutiveService._contract_year_start(datetime.date(2026, 7, 31))
        aug_1 = ExecutiveService._contract_year_start(datetime.date(2026, 8, 1))
        assert july_31 == datetime.date(2025, 8, 1)
        assert aug_1 == datetime.date(2026, 8, 1)
        assert july_31 != aug_1


class TestSafeFuture:
    class _FakeFuture:
        def __init__(self, value=None, exc=None):
            self._value = value
            self._exc = exc

        def result(self):
            if self._exc:
                raise self._exc
            return self._value

    def test_returns_result_on_success(self):
        assert _safe_future(self._FakeFuture(value={"cost": 100})) == {"cost": 100}

    def test_returns_empty_list_default_on_exception(self):
        assert _safe_future(self._FakeFuture(exc=RuntimeError("boom"))) == []

    def test_returns_explicit_default_on_exception(self):
        assert _safe_future(self._FakeFuture(exc=RuntimeError("boom")), default={}) == {}

    def test_does_not_swallow_success_even_with_falsy_result(self):
        # A falsy-but-valid result (0, [], {}) must be returned as-is, not
        # replaced by the default — only an actual exception should do that.
        assert _safe_future(self._FakeFuture(value=0)) == 0
        assert _safe_future(self._FakeFuture(value=[])) == []
