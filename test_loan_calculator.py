import logging
import re
import pytest
from playwright.sync_api import Page, expect

from pathlib import Path
#URL = "loan-calculator.html"  # or your local file:// path
URL = f"file://{Path(__file__).parent / 'loan-calculator.html'}"

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def go(page: Page):
    logger.info("Navigating to %s", URL)
    page.goto(URL)
    page.wait_for_selector('[data-testid="emi-value"]')


def to_number(text: str) -> float:
    return float(re.sub(r"[₹,]", "", text))


def test_emi_calculates_on_load(page: Page):
    logger.info("Checking EMI/interest/total render a value on load")
    expect(page.locator('[data-testid="emi-value"]')).not_to_have_text("–")
    expect(page.locator('[data-testid="interest-value"]')).not_to_have_text("–")
    expect(page.locator('[data-testid="total-value"]')).not_to_have_text("–")


def test_changing_loan_amount_updates_emi(page: Page):
    before = to_number(page.locator('[data-testid="emi-value"]').inner_text())
    logger.info("EMI before amount change: %.2f", before)

    page.locator('[data-testid="amt-input"]').fill("5000000")
    page.locator('[data-testid="amt-input"]').dispatch_event("input")

    after = to_number(page.locator('[data-testid="emi-value"]').inner_text())
    logger.info("EMI after amount change to 5,000,000: %.2f", after)
    assert after > before


def test_emi_matches_formula(page: Page):
    page.locator('[data-testid="amt-input"]').fill("1000000")
    page.locator('[data-testid="amt-input"]').dispatch_event("input")
    page.locator('[data-testid="rate-input"]').fill("9")
    page.locator('[data-testid="rate-input"]').dispatch_event("input")
    page.locator('[data-testid="yrs-input"]').fill("10")
    page.locator('[data-testid="yrs-input"]').dispatch_event("input")

    P, annual, years = 1_000_000, 9, 10
    r, n = annual / 1200, years * 12
    expected_emi = P * r * (1 + r) ** n / ((1 + r) ** n - 1)

    shown_emi = to_number(page.locator('[data-testid="emi-value"]').inner_text())
    logger.info(
        "P=%s rate=%s%% years=%s -> expected EMI=%.2f, shown EMI=%.2f",
        P, annual, years, expected_emi, shown_emi,
    )
    assert shown_emi == pytest.approx(expected_emi, rel=0.01)


def test_year_tabs_filter_schedule(page: Page):
    logger.info("Clicking Year 2 tab and checking schedule filters to months 13-24")
    page.locator('[data-testid="year-tab-2"]').click()
    expect(page.locator('[data-testid="year-tab-2"]')).to_have_class(re.compile("active"))
    expect(page.locator('[data-testid="row-month-13"]')).to_be_visible()
    expect(page.locator('[data-testid="row-month-1"]')).to_have_count(0)


def test_schedule_row_count_matches_year(page: Page):
    page.locator('[data-testid="year-tab-1"]').click()
    rows = page.locator('[data-testid="schedule-body"] tr')
    logger.info("Year 1 schedule row count: %d (expected 12)", rows.count())
    expect(rows).to_have_count(12)


def test_balance_decreases_to_near_zero_at_end(page: Page):
    page.locator('[data-testid="yrs-input"]').fill("1")
    page.locator('[data-testid="yrs-input"]').dispatch_event("input")

    last_row = page.locator('[data-testid="row-month-12"] td').nth(4)
    balance = to_number(last_row.inner_text())
    logger.info("Final balance for a 1-year loan at month 12: %.2f", balance)
    assert balance < 100
