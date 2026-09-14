# envguard

A small git pre-commit guard for two things that go wrong in almost every
repo that uses a `.env` file:

1. **A required variable is missing or still a placeholder** — you pull the
   repo, forget to fill in `.env`, and the app fails at startup with a
   confusing error three layers deep.
2. **A real secret gets committed** — an API key ends up in a config file,
   `.env` gets `git add`-ed by accident, and now it's in history forever.

`envguard` is a zero-dependency Python CLI that checks for both, and installs
itself as a git hook so the check runs automatically before every commit.

This isn't a novel idea — [gitleaks](https://github.com/gitleaks/gitleaks),
[git-secrets](https://github.com/awslabs/git-secrets), and
[dotenv-linter](https://github.com/dotenv-linter/dotenv-linter) all cover
pieces of this. The point of building it wasn't originality — it's a tool
small enough to fully own: every regex, every edge case in the `.env`
parser, and the exact rule for what counts as "still a placeholder" is a
choice I made and can explain, not a black box.

## What it checks

### `envguard check` — is `.env` actually ready?

Compares your `.env` against `.env.example` and reports:

- **missing** — a key `.env.example` declares that `.env` doesn't have at all
- **unfilled** — present, but still empty, a placeholder word (`changeme`,
  `TODO`, `<your-key-here>`, ...), or copied verbatim from the example
- **undocumented** — in `.env` but not in `.env.example` (informational —
  doesn't fail the check, just flags drift)

```
$ envguard check
Missing from .env (declared in .env.example):
  - GITHUB_TOKEN
Still look like placeholders in .env:
  - ANTHROPIC_API_KEY

envguard: environment is not ready - see above.
```

### `envguard scan` — is a secret about to be committed?

Scans file contents (or, with `--staged`, exactly what's in the git index —
not your unstaged edits) for known credential shapes (AWS keys, GitHub
tokens, Anthropic/OpenAI/Stripe/Slack keys, PEM private key blocks) plus a
generic rule for `SOMETHING_KEY=<long value>`-style assignments. Matches are
masked in the output (`AKIA****************MNOP`) so the finding itself
doesn't become a second leak.

```
$ envguard scan --staged
envguard: 1 possible secret(s) found:

  config/settings.py:14: [AWS Access Key ID] AKIA****************MNOP

If a match is a false positive, add `# envguard:ignore` on that line, or
move the real secret out of the repo (e.g. into your local .env).
```

### `envguard install-hook` — wire it into git

```
$ envguard install-hook
envguard: installed pre-commit hook at .git/hooks/pre-commit
```

From then on, `git commit` runs `envguard scan --staged` first and blocks
the commit if it finds something. It refuses to overwrite a pre-commit hook
it didn't create unless you pass `--force` (which backs up the old one to
`pre-commit.bak.envguard` — restored by `envguard uninstall-hook`).

## Install

```bash
git clone <this-repo>
cd envguard
pip install -e ".[dev]"
```

No third-party runtime dependencies — the checker, scanner, and hook
installer are all standard library (`re`, `subprocess`, `pathlib`).

## Usage in another project

```bash
cd your-project
pip install -e /path/to/envguard   # or `pip install envguard` once published
envguard install-hook
envguard check                      # run manually any time
```

## Tests

```bash
pytest -v
```

49 tests, no network access and no fixtures beyond temp directories and a
real (throwaway) git repo per test — `test_hook.py` and `test_git_utils.py`
actually `git init` in `tmp_path` rather than mocking subprocess calls,
since the hook script and the staged-vs-working-tree distinction are the
parts most worth testing for real.

## Design notes / known limits

- The secret scanner is a fixed pattern list plus one heuristic, not an
  entropy-scoring engine — it will miss secret shapes it doesn't know about
  and won't catch a high-entropy string in a variable that doesn't look like
  `*_KEY`/`*_TOKEN`/`*_SECRET`/`*_PASSWORD`. Extending `_KNOWN_PATTERNS` in
  `scanner.py` is the intended way to add coverage for a new provider.
- `check` only understands the flat `KEY=VALUE` `.env` format — no
  multi-line values, no variable interpolation (`${OTHER_VAR}`).
- The pre-commit hook shells out to the installed `envguard` command, so it
  needs to be on `PATH` inside whatever environment runs `git commit`
  (a venv that's activated, or a global install).

## License

MIT — see [LICENSE](LICENSE).
