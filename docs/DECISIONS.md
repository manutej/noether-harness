# Decisions and judgments

The machine-readable record is `.noether/log.jsonl`, written as the work happened. Read it with `python3 .noether/noether.py log`. This file holds what was fixed in advance and a readable summary.

## Scoring rubric

Fixed before the improvement round and before any scoring. Evaluators are fresh and did not build this. The target is a weighted score of at least 9.5 from the panel.

| Axis | Weight | 10 means | Deduct when |
|---|---:|---|---|
| A. First run | 15 | A capable agent reaches a passing gate from `SKILL.md` alone, inventing nothing | You had to guess, read the runtime, or recover from an error the docs did not prepare you for |
| B. Gate correctness | 20 | Honest mistakes and lazy shortcuts cannot produce a false certificate, and good work is not falsely blocked | You reproduced a false pass or a false veto |
| C. Long-horizon survival | 15 | After a context reset, work resumes from what the harness kept, including why earlier choices were made | Something needed to continue was lost |
| D. Ceremony | 10 | Harness steps are small next to the work | A step adds no value for its cost |
| E. Composition | 15 | Chaining, parallel and nesting work as documented, and failures have a way forward | A documented path fails or dead-ends |
| F. Truthful docs | 10 | Every claim in the docs matches behaviour; limits are stated | You found a claim that is false or a limit that is hidden |
| G. Lean footprint | 5 | Little context, few files, no dependencies | Something loads or exists without earning it |
| H. Fit | 10 | Uses native features, does not rebuild them, is not over-engineered | A mechanism duplicates a native one or exceeds its value |

Scale for each axis: 10, nothing reproducible to deduct. 9, one small friction. 8, a minor defect with an easy workaround. 7, a real defect with a workaround. 6 or below, a documented path fails. Every deduction must cite something reproduced or quoted. A feature nobody promised is not a deduction. An environment limit, such as no subagent tool, is not a deduction.

## Scores

| Lens | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 |
|---|---:|---:|---:|---:|---:|
| Greenfield build | 8.5 | 8.5 | 9.05 | 9.15 | 8.4 |
| Messy adoption | 6.8 | 7.4 | 8.05 | 8.15 | 8.85 |
| Chains and recovery | 7.3 | 8.65 | 8.4 | 8.7 | 9.05 |
| Skeptical architect | 7.5 | 7.85 | 7.9 | 8.05 | 8.1 |
| **Mean** | **7.53** | **8.10** | **8.35** | **8.51** | **8.60** |

The target was 9.5. It was not reached: the last measured score is below it, and the fixes made after round five have not been scored. Rounds stopped because gains had slowed to about 0.1 per round and further work risked the over-engineering the owner ruled out.

## Decisions, as logged

