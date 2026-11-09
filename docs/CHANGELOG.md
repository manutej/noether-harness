# Change ledger

Everything that changed, in order, with the reason and who found it. The published explainer page, kept outside this repo, shows the same data with filters, and each individual decision is in `.noether/log.jsonl`.

## 1 First adversarial pass

| Kind | Area | Change | Why | Found by |
|---|---|---|---|---|
| Fixed | Stop rule | Running out of repairs can no longer commit a change below the threshold | The schema allowed a commit that the joint stop forbade | Fable reviewer |
| Fixed | Scoring | The null lens became a true identity (confidence 0) | It was a perfect extra vote: a 0.5 score became 0.75 | Fable reviewer |
| Added | Tests | `tests_not_weakened` and per-judge floors | Deleting a failing assertion could still reach commit | Fable reviewer |
| Fixed | Flakiness | A persistent flake is re-run on the baseline before quarantine | A race the change introduced could be excused and committed | Fable reviewer |
| Fixed | Learning | Critical checks marked protected | The reflection step could retire `no_secrets` for never firing | Fable reviewer |
| Fixed | Escape | Soft escape given a defined effect | It raised a tolerance nothing read | Fable reviewer |
| Fixed | Loops | NO-PROGRESS kept in the inner budget; outer loop bounded | Both loops could run without end | Fable reviewer, build review |
| Fixed | Fragments | Corrected LangGraph, AutoGen, Aider, Cursor, OpenHands and gitleaks snippets | Several were wrong; Aider committed before its checks | Fable reviewer, source check |
| Fixed | Accuracy | Corrected the worked example, one quotation and the associativity claims | Numbers and citations did not hold | Fable reviewer |

## 2 Rebuild after the six-lane roast

| Kind | Area | Change | Why | Found by |
|---|---|---|---|---|
| Changed | Form | 2,006 lines of theory replaced by a short SKILL.md, two references and a runnable script | It took about 18k tokens and 18 hand-written files before the first check could run | Dry run, packaging |
| Added | Runtime | `noether.py`: stdlib-only CLI that decides, records and restores itself in the repo | Models follow a script more reliably than a checklist | Dry run, packaging |
| Changed | Core object | Pass-or-score lens replaced by checks with an order on repo state | A ratchet composes and bounds drift | Conservation maths |
| Changed | Drift | Tolerance measured from a high-water mark | Per-commit tolerance adds up without limit | Conservation maths |
| Changed | Judging | One fresh evaluation at the end of a unit; every axis must pass | Averaging let one bad axis through and re-judging inflated false passes | Conservation maths, frontier |
| Cut | Roles | Four role prompts and the fixed budget of three | Native loops and subagents do this | Frontier |
| Cut | Frameworks | Six third-party framework fragments | Unverified, unused, and costing tokens | Frontier, packaging |
| Cut | Theory | Lens category, internal hom, retract, adjunction and 2-cell vocabulary | The named structures were not present | Category review |
| Added | Composition | Sequence, parallel and nesting with typed stages | The skill had no way to combine harnesses | Orchestration, category review |
| Added | Receipts | Certificates bound to an exact tree | Handoffs need something a later stage can check | Orchestration |
| Added | Integration | Merge in a temporary worktree and re-verify everything, atomically | Two branches can pass alone and fail together | Orchestration |
| Added | Footprints | Stages declare reads and writes | Results otherwise depend on scheduling | Category review |
| Fixed | Hashing | Tree hash no longer misses a same-size edit inside one second | A gate pass could be reused for a different state | Build testing |
| Changed | Packaging | One skill, one repo, also a plugin marketplace | All three advisors: a split duplicates the runtime and breaks receipts | Packaging, orchestration, category review |

## 3 Verification of the rebuild

