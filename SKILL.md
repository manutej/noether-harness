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

`init` needs a git repo with a commit and a clean tree (`--dirty` baselines it as is; your next commit then includes those edits. `--force` re-detects checks). It detects checks, baselines the current commit, installs a git pre-commit gate, and copies the runtime into `.noether/`, so later sessions need only the repo. Read its warnings. Below, `n` means `python3 .noether/noether.py`.

## Constructs

| Construct | What it is | Where it lives |
|---|---|---|
| **Check** | A measurement of repo state with an order: `pass`, `keep` (nothing lost), `none` (no violations), `max` and `min` (a number that must not rise above or fall below the baseline) | `.noether/harness.json` |
| **Harness** | Checks + scope + budgets. It decides; you do not | `.noether/` |
| **Loop** | Bounded work units, each ending in a proof command | `.noether/units/` |
| **Agent** | An untrusted worker with a declared footprint: you, or a subagent | a chain stage |
| **Skill** | A capability named in an agent's binding, passed at spawn and recorded in the receipt | a chain's `agents` entry |
| **Receipt** | What a harness certifies at one exact tree | the unit file |
| **Chain** | Sequence, parallel or nesting of stages, each binding the above | `chain.json` |

## Contract

- **A commit needs the state to be at least the baseline, on every check.** Baselines are high-water marks, so slow drift cannot accumulate. Commit only with `n commit` (`--unit -` for files outside any unit, like a chain file).
- **Exact checks veto. Nothing averages them away.** Tests that were red before you started do not block you. Fixing the code behind one is free; editing or deleting its assertions needs a named grant, like any other test. A new test must not be red. Tests that were green must stay green, unless they also flake on the unchanged code; those are reported on each gate and receipt while they fail, and protected again after five straight passing commits.
- **Evaluate once, fresh, at the end of a unit.** Every evaluator must clear every axis. With independent evaluators, each failed evaluation raises how many must. Three failures halt the unit.
- **Never make a check pass by weakening it.** If a test is wrong, say so and ask. Exceptions name exactly what is excused and appear in the receipt: after `n gate`, run `n grant CHECK --unit U --allow 'pattern' --reason "<the person's words>"`, copying the line the gate printed, with `*` if needed. `--axis` waives one soft axis for a unit, the same way. In Claude Code a hook asks the person; elsewhere nothing enforces that, so only grant what the person actually asked for. A secret finding can be excused only as one exact false positive, copied from the gate's output.
- **When a unit saturates or the gate halts, stop and report.** Never loosen a check to get through.

## Working a long task

1. **Cut the work into units.** `n unit add ID --goal "..." --proof "<command that exits 0 only when this is true>" [--scope 'glob' ...]`. The proof is required, and the unit file is committed with the unit; change a wrong proof or goal with `n unit reopen ID --proof "..." --goal "..."`. Scope globs use `*` across directories. The proof states the end state, so a pure refactor is provable too (for example, that the old module is gone).
2. **Work however suits the problem.** `n gate` (optional) gives a verdict any time and costs nothing. It exits 0 pass, 1 reject, 2 halt, and rechecks only when the tree changes (`--fresh` forces it). A failed commit, brief or done costs one attempt per distinct tree. `n commit -m "..."` (optional) makes a checkpoint of everything not ignored, so keep scratch files ignored.
3. **Finish a unit.** Run `n brief`, which refuses if the gate is red. Give its output to a subagent, with none of your reasoning; it records its verdict with `n judge`. Then run `n done` (it takes no message), which reruns the gate and the proof, checks the verdicts, writes the receipt and commits. With no subagents available, judge inline using `--by self`. Extra self-samples add no independence, so one is enough even after a failure; the receipt records it.
4. **Record real choices.** When you pick between live alternatives, run `n decide "what" --why "why"`. `n log` shows every decision and judgment (`--only decisions` for just the choices); the record is committed with the repo, so the reasons survive resets and machines.
5. **After any reset or compaction, run `n status`.** It gives you units, the current goal, proof and scope, the last verdict, grants, recent decisions and the working tree. With `--claude`, it is injected automatically after compaction or resume.

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
n learn promote no_raw_sql                 # needs at least 4 confirmed fires on different code
```

New checks run in shadow, logging what they would have blocked and blocking nothing. Promotion needs evidence. Protected checks can never be retired, because a check that never fires is working. Retiring any other check is a person's decision (`n learn retire ID`).

## Chains

For work that divides, or needs several agents each under its own harness, write a `chain.json`:

```
{"name": "x", "flow": "(api | ui) ; review", "stages": {"api": {"goal": "...", "proof": "...", "writes": ["src/api/**"]}, ...}}
```

`n chain check` refuses overlapping footprints, unmet needs and budget overruns before anything starts. `n chain next` says what to do, `n chain start` prepares a worktree and a brief for one stage, and `n chain integrate` merges certified stages and re-verifies everything on the combined tree, atomically. Read `references/chains.md` before writing one.

## Limits

This is tamper-evident, not a sandbox: an agent determined to bypass it can. It proves nothing about the model, and a passing gate means only that the named quantities held. Gaps to know:

- The gate runs in your working directory, so gitignored files can affect it. It warns about gitignored test files, and chain integration runs on a clean checkout.
- Weakening a test without removing an assertion or uppercase test constant (an early `return`, say) is left to the evaluator's `test_honesty` axis. Nothing can verify who ran `judge`: independence comes from following the protocol.
- Tests are identified by name, so renaming a test, or editing an `assert` line in place, needs a grant. A change to the numbers a test compares against, away from the `assert` line and not an uppercase constant, is left to the evaluator.
- `public_api` (Python only) treats a moved symbol as lost, even if re-exported. Grant it with `--allow 'module.Name*'`.
- A hook asks for a person in Claude Code only. Python, `node --test`, Go and Cargo get per-test tracking; other runners get pass or fail, and if those start red they run in shadow and every gate warns.

Why it is built this way: `references/theory.md`.
