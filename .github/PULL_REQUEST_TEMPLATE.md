<!-- Title format: `type(scope): short imperative description` -->

## Summary

<!-- 1–3 bullets describing *why* this change exists. Link issues. -->

## Changes

<!-- Bullet list of concrete edits. Group related changes. -->

## Test plan

- [ ] `uv run ruff check src tests`
- [ ] `uv run ruff format --check src tests`
- [ ] `uv run mypy src`
- [ ] `uv run pytest -q`
- [ ] Manual verification: <commands or steps>

## Checklist

- [ ] Branch follows the documented flow (feature/fix → main)
- [ ] Commits use conventional commit format
- [ ] No secrets, tokens, or `.db` files committed
- [ ] Public API changes documented in `docs/CHANGELOG.md`
- [ ] New behavior is covered by tests

## Related

<!-- Closes #<issue>, refs #<issue>, security advisory link, etc. -->