| Kind | Area | Change | Why | Found by |
|---|---|---|---|---|
| Fixed | Binding | A proof that writes files can no longer land them | A proof could put a secret into a certified commit | Red team |
| Fixed | Flakiness | A failure on every run is a failure, not a flake | A real regression could be excused for good | Red team, maths |
| Fixed | Integration | Only integration moves the integration line's baseline | A stage could lower it | Red team |
| Fixed | Paths | Non-ASCII paths are scanned | A key in `café.py` was missed | Red team |
| Fixed | Integration | Earlier stages' added checks re-run | Integration skipped them | Maths |
| Fixed | Records | A failed commit no longer leaves a unit marked passed | Status said done when nothing was committed | Red team |
| Fixed | Judging | Touching the tree no longer resets the retry count | It defeated the retry rule | Maths |
| Fixed | Integrity | Normal commands cannot re-sign a tampered harness | It defeated the integrity check | Maths |
| Fixed | Receipts | Receipts stop claiming excused checks; nested chains must really run | False claims | Maths |
| Fixed | Usability | Repeated `--scope`, optional parameters, committing outside a unit, moved-branch landing, halt recovery | Normal use was blocked | Blind user, red team |
| Cut | Learning | Timed retirement windows and `learn demote` | Machinery for a decision a person should make | Over-engineering rule |
| Cut | Judging | Self-judge margin, per-stage extra axes, mean-of-samples | Bypassable or more complex than the plain rule | Over-engineering rule |

## 4 Improvement to the rubric: decisions and ceremony

| Kind | Area | Change | Why | Found by |
|---|---|---|---|---|
| Added | Rubric | Scoring rubric fixed before any scoring | So the target is judged by others, not by the builder | Owner request |
| Added | Records | `decide` and `log`; decisions in `status`; rejections and evaluator notes recorded | The reasons for choices must survive a reset | Owner request |
| Changed | Ceremony | `brief` refuses a red tree; `gate` and `commit` are optional checkpoints | An evaluator should never be spent on a broken tree | Blind user |
| Added | Dogfooding | The skill's own repo runs under its own harness | It caught a planted key and lint regressions in the work itself | Build |
| Fixed | Trust | Receipts checked against the unit at head; warning for gitignored test files | A hand-written receipt was accepted | Red team |

## 5 Round one panel, 7.5

| Kind | Area | Change | Why | Found by |
|---|---|---|---|---|
| Fixed | Flakiness | Quarantined tests stay visible and warn on every gate and receipt | A silent drop let a permanently broken test pass | Messy adoption |
| Added | Languages | Per-test tracking for Node, Go and Rust | One red test left those languages with no protection | Messy adoption |
| Fixed | Proofs | A proof is required, and a proof of `true` is flagged | A forgotten proof certified a claim of proof | Architect |
| Fixed | Grants | Grants must match lines the gate printed; exact finding for secrets | A grant on a file path did nothing and pushed agents to `*` | Greenfield, chains, architect |
| Fixed | Halting | A saturated stage needs a person to reopen it | `chain start --reopen` reset the budget silently | Chains |
| Fixed | Land | `land --merge` gates the combination with the stages' grants | The old fallback dropped them | Architect |
| Fixed | State | Build caches excluded from the code state | `__pycache__` caused scope rejections | Architect |
| Fixed | Weakening | Comment-only edits are not weakening | False veto | Messy adoption |

## 6 Round two panel, 8.1

| Kind | Area | Change | Why | Found by |
|---|---|---|---|---|
| Fixed | Masking | A test failing anywhere under a name counts as not passing | A same-named test in another package hid a regression | Messy adoption |
| Fixed | Flakiness | Quarantine holds for five straight passing commits | One pass re-armed the veto and caused false rejects | Messy adoption |
| Changed | Budgets | `gate` is free; a failed commit, brief or done costs an attempt | Probing could saturate a unit in minutes | Architect |
| Fixed | Judging | A failed evaluator cannot re-judge the same tree | It sidestepped the retry rule | Architect |
| Fixed | Proofs | A proof that only skips does not pass | `importorskip` certified nothing | Architect |
| Fixed | Weakening | Tests that were never green can be fixed freely | Honest repair was blocked | Architect |
| Changed | Learning | Promotion needs distinct fires, on clean code | One fire could be confirmed four times | Architect |
| Changed | Checks | Lint ratchet only when the project configures it | It vetoed first edits in projects that never asked | Architect |

