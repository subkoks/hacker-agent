#!/usr/bin/env bash
# Hacker Agent — seed the memory store with a starter pack of techniques/tools.
# Idempotent: duplicate content is keyed by SHA-256 over (timestamp + content) so
# re-runs just refresh timestamps.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_DIR}"

learn() {
    local category="$1" content="$2" tags="$3" importance="${4:-6}"
    python3 -m hacker_agent learn \
        --content "${content}" \
        --category "${category}" \
        --tags "${tags}" \
        --importance "${importance}" \
        --source seed
}

learn technique "Test JWT 'none' algorithm bypass — many libraries still accept alg=none without explicit allowlist" "jwt,auth,bypass" 8
learn technique "Probe GraphQL endpoints for introspection — disabled in prod usually means misconfigured staging is wide open" "graphql,recon,introspection" 7
learn technique "Path-traversal payloads: ..%2f..%2f, ..;/ (Java), %252e%252e/ (double encoding)" "traversal,web,encoding" 7
learn technique "JWT 'kid' header SQL injection — some servers join kid into a DB lookup" "jwt,sqli,auth" 8
learn technique "HTTP request smuggling primer: TE.CL and CL.TE — Burp HTTP Request Smuggler" "smuggling,http,burp" 8
learn tool "ffuf: ffuf -u https://t/FUZZ -w wl.txt -mc 200,204,301,302,401,403 -fc 404" "ffuf,fuzzing,recon" 7
learn tool "gobuster dir -u https://t -w wl.txt -t 50 -k --no-error -x php,asp,aspx,jsp" "gobuster,dirbust,recon" 6
learn tool "nmap: nmap -sV -sC -p- -T4 --min-rate 1000 -oA scan target" "nmap,recon,scanning" 8
learn tool "amass enum -d target.tld -active -brute -src -o subs.txt" "amass,subdomain,osint" 7
learn tool "trufflehog filesystem . --json | jq 'select(.Verified)'" "trufflehog,secrets,git" 7
learn threat "Spring4Shell (CVE-2022-22965) — Tomcat + Spring binding + JDK 9+ exposes RCE via class.module.classLoader" "spring,rce,jvm" 9
learn threat "Log4Shell (CVE-2021-44228) — JNDI lookup via crafted log strings still in long-tail Java workloads" "log4j,jndi,rce" 9
learn threat "Polyfill.io supply-chain (2024) — abandoned CDN inserting malicious JS into 100k+ sites" "supply-chain,cdn,polyfill" 9
learn insight "Always check robots.txt + sitemap.xml — they leak admin paths and staging routes" "recon,web,quickwin" 5
learn insight "Verify scope before every active scan — out-of-scope discoveries get flagged, not exploited" "scope,authorization,policy" 9
learn failure "Mass-scanning prod from a single IP triggers WAF reputation rules — rotate via Burp upstream + cloud egress IPs" "waf,evasion,opsec" 7

echo
echo "[+] Seeded. Current stats:"
python3 -m hacker_agent stats
