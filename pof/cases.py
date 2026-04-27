"""Registry of real-world forensic cases for investigation.

Each case contains the publicly known Bitcoin addresses, a brief description,
and links to the primary sources (DOJ press releases, court filings, etc.).
These are used by the case-study notebook and the dashboard to run reproducible
investigations on actual criminal activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Case:
    name: str
    slug: str
    description: str
    date: date
    seed_addresses: list[str] = field(default_factory=list)
    category: str = ""
    abuse: str = ""
    expected_severity: float = 1.0
    sources: list[str] = field(default_factory=list)


CASES: dict[str, Case] = {
    "wannacry": Case(
        name="WannaCry Ransomware",
        slug="wannacry",
        description=(
            "WannaCry was a worldwide ransomware attack in May 2017 that "
            "exploited the EternalBlue vulnerability. The malware hardcoded "
            "three BTC payment addresses. Attributed to the Lazarus Group "
            "(North Korea) by the US, UK, and others."
        ),
        date=date(2017, 5, 12),
        seed_addresses=[
            "12t9YDPgwueZ9NyMgw519p7AA8isjr6SMw",
            "13AM4VW2dhxYgXeQepoHkHSQuy6NgaEb94",
            "115p7UMMngoj1pMvkpHijcRdfJNXj6LrLn",
        ],
        category="ransomware",
        abuse="ransomware",
        expected_severity=1.0,
        sources=[
            "https://en.wikipedia.org/wiki/WannaCry_ransomware_attack",
            "https://www.justice.gov/opa/pr/north-korean-regime-backed-programmer-charged-conspiracy-conduct-multiple-cyber-attacks-and",
        ],
    ),
    "twitter_hack": Case(
        name="Twitter Hack (2020)",
        slug="twitter_hack",
        description=(
            "On July 15, 2020, attackers compromised high-profile Twitter "
            "accounts (Obama, Musk, Apple) and posted a BTC doubling scam. "
            "~$120k in BTC was collected. Perpetrators were identified and "
            "arrested within weeks."
        ),
        date=date(2020, 7, 15),
        seed_addresses=[
            "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "bc1q0kznuxzk6d82e27p7gplwl68zkv40swyy4d24x",
            "bc1qwr30ddc04zqp878c0evdrqfx564mmf0dy2w39l",
        ],
        category="scam",
        abuse="scam",
        expected_severity=0.8,
        sources=[
            "https://www.justice.gov/opa/press-release/file/1300261/download",
            "https://en.wikipedia.org/wiki/2020_Twitter_account_hijacking",
        ],
    ),
    "colonial_pipeline": Case(
        name="Colonial Pipeline / DarkSide (2021)",
        slug="colonial_pipeline",
        description=(
            "In May 2021, the DarkSide ransomware group attacked Colonial "
            "Pipeline, causing fuel shortages across the US East Coast. "
            "Colonial paid ~75 BTC (~$4.4M). The DOJ later recovered ~63.7 "
            "BTC by tracing and seizing funds."
        ),
        date=date(2021, 5, 7),
        seed_addresses=[
            "bc1qq2euq8pw950klpjcawuy4uj39ym43hs6cfsegq",
        ],
        category="ransomware",
        abuse="ransomware",
        expected_severity=1.0,
        sources=[
            "https://www.justice.gov/opa/pr/department-justice-seizes-23-million-cryptocurrency-paid-ransomware-extortionists-darkside",
            "https://www.elliptic.co/blog/us-authorities-seize-darkside",
        ],
    ),
    "bitfinex_hack": Case(
        name="Bitfinex Hack (2016)",
        slug="bitfinex_hack",
        description=(
            "In August 2016, ~119,756 BTC were stolen from the Bitfinex "
            "exchange. The funds were laundered through thousands of "
            "transactions over several years. In February 2022, Ilya "
            "Lichtenstein and Heather Morgan were arrested and ~94,000 BTC "
            "were seized — the largest financial seizure in DOJ history."
        ),
        date=date(2016, 8, 2),
        seed_addresses=[
            "16t35Fhe2HqKN5XT2ocEd9Fe3eKm5UhRcm",
            "1Hy1rceh2EaKnAQhGZocTFUGnKFFD3mNG5",
        ],
        category="service_hack",
        abuse="service_hack",
        expected_severity=0.85,
        sources=[
            "https://www.justice.gov/opa/pr/two-arrested-alleged-conspiracy-launder-45-billion-stolen-cryptocurrency",
            "https://www.chainalysis.com/blog/bitfinex-hack-seizure-arrest-2022/",
        ],
    ),
}


def get_case(slug: str) -> Case:
    """Return a case by slug, raising KeyError if not found."""
    return CASES[slug]


def list_cases() -> list[str]:
    """Return all registered case slugs."""
    return list(CASES.keys())


def all_seed_addresses() -> list[str]:
    """Return a flat list of all seed addresses across all cases."""
    addrs: list[str] = []
    for case in CASES.values():
        addrs.extend(case.seed_addresses)
    return addrs
