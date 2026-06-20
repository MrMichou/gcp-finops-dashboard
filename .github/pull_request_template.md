<!--
Use a Conventional Commit style title, e.g.:
  feat: add cost forecast panel
  fix: handle empty billing export
The title drives the changelog and version bump (see RELEASING.md).
-->

## What & why

<!-- Summarise the change and the motivation. Link issues with "Closes #123". -->

## Type of change

- [ ] `fix` — bug fix (patch)
- [ ] `feat` — new feature (minor)
- [ ] `docs` / `refactor` / `perf` / `deps`
- [ ] `chore` / `ci` / `test` / `build` (no release on its own)
- [ ] Breaking change (`feat!:` / `BREAKING CHANGE:`)

## Checklist

- [ ] `ruff check .` passes
- [ ] `mypy src` passes
- [ ] `pytest` passes (coverage stays ≥ 85%)
- [ ] Docs updated if behaviour or config changed
- [ ] Deployment artifacts updated if relevant (Dockerfile / Helm / Terraform)
