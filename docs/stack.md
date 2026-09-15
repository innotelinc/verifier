# Verifier in the Innotel Platform Stack

**Role: PlatformOps** — the portfolio's cross-cutting conformity and attribution
tooling.

Verifier is not a product surface. It packages guarantees every other platform
adopts verbatim — the attribution guard, the conformity scaffolding, and the
self-test that proves both still fire — so the portfolio's rules live in one
place and cannot drift between repos.

This page declares Verifier's role in the
[**Innotel Platform Stack**](https://github.com/innotelinc/innotel-platform-stack) —
the canonical single-responsibility architecture. The stack is defined in exactly
one place; this page links the platform to it and states what it owns, consumes,
provides, and explicitly does not own.

## Owns

- The attribution policy: one `guard-lib`, enforced at `commit-msg`, `pre-commit`,
  and CI
- Conformity scaffolding: repository structure, guard workflows, landing layout
- The guard self-test (`make check-guard`) that forces the guard's failure paths
- Portfolio drift detection across sibling repos' vendored guard copies

## Provides

- Guard hooks + workflows vendored into every platform repository
- `scripts/setup.sh`, `make check-guard` and `make check-commits` as the receipt
  that the guard fires
- A CI-visible, runnable definition of "conformant" for the rest of the portfolio

## Consumes

- Cerulean Vault — secrets (SecretOps). Verifier ships no runtime and holds no
  secrets of its own; it states the posture so the portfolio has one rule.

## Explicitly does NOT own

- Identity (Authentik)
- Secrets (Cerulean Vault)
- Trust / DNS / TLS (Cerulean)
- Storage (ONYX)
- Billing (Magnate)
- Any product surface — Verifier is tooling, not a platform

## Service map (Verifier-owned)

| Component | Technology | Job |
| --- | --- | --- |
| Attribution guard | bash + git hooks | Reject foreign credit lines locally and in CI |
| Guard self-test | bash (`scripts/setup.sh`) | Prove the guard still fires on banned input |
| Drift workflow | GitHub Actions | Fail CI if a sibling repo's guard copy differs |
| Landing page | static `web/landing/index.html` | Public face (GitHub Pages) |

## In the ecosystem

| Flow | Path |
| --- | --- |
| Identity | Cerulean's Authentik → GitHub repository access (no runtime identity) |
| Secrets | Cerulean Vault (SecretOps, KV v2) → `vault://` references in `.env`; never committed |
| Trust | Cerulean issues DNS + per-zone wildcard TLS; NPM Edge fronts public hosts |
| Revenue | None — tooling carries no billing |
| Source of truth | This repository's `docs/stack.md` points back to the Innotel Platform Stack |

Back to the canonical definition: the
[Innotel Platform Stack](https://github.com/innotelinc/innotel-platform-stack).
