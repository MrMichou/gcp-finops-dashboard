# Contributing

Thanks for your interest in improving the GCP FinOps Dashboard! This guide
covers the local workflow and the conventions CI enforces.

## Development setup

```bash
# Editable install with dev + optional extras.
python -m pip install --upgrade pip
pip install -e '.[dev]'

# Optional but recommended: install the git hooks (mirror the CI checks).
pip install pre-commit
pre-commit install
```

Python 3.11 and 3.12 are supported; CI runs the test matrix against both.

## Checks (must pass before merging)

These are exactly what runs in [CI](.github/workflows/ci.yml):

```bash
ruff check .                                    # lint
mypy src                                         # type-check
pytest --cov=gcp_finops_dashboard --cov-fail-under=85   # tests + coverage gate
```

You can run all the pre-commit hooks at once with:

```bash
pre-commit run --all-files
```

### Deployment artifacts

If you touch the container or deployment surfaces, CI also validates them — run
the equivalent locally when relevant:

```bash
hadolint Dockerfile
docker build -t gcp-finops-dashboard:dev .
helm lint deploy/helm/gcp-finops-dashboard
terraform -chdir=deploy/terraform fmt -check -recursive
```

## Commit messages — Conventional Commits

Commits and PR titles **must** follow
[Conventional Commits](https://www.conventionalcommits.org/). The type drives
the automated version bump and changelog (see [RELEASING.md](RELEASING.md)):

| Prefix | Effect |
| --- | --- |
| `fix:` | patch release |
| `feat:` | minor release |
| `feat!:` / `BREAKING CHANGE:` | breaking change |
| `docs:`, `refactor:`, `perf:`, `deps:` | changelog entry, patch |
| `chore:`, `ci:`, `test:`, `build:`, `style:` | no release on its own |

## Pull requests

1. Branch off `main`.
2. Keep the change focused; add or update tests.
3. Make sure all checks above pass.
4. Open a PR with a Conventional Commit title and fill in the template.

Releases are fully automated — never bump the version or edit `CHANGELOG.md`
by hand. See [RELEASING.md](RELEASING.md) for how shipping works.
