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

4. Two workflows run on the published release and attach artifacts to it:
   - [`Release binaries`](.github/workflows/release-binaries.yml) builds
     standalone single-file executables (Linux, macOS x86_64/arm64, Windows)
     with PyInstaller and uploads them, each with a `.sha256` checksum.
   - [`Publish Docker image`](.github/workflows/docker-publish.yml) builds and
     pushes the multi-arch container image to GHCR.

That's it — no manual tagging, version editing, or changelog writing.

## Re-firing the publish workflows

> **Important:** a release created by release-please uses the default
> `GITHUB_TOKEN`, and GitHub does not let token-generated events trigger other
> workflows. So merging the release PR creates the Release but the binary/Docker
> workflows **do not start on their own**.

To actually publish the assets, re-fire the release with a real user token:

```bash
# Re-run the workflows for an existing release (simplest):
gh workflow run "Release binaries" -f tag=v0.3.0
# or re-publish the release to fire both workflows:
gh release delete v0.3.0 --yes --cleanup-tag=false
gh release create v0.3.0 --title v0.3.0 --notes-from-tag
```

(The permanent fix would be giving release-please a Personal Access Token so its
release event triggers downstream workflows; not currently configured.)

## Notes

- Distribution is via the **GitHub Release binaries** and the **GHCR container
  image** (plus the Helm chart). There is no PyPI publishing.
- Pull requests opened by release-please use the default `GITHUB_TOKEN`. CI still
  runs on them because it triggers on `pull_request`.
- The current version lives in `.release-please-manifest.json` — it is managed
  automatically; don't edit it manually.
