# Releasing

Releases are fully automated with
[release-please](https://github.com/googleapis/release-please) and GitHub
Actions. You never edit the version by hand.

## How it works

1. **Commit using [Conventional Commits](https://www.conventionalcommits.org/).**
   The commit type drives the version bump and the changelog:

   | Commit prefix          | Example                                | Effect                          |
   | ---------------------- | -------------------------------------- | ------------------------------- |
   | `fix:`                 | `fix: handle empty billing export`     | patch bump (`0.2.0` → `0.2.1`)  |
   | `feat:`                | `feat: add cost forecast panel`        | minor bump (`0.2.0` → `0.3.0`)  |
   | `feat!:` / `BREAKING CHANGE:` | `feat!: drop Python 3.10 support` | major bump (`0.x` stays minor pre-1.0) |
   | `docs:`, `refactor:`, `perf:`, `deps:` | `docs: clarify auth setup` | shown in changelog, patch bump  |
   | `chore:`, `ci:`, `test:`, `build:`, `style:` | `chore: tidy imports` | no release on their own         |

2. **Push / merge to `main`.** The
   [`Release Please`](.github/workflows/release-please.yml) workflow opens (or
   updates) a **release PR** titled like `chore(main): release 0.3.0`. This PR
   bumps the version in `pyproject.toml` and `src/gcp_finops_dashboard/__init__.py`
   and updates `CHANGELOG.md`.

3. **Merge the release PR** when you're ready to ship. release-please then:
   - creates the git tag (`v0.3.0`),
   - publishes the GitHub Release with auto-generated notes.

4. The [`Release`](.github/workflows/release.yml) workflow runs on the published
   release: it builds the `sdist` + `wheel`, attaches them to the release, and
   publishes to PyPI.

That's it — no manual tagging, version editing, or changelog writing.

## One-time PyPI setup (Trusted Publishing)

The PyPI publish job uses OIDC Trusted Publishing, so there is **no API token
to manage**. Configure it once on PyPI:

1. Go to <https://pypi.org/manage/account/publishing/> (create the
   `gcp-finops-dashboard` project first, or add it as a *pending* publisher).
2. Add a **GitHub** trusted publisher with:
   - **Owner:** `mrmichou`
   - **Repository:** `gcp-finops-dashboard`
   - **Workflow:** `release.yml`
   - **Environment:** `pypi`
3. In the GitHub repo settings, create an **Environment** named `pypi`
   (Settings → Environments). Optionally add required reviewers to gate
   publishing behind a manual approval.

Until this is configured, the `pypi-publish` job will fail, but the GitHub
Release and its attached artifacts are created regardless — so nothing else
breaks.

## Notes

- Pull requests opened by release-please use the default `GITHUB_TOKEN`. The
  existing CI workflow still runs on them because it triggers on
  `pull_request`. (If you ever need release-please's *own* push events to
  trigger other workflows, switch the action to a Personal Access Token.)
- The current version lives in `.release-please-manifest.json` — it is managed
  automatically; don't edit it manually.
