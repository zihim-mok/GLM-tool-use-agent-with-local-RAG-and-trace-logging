"""finance_tools 单元测试。"""
from finance_tools import cagr, compound_interest, loan_monthly_payment, sharpe_ratio, max_drawdown, bond_yield_estimate


def test_compound_interest():
    r = compound_interest(10000, 3, 5, 12)
    assert "error" not in r
    assert r["future_value"] > 10000
    assert r["principal"] == 10000


def test_loan_monthly_payment():
    r = loan_monthly_payment(800000, 4.5, 360)
    assert "error" not in r
    assert r["monthly_payment"] > 0
    assert r["months"] == 360


def test_cagr():
    r = cagr(100, 150, 3)
    assert "error" not in r
    assert r["cagr_pct"] > 0


def test_sharpe_ratio():
    r = sharpe_ratio([0.01, 0.02, -0.01, 0.015], 0.0)
    assert "error" not in r
    assert "sharpe_ratio" in r


def test_max_drawdown():
    r = max_drawdown([100, 110, 95, 105, 80])
    assert "error" not in r
    assert r["max_drawdown_pct"] > 0


def test_bond_yield_estimate():
    r = bond_yield_estimate(100, 95, 5, 3)
    assert "error" not in r
    assert r["ytm_pct"] > 0
