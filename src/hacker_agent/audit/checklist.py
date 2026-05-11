"""Security audit checklist generator (web, API, crypto-casino, Solana, infra)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

CHECKLISTS: dict[str, dict[str, Any]] = {
    "web-application": {
        "name": "Web Application Security Audit",
        "description": "Comprehensive web application security assessment",
        "categories": [
            {
                "name": "Information Gathering",
                "items": [
                    "Identify technology stack (Wappalyzer, BuiltWith)",
                    "Map all endpoints (gobuster, ffuf, dirb)",
                    "Enumerate subdomains (sublist3r, amass, crt.sh)",
                    "Check DNS records and MX records",
                    "Identify WAF/CDN (wafw00f)",
                    "Analyze robots.txt and sitemap.xml",
                    "Check for exposed .git directories",
                    "Find backup files (.bak, .old, .zip, .tar.gz)",
                    "Check for exposed API documentation (Swagger, OpenAPI)",
                    "Analyze JavaScript files for secrets and endpoints",
                ],
            },
            {
                "name": "Authentication",
                "items": [
                    "Test password policy enforcement",
                    "Check for weak/default credentials",
                    "Test account lockout mechanism",
                    "Verify password reset functionality",
                    "Test for username enumeration",
                    "Check session management (token generation, expiration)",
                    "Test for session fixation",
                    "Verify logout invalidates session",
                    "Check for JWT vulnerabilities (none alg, weak secret)",
                    "Test MFA bypass possibilities",
                    "Check for brute force protection",
                    "Test OAuth implementation security",
                ],
            },
            {
                "name": "Injection Vulnerabilities",
                "items": [
                    "Test SQL Injection (error-based, union, blind)",
                    "Check for NoSQL Injection",
                    "Test Command Injection",
                    "Check for LDAP Injection",
                    "Test XPath Injection",
                    "Check for XML/XXE Injection",
                    "Test for SSTI (Server-Side Template Injection)",
                    "Check for CSS Injection",
                    "Test for Expression Language (EL) Injection",
                    "Check for HQL Injection",
                ],
            },
            {
                "name": "XSS & Client-Side",
                "items": [
                    "Test for Reflected XSS",
                    "Check for Stored XSS",
                    "Test for DOM-based XSS",
                    "Check for Blind XSS",
                    "Test Content Security Policy (CSP) bypass",
                    "Check for prototype pollution",
                    "Test for open redirects",
                    "Check for clickjacking (X-Frame-Options)",
                    "Verify secure cookie flags (HttpOnly, Secure, SameSite)",
                ],
            },
            {
                "name": "Access Control",
                "items": [
                    "Test for IDOR vulnerabilities",
                    "Check horizontal privilege escalation",
                    "Test vertical privilege escalation",
                    "Verify role-based access control",
                    "Check for forced browsing",
                    "Test path traversal",
                    "Verify file upload restrictions",
                    "Check for insecure direct references",
                ],
            },
            {
                "name": "Business Logic",
                "items": [
                    "Test for race conditions",
                    "Check for price manipulation",
                    "Test workflow bypass",
                    "Verify transaction integrity",
                    "Check for time-based attacks",
                    "Test for replay attacks",
                    "Verify business rule enforcement",
                ],
            },
        ],
    },
    "api-security": {
        "name": "API Security Audit",
        "description": "REST/GraphQL API security assessment",
        "categories": [
            {
                "name": "Discovery & Recon",
                "items": [
                    "Identify all API endpoints",
                    "Check API versioning strategy",
                    "Analyze API documentation",
                    "Identify deprecated endpoints",
                    "Check for API key exposure in code",
                ],
            },
            {
                "name": "Authentication & Authorization",
                "items": [
                    "Test API authentication mechanisms",
                    "Check for token exposure in logs/URLs",
                    "Verify JWT implementation",
                    "Test for broken object level authorization (BOLA)",
                    "Check for broken function level authorization (BFLA)",
                    "Test for mass assignment vulnerabilities",
                    "Verify rate limiting per endpoint",
                ],
            },
            {
                "name": "Input Validation",
                "items": [
                    "Test for injection in all parameters",
                    "Check parameter pollution",
                    "Verify content-type validation",
                    "Test for XXE in XML endpoints",
                    "Check file upload endpoints",
                    "Verify input size limits",
                    "Test for special character handling",
                ],
            },
            {
                "name": "GraphQL Specific",
                "items": [
                    "Enable introspection query",
                    "Test for query depth limiting",
                    "Check for query complexity analysis",
                    "Test for batching attacks",
                    "Verify field suggestions disabled in prod",
                    "Check for SQL injection via arguments",
                    "Test for DoS via nested queries",
                ],
            },
        ],
    },
    "crypto-casino": {
        "name": "Crypto Casino Security Audit",
        "description": "Crypto gambling platform security assessment",
        "categories": [
            {
                "name": "Provably Fair System",
                "items": [
                    "Verify server seed generation (cryptographically secure)",
                    "Check server seed hash commitment",
                    "Verify result calculation algorithm",
                    "Test client-side verification works",
                    "Check for predictability in RNG",
                    "Verify nonce increment properly",
                    "Test hash chain integrity",
                    "Check for result manipulation",
                ],
            },
            {
                "name": "Game Logic",
                "items": [
                    "Verify RTP calculation accuracy",
                    "Test house edge implementation",
                    "Check max win limits enforced",
                    "Verify game state transitions",
                    "Test for race conditions in betting",
                    "Check concurrent bet handling",
                    "Verify payout calculations",
                    "Test edge cases (max multiplier, min bet)",
                ],
            },
            {
                "name": "Financial Security",
                "items": [
                    "Verify deposit address generation",
                    "Check confirmation requirements",
                    "Test withdrawal authorization",
                    "Verify balance reconciliation",
                    "Check for double-spend protection",
                    "Test hot/cold wallet separation",
                    "Verify transaction fee handling",
                    "Check for integer overflow in calculations",
                ],
            },
            {
                "name": "Smart Contract (if applicable)",
                "items": [
                    "Check for reentrancy vulnerabilities",
                    "Verify access control on admin functions",
                    "Test for integer overflow/underflow",
                    "Check external call safety",
                    "Verify randomness source (NOT block.hash)",
                    "Test for frontrunning susceptibility",
                    "Check for timestamp dependence",
                    "Verify emergency pause functionality",
                ],
            },
            {
                "name": "Session & Betting",
                "items": [
                    "Verify session timeout handling",
                    "Check for bet replay attacks",
                    "Test session fixation",
                    "Verify proper bet logging",
                    "Check for bet manipulation after submit",
                    "Verify user cannot modify game parameters",
                    "Test for concurrent session handling",
                ],
            },
        ],
    },
    "smart-contract-solana": {
        "name": "Solana Smart Contract Audit",
        "description": "Solana/Anchor program security assessment",
        "categories": [
            {
                "name": "Account Validation",
                "items": [
                    "Verify all accounts have owner checks",
                    "Check account data length validation",
                    "Verify PDA derivation correctness",
                    "Check PDA bump seed validation",
                    "Verify account signer checks",
                    "Check for account confusion attacks",
                    "Verify program-derived address ownership",
                ],
            },
            {
                "name": "Access Control",
                "items": [
                    "Verify admin function restrictions",
                    "Check for missing signer checks",
                    "Verify proper authority validation",
                    "Check for privilege escalation",
                    "Verify token account ownership",
                    "Check for arbitrary CPI calls",
                ],
            },
            {
                "name": "Arithmetic & Math",
                "items": [
                    "Check for integer overflow/underflow",
                    "Verify checked math operations",
                    "Check precision loss in calculations",
                    "Verify proper decimal handling",
                    "Check for division by zero",
                    "Verify rounding behavior",
                ],
            },
            {
                "name": "CPI & Cross-Program",
                "items": [
                    "Verify CPI target program validation",
                    "Check for reentrancy via CPI",
                    "Verify state changes before CPI",
                    "Check for account data races",
                    "Verify proper error handling on CPI",
                ],
            },
            {
                "name": "Token & Economic",
                "items": [
                    "Verify token mint validation",
                    "Check token account validation",
                    "Verify proper transfer amounts",
                    "Check for token account reuse",
                    "Verify freeze/thaw authority checks",
                    "Check for mint authority abuse",
                ],
            },
        ],
    },
    "infrastructure": {
        "name": "Infrastructure Security Audit",
        "description": "Network and infrastructure security assessment",
        "categories": [
            {
                "name": "Network Scanning",
                "items": [
                    "Full port scan (TCP/UDP)",
                    "Service version detection",
                    "OS fingerprinting",
                    "Check for open management ports",
                    "Identify unnecessary services",
                    "Check for default credentials on services",
                    "Verify firewall rules",
                ],
            },
            {
                "name": "Cloud Configuration",
                "items": [
                    "Check S3 bucket permissions",
                    "Verify IAM policies (least privilege)",
                    "Check for exposed storage accounts",
                    "Verify security group rules",
                    "Check for publicly accessible databases",
                    "Verify logging is enabled",
                    "Check for hardcoded credentials in user-data",
                ],
            },
            {
                "name": "Container Security",
                "items": [
                    "Check for exposed Docker sockets",
                    "Verify container image scanning",
                    "Check for privileged containers",
                    "Verify secrets in environment variables",
                    "Check for mounted sensitive host paths",
                    "Verify network policies",
                    "Check for latest image tags",
                ],
            },
        ],
    },
}

AVAILABLE_AUDIT_TYPES: tuple[str, ...] = tuple(CHECKLISTS.keys())


class AuditChecklistGenerator:
    """Static-data driven checklist generator (markdown/json/html output)."""

    CHECKLISTS = CHECKLISTS

    @classmethod
    def generate(cls, audit_type: str, target: str | None = None) -> dict[str, Any]:
        if audit_type not in cls.CHECKLISTS:
            available = ", ".join(cls.CHECKLISTS.keys())
            raise ValueError(f"Unknown audit type '{audit_type}'. Available: {available}")
        # Deep-ish copy: we only mutate top-level + counters.
        base = cls.CHECKLISTS[audit_type]
        checklist: dict[str, Any] = {
            "name": base["name"],
            "description": base["description"],
            "categories": base["categories"],
            "generated_at": datetime.now(UTC).isoformat(),
            "target": target or "Not specified",
            "audit_type": audit_type,
        }
        total_items = sum(len(cat["items"]) for cat in checklist["categories"])
        checklist["total_items"] = total_items
        checklist["completed_items"] = 0
        checklist["progress_percentage"] = 0
        return checklist

    @classmethod
    def generate_all(cls, target: str | None = None) -> dict[str, dict[str, Any]]:
        return {audit_type: cls.generate(audit_type, target) for audit_type in cls.CHECKLISTS}

    @classmethod
    def format_markdown(cls, checklist: dict[str, Any]) -> str:
        lines: list[str] = [
            f"# {checklist['name']}",
            "",
            f"**Target:** {checklist['target']}",
            f"**Generated:** {checklist['generated_at']}",
            (
                f"**Progress:** {checklist['progress_percentage']}% "
                f"({checklist['completed_items']}/{checklist['total_items']})"
            ),
            "",
            f"_{checklist['description']}_",
            "",
            "---",
            "",
        ]
        for category in checklist["categories"]:
            lines.append(f"## {category['name']}")
            lines.append("")
            for item in category["items"]:
                lines.append(f"- [ ] {item}")
            lines.append("")
        lines.extend(["---", "", "## Notes", "", "_Add findings and observations here..._", ""])
        return "\n".join(lines)

    @classmethod
    def format_html(cls, checklist: dict[str, Any]) -> str:
        sections: list[str] = []
        for category in checklist["categories"]:
            items_html = "\n".join(f"        <li>{item}</li>" for item in category["items"])
            sections.append(f"    <h2>{category['name']}</h2>\n    <ul>\n{items_html}\n    </ul>")
        body = "\n".join(sections)
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{checklist["name"]}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 900px; margin: 0 auto; padding: 20px;
                background: #0d0d0f; color: #e7e7ea; }}
        h1 {{ border-bottom: 2px solid #e74c3c; padding-bottom: 10px; }}
        h2 {{ margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }}
        .meta {{ background: #18181b; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ padding: 8px 0; border-bottom: 1px solid #27272a; }}
        li::before {{ content: "☐ "; color: #3498db; font-weight: bold; margin-right: 8px; }}
        .progress {{ background: #27272a; border-radius: 10px; height: 20px; margin: 10px 0; }}
        .progress-bar {{ background: #2ecc71; height: 100%; border-radius: 10px;
                          text-align: center; color: white; line-height: 20px; }}
    </style>
</head>
<body>
    <h1>{checklist["name"]}</h1>
    <div class="meta">
        <strong>Target:</strong> {checklist["target"]}<br>
        <strong>Generated:</strong> {checklist["generated_at"]}<br>
        <strong>Progress:</strong> {checklist["progress_percentage"]}%
        <div class="progress">
            <div class="progress-bar" style="width: {checklist["progress_percentage"]}%"></div>
        </div>
    </div>
    <p><em>{checklist["description"]}</em></p>
{body}
</body>
</html>
"""


__all__ = ["AVAILABLE_AUDIT_TYPES", "CHECKLISTS", "AuditChecklistGenerator"]
