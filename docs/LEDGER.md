# Usability ledger for long-horizon coding

Six independent reviewers roasted the previous skill, on separate lanes: frontier practice, composition, conservation maths, a real dry run, packaging and orchestration. The rebuild then went to three more who had not built it: a red team, a blind user and a maths check on the actual code. All findings were checked before use.

**The rule for what got fixed:** a change goes in only if it stops the harness certifying something false, or stops normal use. Everything else is cut or stated as a limit.

## Scores

| Measure | Previous skill | Rebuilt |
|---|---|---|
| Long-horizon feasibility | 3/10 | Not re-scored |
| Out-of-the-box usability | 3/10 (dry run) | 8.6/10 (five-round blind panel; see DECISIONS.md) |
| Must read before acting | about 18k tokens | about 2.3k tokens |
| Files hand-written before the first gate | 18 | 0 |
| Time to first gate | 177 s, after building the machinery | about 140 s, including recovering from two bugs since fixed |
| Harness versus work tokens per commit | 30:1 (soft judges every repair step) | Judged once per unit |
| Could resume after a context reset | No | Yes, from `status` |
| Chaining | Absent | Sequence, parallel, nesting |

Later rounds are recorded in `docs/DECISIONS.md` and `docs/CHANGELOG.md`.

## What the frontier review changed

| Previous design | Decision | Why |
|---|---|---|
| Targets six third-party frameworks; never mentions Claude Code | Cut | Unverified fragments for tools not in use. The runtime is plain Python and CLI |
| Inner loop with a budget of 3, role prompts on one model | Cut | Native loops and subagents do this. Opus 5.5 reportedly runs for many hours, so scaffolding built for short horizons gets in the way |
| Verdict computed by an LLM following prose | Replaced with code | The decision is arithmetic. The first adversarial pass had already found the prose version wrong |
| State in framework checkpointers | Replaced | On disk in the repo, recoverable by a fresh session |
| Weighted confidence mean against tau | Cut | One bad axis gets averaged away (99.5% accept in simulation) |
| Soft judges at every repair step | Replaced | One fresh evaluator per unit. Separate context removes self-grading |
| Soft escape with TTL | Replaced | Typed, named grants |
| `hooks:` in skill frontmatter (proposed) | Rejected | claude.ai rejects that key outright. `init --claude` writes hooks into the project instead |
| `tests_not_weakened`, API stability, secret veto | Kept | No native feature compares tests against a baseline. This is the skill's real value |

## What the mathematics review changed

| Previous construct | Finding | Decision |
|---|---|---|
| Monoidal lens category | No `put`; really a monoid on verdicts | Replaced by a product order on checks |
| Internal hom, retract, Free ⊣ Forgetful, 2-cell | The named structures are not present | Renamed to what they are, or cut |
| Pass/fail lens with tolerance | A monotone ratchet composes and bounds drift | Core object is now a check with an order and a high-water mark |
| "Sequential closure" as a law | False: an accepted later step can break an earlier one | Re-verify everything at the end of a composite |
| Parallel composition | Receipts do not glue across checks spanning both branches | Integration re-runs on the merged tree |
| Footprints | Results depend on scheduling if one branch reads another's writes | Declared reads and writes, refused before start |
| Retried judging | Re-judge until it passes: 19% false accept | All evaluators must pass, more each failure: 7% |
| Learning after one observation | Too little evidence | Shadow first, then promote on a Wilson bound |
| Automatic retirement after 20 quiet tasks | Retires a working check 98% of the time within 100 tasks | Protected checks cannot retire; others are a person's decision |

## Findings on the rebuild

### Fixed

| Finding | From | Why it qualified |
|---|---|---|
| A proof that writes files could land them in a certified commit, including a secret | Red team | False certification |
| A deterministic failure could be excused as flaky, removing the test for good | Red team, maths | False certification |
| Tree hash could miss a same-size edit made within one second | Build testing | False certification |
| A stage could lower the integration baseline | Red team | False certification |
| Non-ASCII paths skipped the secret scan and failed scope checks | Red team | False certification; blocks use |
| Integration skipped earlier stages' added checks | Maths | False certification |
| A failed commit left the unit marked passed | Red team | False certification |
| Touching the tree reset the judge retry count | Maths | Defeated the retry rule |
| Normal `learn add` could re-sign a tampered harness | Maths | Defeated the integrity check |
| Receipts claimed checks that had been excused | Maths | False claim |
| A nested chain was never required to run | Maths | False claim |
| Proof failures were uncounted and untimed | Maths | Unbounded loop |
| A permanent halt with no way forward | Red team | Blocks use |
| Repeated `--scope` kept only the last value | Blind user | Blocks use |
| Adding an optional parameter counted as breaking the API | Blind user, red team | False alarm on ordinary features |
| Files outside any unit could not be committed | Blind user | Blocks use |
| `chain land` died with raw git output when the branch had moved | Blind user, red team | Blocks use |
| A landed chain name could not be run again | Red team | Blocks use |
| Three figures in `theory.md` did not reproduce | Maths | Accuracy |

### Cut to avoid over-engineering

| Removed | Why |
|---|---|
| Timed retirement windows and `learn demote` | Machinery for a decision a person should make |
| Self-judge threshold margin | Bypassable by any label; the receipt records self-judging instead |
| Per-stage extra judge axes | Added checks cover this |
| Mean-of-samples judging | Simple all-must-pass is both clearer and stricter |

### Accepted as stated limits

| Finding | Why it stays |
|---|---|
| Gitignored files can influence a gate | Running every gate in a clean export would break virtualenvs and `.env` setups. Integration already uses a clean checkout |
| Hand-forged receipts or fabricated records | Tamper-evident by design; defeating a determined forger is a different product |
| Weakening a test without removing an assertion | A full semantic check is a project of its own. The evaluator's `test_honesty` axis covers it |
| Merge, rebase and cherry-pick skip the pre-commit gate | Ordinary git operations a person may need |
| A moved symbol counts as a lost API | Conservative, and a typed grant handles it |
| Stage reads are declared, not measured | Measuring needs a sandbox |
| Chain attempt budgets are checked at plan time only | Native spend and turn caps enforce the real limit |
| Definitions under module-level `if` or `try` are invisible to `public_api` | Rare; not worth more parsing |
| Verify-only units with no change cannot certify | "No change" is treated as no progress |

## Split or nest?

**One skill, in one repo that is also its own plugin marketplace.** All three reviewers agreed, from packaging, orchestration and composition angles. The runtime and state are shared, and receipts are pinned to the runtime's bytes. Splitting duplicates the runtime or breaks verification, and separate skills would compete for the same triggers. Reconsider if chains need their own state, or must run in repos with no gate.

## Not verified

- The rebuilt skill has not run inside a live Claude Code session with real hooks, subagents and `/goal`. Hook behaviour was tested by feeding the documented event format to the handler.
- Plugin install has not been run. The layout follows the current docs.
- Opus 5.5 long-run figures come from Anthropic's own materials. No independent measure, such as METR's, was found.
- Simulation figures assume Gaussian judge noise with standard deviation 0.10.
- Non-Python projects were tested only lightly.