## 7 Round three panel, 8.35

| Kind | Area | Change | Why | Found by |
|---|---|---|---|---|
| Added | Tests | A new failing test fails the gate | A unit could add a red test and still certify | Messy adoption |
| Fixed | Node | Uses the project's own test script | Tests in non-default paths were unprotected | Messy adoption |
| Fixed | Proofs | A pytest proof fails only when its summary shows nothing passed | Quiet configurations were falsely failed | Messy adoption |
| Fixed | Chains | A stage's proof is changed in the chain file | Integration ran a different proof and vetoed sound work | Chains |
| Added | Clones | The pre-commit gate restores itself on first use | Hooks do not travel with a clone | Messy adoption |
| Fixed | Units | A planned unit takes its base when the previous one finishes | Every planned unit reported the whole history | Greenfield |
| Fixed | Attempts | A failed proof costs one attempt per tree | Docs and behaviour disagreed | Architect |
| Fixed | Weakening | Edited uppercase test constants are flagged | Changing an expected value slipped through | Architect |
| Changed | Secrets | A password-shaped string in a test is not a hard stop | A fixture froze a whole chain | Architect |
| Fixed | Compatibility | Adding a default to a parameter is compatible | False veto | Architect |

## 8 Round four panel, 8.51

| Kind | Area | Change | Why | Found by |
|---|---|---|---|---|
| Fixed | Reopen | A reopened stage keeps its own tests protected | Two panelists gutted their own test without a grant | Messy adoption, chains |
| Fixed | Grants | Grants on weakening must include the printed text | `tests/*` excused every later weakening | Greenfield |
| Changed | Hooks | Native `permissions.deny` replaces the Edit and Write hook | Claude Code enforces it; a regex is best effort | Architect |
| Fixed | Hooks | Shorthand no longer skips the person prompt; `git log --grep commit -n` no longer denied | False negatives and false denials | Architect |
| Fixed | Records | `done` leaves a clean tree and logs only after the commit succeeds | Dirty trees and false `unit_done` rows | Greenfield, architect |
| Fixed | Messages | Self-judging and failed-tree messages agree; failed checks show their output | Agents had to guess | Greenfield, messy adoption |

## 9 Round five panel, 8.6 (fixes not re-scored)

| Kind | Area | Change | Why | Found by |
|---|---|---|---|---|
| Fixed | Grants | Chain-file grants follow the same rules as command-line grants | A bare star in a chain file landed deleted tests with no person asked | Architect |
| Fixed | API | New untracked Python files count toward `public_api` | New symbols were unprotected until the next commit | Greenfield, messy adoption |
| Fixed | Hooks | `git commit -nm` and the `n` shorthand are recognised | A bypass and a missed prompt | Architect |
| Fixed | Records | A failed commit restores the baseline; the gate cache sees branch changes | Baseline advanced with no commit; a stale detached-HEAD warning | Architect, messy adoption |
| Changed | Grants | A grant accepts the gate's printed line as is; learned checks can be granted | Agents stumbled on the format | Greenfield, chains, architect |
| Changed | Weakening | `pytest.raises` counts as an assertion | Loosening it was invisible | Greenfield |
| Changed | Docs | Documented `--axis`, what editing an assertion covers, bare `unit reopen`, how a bound skill is applied | Claims and behaviour differed | Architect, chains |
| Fixed | Messages | Halted units say so in `brief`; `integrate` hints at `--only`; `reopen` confirms | Dead ends | Greenfield, chains |

## 10 Final evaluator (fixes not re-scored)