```
2026-11-09T02:56:32Z decision   [polish] Quarantine is sticky for five straight passing commits (because one pass re-armed the veto and produced intermittent false rejects)
2026-11-09T02:56:32Z decision   [polish] Failed gates cost nothing; only a failed commit, brief or done costs an attempt (because probing with gate could saturate a unit in minutes, and frontier models iterate far more than this assumed)
2026-11-09T02:56:32Z decision   [polish] A failed evaluator cannot re-judge the same tree (because otherwise the retry rule could be sidestepped by asking the same evaluator again)
2026-11-09T02:56:32Z decision   [polish] Self-judging stays one sample and the docs say so (because repeating the same judge adds no independence; three failures still halt the unit)
2026-11-09T02:56:32Z decision   [polish] Assertions in tests that were never green are exempt from the weakening scan, but edited assertions in green tests still need a grant (because fixing a test that was wrong is the honest path; a line diff cannot tell strengthening from weakening, so the safe side stays strict)
2026-11-09T02:56:32Z decision   [polish] Lint ratchet only when the project configures ruff (because an unconfigured linter vetoed a first edit in projects that never asked for it)
2026-11-09T02:56:32Z decision   [polish] Did not implement scope checks against the unit's base commit (because that case needs a deliberate --no-verify, and chain integration already catches it)
2026-11-09T02:56:32Z decision   [polish] Did not add required brief before judge (because it would add a step without catching a defect)
2026-11-09T04:28:30Z decision   [polish] Round 3 panel so far 9.05, 8.4, 8.05 (because architect's score pending; recorded as received)
2026-11-09T04:28:30Z decision   [polish] A new failing test now fails the gate, tracked through a red list rather than a new check (because the messy panelist certified a unit that had added a red test; a red-count check would have run the suite twice)
2026-11-09T04:28:30Z decision   [polish] Node runs the project's own test script with the TAP reporter (because ignoring it left tests in non-default paths unprotected)
2026-11-09T04:28:30Z decision   [polish] A pytest proof fails only when its summary shows nothing passed (because trusting exit codes alone missed skip-only proofs, and requiring a summary falsely failed quiet configurations)
2026-11-09T04:28:30Z decision   [polish] A proof inside a chain stage is changed in the chain file (because integration re-runs the chain's proof, so changing only the unit made a sound stage fail)
2026-11-09T04:28:30Z decision   [polish] Pre-commit hook restores itself on first use in a clone (because hooks do not travel with git, and a new machine silently lost the gate)
2026-11-09T04:28:30Z decision   [polish] Planned units take their diff base when the previous unit finishes (because every pre-planned unit otherwise reported the whole history as its own change)
2026-11-09T04:30:35Z decision   [polish] Round 3 blind panel scored 8.35 weighted (9.05, 8.05, 8.4, 7.9) (because recorded before fixes; progression is 7.5, 8.1, 8.35)
2026-11-09T04:30:35Z decision   [polish] Do not flag every edited line in a green test, but do flag edited uppercase test constants (because the architect's change of an expected value slipped through; a blanket rule would veto ordinary test maintenance)
2026-11-09T04:30:35Z decision   [polish] A secret-shaped assignment in a test file is not a hard stop; real key formats still are (because a test fixture password froze a whole chain)
2026-11-09T04:30:35Z decision   [polish] Documented that evaluator independence is a protocol (because the runtime cannot verify who ran judge; claiming otherwise would be false)
2026-11-09T04:30:35Z decision   [polish] Chain nesting does not depend on subagents nesting (because chains nest through worktrees, so the doc should not claim anything about subagent depth)
2026-11-09T06:00:45Z decision   [polish] Round 4 blind panel scored 8.51 weighted (9.15, 8.15, 8.7, 8.05) (because recorded before fixes; progression is 7.5, 8.1, 8.35, 8.51)
2026-11-09T06:00:45Z decision   [polish] Stop after one more full panel round and report the real score (because the curve is flattening and each panel now finds narrower edge cases; continuing indefinitely would turn into the over-engineering the owner ruled out)
2026-11-09T06:00:45Z decision   [polish] A reopened stage keeps its own committed tests protected (because two panelists gutted their own test after reopen and the docs said a grant was needed)
2026-11-09T06:00:45Z decision   [polish] Replace the Edit and Write hook with native permissions.deny rules (because the architect noted native rules are enforced by Claude Code while a regex hook is best effort)
2026-11-09T06:00:45Z decision   [polish] Grants on a none check must include the printed text after the file name (because a file-wide pattern excused every later weakening in that unit)
2026-11-09T06:00:45Z decision   [polish] Leave --unit - commits unscoped (because that is its purpose, for files outside any unit such as a chain file; the receipt records what was touched)
2026-11-09T06:00:45Z decision   [polish] Keep four flake runs (because two would turn real flakes into false rejects, and a failing gate should not be the fast path)
2026-11-09T06:00:45Z decision   [polish] Do not qualify Go test names by package (because a test failing anywhere under a name already counts as not passing; the residual case needs a package to fail to build while a same-named test passes elsewhere)
2026-11-09T07:56:02Z decision   [polish] Round 5 blind panel scored 8.6 weighted (8.4, 8.85, 9.05, 8.1); the 9.5 target was not reached (because the score is reported as measured; progression is 7.53, 8.1, 8.35, 8.51, 8.6)
2026-11-09T07:56:02Z decision   [polish] Stop the rounds here, and fix only what certifies something false or misstates behaviour (because gains have slowed to about 0.1 per round while each panel finds narrower edge cases; pushing further would add machinery the owner has ruled out)
2026-11-09T07:56:02Z decision   [polish] Fixes made after round 5 were not re-scored (because a score must come from evaluators, and no panel has seen this exact build)
2026-11-09T07:56:02Z decision   [polish] Chain grants obey the same rules as command-line grants (because a bare star in a chain file landed deleted tests without any person being asked)
2026-11-09T07:56:02Z decision   [polish] Untracked Python files count toward public_api (because new symbols were unprotected until the commit after they were added)
2026-11-09T07:56:02Z decision   [polish] Keep unit reopen resetting attempts (because it requires a person in Claude Code, is logged, and is recorded in the receipt)
2026-11-09T07:56:02Z decision   [polish] Do not add per-test AST hashing for weakening (because a semantic check is a project of its own; documented as a limit)
2026-11-09T08:15:07Z decision   [polish] Restored the original chain fixture line in the test instead of granting an exception (because the harness flagged my own edit, and there was a way to make the change without weakening anything, so no grant was needed)
2026-11-09T08:43:19Z decision   [polish] The final evaluator failed the unit; fixed its findings rather than arguing with the score (because a bare star could still slip through a grant prefix, and several tests would have passed with the feature removed)
2026-11-09T09:02:19Z decision   [polish] When every test fails, name the losses instead of saying the suite did not run (because the veto held either way, but an agent told 'did not run' goes looking for a broken toolchain instead of its own regression)
2026-11-09T09:37:04Z decision   Reversed the never-green exemption: rewriting or deleting a red test's assertions needs a named grant (because the owner spotted it on the explainer; reproduced: assert True passed the gate and entered the baseline as green, and the exemption's own test did exactly that)
2026-11-09T09:37:04Z decision   Committed at the owner's request with unit polish still open; two fresh evaluators failed it (because the owner chose to stop and test this version; the deterministic gate is green, the verdicts stand as failed, and the reproduced defects are listed as open rather than scored over)
```

