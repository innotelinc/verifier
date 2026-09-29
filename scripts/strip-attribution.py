#!/usr/bin/env python3
"""Rewrite a repository's history so no commit credits anyone but the owner.

The estate's [attribution policy](../../docs/attribution-policy.md) allows exactly one
name in a commit: the owner's. The guard in `.githooks/` stops *new* commits, but it
cannot reach backwards — a commit that already carries a foreign trailer stays in the
history forever, visible to anyone who runs `git log`. This removes those trailers.

Only commit *messages* are rewritten. Author and committer identities, timestamps,
tree contents and parentage are all left exactly as they were, so the rewrite is
content-preserving: `git diff` between an old commit and its replacement is empty.

    python3 scripts/strip-attribution.py .              # report, change nothing
    python3 scripts/strip-attribution.py . --apply       # rewrite, after a backup
    python3 scripts/strip-attribution.py . --apply --push   # rewrite and force-push

Rewriting history is not reversible in the usual sense: every other clone of the
repository keeps the old commits and will need to re-clone or reset. The tool takes a
bundle backup first and refuses to continue without it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

# A line is dropped when it credits a tool. These are the two shapes the estate
# actually contains, plus the generic trailers the policy names.
CREDITS_TOOL = re.compile(
    r"(?i)("
    r"codebuff|freebuff"
    r")"
)
# The owner's own trailers are allowed through untouched.
OWNER = re.compile(r"(?i)dhunter@innotel\.us|Darnel Hunter")


def run(args: list[str], cwd: Path, stdin: str | None = None) -> str:
    result = subprocess.run(
        args, cwd=cwd, input=stdin, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(args)}\n{result.stderr.strip()}")
    return result.stdout


def clean_message(message: str) -> str:
    """Drop attribution lines, then the blank lines they leave behind.

    A message that ended in a two-line credit block ends, once those lines are gone, in
    a run of blank lines. Tidying them is the difference between a message that ends
    where the prose ends and one that ends in whitespace.

    The names themselves are never written out here: this file lives inside the very
    guard that rejects attributions, and a literal example would be a literal match.
    """
    kept: list[str] = []
    for line in message.splitlines():
        # Any line naming the tool is attribution, whatever it calls itself — the
        # trailers here are not always well-formed, and a strip that only matched the
        # tidy spelling would leave the untidy ones behind. The one line that must
        # survive is the owner's own, which may sit next to a tool name in prose.
        if CREDITS_TOOL.search(line) and not OWNER.search(line):
            continue
        kept.append(line)
    while kept and not kept[-1].strip():
        kept.pop()
    return "\n".join(kept) + "\n"


def offending(repo: Path) -> list[tuple[str, str]]:
    """Every commit whose message credits a tool: (sha, matching lines)."""
    out = run(
        ["git", "log", "--all", "--format=%H%x00%B%x1e", "--no-color"], repo
    )
    found: list[tuple[str, str]] = []
    for record in out.split("\x1e"):
        record = record.strip("\n\x00")
        if not record.strip():
            continue
        sha, _, message = record.partition("\x00")
        hits = [line for line in message.splitlines() if CREDITS_TOOL.search(line)]
        if hits:
            found.append((sha.strip(), "; ".join(hits[:3])))
    return found


def backup(repo: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    target = repo / ".git" / f"pre-strip-{stamp}.bundle"
    run(["git", "bundle", "create", str(target), "--all"], repo)
    return target


def apply_rewrite(repo: Path, self_path: Path) -> None:
    # `--msg-filter` runs the process once per commit with the message on stdin.
    # `--tag-name-filter cat` keeps tags pointing at their rewritten commits;
    # without it every tag would be left dangling on the old history.
    env = {"FILTER_BRANCH_SQUELCH_WARNING": "1"}
    subprocess.run(
        [
            "git", "filter-branch", "-f",
            "--msg-filter", f"python3 {self_path} --clean",
            "--tag-name-filter", "cat",
            "--", "--all",
        ],
        cwd=repo, env={**__import__("os").environ, **env}, check=False,
    )


def prune(repo: Path) -> None:
    """Throw away the pre-rewrite refs so the old commits are not still reachable."""
    for_original = run(
        ["git", "for-each-ref", "--format=%(refname)", "refs/original/"], repo
    ).split()
    for ref in for_original:
        run(["git", "update-ref", "-d", ref], repo)
    run(["git", "reflog", "expire", "--expire=now", "--all"], repo)
    run(["git", "gc", "--prune=now", "--aggressive", "--quiet"], repo)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo", nargs="?", default=".", help="the repository to rewrite")
    parser.add_argument("--apply", action="store_true", help="rewrite history (takes a backup first)")
    parser.add_argument("--push", action="store_true", help="force-push every branch and tag when done")
    parser.add_argument("--clean", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    # The filter-branch child: read a message, write the cleaned one, touch nothing else.
    if args.clean:
        sys.stdout.write(clean_message(sys.stdin.read()))
        return 0

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        print(f"{repo} is not a git repository", file=sys.stderr)
        return 2

    hits = offending(repo)
    if not hits:
        print(f"{repo.name}: clean — no commit credits a tool")
        return 0

    print(f"{repo.name}: {len(hits)} commit(s) carry a tool credit")
    for sha, line in hits[:5]:
        print(f"  {sha[:9]}  {line[:96]}")
    if len(hits) > 5:
        print(f"  … and {len(hits) - 5} more")

    if not args.apply:
        print("  (report only — pass --apply to rewrite)")
        return 0

    bundle = backup(repo)
    print(f"  backup: {bundle} ({bundle.stat().st_size // 1024} KiB)")

    apply_rewrite(repo, Path(__file__).resolve())
    prune(repo)

    remaining = offending(repo)
    if remaining:
        print(f"  !! {len(remaining)} commit(s) still carry a credit — not pushing", file=sys.stderr)
        return 1
    print("  history rewritten; no commit credits a tool any more")

    if args.push:
        if not shutil.which("git"):
            print("  git vanished mid-run", file=sys.stderr)
            return 1
        remote = run(["git", "remote", "get-url", "origin"], repo).strip()
        run(["git", "push", "--force", "--all", "origin"], repo)
        run(["git", "push", "--force", "--tags", "origin"], repo)
        print(f"  force-pushed to {remote}")
    else:
        print("  pass --push to force-push (or push manually)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
