# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.2.x   | ✅        |
| < 0.2   | ❌        |

Until `1.0`, only the latest minor release receives security fixes.

## Reporting a vulnerability

**Do not open a public GitHub issue for security problems.**

Email `subkoks@gmail.com` with:

- A description of the vulnerability and its impact.
- Reproduction steps (commands, payloads, environment).
- Affected version(s).
- Any suggested remediation.

Acknowledgment within 72 hours. We aim to release a fix or mitigation within 14 days for high-severity issues, longer for lower severity.

## Scope

`hacker-agent` is a **research and defensive-tooling** package. The reported issue must affect the package itself — for example:

- Arbitrary code execution via parsing untrusted inputs (memory imports, CVE feeds, brain-dump JSON).
- Path traversal or file overwrite via CLI arguments.
- Dependency vulnerabilities that materially affect users (we track these via Dependabot).

The following are **out of scope**:

- Tools, exploits, or detections produced *by* the agent during an engagement.
- Vulnerabilities in third-party services the agent integrates with (report those to the vendor).
- Findings on systems you do not own or have authorization to test (see "Authorized use" below).

## Dependabot alerts policy

Dependabot is enabled and configured to open PRs against `develop` weekly. The repo has historically surfaced two categories of alert:

1. **Real CVEs in pinned dependencies** — fixed by bumping the version in `pyproject.toml`, syncing `uv.lock`, and merging the resulting PR. Example: GHSA-6w46-j5rx-g56g (pytest tmpdir handling) — resolved by pinning `pytest>=9.0.3`.
2. **"Malware" flags on transitive packages** — investigated case-by-case. If the package is genuinely malicious, it is replaced. If the alert is a false positive (e.g., the dependency does pattern matching that mimics security-research strings), the rationale is documented in this file.

Currently no "malware" alerts are open. The single CVE alert (pytest) is patched in this release cycle.

## Authorized use

`hacker-agent` is a tool for **authorized** security research — pentests with signed Rules of Engagement, CTF, bug bounty programs, and your own systems. Use against systems you do not have permission to test is illegal in most jurisdictions and unsupported by this project.

By contributing to or using this package you confirm that you operate inside an explicit authorization boundary, per the global rules in [`AGENTS.md`](https://github.com/subkoks/agents-md).
