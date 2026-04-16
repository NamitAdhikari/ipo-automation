"""
Meroshare API Client

This module provides a REST API client for Meroshare (Nepal's share trading platform).
It replaces Selenium-based automation with direct HTTP API calls using requests.

Note: We use 'requests' instead of 'httpx' because the Meroshare WAF is more 
compatible with requests' HTTP/1.1 and header handling.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dataclasses import dataclass
from typing import Any

from rich.console import Console

console = Console()


# Constants
MS_API_BASE = "https://webbackend.cdsc.com.np/api"

# Chrome-based User-Agent (more compatible with WAF)
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"

# Headers that match Chrome browser behavior to avoid WAF blocking
# These headers are critical to avoid "URL was rejected" errors
BASE_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Origin": "https://meroshare.cdsc.com.np",
    "Referer": "https://meroshare.cdsc.com.np/",
    "User-Agent": USER_AGENT,
    # Chrome-specific headers required by WAF
    "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}


def _create_session() -> requests.Session:
    """
    Create a requests session with retry strategy.
    
    Returns:
        Configured requests.Session with retry strategy
    """
    session = requests.Session()
    
    # Configure retry strategy (similar to working implementation)
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


@dataclass
class Capital:
    """Represents a Depository Participant (DP/Capital)"""

    id: int
    code: str
    name: str


@dataclass
class BankAccount:
    """Represents a bank account for IPO application"""

    id: int
    account_number: str
    branch_id: int
    customer_id: int
    account_type_id: int
    bank_name: str


@dataclass
class IPOIssue:
    """Represents an IPO issue available for application"""

    company_share_id: int
    company_name: str
    scrip: str
    share_type: str
    share_group: str
    sub_group: str
    share_per_unit: int
    min_unit: int
    max_unit: int
    issue_open_date: str
    issue_close_date: str
    action: str | None  # None means can apply, otherwise already applied


class MeroshareAPIError(Exception):
    """Custom exception for Meroshare API errors"""

    def __init__(self, message: str, status_code: int | None = None, response: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class MeroshareClient:
    """
    Meroshare REST API Client

    This client handles all API interactions with the Meroshare platform including:
    - Authentication (login/logout)
    - Fetching available IPOs
    - Applying for IPOs
    - Getting account details
    """

    def __init__(self, timeout: tuple[int, int] = (10, 30)):
        """
        Initialize the Meroshare client.

        Args:
            timeout: HTTP request timeout as (connect_timeout, read_timeout) in seconds
        """
        # Use requests.Session with retry strategy for better WAF compatibility
        self._session = _create_session()
        self._timeout = timeout
        self._auth_token: str | None = None
        self._dmat: str | None = None
        self._dpid: str | None = None
        self._username: str | None = None
        self._capitals: dict[str, Capital] = {}

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self) -> "MeroshareClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @property
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        return self._auth_token is not None

    def fetch_capitals(self) -> list[Capital]:
        """
        Fetch the list of all Depository Participants (DPs/Capitals).

        Returns:
            List of Capital objects representing available DPs

        Raises:
            MeroshareAPIError: If the API request fails
        """
        headers = self._get_headers()
        headers["Authorization"] = "null"

        try:
            response = self._session.get(
                f"{MS_API_BASE}/meroShare/capital/",
                headers=headers,
                timeout=self._timeout
            )
        except requests.RequestException as e:
            raise MeroshareAPIError(f"Network error fetching capitals: {e}")

        if response.status_code != 200:
            # Check for WAF blocking
            if "URL was rejected" in response.text or "support ID" in response.text.lower():
                raise MeroshareAPIError(
                    f"Request blocked by WAF. Response: {response.text[:500]}",
                    status_code=response.status_code,
                )
            raise MeroshareAPIError(
                f"Failed to fetch capital list: {response.text}",
                status_code=response.status_code,
                response=response.json() if response.text else None,
            )

        try:
            data = response.json()
        except Exception as e:
            raise MeroshareAPIError(f"Invalid JSON response: {response.text[:500]}")

        capitals = []
        for cap in data:
            capital = Capital(
                id=cap.get("id"),
                code=cap.get("code"),
                name=cap.get("name"),
            )
            capitals.append(capital)
            self._capitals[cap.get("code")] = capital

        return capitals

    def find_capital_by_code(self, code: str) -> Capital | None:
        """
        Find a capital/DP by its code.

        Args:
            code: The DP code (e.g., "13700" or partial name like "PRABHU")

        Returns:
            Capital object if found, None otherwise
        """
        if not self._capitals:
            self.fetch_capitals()

        # Try exact match first
        if code in self._capitals:
            return self._capitals[code]

        # Try partial match (case-insensitive) on code or name
        code_lower = code.lower()
        for cap_code, capital in self._capitals.items():
            if code_lower in cap_code.lower() or code_lower in capital.name.lower():
                return capital

        return None

    def find_capitals_by_code(self, code: str) -> list[Capital]:
        """
        Find all capitals/DPs matching a code pattern.

        Args:
            code: The DP code pattern to search for

        Returns:
            List of matching Capital objects
        """
        if not self._capitals:
            self.fetch_capitals()

        code_lower = code.lower()
        matches = []

        for cap_code, capital in self._capitals.items():
            if code_lower in cap_code.lower() or code_lower in capital.name.lower():
                matches.append(capital)

        return matches

    def login(self, capital_id: int, username: str, password: str) -> str:
        """
        Authenticate with Meroshare.

        Args:
            capital_id: The DP/Capital ID (numeric)
            username: Meroshare username (usually last 8 digits of DMAT)
            password: Meroshare password

        Returns:
            Authorization token on success

        Raises:
            MeroshareAPIError: If login fails
        """
        headers = self._get_headers()
        headers["Authorization"] = "null"

        data = {
            "clientId": str(capital_id),
            "username": username,
            "password": password,
        }

        try:
            response = self._session.post(
                f"{MS_API_BASE}/meroShare/auth/",
                json=data,
                headers=headers,
                timeout=self._timeout
            )
        except requests.RequestException as e:
            raise MeroshareAPIError(f"Network error during login: {e}")

        # Check for WAF blocking first
        if "URL was rejected" in response.text or "support ID" in response.text.lower():
            raise MeroshareAPIError(
                f"Request blocked by WAF. This may indicate incorrect headers. Response: {response.text[:500]}",
                status_code=response.status_code,
            )

        if response.status_code != 200:
            error_msg = "Login failed"
            try:
                resp_json = response.json()
                if isinstance(resp_json, dict):
                    error_msg = resp_json.get("message", error_msg)
            except Exception:
                error_msg = f"Login failed with status {response.status_code}: {response.text[:200]}"
            raise MeroshareAPIError(
                error_msg,
                status_code=response.status_code,
                response=response.json() if response.text else None,
            )

        try:
            resp_json = response.json()
        except Exception as e:
            raise MeroshareAPIError(f"Invalid JSON response from login: {response.text[:500]}")

        # Check for various account issues
        if resp_json.get("passwordExpired"):
            raise MeroshareAPIError("Password has expired")
        if resp_json.get("accountExpired"):
            raise MeroshareAPIError("Account has expired")
        if resp_json.get("dematExpired"):
            raise MeroshareAPIError("DMAT has expired")

        auth_token = response.headers.get("Authorization")
        if not auth_token:
            raise MeroshareAPIError("No authorization token received")

        self._auth_token = auth_token
        self._username = username

        return auth_token

    def logout(self) -> bool:
        """
        Logout from Meroshare.

        Returns:
            True on successful logout

        Raises:
            MeroshareAPIError: If logout fails
        """
        if not self._auth_token:
            return True

        headers = self._get_headers()

        response = self._session.get(
            f"{MS_API_BASE}/meroShare/auth/logout/",
            headers=headers,
            timeout=self._timeout
        )

        # 201 is the expected status code for logout
        if response.status_code not in (200, 201):
            raise MeroshareAPIError(
                f"Logout failed: {response.text}",
                status_code=response.status_code,
            )

        self._auth_token = None
        return True

    def get_own_details(self) -> dict:
        """
        Get the logged-in user's own details including DMAT number.

        Returns:
            Dictionary containing user details

        Raises:
            MeroshareAPIError: If not authenticated or request fails
        """
        self._require_auth()

        headers = self._get_headers()
        response = self._session.get(
            f"{MS_API_BASE}/meroShare/ownDetail/",
            headers=headers,
            timeout=self._timeout
        )

        if response.status_code != 200:
            raise MeroshareAPIError(
                f"Failed to get own details: {response.text}",
                status_code=response.status_code,
            )

        details = response.json()
        self._dmat = details.get("demat")
        return details

    def get_account_details(self, dmat: str) -> dict:
        """
        Get account details for a specific DMAT.

        Args:
            dmat: The DMAT number

        Returns:
            Dictionary containing account details

        Raises:
            MeroshareAPIError: If not authenticated or request fails
        """
        self._require_auth()

        headers = self._get_headers()
        response = self._session.get(
            f"{MS_API_BASE}/meroShareView/myDetail/{dmat}",
            headers=headers,
            timeout=self._timeout
        )

        if response.status_code != 200:
            raise MeroshareAPIError(
                f"Failed to get account details: {response.text}",
                status_code=response.status_code,
            )

        return response.json()

    def get_bank_list(self) -> list[dict]:
        """
        Get the list of banks linked to the account.

        Returns:
            List of bank dictionaries

        Raises:
            MeroshareAPIError: If not authenticated or request fails
        """
        self._require_auth()

        headers = self._get_headers()
        response = self._session.get(
            f"{MS_API_BASE}/meroShare/bank/",
            headers=headers,
            timeout=self._timeout
        )

        if response.status_code != 200:
            raise MeroshareAPIError(
                f"Failed to get bank list: {response.text}",
                status_code=response.status_code,
            )

        return response.json()

    def get_bank_details(self, bank_id: int) -> list[dict]:
        """
        Get details for a specific bank.

        Args:
            bank_id: The bank ID

        Returns:
            List of bank account details

        Raises:
            MeroshareAPIError: If not authenticated or request fails
        """
        self._require_auth()

        headers = self._get_headers()
        response = self._session.get(
            f"{MS_API_BASE}/meroShare/bank/{bank_id}",
            headers=headers,
            timeout=self._timeout
        )

        if response.status_code != 200:
            raise MeroshareAPIError(
                f"Failed to get bank details: {response.text}",
                status_code=response.status_code,
            )

        return response.json()

    def fetch_applicable_issues(self) -> list[IPOIssue]:
        """
        Fetch all IPOs that the user can apply for.

        Returns:
            List of IPOIssue objects representing available IPOs

        Raises:
            MeroshareAPIError: If not authenticated or request fails
        """
        self._require_auth()

        headers = self._get_headers()

        data = {
            "filterFieldParams": [
                {"key": "companyIssue.companyISIN.script", "alias": "Scrip"},
                {"key": "companyIssue.companyISIN.company.name", "alias": "Company Name"},
                {"key": "companyIssue.assignedToClient.name", "value": "", "alias": "Issue Manager"},
            ],
            "page": 1,
            "size": 100,
            "searchRoleViewConstants": "VIEW_APPLICABLE_SHARE",
            "filterDateParams": [
                {"key": "minIssueOpenDate", "condition": "", "alias": "", "value": ""},
                {"key": "maxIssueCloseDate", "condition": "", "alias": "", "value": ""},
            ],
        }

        response = self._session.post(
            f"{MS_API_BASE}/meroShare/companyShare/applicableIssue/",
            json=data,
            headers=headers,
            timeout=self._timeout
        )

        if response.status_code != 200:
            raise MeroshareAPIError(
                f"Failed to fetch applicable issues: {response.text}",
                status_code=response.status_code,
            )

        issues = []
        resp_json = response.json()
        for item in resp_json.get("object", []):
            issue = IPOIssue(
                company_share_id=item.get("companyShareId"),
                company_name=item.get("companyName", ""),
                scrip=item.get("scrip", ""),
                share_type=item.get("shareTypeName", ""),
                share_group=item.get("shareGroupName", ""),
                sub_group=item.get("subGroup", ""),
                share_per_unit=item.get("sharePerUnit", 0),
                min_unit=item.get("minUnit", 0),
                max_unit=item.get("maxUnit", 0),
                issue_open_date=item.get("issueOpenDate", ""),
                issue_close_date=item.get("issueCloseDate", ""),
                action=item.get("action"),
            )
            issues.append(issue)

        return issues

    def get_issue_details(self, company_share_id: int) -> dict:
        """
        Get detailed information about a specific IPO issue.

        Args:
            company_share_id: The IPO company share ID

        Returns:
            Dictionary containing issue details including min/max units

        Raises:
            MeroshareAPIError: If not authenticated or request fails
        """
        self._require_auth()

        headers = self._get_headers()
        response = self._session.get(
            f"{MS_API_BASE}/meroShare/active/{company_share_id}",
            headers=headers,
            timeout=self._timeout
        )

        if response.status_code != 200:
            raise MeroshareAPIError(
                f"Failed to get issue details: {response.text}",
                status_code=response.status_code,
            )

        return response.json()

    def check_can_apply(self, company_share_id: int, dmat: str) -> dict:
        """
        Check if the user can apply for a specific IPO.

        Args:
            company_share_id: The IPO company share ID
            dmat: The user's DMAT number

        Returns:
            Dictionary with eligibility information

        Raises:
            MeroshareAPIError: If not authenticated or request fails
        """
        self._require_auth()

        headers = self._get_headers()
        response = self._session.get(
            f"{MS_API_BASE}/meroShare/applicantForm/customerType/{company_share_id}/{dmat}",
            headers=headers,
            timeout=self._timeout
        )

        if response.status_code != 200:
            raise MeroshareAPIError(
                f"Failed to check application eligibility: {response.text}",
                status_code=response.status_code,
            )

        return response.json()

    def apply_ipo(
        self,
        company_share_id: int,
        dmat: str,
        bank_id: int,
        account_number: str,
        customer_id: int,
        branch_id: int,
        account_type_id: int,
        kitta: int,
        crn: str,
        pin: str,
    ) -> dict:
        """
        Apply for an IPO.

        Args:
            company_share_id: The IPO company share ID
            dmat: The user's DMAT number
            bank_id: The bank ID
            account_number: The bank account number
            customer_id: The customer ID
            branch_id: The account branch ID
            account_type_id: The account type ID
            kitta: Number of shares to apply for
            crn: CRN number
            pin: Transaction PIN

        Returns:
            Dictionary containing application result

        Raises:
            MeroshareAPIError: If application fails
        """
        self._require_auth()

        headers = self._get_headers()

        # Extract BOID (last 8 digits of DMAT)
        boid = dmat[-8:]

        data = {
            "demat": dmat,
            "boid": boid,
            "accountNumber": account_number,
            "customerId": customer_id,
            "accountBranchId": branch_id,
            "accountTypeId": account_type_id,
            "appliedKitta": str(kitta),
            "crnNumber": crn,
            "transactionPIN": pin,
            "companyShareId": str(company_share_id),
            "bankId": bank_id,
        }

        response = self._session.post(
            f"{MS_API_BASE}/meroShare/applicantForm/share/apply",
            json=data,
            headers=headers,
            timeout=self._timeout
        )

        if response.status_code != 201:
            error_msg = "IPO application failed"
            try:
                resp_json = response.json()
                if isinstance(resp_json, dict):
                    error_msg = resp_json.get("message", error_msg)
            except Exception:
                error_msg = response.text or error_msg
            raise MeroshareAPIError(
                error_msg,
                status_code=response.status_code,
                response=response.json() if response.text else None,
            )

        return response.json()

    def fetch_application_reports(self) -> list[dict]:
        """
        Fetch the list of IPO applications (history).

        Returns:
            List of application report dictionaries

        Raises:
            MeroshareAPIError: If not authenticated or request fails
        """
        self._require_auth()

        headers = self._get_headers()

        data = {
            "filterFieldParams": [
                {"key": "companyShare.companyIssue.companyISIN.script", "alias": "Scrip"},
                {"key": "companyShare.companyIssue.companyISIN.company.name", "alias": "Company Name"},
            ],
            "page": 1,
            "size": 200,
            "searchRoleViewConstants": "VIEW_APPLICANT_FORM_COMPLETE",
            "filterDateParams": [
                {"key": "appliedDate", "condition": "", "alias": "", "value": ""},
                {"key": "appliedDate", "condition": "", "alias": "", "value": ""},
            ],
        }

        response = self._session.post(
            f"{MS_API_BASE}/meroShare/applicantForm/active/search/",
            json=data,
            headers=headers,
            timeout=self._timeout
        )

        if response.status_code != 200:
            raise MeroshareAPIError(
                f"Failed to fetch application reports: {response.text}",
                status_code=response.status_code,
            )

        return response.json().get("object", [])

    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        headers = BASE_HEADERS.copy()
        if self._auth_token:
            headers["Authorization"] = self._auth_token
        return headers

    def _require_auth(self) -> None:
        """Ensure the client is authenticated."""
        if not self._auth_token:
            raise MeroshareAPIError("Not authenticated. Please login first.")


class MeroshareIPOApplicator:
    """
    High-level IPO application handler.

    This class provides a simplified interface for applying to IPOs,
    handling all the necessary account detail fetching automatically.
    """

    def __init__(
        self,
        username: str,
        password: str,
        dp_code: str,
        crn: str,
        pin: str,
    ):
        """
        Initialize the IPO applicator.

        Args:
            username: Meroshare username
            password: Meroshare password
            dp_code: DP code (e.g., "13700" or partial name)
            crn: CRN number
            pin: Transaction PIN
        """
        self.username = username
        self.password = password
        self.dp_code = dp_code
        self.crn = crn
        self.pin = pin

        self._client = MeroshareClient()
        self._capital: Capital | None = None
        self._dmat: str | None = None
        self._bank_info: dict | None = None
        self._is_logged_in = False

    def close(self) -> None:
        """Close the client and cleanup."""
        if self._is_logged_in:
            try:
                self._client.logout()
            except Exception:
                pass
        self._client.close()

    def __enter__(self) -> "MeroshareIPOApplicator":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def find_matching_dps(self) -> list[Capital]:
        """
        Find DPs matching the configured dp_code.

        Returns:
            List of matching Capital objects
        """
        return self._client.find_capitals_by_code(self.dp_code)

    def login(self, capital: Capital | None = None) -> None:
        """
        Login to Meroshare.

        Args:
            capital: Optional specific Capital to use. If not provided,
                    will auto-select if only one match found.

        Raises:
            MeroshareAPIError: If login fails or multiple DPs match without selection
        """
        if capital:
            self._capital = capital
        else:
            matches = self.find_matching_dps()
            if not matches:
                raise MeroshareAPIError(f"No DP found matching '{self.dp_code}'")
            if len(matches) > 1:
                raise MeroshareAPIError(
                    f"Multiple DPs match '{self.dp_code}'. Please select one: "
                    + ", ".join(f"{m.code} ({m.name})" for m in matches)
                )
            self._capital = matches[0]

        self._client.login(self._capital.id, self.username, self.password)
        self._is_logged_in = True

        # Fetch account details
        own_details = self._client.get_own_details()
        self._dmat = own_details.get("demat")

        # Fetch bank details
        banks = self._client.get_bank_list()
        if banks:
            bank_id = banks[0].get("id")
            bank_details = self._client.get_bank_details(bank_id)
            if bank_details:
                self._bank_info = {
                    "bank_id": bank_id,
                    "account_number": bank_details[0].get("accountNumber"),
                    "branch_id": bank_details[0].get("accountBranchId"),
                    "customer_id": bank_details[0].get("id"),
                    "account_type_id": bank_details[0].get("accountTypeId"),
                    "bank_name": banks[0].get("name", ""),
                }

    def logout(self) -> None:
        """Logout from Meroshare."""
        if self._is_logged_in:
            self._client.logout()
            self._is_logged_in = False

    def get_applicable_ipos(self) -> list[IPOIssue]:
        """
        Get list of IPOs available for application.

        Returns:
            List of IPOIssue objects that can be applied to
        """
        issues = self._client.fetch_applicable_issues()
        # Filter to only those that can be applied (no action means can apply)
        return [issue for issue in issues if issue.action is None]

    def apply_ipo(self, issue: IPOIssue, kitta: int | None = None) -> dict:
        """
        Apply for an IPO.

        Args:
            issue: The IPOIssue to apply for
            kitta: Number of shares to apply for. If None, uses minimum.

        Returns:
            Dictionary containing application result

        Raises:
            MeroshareAPIError: If application fails
        """
        if not self._dmat:
            raise MeroshareAPIError("Not logged in. Please login first.")
        if not self._bank_info:
            raise MeroshareAPIError("Bank information not available.")

        # Get issue details for min/max units
        details = self._client.get_issue_details(issue.company_share_id)
        min_kitta = details.get("minUnit", issue.min_unit)
        max_kitta = details.get("maxUnit", issue.max_unit)

        if kitta is None:
            kitta = min_kitta

        if kitta < min_kitta:
            raise MeroshareAPIError(f"Kitta must be at least {min_kitta}")
        if kitta > max_kitta:
            raise MeroshareAPIError(f"Kitta must be at most {max_kitta}")

        # Check eligibility
        eligibility = self._client.check_can_apply(issue.company_share_id, self._dmat)
        if eligibility.get("message") != "Customer can apply.":
            raise MeroshareAPIError(
                f"Cannot apply: {eligibility.get('message', 'Unknown reason')}"
            )

        # Apply
        return self._client.apply_ipo(
            company_share_id=issue.company_share_id,
            dmat=self._dmat,
            bank_id=self._bank_info["bank_id"],
            account_number=self._bank_info["account_number"],
            customer_id=self._bank_info["customer_id"],
            branch_id=self._bank_info["branch_id"],
            account_type_id=self._bank_info["account_type_id"],
            kitta=kitta,
            crn=self.crn,
            pin=self.pin,
        )

    @property
    def dmat(self) -> str | None:
        """Get the DMAT number."""
        return self._dmat

    @property
    def bank_info(self) -> dict | None:
        """Get the bank information."""
        return self._bank_info

    @property
    def capital(self) -> Capital | None:
        """Get the selected capital/DP."""
        return self._capital
