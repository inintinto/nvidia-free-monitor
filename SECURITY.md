# Security Policy

The `inintinto/nvidia-free-monitor` project takes the security of our codebase, automated monitoring pipelines, and serverless edge endpoints seriously.

## Supported Versions

Only the latest active major version is actively maintained and receives security updates.

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| 3.x     | :white_check_mark: | Current Active Version (Supported) |
| 2.x     | :x:                | Deprecated |
| < 2.0   | :x:                | End of Life |

## Reporting a Vulnerability

If you discover a potential security vulnerability in this project:

1. **Please do NOT disclose the issue publicly** via GitHub Issues, Discussions, or social media.
2. **Use GitHub Private Vulnerability Reporting**:
   - Go to the **Security** tab of the repository: `https://github.com/inintinto/nvidia-free-monitor/security/advisories`
   - Click **"Report a vulnerability"** to privately submit a report to the repository maintainers.
3. **Include the following details in your report**:
   - Type of issue (e.g., secret leakage, SSRF, edge runtime vulnerability, injection).
   - Step-by-step instructions or proof-of-concept (PoC) to reproduce the vulnerability.
   - Affected files and potential impact.
   - Any suggested remediation or mitigation.

The maintainers will review the report, acknowledge receipt within 48 hours, and work with you on a coordinated disclosure timeline.

## Security Practices in this Repository

This project implements defense-in-depth security hygiene:

- **Zero-Secret Codebase**: No credentials, bot tokens, or API keys are stored in the repository.
- **Defensive Log Sanitization**: Exception logging automatically redacts sensitive Telegram Bot API tokens (`bot***REDACTED***`).
- **Standardized Proxy Handling**: Network requests respect standard `HTTP_PROXY` / `HTTPS_PROXY` environment variables and default to pure direct connections without hardcoded localhost fallbacks.
- **Strict CI Whitelisting**: Automated metadata synchronization pipelines enforce strict Git diff whitelists to prevent unauthorized file modifications.
- **Environment Isolation**: Local secrets must be configured via untracked `.env` (Python) and `worker/.dev.vars` (Worker), templated by `.env.example` and `worker/.dev.vars.example`.