## Judgments, as logged

```
-                    judge      [ceremony] fable-evaluator-ceremony passed {'acceptance': 0.75, 'maintainable': 0.8, 'test_honesty': 0.75}
-                    judge      [ceremony] fable-evaluator-2 passed {'acceptance': 0.75, 'maintainable': 0.8, 'test_honesty': 0.75}
-                    judge      [records] fable-evaluator-2 passed {'acceptance': 0.7, 'maintainable': 0.75, 'test_honesty': 0.7}
-                    unit_done  [records] grants=0
-                    unit_done  [ceremony] grants=0
2026-11-09T08:14:45Z reject     [polish] failures=['secrets', 'tests_not_weakened']
2026-11-09T08:25:05Z reject     [polish] failures=['secrets']
2026-11-09T08:42:35Z judge      [polish] fable-evaluator-final FAILED {'acceptance': 0.5, 'maintainable': 0.7, 'test_honesty': 0.5}: grant tests --allow 'lost: *' (or 'new failure: *') bypasses the bare-star guard and stores allow=['*'], excusing every lost test; the exact 'new failure: X' line the gate prints cannot be granted at all; build-cache e2e check passes with the exclusion removed, two ck(..., True) checks, and quarantine visibility has no test
2026-11-09T09:29:43Z judge      [polish] fresh-eval-a FAILED {'acceptance': 0.45, 'maintainable': 0.65, 'test_honesty': 0.7}: acceptance: the bare-star fix is a literal check; ?* and "*: *" pass CLI grant and chain typecheck and land deleted tests unasked; reopening an integrated stage loses certified work at land; land --merge skips stage proofs/checks and drops uncommitted log on failure
2026-11-09T09:36:37Z judge      [polish] fresh-eval-b FAILED {'acceptance': 0.8, 'maintainable': 0.65, 'test_honesty': 0.5}: test_honesty: removing the secret hash suffix, the grant must-match rule or the land --merge gate leaves every e2e check green; three goal items have tests that cannot fail
2026-11-09T09:36:37Z saturated  [polish] why=judges
```
