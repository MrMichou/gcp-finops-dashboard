# Security Policy

## Supported versions

This project follows a rolling release model: only the **latest released
version** receives security fixes. Please upgrade before reporting an issue.

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, report privately via GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
("Report a vulnerability" under the repository's **Security** tab).

When reporting, please include:

- a description of the issue and its impact,
- steps to reproduce or a proof of concept,
- affected version(s) and environment.

We aim to acknowledge reports within a few business days and will keep you
updated on remediation progress.

## Scope & handling

- This tool requires **read-only** GCP permissions; never commit service-account
  keys or credentials. The repository ignores common credential file patterns
  (see `.gitignore` / `.dockerignore`).
- Container images are built with provenance and SBOM attestations and run as a
  non-root user (see `Dockerfile` and the Helm `securityContext`).
- Dependencies are kept current automatically via Dependabot.
