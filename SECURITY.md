# Security policy

Project Krypton 1.0.0 is a research-software prototype. Security reports may concern software vulnerabilities, dependency vulnerabilities, accidental credential/private-key exposure, path traversal, provenance-integrity failures, or accidental publication of external scientific data.

## Supported versions

Only the current public 1.0.x release line is planned for security fixes. No support promise is made for unreleased branches or private scientific artifacts.

## Reporting

Report a vulnerability confidentially through GitHub Private Vulnerability Reporting: open the repository's **Security** tab and choose **Report a vulnerability**. Do not disclose sensitive details in a public issue, discussion, or pull request. No dedicated security email address is published.

Include the affected version, platform, minimal reproduction, impact, and whether the report may involve a secret or external-data leak. Remove or redact sensitive payloads unless a secure reporting channel explicitly requests them.

## Scope and response

The public wheel, sdist, Dockerfile, source tree, dependency boundary, local-pack loader, and packaging/verification scripts are in scope. Private scientific data and third-party services are not distributed components, but a Krypton defect that exposes them is in scope.

No clinical safety claim is made. Patient-specific, diagnostic, or treatment-use reports should not be submitted as supported-use cases; Project Krypton is not medical software.
