"""Web scraper for fetching election results from election.ekantipur.com."""

import re
import time
from typing import Dict, List, Optional, Tuple

from scrapling import Fetcher

from .models import (
    CandidateResult,
    ConstituencyResult,
    ElectionData,
    Location,
    PartyResult,
    ProvincePartyResult,
    ResultStatus,
)


class ElectionScraper:
    """Scraper for election results."""

    BASE_URL = "https://election.ekantipur.com"
    MAX_RETRIES = 5
    RETRY_DELAY = 2  # seconds

    # Default party colors (fallback)
    DEFAULT_COLORS = {
        "Rastriya Swatantra Party": "#4A90E2",
        "Nepali Congress": "#228B22",
        "CPN (UML)": "#FF0000",
        "CPN (Maoist Centre)": "#8B0000",
        "Rastriya Prajatantra Party": "#FFD700",
        "Janata Samajwadi Party": "#FF6347",
        "CPN (Unified Socialist)": "#DC143C",
        "Janamat Party": "#9370DB",
        "Loktantrik Samajwadi Party": "#FF8C00",
    }

    def __init__(self):
        """Initialize the scraper."""
        self.fetcher = Fetcher()
        self.party_colors: Dict[str, str] = self.DEFAULT_COLORS.copy()

    def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Fetch URL with exponential backoff retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.fetcher.get(url)
                if response and response.status == 200:
                    # Scrapling returns a Response object with body attribute
                    # The body contains the HTML content (may be bytes or string)
                    html_content = None
                    if hasattr(response, "body"):
                        html_content = response.body
                    elif hasattr(response, "text"):
                        html_content = response.text
                    else:
                        html_content = str(response)

                    # Decode bytes to string if necessary
                    if isinstance(html_content, bytes):
                        return html_content.decode("utf-8", errors="ignore")
                    return html_content
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY * (2**attempt)
                    time.sleep(delay)
                else:
                    raise Exception(
                        f"Failed to fetch {url} after {self.MAX_RETRIES} attempts: {e}"
                    )
        return None

    def _extract_color_from_style(self, style_str: str) -> Optional[str]:
        """Extract color from style attribute."""
        if not style_str:
            return None

        # Look for background-color or color property
        color_match = re.search(r"(?:background-)?color:\s*([^;]+)", style_str)
        if color_match:
            return color_match.group(1).strip()
        return None

    def scrape_homepage(self) -> ElectionData:
        """Scrape homepage for party-wise results."""
        url = f"{self.BASE_URL}/?lng=eng"
        html = self._fetch_with_retry(url)

        if not html:
            raise Exception("Failed to fetch homepage")

        from scrapling import Selector

        selector = Selector(html)

        party_results = []

        # Find the party stats container
        party_container = selector.find("div.party-stat-inside-wrap")
        if not party_container:
            raise Exception("Could not find party results container")

        # Find all party rows within the container
        party_rows = party_container.find_all("div.party-row")

        for row in party_rows:
            # Skip if this is a header row (shouldn't be in the wrap, but check anyway)
            row_class = row.attrib.get("class", "")
            if "party-table-head" in row_class:
                continue

            # Extract party name from the first column link
            party_link = row.find("a.first-col")
            if not party_link:
                continue

            party_name_elem = party_link.find("p")
            if not party_name_elem:
                continue

            party_name = party_name_elem.text.strip()
            if not party_name:
                continue

            # Extract win count from span.win-count
            win_count = 0
            win_link = row.find("a[href*='/elected']")
            if win_link:
                win_elem = win_link.find("span.win-count")
                if win_elem:
                    try:
                        win_count = int(win_elem.text.strip())
                    except (ValueError, AttributeError):
                        win_count = 0

            # Extract lead count from span.lead-count
            lead_count = 0
            lead_link = row.find("a[href*='/leading']")
            if lead_link:
                lead_elem = lead_link.find("span.lead-count")
                if lead_elem:
                    try:
                        lead_count = int(lead_elem.text.strip())
                    except (ValueError, AttributeError):
                        lead_count = 0

            # Try to extract color from party logo or use default
            color = "#888888"  # Default gray

            # Use default color if available
            if party_name in self.DEFAULT_COLORS:
                color = self.DEFAULT_COLORS[party_name]

            # Store color for future use
            self.party_colors[party_name] = color

            party_results.append(
                PartyResult(
                    party_name=party_name,
                    win_count=win_count,
                    lead_count=lead_count,
                    color=color,
                )
            )

        if not party_results:
            raise Exception("No party results found on homepage")

        # Sort by total (wins + leads) descending
        party_results.sort(key=lambda x: x.total, reverse=True)

        election_data = ElectionData(
            party_results=party_results,
            last_updated=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        return election_data

    def get_provinces(self) -> List[Tuple[int, str]]:
        """Get list of provinces."""
        return [
            (1, "Koshi"),
            (2, "Madhesh"),
            (3, "Bagmati"),
            (4, "Gandaki"),
            (5, "Lumbini"),
            (6, "Karnali"),
            (7, "Sudurpaschim"),
        ]

    def get_districts_for_province(self, province_number: int) -> List[str]:
        """Get list of districts for a province.

        Note: The website loads districts dynamically via JavaScript.
        We return a hardcoded list based on Nepal's actual districts per province.
        """
        # Hardcoded district lists per province (as of 2024)
        districts_by_province = {
            1: [
                "Bhojpur",
                "Dhankuta",
                "Ilam",
                "Jhapa",
                "Khotang",
                "Morang",
                "Okhaldhunga",
                "Panchthar",
                "Sankhuwasabha",
                "Solukhumbu",
                "Sunsari",
                "Taplejung",
                "Terhathum",
                "Udayapur",
            ],
            2: [
                "Bara",
                "Dhanusha",
                "Mahottari",
                "Parsa",
                "Rautahat",
                "Saptari",
                "Sarlahi",
                "Siraha",
            ],
            3: [
                "Bhaktapur",
                "Chitwan",
                "Dhading",
                "Dolakha",
                "Kathmandu",
                "Kavrepalanchok",
                "Lalitpur",
                "Makwanpur",
                "Nuwakot",
                "Ramechhap",
                "Rasuwa",
                "Sindhuli",
                "Sindhupalchok",
            ],
            4: [
                "Baglung",
                "Gorkha",
                "Kaski",
                "Lamjung",
                "Manang",
                "Mustang",
                "Myagdi",
                "Nawalparasi East",
                "Parbat",
                "Syangja",
                "Tanahun",
            ],
            5: [
                "Arghakhanchi",
                "Banke",
                "Bardiya",
                "Dang",
                "Gulmi",
                "Kapilvastu",
                "Nawalparasi West",
                "Palpa",
                "Parasi",
                "Pyuthan",
                "Rolpa",
                "Rukum East",
                "Rupandehi",
            ],
            6: [
                "Dailekh",
                "Dolpa",
                "Humla",
                "Jajarkot",
                "Jumla",
                "Kalikot",
                "Mugu",
                "Rukum West",
                "Salyan",
                "Surkhet",
            ],
            7: [
                "Achham",
                "Baitadi",
                "Bajhang",
                "Bajura",
                "Dadeldhura",
                "Darchula",
                "Doti",
                "Kailali",
                "Kanchanpur",
            ],
        }

        return districts_by_province.get(province_number, [])

    def get_constituencies_for_district(
        self, province_number: int, district_name: str
    ) -> List[int]:
        """Get list of constituencies for a district.

        Note: The website loads constituencies dynamically via JavaScript.
        We provide a reasonable default range. Most districts have 1-10 constituencies.
        """
        # Major districts with known high constituency counts
        major_districts = {
            "Kathmandu": 10,
            "Morang": 7,
            "Jhapa": 5,
            "Sunsari": 5,
            "Rupandehi": 5,
            "Banke": 3,
            "Kailali": 5,
            "Dang": 3,
            "Chitwan": 3,
            "Lalitpur": 3,
            "Bhaktapur": 2,
            "Kaski": 3,
            "Bara": 4,
            "Parsa": 4,
            "Dhanusha": 4,
            "Saptari": 3,
            "Siraha": 3,
            "Mahottari": 3,
        }

        # Default to reasonable constituency count
        max_const = major_districts.get(district_name, 2)

        # Return list from 1 to max_const
        return list(range(1, max_const + 1))

    def scrape_constituency(self, location: Location) -> Optional[ConstituencyResult]:
        """Scrape constituency-level results."""
        if not location.is_complete():
            return None

        url = location.get_url()
        html = self._fetch_with_retry(url)

        if not html:
            return None

        from scrapling import Selector

        selector = Selector(html)
        candidates = []

        # Find the results table
        table = selector.find("table.table-bordered")
        if not table:
            return None

        # Find all table body rows
        tbody = table.find("tbody")
        if not tbody:
            return None

        rows = tbody.find_all("tr")

        rank = 1
        for row in rows:
            cells = row.find_all("td")
            if not cells or len(cells) < 3:
                continue

            # Extract candidate name from first cell
            candidate_link = cells[0].find("a.candidate-name-link")
            if not candidate_link:
                continue

            candidate_span = candidate_link.find("span")
            if not candidate_span:
                continue

            candidate_name = candidate_span.text.strip()

            # Extract party name from second cell
            party_link = cells[1].find("a")
            party_name = "Independent"
            if party_link:
                party_span = party_link.find("span.party-name")
                if party_span:
                    party_name = party_span.text.strip()

            # Extract votes from third cell
            vote_div = cells[2].find("div.votecount")
            votes = 0
            status = ResultStatus.UNKNOWN

            if vote_div:
                vote_p = vote_div.find("p")
                if vote_p:
                    try:
                        votes_text = vote_p.text.strip().replace(",", "")
                        votes = int(votes_text)
                    except (ValueError, AttributeError):
                        votes = 0

                # Check status - prioritize text content over class
                status_span = vote_div.find("span")
                if status_span:
                    status_text = status_span.text.strip().lower()
                    if "elected" in status_text:
                        status = ResultStatus.WIN
                    elif "leading" in status_text or "lead" in status_text:
                        status = ResultStatus.LEAD
                else:
                    # Fallback to div class if no span
                    div_class = vote_div.attrib.get("class", "")
                    if "win" in div_class.lower() or "elected" in div_class.lower():
                        status = ResultStatus.WIN
                    elif "lead" in div_class.lower():
                        status = ResultStatus.LEAD

            # If no explicit status and this is rank 1, mark as LEAD
            if status == ResultStatus.UNKNOWN and rank == 1 and votes > 0:
                status = ResultStatus.LEAD

            # Get color for party
            color = self.party_colors.get(party_name, "#888888")

            candidates.append(
                CandidateResult(
                    rank=rank,
                    party_name=party_name,
                    candidate_name=candidate_name,
                    votes=votes,
                    status=status,
                    color=color,
                )
            )

            rank += 1

            # Limit to top 5 candidates
            if rank > 5:
                break

        if not candidates:
            return None

        return ConstituencyResult(
            province_number=location.province_number,
            province_name=location.province_name,
            district_name=location.district_name,
            constituency_number=location.constituency_number,
            candidates=candidates,
        )

    def scrape_province_results(
        self, province_number: int
    ) -> List[ProvincePartyResult]:
        """Scrape province-wise party results."""
        url = f"{self.BASE_URL}/pradesh-{province_number}?lng=eng"
        html = self._fetch_with_retry(url)

        if not html:
            return []

        from scrapling import Selector

        selector = Selector(html)

        province_name = dict(self.get_provinces()).get(
            province_number, f"Province {province_number}"
        )

        results = []
        party_rows = selector.find_all("div.party-row")

        for row in party_rows:
            if "party-table-head" in row.attrib.get("class", ""):
                continue

            party_link = row.find("a.first-col")
            if not party_link:
                continue

            party_name_elem = party_link.find("p")
            if not party_name_elem:
                continue

            party_name = party_name_elem.text.strip()

            win_elem = row.find("span.win-count")
            win_count = int(win_elem.text.strip()) if win_elem else 0

            lead_elem = row.find("span.lead-count")
            lead_count = int(lead_elem.text.strip()) if lead_elem else 0

            color = self.party_colors.get(party_name, "#888888")

            results.append(
                ProvincePartyResult(
                    province_name=province_name,
                    province_number=province_number,
                    party_name=party_name,
                    win_count=win_count,
                    lead_count=lead_count,
                    color=color,
                )
            )

        results.sort(key=lambda x: x.total, reverse=True)
        return results
