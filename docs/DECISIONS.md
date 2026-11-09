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
