---
name: noether-harness
description: Keeps long-running coding agents honest. Tools veto regressions, fresh evaluators grade, baselines only ratchet, and harnesses chain or nest with typed receipts. Use for Noether harness, conservation lens, long-horizon coding, or chaining agents without breaking working code.
---

# Noether Harness

A long task fails by drift: each step looks fine and the sum does not. This harness names what must be conserved, measures it from repo state, and refuses any commit that loses it. You keep your full ability to plan, edit and recover; the harness only decides what counts as kept.

## Start

```
python3 <this skill's directory>/scripts/noether.py init --claude   # omit --claude outside Claude Code
python3 .noether/noether.py commit -m "noether: init"
```

`init` needs a git repo with a commit. It detects checks, baselines the current commit, installs a git pre-commit gate, and copies the runtime into `.noether/`, so later sessions need only the repo. Read its warnings. Below, `n` means `python3 .noether/noether.py`.

## Constructs

| Construct | What it is | Where it lives |
|---|---|---|
| **Check** | A measurement of repo state with an order: `pass`, `keep` (nothing lost), `none` (no violations), `max`, `min` | `.noether/harness.json` |
| **Harness** | Checks + scope + budgets. It decides; you do not | `.noether/` |
| **Loop** | Bounded work units, each ending in a proof command | `.noether/units/` |
| **Agent** | An untrusted worker with a declared footprint: you, or a subagent | a chain stage |
| **Skill** | A capability bound to an agent | a chain stage's `agents` entry |
| **Receipt** | What a harness certifies at one exact tree | the unit file |
| **Chain** | Sequence, parallel or nesting of stages, each binding the above | `chain.json` |

## Contract

- **A commit needs the state to be at least the baseline, on every check.** Baselines are high-water marks, so slow drift cannot accumulate. Commit only with `n commit` (`--unit -` for files outside any unit, like a chain file).
- **Exact checks veto. Nothing averages them away.** Tests that were red before you started do not block you. Tests that were green must stay green.
- **Evaluate once, fresh, at the end of a unit.** Every evaluator must clear every axis. Each failed evaluation raises how many must, and three failures halt the unit.
- **Never make a check pass by weakening it.** If a test is wrong, say so and ask. Exceptions name exactly what is excused and appear in the receipt: `n grant CHECK --unit U --allow 'glob' --reason "<the person's words>"`. In Claude Code a hook asks the person; elsewhere nothing enforces that, so only grant what the person actually asked for.
- **When a unit saturates or the gate halts, stop and report.** Never loosen a check to get through.

## Working a long task

1. **Cut the work into units.** `n unit add ID --goal "..." --proof "<command that exits 0 only when this is true>" [--scope 'glob' ...]`. The proof states the end state, so a pure refactor is provable too (for example, that the old module is gone).
2. **Work however suits the problem.** Run `n gate` when you want a verdict. It exits 0 pass, 1 reject, 2 halt, and rechecks only when the tree changes. Attempts count only for distinct failing trees.
3. **Commit at stable points** with `n commit -m "..."`.
4. **Finish a unit.** Give a subagent the output of `n brief`, and none of your reasoning. It records its verdict with `n judge`. Then run `n done`, which reruns the gate and the proof, checks the verdicts, writes the receipt and commits. With no subagents available, judge inline using `--by self`; the receipt records it.
5. **After any reset or compaction, run `n status`.** It gives you units, the current goal, proof and scope, the last verdict, grants and the working tree. With `--claude`, it is injected automatically after compaction or resume.

For unattended runs in Claude Code, `n goal` prints a condition for `/goal`. Add a subagent, `/loop` or a schedule as the work needs; those are native and the harness does not replace them.

## Your judgment

The harness cannot decide these:

- **What to conserve here.** Prefer a check that measures state over a judge that reads a diff. If a rule can be a linter, make it one.
- **The proof for each unit**, and how to size units.
- **Whether a failure is the code or the check.** Investigate; do not retry blindly.
- **When to involve a person**: a saturated unit, a strangling reject rate, a grant you think is needed, or anything irreversible.

## Learning what to conserve

When a defect slips through, add the check that would have caught it:

```
n learn add no_raw_sql --cls none --cmd "<prints one line per violation>" --why "<the failure you saw>"
n learn confirm no_raw_sql --real yes      # after each would-be veto you verified was a real defect
n learn promote no_raw_sql                 # needs enough evidence, e.g. 5 of 5 confirmed
```

New checks run in shadow, logging what they would have blocked and blocking nothing. Promotion needs evidence. Protected checks can never be retired, because a check that never fires is working. Retiring any other check is a person's decision (`n learn retire ID`).

## Chains

For work that divides, or needs several agents each under its own harness, write a `chain.json`:

```
{"name": "x", "flow": "(api | ui) ; review", "stages": {"api": {"goal": "...", "proof": "...", "writes": ["src/api/**"]}, ...}}
```

`n chain check` refuses overlapping footprints, unmet needs and budget overruns before anything starts. `n chain next` says what to do, `n chain start` prepares a worktree and a brief for one stage, and `n chain integrate` merges certified stages and re-verifies everything on the combined tree, atomically. Read `references/chains.md` before writing one.

## Limits

This is tamper-evident, not a sandbox: an agent determined to bypass it can. It proves nothing about the model, and a passing gate means only that the named quantities held. Three gaps to know:

- The gate runs in your working directory, so gitignored files can affect it. Chain integration runs on a clean checkout.
- Weakening a test without removing an assertion (an early `return`, say) is left to the evaluator's `test_honesty` axis.
- `public_api` treats a moved symbol as lost, even if re-exported. Grant it with `--allow 'module.Name*'`.

Why it is built this way: `references/theory.md`.
