# Chains

A **stage** binds an Agent, a Harness, a Loop and a footprint. A chain composes stages. `;` is sequence, `|` is parallel and binds tighter, and a stage with `"chain": "other.json"` nests a whole chain as its worker.

```json
{
 "name": "tax",
 "flow": "(rates | invoice) ; review",
 "budget": {"attempts": 40},
 "agents": {"coder": {"model": "inherit", "skills": ["noether-harness"]}},
 "stages": {
  "rates": {"agent": "coder", "goal": "...", "proof": "pytest tests/test_rates.py -q",
            "writes": ["lib/money.py", "tests/test_money.py"], "provides": ["taxed"],
            "grants": [{"check": "public_api", "allow": ["lib.money.total*"], "reason": "Requested in issue 12"}]},
  "invoice": {"agent": "coder", "goal": "...", "proof": "...", "writes": ["lib/bill.py"], "reads": ["lib/money.py"]},
  "review": {"goal": "...", "proof": "...", "writes": ["NOTES.md"], "needs": ["taxed"],
             "harness": {"add_checks": [{"id": "notes", "class": "pass", "cmd": "test -s NOTES.md"}]}}
 }
}
```

That example is refused as written, because `invoice` reads what `rates` writes while running in parallel. Sequence them, or change the footprint.

## Running one

```
n chain check chain.json        # well typed, or it does not start
n chain next chain.json         # stage states, what to start, what to integrate
n chain start chain.json STAGE  # makes the worktree and branch; prints the brief for the agent
n chain integrate chain.json    # verifies receipts, merges, re-verifies; atomic
n chain land chain.json         # fast-forwards your branch once every stage is integrated
```

Commit `.noether/` and the chain file first, and don't commit on your branch until the chain has landed. Each stage runs the ordinary loop (`gate`, `commit`, `brief`, `judge`, `done`) inside its worktree. Spawn one subagent per started stage with the brief `start` prints, using any bound model or skills. Use the worktree `start` creates rather than native worktree isolation, because stages must branch from the integration line.

## What holds, and why

| Rule | What it prevents |
|---|---|
| Parallel stages must have disjoint writes, and neither may read what the other writes | Results depending on scheduling |
| A stage's `needs` must be `provides` of stages before it | Building on something nobody established |
| A stage may add `pass` or `none` checks, never remove or loosen | A child weakening its parent |
| Declared attempts sum to at most the chain budget; a nested budget fits inside its stage | Plans that cannot fit. Spend is capped natively |
| Receipts are evidence that a stage passed alone. They are never evidence that the combination passes | Two branches green apart, red together |
| Integration re-runs every check and every integrated stage's proof on the merged tree | Chaining silently weakening an earlier guarantee |
| Integration is atomic: a failure advances nothing | Half-merged composites |
| A parent needs its nested chain landed, then claims only its own proof; the child's receipts are logged evidence | Claiming checks the parent never ran |

## When things fail

- **SEMANTIC conflict at integration.** Nothing merged. Integrate the sound subset with `--only`, then `chain start --reopen` the other stage, which merges the integration line in, and repair it. Or sequence the stages.
- **A stage saturates.** It halts; downstream stages wait; siblings continue and keep their work.
- **A hard stop (a secret).** Sibling gates exit 2, and `chain next` tells you to start nothing and tell a person. Once it is dealt with, a person runs `chain resume`.
- **`land` says the branch moved.** It prints the command that gates the combined tree instead.
- **Crash or reset.** Everything is on disk. `chain next` picks up from receipts, and re-running `start` on an existing stage is safe.

## Native features to use, not rebuild

| Need | Use |
|---|---|
| Fan-out and independent context | Subagents, up to 3 nesting levels |
| Keep going until done | `/goal` (see `n goal`), or a Stop hook |
| Spend and turn caps | `maxTurns`, `maxBudgetUsd` |
| Compaction and resume | Native; `status` re-injects state |
| Recurring work | `/loop`, scheduled tasks |

Agent teams are experimental and cannot resume or nest, so chains do not depend on them.
