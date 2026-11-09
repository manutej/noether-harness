# Why it is built this way

Read this only to explain or extend the design. Nothing here is needed to run it.

## The idea

Noether's theorem ties a symmetry to a conserved quantity, and a conserved quantity confines a trajectory to a smaller space. Noether Networks learn which quantity is useful to conserve and enforce it at prediction time; Tailoring adapts per query and discards the adaptation. This harness keeps those ideas and changes the medium from gradients on weights to revisions in a repo, with zero weight updates. That lets it conserve things no loss can express, such as an exit code.

The analogy has teeth in one place. The symmetries of code are behaviour-preserving transformations (rename, extract, move). A quantity is conserved only if it is unchanged by them and is a function of state, not of the diff: the passing-test set, the public signatures, the type-error count. Diff size and readability are not conserved quantities. They are preferences, so they are graded separately and never mixed into the order.

## The mathematics that survives

Each rule changes a decision the runtime makes.

| Rule | Runtime consequence |
|---|---|
| **Product order.** State ≥ baseline, pointwise over checks (`keep` is ⊇, `max` is ≤) | The commit decision. Needs no threshold or average |
| **Approximation is bounded by a pin.** Each `eps` is measured from a high-water mark that only improves | Without a grant or re-init, total drift ≤ ε over any number of commits. Tolerating ε per commit instead allows Nε |
| **Soft axes are conjoined, not averaged.** | With one axis truly at 0.45 and two at 0.90, a mean against 0.6 accepts 99.5% of the time; per-axis thresholds, 7% |
| **Retries are multiple testing.** Every evaluator must pass; the number required rises 1, 2, 3 across failures, capped at 3 attempts | For a flawed change at 0.45 and judge noise 0.10, false accepts fall from 19% (re-judge three times, keep the best) to 7%; at 0.55, from 67% to 39%. Thresholds should sit clear of what you would reject |
| **Termination.** Attempts per unit and units per task are finite; chain budgets sum | Every loop is bounded by a stated counter |
| **Sequencing is typed.** `needs` ⊆ what came before | A chain that cannot be satisfied never starts |
| **Parallel needs Bernstein's condition.** Writes disjoint; no read of another's write | Otherwise scheduling changes results |
| **Receipts do not compose by union.** The guarantee of `a;b` holds only if `a`'s checks are re-verified after `b` | Integration re-runs the harness checks, every stage's added checks and proofs. A later step can break an earlier check, and a check spanning two branches can pass on each and fail on the merge |
| **Composites are atomic.** | Otherwise `(a;b);c` and `a;(b;c)` can commit different states. Bracketing must not be a transaction boundary |
| **Learning needs evidence, and retirement needs a person.** Promote at Wilson lower bound ≥ 0.5 on distinct fires (4 of 4 is enough) | A rule of "retire after 20 quiet tasks" retires a lens with a 5% fire rate within 100 tasks 98% of the time, and cannot see deterrence |

The figures assume Gaussian judge noise of standard deviation 0.10. They show the direction of each effect; the exact values do not transfer.

## What the category theory was, and is now

The earlier version named a monoidal lens category, an internal hom, retracts, a Free ⊣ Forgetful adjunction and 2-cells. Under review, only the first did any work, and it was misnamed. There is no `put`, no currying bijection, no section, no pair of functors, no 2-category. What the system actually has is plainer and tested:

| Earlier name | What it really is | Status here |
|---|---|---|
| Monoidal lens category | A commutative monoid on verdicts (conjunction) | Kept as the product order |
| Internal hom g_φ | A scoped measurement | `Check` |
| Approximate retract | A repair step, checked by re-running everything | Agent's own loop plus gate |
| Budget identity morphism | A loop bound | `attempts` |
| Free ⊣ Forgetful | Grow and prune with evidence | `learn` |
| 2-cell log | An append-only change log | `log.jsonl` |

The composition that matters is of harnesses: a stage has a precondition (`needs`), a guarantee (its checks and proof) and a footprint. Sequencing is associative, and parallel with disjoint footprints commutes, because composites are atomic and a stage's order comes only from the flow. Interchange `(a;b)|(c;d) = (a|c);(b|d)` holds for the landed tree, not the schedule, and only if no branch reads what another writes, which is exactly why footprints are declared. Footprints are declarations: writes are verified at integration, reads are trusted. A category-theoretic reading is available and nothing is built on it. The mathematics earns its place by telling you which composition is legal.

## What this is not

It is a contract with gates, not a proof about the model. A stochastic worker cannot be proven correct by its harness. What can be guaranteed is narrower and useful: every commit satisfied the named conditions on that exact tree, and the record says so.

## Lineage

Alet et al., "Noether Networks" (NeurIPS 2021). Alet et al., "Tailoring" (NeurIPS 2021). Shinn et al., "Reflexion" (NeurIPS 2023). Madaan et al., "Self-Refine" (NeurIPS 2023). Yao et al., "ReAct" (ICLR 2023). Hoare, "An Axiomatic Basis for Computer Programming" (1969). Bernstein, "Analysis of Programs for Parallel Processing" (1966). Anthropic, "Effective harnesses for long-running agents" (2025) and "Harness design for long-running apps" (2026).
