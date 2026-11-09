# noether-harness

A conservation gate for long-running coding agents. It names what must not be lost, measures it from repo state, and refuses any commit that loses it. Harnesses chain, run in parallel and nest, with typed receipts between them.

## Progressive disclosure

Most of this repo never enters a model's context. Each layer loads only when the one above asks for it.

| Layer | File | Size | Loaded |
|---|---|---|---|
| 0. Trigger | `description` in `SKILL.md` | 276 characters | Always |
| 1. Contract | `SKILL.md` | about 2.3k tokens | When the skill triggers |
| 2. Chains | `references/chains.md` | about 1.3k tokens | Only when writing a chain |
| 2. Why | `references/theory.md` | about 1.5k tokens | Only when explaining or extending the design |
| 3. Runtime | `scripts/noether.py` | not read | Executed, then copied into your repo's `.noether/` |
| 4. Live state | `n status` | short | Printed on demand, and after compaction in Claude Code |

The previous version asked a model to read about 18k tokens before it could act, and left it to hand-write the machinery.

## Install

**Claude Code, as a plugin** (needs read access to this repo):

```
claude plugin marketplace add manutej/noether-harness
claude plugin install noether-harness@noether
```

**claude.ai:** upload `dist/noether-harness.skill`.

**Anywhere else with Python and git:** run `python3 scripts/noether.py init`. No dependencies.

## Use

```
python3 <skill dir>/scripts/noether.py init --claude     # omit --claude outside Claude Code
python3 .noether/noether.py commit -m "noether: init"
python3 .noether/noether.py unit add feat --goal "..." --proof "<exits 0 only when done>"
# work; then:
python3 .noether/noether.py brief      # refuses a red tree; give the output to a fresh evaluator, which runs `judge`
python3 .noether/noether.py done       # `gate` and `commit` are optional checkpoints along the way
python3 .noether/noether.py log        # every decision and judgment, with reasons
```

`SKILL.md` is the full guide.

## One skill, deliberately

Three reviewers looked at splitting this into gate, chains, learning and evaluator skills. All three said not to. The parts share one runtime and one state directory, and a chain's receipts are pinned to that runtime's exact bytes, so a split would either duplicate it or break verification. Separate skills would also compete on the same trigger words. Progressive disclosure already delivers what a split would.

Revisit this if chains ever need their own state or have to run in repos with no gate. In that case the chain skill should depend on this runtime, not copy it.

## How it was tested

`python3 tests/e2e.py` runs about 150 checks on real, throwaway git repos: gaming attempts, flaky tests, drift, typed exceptions, hooks, context recovery, parallel conflicts, nesting and hard stops.

Five rounds of blind review scored it 7.53, 8.1, 8.35, 8.51 and 8.6 out of 10 against a fixed rubric. The target was 9.5, and it was not reached. Fixes after the last round are not scored. The last unit, `polish`, was committed with two fresh evaluators' failing verdicts on record; the defects they reproduced are listed as open in the change ledger. See [`docs/DECISIONS.md`](docs/DECISIONS.md) for every decision and judgment, [`docs/CHANGELOG.md`](docs/CHANGELOG.md) for every change, and [`docs/LEDGER.md`](docs/LEDGER.md) for the original review. The rule was to fix what would certify something false or stop normal use, and to state everything else as a limit.

## Limits

It is tamper-evident, not a sandbox. It proves nothing about the model. A passing gate means the named quantities held, nothing more. Python gets the deepest checks out of the box; other languages start with their test command, type errors where available, secrets and test-weakening.
