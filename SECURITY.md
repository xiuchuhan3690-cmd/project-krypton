# Security policy

Project Krypton 1.0.0 is a research-software prototype. Security reports may concern software vulnerabilities, dependency vulnerabilities, accidental credential/private-key exposure, path traversal, provenance-integrity failures, or accidental publication of external scientific data.

## Supported versions

Only the current public 1.0.x release line is planned for security fixes. No support promise is made for unreleased branches or private scientific artifacts. This policy will be revised when a public release supersedes 1.0.x.

## Reporting

The repository exists at <https://github.com/xiuchuhan3690-cmd/project-krypton> but remains private during pre-publication validation. Its final confidential reporting mechanism is not yet active: `SECURITY_REPORTING_ACTIVATION_REQUIRED_BEFORE_PUBLIC_READER_ACCESS`. Activating and verifying GitHub Private Vulnerability Reporting, or another owner-approved private route, is a hard Task-7B visibility gate. Until that gate passes, the repository must not become publicly readable. Do not post sensitive details publicly; retain the report securely and use only a verified private channel published by the project owner. A dedicated email address is not published and is not fabricated here.

Include the affected version, platform, minimal reproduction, impact, and whether the report may involve a secret or external-data leak. Remove or redact sensitive payloads unless a secure reporting channel explicitly requests them.

## Scope and response

The public wheel, sdist, Dockerfile, source tree, dependency boundary, local-pack loader, and packaging/verification scripts are in scope. Private scientific data and third-party services are not distributed components, but a Krypton defect that exposes them is in scope.

No clinical safety claim is made. Patient-specific, diagnostic, or treatment-use reports should not be submitted as supported-use cases; Project Krypton is not medical software.
