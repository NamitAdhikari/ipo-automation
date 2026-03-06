"""Data models for election results."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ResultStatus(Enum):
    """Status of a candidate in election results."""

    WIN = "Win"
    LEAD = "Lead"
    UNKNOWN = "Unknown"


@dataclass
class PartyResult:
    """Party-wise aggregated results."""

    party_name: str
    win_count: int = 0
    lead_count: int = 0
    color: str = "#888888"  # Default gray color

    @property
    def total(self) -> int:
        """Total seats (wins + leads)."""
        return self.win_count + self.lead_count

    def __repr__(self) -> str:
        return (
            f"PartyResult({self.party_name}, W:{self.win_count}, L:{self.lead_count})"
        )


@dataclass
class ProvincePartyResult:
    """Province-wise party results."""

    province_name: str
    province_number: int
    party_name: str
    win_count: int = 0
    lead_count: int = 0
    color: str = "#888888"

    @property
    def total(self) -> int:
        """Total seats (wins + leads)."""
        return self.win_count + self.lead_count


@dataclass
class CandidateResult:
    """Individual candidate result."""

    rank: int
    party_name: str
    candidate_name: str
    votes: int
    status: ResultStatus
    color: str = "#888888"

    def __repr__(self) -> str:
        return f"CandidateResult({self.rank}. {self.candidate_name} ({self.party_name}): {self.votes} votes - {self.status.value})"


@dataclass
class ConstituencyResult:
    """Complete result for a constituency."""

    province_number: int
    province_name: str
    district_name: str
    constituency_number: int
    candidates: List[CandidateResult] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"ConstituencyResult({self.province_name}/{self.district_name}/Constituency-{self.constituency_number})"


@dataclass
class ElectionData:
    """Complete election data."""

    party_results: List[PartyResult] = field(default_factory=list)
    province_party_results: Dict[int, List[ProvincePartyResult]] = field(
        default_factory=dict
    )
    constituency_result: Optional[ConstituencyResult] = None
    last_updated: str = ""

    def get_party_color(self, party_name: str) -> str:
        """Get color for a party name."""
        for party in self.party_results:
            if party.party_name == party_name:
                return party.color
        return "#888888"

    def __repr__(self) -> str:
        return f"ElectionData(parties={len(self.party_results)}, last_updated={self.last_updated})"


@dataclass
class Location:
    """Selected location for navigation."""

    province_number: Optional[int] = None
    province_name: Optional[str] = None
    district_name: Optional[str] = None
    constituency_number: Optional[int] = None

    def is_complete(self) -> bool:
        """Check if all location components are selected."""
        return all(
            [
                self.province_number is not None,
                self.district_name is not None,
                self.constituency_number is not None,
            ]
        )

    def get_breadcrumb(self) -> str:
        """Generate breadcrumb string."""
        parts = ["Home"]
        if self.province_name:
            parts.append(f"Province {self.province_number} ({self.province_name})")
        if self.district_name:
            parts.append(self.district_name)
        if self.constituency_number is not None:
            parts.append(f"Constituency {self.constituency_number}")
        return " > ".join(parts)

    def get_url(self) -> str:
        """Generate URL for current location."""
        if not self.is_complete():
            return "https://election.ekantipur.com/?lng=eng"

        return (
            f"https://election.ekantipur.com/"
            f"pradesh-{self.province_number}/"
            f"district-{self.district_name.lower().replace(' ', '-')}/"
            f"constituency-{self.constituency_number}?lng=eng"
        )

    def __repr__(self) -> str:
        return f"Location({self.get_breadcrumb()})"


@dataclass
class QuickCard:
    """A quick card for tracking a specific constituency."""

    name: str
    province_number: int
    district_name: str
    constituency_number: int

    def to_location(self) -> Location:
        """Convert to a Location object."""
        # We don't have province_name here, but it will be populated by scraper
        return Location(
            province_number=self.province_number,
            province_name=None,
            district_name=self.district_name,
            constituency_number=self.constituency_number,
        )

    def __repr__(self) -> str:
        return f"QuickCard({self.name}: P{self.province_number}/{self.district_name}/C{self.constituency_number})"


# Hardcoded quick cards for tracking specific constituencies
QUICK_CARDS: List[QuickCard] = [
    QuickCard(
        name="Jhapa-5",
        province_number=1,
        district_name="Jhapa",
        constituency_number=5,
    ),
    QuickCard(
        name="Dang-2",
        province_number=5,
        district_name="Dang",
        constituency_number=2,
    ),
    QuickCard(
        name="Kathmandu-3",
        province_number=3,
        district_name="Kathmandu",
        constituency_number=3,
    ),
    QuickCard(
        name="Myagdi-1",
        province_number=4,
        district_name="Myagdi",
        constituency_number=1,
    ),
    QuickCard(
        name="Chitwan-3",
        province_number=3,
        district_name="Chitwan",
        constituency_number=3,
    ),
    QuickCard(
        name="Sarlahi-4",
        province_number=2,
        district_name="Sarlahi",
        constituency_number=4,
    ),
    QuickCard(
        name="Gulmi-1",
        province_number=5,
        district_name="Gulmi",
        constituency_number=1,
    ),
    QuickCard(
        name="Illam-2",
        province_number=1,
        district_name="Illam",
        constituency_number=2,
    ),
]


# Province information: (province_number, name, seats)
PROVINCE_INFO: List[Tuple[int, str, int]] = [
    (1, "Koshi", 28),
    (2, "Madhesh", 32),
    (3, "Bagmati", 33),
    (4, "Gandaki", 18),
    (5, "Lumbini", 26),
    (6, "Karnali", 12),
    (7, "Sudurpaschim", 16),
]


def get_province_seats_info() -> Dict[int, Tuple[str, int]]:
    """Get province information as dict: {province_num: (name, seats)}."""
    return {prov[0]: (prov[1], prov[2]) for prov in PROVINCE_INFO}


def get_total_seats() -> int:
    """Get total parliamentary seats."""
    return sum(prov[2] for prov in PROVINCE_INFO)