| Kind | Area | Change | Why | Found by |
|---|---|---|---|---|
| Fixed | Grants | A star behind a printed prefix (`lost: *`) is refused like a bare star | A grant could excuse everything through the prefix the gate itself prints | Fresh evaluator |
| Fixed | Grants | A new failure can be granted from the line the gate printed | Only lost tests had a matching prefix, so the printed advice could not be followed | Fresh evaluator |
| Fixed | Tests | Placeholder checks replaced by real ones: one fire cannot promote, a stage cannot lower the integration baseline, build caches are never committed | Those checks would have passed with the feature removed | Fresh evaluator |
| Added | Tests | Go and Rust per-test tracking and regression vetoes are exercised end to end | The tracking was claimed for those runners without a test behind it | Fresh evaluator |
| Fixed | Runners | When every test fails, the gate names the losses instead of saying the suite did not run | The veto held, but the message sent the agent looking for a broken toolchain | The new Go test |
| Fixed | Tests | The test fixture stops on a failed setup step | A transient git failure surfaced as a misleading crash far from its cause | Build |
| Changed | Weakening | Reversed the round-three exemption: editing or deleting the assertions of a never-green test now needs a named grant. Fixing the code behind it stays free | `assert True` passed the gate and entered the baseline as green, so a known failure could be erased. The exemption's own test did exactly that | Review comment on this page |
| Fixed | Weakening | Deleting a whole test file now counts as removing its assertions | Deleted files were skipped by the diff, so a never-green test could vanish unnoticed | Review comment on this page |

## Open at this commit (unit polish failed its evaluators)

| Kind | Area | Change | Why | Found by |
|---|---|---|---|---|
| Open | Grants | A pattern that is not literally `*` (`?*`, `*: *`, `tests.*`) can still excuse everything, and a chain file can carry one with nobody asked | Reproduced by a fresh evaluator. Same class as the `lost: *` bypass | Fresh evaluator |
| Open | Chains | Reopening an already integrated stage loses its new certified work at land, and the branch is deleted | Reproduced by a fresh evaluator | Fresh evaluator |
| Open | Chains | `land --merge` gates the combined tree but does not re-run stage proofs or stage-added checks | Reproduced by a fresh evaluator. Plain integration does re-run them | Fresh evaluator |
| Open | Records | A failed `land --merge` drops uncommitted log entries | Reproduced by a fresh evaluator | Fresh evaluator |
| Open | Build caches | Only Python caches are excluded: without a `.gitignore`, a Rust repo's `target/` is committed at init | Reproduced by a fresh evaluator | Fresh evaluator |
| Open | Hooks | `git -c core.hookspath=...` and `git -C . commit -n` get past the hook | Reproduced by a fresh evaluator. The hook is best-effort; the gate itself is unaffected | Fresh evaluator |
| Open | Tests | No check goes red if the secret hash suffix, the grant must-match rule, the `land --merge` gate or the five-commit quarantine hold is removed | Each behaviour was correct under direct experiment, but the suite would not notice losing it | Fresh evaluator |

## Accepted limits

| Kind | Area | Change | Why | Found by |
|---|---|---|---|---|
| Limit | Sandbox | Tamper-evident, not a sandbox | Stopping a determined forger is a different product | Red team, architect |
| Limit | Ignored files | Gitignored files can influence a gate; it warns for test files | A clean export breaks virtualenvs and `.env` setups. Integration is clean | Red team |
| Limit | Weakening | Weakening without removing an assertion is left to evaluators | A semantic check is a project of its own | Red team |
| Limit | Judges | Nothing can verify who ran `judge` | Independence is a protocol, and the docs say so | Architect |
| Limit | Names | Tests are identified by name; renames need a grant | Rename and weakening look alike to a line diff | Architect |
| Limit | Score | The blind panel reached 8.6, short of the 9.5 target; its fixes are not re-scored | Gains slowed to about 0.1 per round and further rounds risked over-engineering | Build |
| Limit | Live hooks | Real hooks and `/goal` have not fired in a live session here | A nested session cannot authenticate in this environment | Build |
