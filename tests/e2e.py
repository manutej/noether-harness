"""End-to-end test of the runtime on real git repos. Each scenario prints PASS or FAIL."""
import hashlib, json, os, shutil, subprocess as sp, sys, tempfile
from pathlib import Path
SRC = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parent.parent / "scripts" / "noether.py")
fails = []
def J(p): return json.loads(Path(p).read_text())
FAKE = "AK" + "IAABCDEFGHIJKLMNOP"  # assembled so this file holds no literal key
def ck(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    if not cond: fails.append(name)
def sh(c, cwd): return sp.run(c, shell=True, cwd=cwd, text=True, capture_output=True)
def repo():
    d = tempfile.mkdtemp(prefix="noe-")
    os.makedirs(f"{d}/lib"); os.makedirs(f"{d}/tests")
    W = lambda p, s: Path(d, p).write_text(s)
    W("lib/__init__.py", "")
    W("lib/money.py", "def total(items, tax_rate=0.0):\n    return round(sum(items) * (1 + tax_rate), 2)\n")
    W("lib/invoice.py", "from lib.money import total\n\ndef invoice(items):\n    return {'total': total(items)}\n")
    W("tests/test_money.py", "from lib.money import total\n\ndef test_total():\n    assert total([1, 2]) == 3\n\ndef test_tax():\n    assert total([10], 0.5) == 15\n")
    W("tests/test_invoice.py", "from lib.invoice import invoice\n\ndef test_invoice():\n    assert invoice([1])['total'] == 1\n")
    W("tests/test_red.py", "def test_preexisting_failure():\n    assert False\n")
    W("conftest.py", "import sys, os\nsys.path.insert(0, os.path.dirname(__file__))\n")
    for c in ("git init -q -b main", "git config user.email a@b", "git config user.name a", "git add -A", "git commit -q -m init"):
        r = sh(c, d); assert r.returncode == 0, (c, r.stdout, r.stderr)
    return d
N = "python3 .noether/noether.py"
def init(d):
    r = sh(f"python3 -I {SRC} init --claude", d); assert r.returncode == 0, r.stdout + r.stderr
    r = sh(f"{N} commit -m 'noether: init'", d); assert r.returncode == 0, r.stdout + r.stderr
    return d
def W(d, p, s): Path(d, p).write_text(s)
def add_unit(d, uid="u1", proof="true", extra=""): return sh(f"{N} unit add {uid} --goal 'do thing' --proof '{proof}' {extra}", d)
def finish(d, uid="u1", s="acceptance=.8,maintainable=.8,test_honesty=.8", by="e1"):
    sh(f"{N} judge --unit {uid} --by {by} --scores {s}", d); return sh(f"{N} done --unit {uid}", d)

d = init(repo())
h = J(f"{d}/.noether/harness.json")
ck("init detects tests, api, secrets, weaken", {"tests", "public_api", "secrets", "tests_not_weakened"} <= {c["id"] for c in h["checks"]})
ck("pre-existing failing test does not block", sh(f"{N} gate", d).returncode == 0)
b = J(f"{d}/.noether/baseline.json")
ck("baseline excludes the failing test", not any("preexisting" in t for t in b["q"]["tests"]) and len(b["q"]["tests"]) == 3)
ck("claude hooks installed", "noether.py" in Path(d, ".claude/settings.json").read_text())

# unit happy path, with progress on a pure refactor
add_unit(d, proof="grep -q _rounded lib/money.py")
W(d, "lib/money.py", "def _rounded(x):\n    return round(x, 2)\n\ndef total(items, tax_rate=0.0):\n    return _rounded(sum(items) * (1 + tax_rate))\n")
ck("clean refactor gates", sh(f"{N} gate", d).returncode == 0)
r = sh(f"{N} done --unit u1", d); ck("done refuses without an evaluator", r.returncode == 1 and "evaluator" in r.stdout, r.stdout)
r = finish(d); ck("refactor certified via proof, not a progress proxy", r.returncode == 0, r.stdout + r.stderr)
u = J(f"{d}/.noether/units/u1.json"); ck("receipt written", u["receipt"]["decision"] == "PASSED" and "tests" in u["receipt"]["claims"])
ck("status --done", sh(f"{N} status --done", d).returncode == 0)

# gaming
add_unit(d, "u2")
W(d, "tests/test_money.py", "from lib.money import total\n\ndef test_total():\n    assert total([1, 2]) == 3\n")
r = sh(f"{N} gate", d); ck("deleting a test is vetoed", r.returncode == 1 and "lost" in r.stdout, r.stdout)
W(d, "tests/test_money.py", "from lib.money import total\n\ndef test_total():\n    assert total([1, 2]) == 3\n\ndef test_tax():\n    total([10], 0.5)\n")
r = sh(f"{N} gate", d); ck("removing an assertion is vetoed", r.returncode == 1 and "tests_not_weakened" in r.stdout, r.stdout)
sh("git checkout tests", d)
W(d, "tests/test_money.py", Path(d, "tests/test_money.py").read_text().replace("def test_tax", "import pytest\n@pytest.mark.skip\ndef test_tax"))
ck("skip marker vetoed", sh(f"{N} gate", d).returncode == 1)
sh("git checkout tests", d)
W(d, "lib/money.py", "def total(items, rate=0.0):\n    return round(sum(items) * (1 + rate), 2)\n")
r = sh(f"{N} gate", d); ck("api change vetoed", r.returncode == 1 and "public_api" in r.stdout, r.stdout)
ck("commit refused while rejected", sh(f"{N} commit -m x", d).returncode == 1)
sh("git add -A", d); ck("plain git commit is blocked", sh("git commit -m sneak", d).returncode != 0)
sh("git reset -q; git checkout lib", d)
W(d, ".noether/harness.json", Path(d, ".noether/harness.json").read_text().replace('"tests_not_weakened"', '"tnw"'))
r = sh(f"{N} gate", d); ck("harness tampering detected", r.returncode == 1 and "integrity" in r.stdout, r.stdout)
sh("git checkout .noether/harness.json", d)
W(d, "lib/k.py", 'API_KEY = "abcd1234abcd1234abcd1234"\n')
r = sh(f"{N} gate", d); ck("secret is a hard stop", r.returncode == 2 and "secrets" in r.stdout, r.stdout)
os.remove(f"{d}/lib/k.py")

# typed grant
W(d, "tests/test_money.py", "from lib.money import total\n\ndef test_total():\n    assert total([1, 2]) == 3\n")
sh(f"{N} gate --unit u2", d); sh(f"{N} grant --unit u2 tests --allow 'tests.test_money::test_tax' --reason 'user removed tax'", d)
r = sh(f"{N} gate --unit u2", d)
ck("grant excuses only the named item, but weaken still fires", r.returncode == 1 and "tests_not_weakened" in r.stdout and '"tests"' not in r.stdout, r.stdout)
sh(f"{N} grant --unit u2 tests_not_weakened --allow 'tests/test_money.py: *' --reason 'user removed tax'", d)
ck("second typed grant clears it", sh(f"{N} gate --unit u2", d).returncode == 0)
r = finish(d, "u2"); ck("granted unit completes", r.returncode == 0, r.stdout + r.stderr)
ck("grant recorded in receipt", J(f"{d}/.noether/units/u2.json")["receipt"]["grants"])
b = J(f"{d}/.noether/baseline.json"); ck("dropped test leaves the baseline", not any("test_tax" in t for t in b["q"]["tests"]))
ck("secrets cannot be granted", sh(f"{N} unit add u3 --goal g --proof true; {N} grant --unit u3 secrets --allow '*' --reason x", d).returncode != 0)
d9 = init(repo()); add_unit(d9, "s1"); W(d9, "lib/fx.py", f'K = "{FAKE}"\n')
ck("a secret still halts", sh(f"{N} gate --unit s1", d9).returncode == 2)
finding = json.loads(sh(f"{N} gate --unit s1", d9).stdout)["failures"][0]["why"][0]
sh(f"{N} grant --unit s1 secrets --allow '{finding}' --reason 'fixture, confirmed by owner'", d9)
ck("a person can excuse one exact false positive", sh(f"{N} gate --unit s1", d9).returncode == 0)
W(d9, "lib/fx2.py", f'K = "{FAKE}"\n'); W(d9, "lib/fx.py", f'K = "{FAKE}"\nJ = "AK" "IAABCDEFGHIJKLMNOQ"\n'); ck("the excuse covers no other finding", sh(f"{N} gate --unit s1", d9).returncode == 2)

# judge escalation and saturation
W(d, "lib/a.py", "A = 1\n")
ck("low axis rejects", finish(d, "u3", "acceptance=.9,maintainable=.3,test_honesty=.9", "e1").returncode == 1)
sh(f"{N} judge --unit u3 --by e2 --scores acceptance=.9,maintainable=.9,test_honesty=.9", d)
r = sh(f"{N} done --unit u3", d); ck("after a judged failure two samples are needed", r.returncode == 1 and "need 2" in r.stdout, r.stdout)
r = sh(f"{N} judge --unit u3 --by e2 --scores acceptance=.9,maintainable=.9,test_honesty=.9", d); ck("same evaluator cannot resample", r.returncode != 0)
sh(f"{N} judge --unit u3 --by e3 --scores acceptance=.9,maintainable=.9,test_honesty=.9", d)
ck("two fresh samples pass", sh(f"{N} done --unit u3", d).returncode == 0)

# ratchet: eps bounds cumulative drift
d2 = init(repo())
h = J(f"{d2}/.noether/harness.json")
Path(d2, "score.txt").write_text("100\n")
sh("git add -A", d2)
h["checks"].append({"id": "cov", "class": "min", "cmd": "cat score.txt", "mode": "veto", "eps": 1.0}); Path(d2, ".noether/harness.json").write_text(json.dumps(h))
b = J(f"{d2}/.noether/baseline.json"); b["q"]["cov"] = 100.0; Path(d2, ".noether/baseline.json").write_text(json.dumps(b))
sh(f"{N} rehash", d2); sh(f"{N} commit -m c0", d2)
walk, stopped = [], None
for v in (99.5, 99.0, 98.5, 98.0):
    Path(d2, "score.txt").write_text(f"{v}\n")
    if sh(f"{N} commit -m c{v}", d2).returncode: stopped = v; break
    walk.append(v)
ck("slow drift stopped at eps below the high-water mark", stopped == 98.5 and walk == [99.5, 99.0], (walk, stopped))
Path(d2, "score.txt").write_text("99\n")

# flaky test: baseline flake is excused per item; real regression is not
d3 = repo()
W(d3, "tests/test_flaky.py", "import random\n\ndef test_coin():\n    assert random.random() < 0.5\n")
sh("git add -A; git commit -q -m flaky", d3)
init(d3); fl_b = J(f"{d3}/.noether/baseline.json")["q"]["tests"]
seen = False
for i in range(12):
    W(d3, "lib/x.py", f"X = {i}\n")
    r = sh(f"{N} commit -m c{i}", d3)
    if r.returncode: r = sh(f"{N} gate --fresh && {N} commit -m c{i}", d3)  # a rare false veto is cheap: re-gate
    if r.returncode: seen = True; ck("flaky baseline test does not veto", False, r.stdout); break
ck("flaky test never vetoed across 12 commits", not seen)

# learning: shadow, evidence, protection
d = init(repo())
sh(f"{N} learn add no_todo --cls none --cmd 'grep -rn TODO lib || true' --why 'a TODO shipped'", d)
W(d, "lib/z.py", "# TODO later\nZ = 1\n")
ck("shadow check does not veto", sh(f"{N} gate", d).returncode == 0)
ck("shadow fire logged", "shadow_fire" in Path(d, ".noether/log.jsonl").read_text())
ck("promote refused on no evidence", sh(f"{N} learn promote no_todo", d).returncode != 0)
for _ in range(5): sh(f"{N} learn confirm no_todo --real yes", d)
ck("one fire cannot be confirmed into a promotion", sh(f"{N} learn promote no_todo", d).returncode != 0)
ck("confirm needs a recorded fire", sh(f"{N} learn confirm ghost --real yes", d).returncode != 0)
for i in range(4):
    W(d, "lib/z.py", f"# TODO later {i}\nZ = 1\n"); sh(f"{N} gate --fresh", d); sh(f"{N} learn confirm no_todo --real yes", d)
ck("promotion waits until existing violations are fixed", sh(f"{N} learn promote no_todo", d).returncode != 0)
os.remove(f"{d}/lib/z.py"); ck("promote allowed at 4 distinct fires", sh(f"{N} learn promote no_todo", d).returncode == 0, sh(f"{N} log", d).stdout[-400:])
W(d, "lib/z.py", "# TODO later\nZ = 1\n"); ck("promoted check vetoes", sh(f"{N} gate --fresh", d).returncode == 1); os.remove(f"{d}/lib/z.py")
ck("protected check cannot be retired", sh(f"{N} learn retire tests", d).returncode != 0)
ck("unprotected check can be retired", sh(f"{N} learn retire no_todo", d).returncode == 0)

# hooks
def hook(d, ev): return sh(f"echo '{json.dumps(dict(ev, cwd=d))}' | {N} hook", d).stdout
d = init(repo())
ck("hook denies --no-verify", "deny" in hook(d, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "git commit --no-verify -m x"}}))
ck("hook asks on grant", '"ask"' in hook(d, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "python3 .noether/noether.py grant tests"}}))
ck("native rules deny harness edits", "Edit(.noether/**)" in J(f"{d}/.claude/settings.json")["permissions"]["deny"])
ck("hook allows ordinary commands", hook(d, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "git status"}}) == "")
ck("context reset is recoverable", "HARNESS" in hook(d, {"hook_event_name": "SessionStart", "source": "compact"}))

# chain: semantic conflict between parallel branches that pass alone
def stage_finish(p, s):
    r = sh(f"{N} commit -m work", p); assert r.returncode == 0, r.stdout + r.stderr
    sh(f"{N} judge --unit {s} --by ev-{s} --scores acceptance=.9,maintainable=.9,test_honesty=.9", p)
    return sh(f"{N} done", p)
d = init(repo())
chain = {"name": "c1", "flow": "(tax | inv) ; review", "budget": {"attempts": 40},
  "agents": {"coder": {"model": "inherit", "skills": ["noether-harness"]}},
  "stages": {"tax": {"agent": "coder", "goal": "default tax", "proof": "python3 -c 'import lib.money as m; assert m.total([10])==12'", "writes": ["lib/money.py", "tests/test_money.py"], "provides": ["taxed"], "grants": [{"check": "public_api", "allow": ["lib.money.total*"], "reason": "chain grant", "axis": False}, {"check": "tests", "allow": ["tests.test_money::test_total"], "reason": "chain grant", "axis": False}, {"check": "tests_not_weakened", "allow": ["tests/test_money.py*"], "reason": "chain", "axis": False}]},
             "inv": {"agent": "coder", "goal": "new caller", "proof": "python3 -c 'import lib.bill as b; assert b.bill([10])==10'", "writes": ["lib/bill.py", "tests/test_bill.py"]},
             "review": {"agent": "coder", "goal": "doc", "proof": "test -f NOTES.md", "writes": ["NOTES.md"], "needs": ["taxed"]}}}
chain["stages"]["tax"]["grants"][2]["allow"] = ["tests/test_money.py: *"]  # a none-class grant must include the printed text
W(d, "lib/invoice.py", "from lib.money import total\n\ndef invoice(items):\n    return {'total': total(items, tax_rate=0.0)}\n")
Path(d, "chain.json").write_text(json.dumps(chain)); sh("git add -A", d); sh(f"{N} commit -m chain", d)
ck("chain well typed", sh(f"{N} chain check chain.json", d).returncode == 0)
r = sh(f"{N} chain next chain.json", d); nx = json.loads(r.stdout); ck("parallel stages ready first", nx["start"] == ["tax", "inv"], r.stdout)
ck("downstream waits", "waits on" in sh(f"{N} chain start chain.json review", d).stderr)
sh(f"{N} chain start chain.json tax", d); sh(f"{N} chain start chain.json inv", d)
wt = lambda s, n="c1": Path(d, ".noether/run/wt", n, s)
W(wt("tax"), "lib/money.py", "def total(items, tax_rate=0.2):\n    return round(sum(items) * (1 + tax_rate), 2)\n")
W(wt("tax"), "tests/test_money.py", "from lib.money import total\n\ndef test_total2():\n    assert total([1, 2]) == 3.6\n\ndef test_tax():\n    assert total([10], 0.5) == 15\n")
W(wt("inv"), "lib/bill.py", "from lib.money import total\n\n\ndef bill(items):\n    return total(items)\n")
W(wt("inv"), "tests/test_bill.py", "from lib.bill import bill\n\n\ndef test_bill():\n    assert bill([10]) == 10\n")
r1 = stage_finish(wt("tax"), "tax"); r2 = stage_finish(wt("inv"), "inv")
ck("both branches certify alone", r1.returncode == 0 and r2.returncode == 0, r1.stdout + r1.stderr + r2.stdout + r2.stderr)
before = sh("git rev-parse noether/c1/int", d).stdout
r = sh(f"{N} chain integrate chain.json", d); ck("semantic conflict caught at the join", r.returncode == 1 and "SEMANTIC" in r.stdout, r.stdout + r.stderr)
ck("failed integration is atomic", sh("git rev-parse noether/c1/int", d).stdout == before)
r = sh(f"{N} chain integrate chain.json --only tax", d); ck("the sound subset integrates", r.returncode == 0, r.stdout + r.stderr)
r = sh(f"{N} chain start chain.json inv --reopen", d)
W(wt("inv"), "lib/bill.py", "from lib.money import total\n\n\ndef bill(items):\n    return total(items, tax_rate=0.0)\n")
r3 = stage_finish(wt("inv"), "inv"); ck("reopened stage certifies on the integrated base", r3.returncode == 0, r3.stdout + r3.stderr)
r = sh(f"{N} chain integrate chain.json", d); ck("repaired stage integrates", r.returncode == 0, r.stdout + r.stderr)
r = json.loads(sh(f"{N} chain next chain.json", d).stdout); ck("resume from disk sees progress", r["start"] == ["review"] and r["stages"]["tax"] == "integrated", r)
sh(f"{N} chain start chain.json review", d); W(wt("review"), "NOTES.md", "ok\n"); ck("seq stage certifies", stage_finish(wt("review"), "review").returncode == 0)
ck("last group integrates", sh(f"{N} chain integrate chain.json", d).returncode == 0)
r = sh(f"{N} chain land chain.json", d); ck("land fast-forwards the target", r.returncode == 0, r.stdout + r.stderr)
ck("landed code present", Path(d, "NOTES.md").exists() and Path(d, "lib/bill.py").exists())

# typing refusals
def badchain(mut):
    c = json.loads(json.dumps(chain)); c["name"] = "bad"; mut(c); Path(d, "b.json").write_text(json.dumps(c)); return sh(f"{N} chain check b.json", d)
ck("overlapping parallel writes refused", "overlap" in badchain(lambda c: c["stages"]["inv"]["writes"].append("lib/money.py")).stdout)
ck("read of a sibling's write refused", "reads what" in badchain(lambda c: c["stages"]["inv"].__setitem__("reads", ["lib/money.py"])).stdout)
ck("unmet need refused", "no earlier stage" in badchain(lambda c: c["stages"]["inv"].__setitem__("needs", ["ghost"])).stdout)
ck("budget overrun refused", "over the chain budget" in badchain(lambda c: c["budget"].__setitem__("attempts", 5)).stdout)
ck("child cannot loosen", "only add" in badchain(lambda c: c["stages"]["inv"].__setitem__("harness", {"remove": ["tests"]})).stdout)
ck("chain cannot excuse secrets", "cannot be excused" in badchain(lambda c: c["stages"]["inv"].__setitem__("grants", [{"check": "secrets", "allow": ["*"], "reason": "x"}])).stdout)
os.remove(f"{d}/b.json")

# hard stop propagates to siblings
d = init(repo())
ch = {"name": "c2", "flow": "a | b", "stages": {"a": {"goal": "g", "proof": "true", "writes": ["lib/a*"]}, "b": {"goal": "g", "proof": "true", "writes": ["lib/b*"]}}}
Path(d, "c.json").write_text(json.dumps(ch)); sh(f"{N} commit -m c", d)
sh(f"{N} chain start c.json a; {N} chain start c.json b", d)
A, B = (Path(d, ".noether/run/wt/c2", s) for s in "ab")
W(A, "lib/a.py", 'TOKEN = "abcd1234abcd1234abcd1234"\n')
ck("stage hard stop", sh(f"{N} gate", A).returncode == 2)
W(B, "lib/b.py", "B = 1\n")
r = sh(f"{N} gate", B); ck("sibling sees the hard stop", r.returncode == 2 and "hard stop" in r.stdout, r.stdout)
ck("chain refuses to go on", sh(f"{N} chain next c.json", d).returncode == 2)

# nesting: a stage whose worker is a chain; parent claims only its own proof
d = init(repo())
inner = {"name": "in1", "flow": "x ; y", "budget": {"attempts": 10}, "stages": {"x": {"goal": "g", "proof": "test -f lib/x1.py", "writes": ["lib/x1.py"], "attempts": 5}, "y": {"goal": "g", "proof": "test -f lib/y1.py", "writes": ["lib/y1.py"], "attempts": 5}}}
outer = {"name": "out1", "flow": "p", "stages": {"p": {"goal": "g", "proof": "test -f lib/x1.py && test -f lib/y1.py", "writes": ["lib/x1.py", "lib/y1.py"], "chain": "inner.json", "attempts": 12}}}
Path(d, "inner.json").write_text(json.dumps(inner)); Path(d, "outer.json").write_text(json.dumps(outer)); sh(f"{N} commit -m c", d)
ck("nested chain typechecks", sh(f"{N} chain check outer.json", d).returncode == 0)
sh(f"{N} chain start outer.json p", d); P = Path(d, ".noether/run/wt/out1/p")
for s, f in (("x", "lib/x1.py"), ("y", "lib/y1.py")):
    r = sh(f"{N} chain start inner.json {s}", P); ck(f"nested start {s}", r.returncode == 0, r.stdout + r.stderr)
    q = P / ".noether/run/wt/in1" / s; W(q, f, "V = 1\n"); r = stage_finish(q, s); ck(f"nested stage {s} certifies", r.returncode == 0, r.stdout + r.stderr)
    r = sh(f"{N} chain integrate inner.json", P); ck(f"nested integrate {s}", r.returncode == 0, r.stdout + r.stderr)
r = sh(f"{N} chain land inner.json", P); ck("nested chain lands in the stage", r.returncode == 0, r.stdout + r.stderr)
sh(f"{N} judge --unit p --by evp --scores acceptance=.9,maintainable=.9,test_honesty=.9", P); r = sh(f"{N} done", P); ck("parent stage certifies with its own proof", r.returncode == 0, r.stdout + r.stderr)
ck("parent receipt carries child evidence", len(J(sh("git rev-parse --git-common-dir", P).stdout.strip() if False else Path(d, ".git/noether/out1/receipts/p.json"))["evidence"]) == 2)
ck("parent integrates", sh(f"{N} chain integrate outer.json", d).returncode == 0)
# brief refuses a red tree and keeps harness records out of the evaluator's diff
d = init(repo()); add_unit(d, "b1"); W(d, "lib/k9.py", f'K = "{FAKE}"\n')
r = sh(f"{N} brief --unit b1", d); ck("brief refuses a red tree", r.returncode != 0 and "evaluator" not in r.stdout, r.stdout); os.remove(f"{d}/lib/k9.py")
W(d, "lib/k9.py", "K = 1\n"); r = sh(f"{N} brief --unit b1", d); ck("brief excludes harness records", "exclude).noether" in r.stdout, r.stdout + r.stderr)

# decisions and judgments are kept
d = init(repo()); add_unit(d, "r1"); sh(f"{N} decide 'use sqlite' --why 'one writer'", d)
ck("status shows decisions after a reset", "use sqlite" in sh(f"{N} status", d).stdout)
W(d, "lib/k.py", f'K = "{FAKE}"\n'); sh(f"{N} commit --unit r1 -m x", d); os.remove(f"{d}/lib/k.py"); W(d, "lib/k.py", "K = 1\n")
sh(f"{N} judge --unit r1 --by evA --scores acceptance=.2,maintainable=.9,test_honesty=.9 --note 'misses edge'", d)
L = sh(f"{N} log", d).stdout; ck("log keeps decisions, rejects and judge notes", all(x in L for x in ("use sqlite", "one writer", "reject", "misses edge")), L)
D = sh(f"{N} log --only decisions", d); ck("log filters to decisions", D.returncode == 0 and "use sqlite" in D.stdout and "misses edge" not in D.stdout, D.stdout + D.stderr)

# a hand-written receipt does not certify; a gitignored test file is flagged
d = init(repo()); ch = {"name": "c7", "flow": "a", "stages": {"a": {"goal": "g", "proof": "true", "writes": ["lib/a.py"]}}}
Path(d, "c.json").write_text(json.dumps(ch)); sh(f"{N} commit -m c", d); sh(f"{N} chain start c.json a", d); A = Path(d, ".noether/run/wt/c7/a"); W(A, "lib/a.py", "A = 1\n"); sh(f"{N} commit -m w", A)
head = sh("git rev-parse HEAD", A).stdout.strip(); sha = sh("python3 -I -c \"import hashlib;print(hashlib.sha256(open('.noether/harness.json','rb').read()+open('.noether/noether.py','rb').read()).hexdigest()[:16])\"", A).stdout.strip()
rec = {"stage": "a", "head": head, "harness_sha": sha, "tree": "x", "base": head, "claims": [], "decision": "PASSED"}; rec["digest"] = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()[:16]
os.makedirs(f"{d}/.git/noether/c7/receipts", exist_ok=True); Path(d, ".git/noether/c7/receipts/a.json").write_text(json.dumps(rec))
r = sh(f"{N} chain integrate c.json", d); ck("hand-written receipt is refused", r.returncode == 1 and "no passed unit" in r.stdout, r.stdout + r.stderr)
d = init(repo()); W(d, ".gitignore", "tests/test_local.py\n"); W(d, "tests/test_local.py", "def test_x():\n    assert True\n")
r = sh(f"{N} gate", d); ck("gitignored test file is flagged", "gitignored test file" in r.stdout, r.stdout)

# regressions from the red team, blind user and maths review
d = init(repo()); add_unit(d, "p1", proof="echo leak > tests/snap.txt")
W(d, "lib/a2.py", "A = 1\n"); sh(f"{N} judge --unit p1 --by e --scores acceptance=.9,maintainable=.9,test_honesty=.9", d)
r = sh(f"{N} done --unit p1", d); ck("proof that writes files cannot land them", r.returncode != 0 and "changed" in r.stderr, r.stdout + r.stderr)
ck("failed commit leaves the unit open", J(f"{d}/.noether/units/p1.json")["status"] == "open")
d = repo(); W(d, ".gitignore", ".env\n"); W(d, ".env", "1\n"); W(d, "lib/cfg.py", "import pathlib\n\n\ndef rate():\n    return int(pathlib.Path('.env').read_text())\n"); W(d, "tests/test_cfg.py", "from lib.cfg import rate\n\n\ndef test_rate():\n    assert rate() == 1\n"); sh("git add -A; git commit -q -m cfg", d); init(d)
W(d, "lib/cfg.py", "import pathlib\n\n\ndef rate():\n    return 2 + int(pathlib.Path('.env').read_text())\n")
ck("deterministic failure is not excused as flaky", sh(f"{N} gate --fresh", d).returncode == 1)
d = init(repo()); W(d, "lib/café.py", f'TOKEN = "{FAKE}"\n'); ck("non-ascii path is scanned", sh(f"{N} gate", d).returncode == 2)
d = init(repo()); W(d, "lib/money.py", "def total(items, tax_rate=0.0, start=0):\n    return round(sum(items) * (1 + tax_rate), 2) + start\n"); ck("adding an optional parameter passes", sh(f"{N} gate", d).returncode == 0)
W(d, "lib/money.py", "def total(items, tax_rate):\n    return round(sum(items) * (1 + tax_rate), 2)\n"); ck("making a parameter required is vetoed", sh(f"{N} gate", d).returncode == 1)
sh("git checkout lib", d)
sh(f"{N} unit add a --goal g --proof true --scope 'lib/x*' --scope 'lib/y*'", d); ck("repeated --scope accumulates", len(J(f"{d}/.noether/units/a.json")["scope"]) == 2)
W(d, "NOTES.txt", "x\n"); ck("commit outside any unit works", sh(f"{N} commit --unit - -m n", d).returncode == 0)
d = init(repo()); ch = {"name": "c9", "flow": "a", "stages": {"a": {"goal": "g", "proof": "true", "writes": ["lib/a.py"]}}}
Path(d, "c.json").write_text(json.dumps(ch)); sh(f"{N} commit -m c", d); sh(f"{N} chain start c.json a", d); A = Path(d, ".noether/run/wt/c9/a")
W(A, "lib/money.py", "def total(items, tax_rate=0.0):\n    return 0\n")
b = J(A / ".noether/baseline.json"); b["red"] = b["red"] + b["q"]["tests"]; b["q"]["tests"] = []; Path(A, ".noether/baseline.json").write_text(json.dumps(b)); Path(A, ".noether/run/stage.json").write_text(json.dumps({**J(A / ".noether/run/stage.json"), "writes": ["lib/*"]}))
r = sh(f"{N} commit -m bad", A)
sh(f"{N} judge --unit a --by e --scores acceptance=.9,maintainable=.9,test_honesty=.9", A); sh(f"{N} done", A)
ch["stages"]["a"]["writes"] = ["lib/*"]; Path(d, "c.json").write_text(json.dumps(ch))
r = sh(f"{N} chain integrate c.json", d); ck("a stage cannot lower the integration baseline", r.returncode == 1 and "SEMANTIC" in r.stdout, r.stdout + r.stderr)
d = init(repo()); ch = {"name": "c8", "flow": "a", "stages": {"a": {"goal": "g", "proof": "true", "writes": ["lib/a.py"]}}}
Path(d, "c.json").write_text(json.dumps(ch)); sh(f"{N} commit -m c", d); sh(f"{N} chain start c.json a", d); A = Path(d, ".noether/run/wt/c8/a"); W(A, "lib/a.py", f'P = "{FAKE}"\n'); sh(f"{N} gate", A); os.remove(A / "lib/a.py")
ck("halted while the file exists", sh(f"{N} chain next c.json", d).returncode == 2)
ck("resume clears a halt", sh(f"{N} chain resume c.json", d).returncode == 0 and sh(f"{N} chain next c.json", d).returncode == 0)
W(A, "lib/a.py", "A = 1\n"); ck("stage proceeds after resume", sh(f"{N} gate --fresh", A).returncode == 0)
# panel regressions
d = repo(); W(d, "tests/test_fl.py", "import os\n\n\ndef test_fl():\n    p = '/tmp/noefl' + str(os.getppid())\n    n = int(open(p).read()) if os.path.exists(p) else 0\n    open(p, 'w').write(str(n + 1))\n    assert n != 2\n"); sh("git add -A; git commit -q -m t", d); init(d)
base = J(f"{d}/.noether/baseline.json"); ck("flaky test starts protected", any("test_fl" in t for t in base["q"]["tests"]))
d = init(repo()); add_unit(d, "w1")
ck("a proof is required", sh(f"{N} unit add zz --goal g", d).returncode != 0)
W(d, "tests/test_money.py", Path(d, "tests/test_money.py").read_text().replace("== 15", "== 15  # note")); ck("a comment-only edit is not weakening", sh(f"{N} gate --unit w1", d).returncode == 0); sh("git checkout tests", d)
W(d, "tests/test_money.py", Path(d, "tests/test_money.py").read_text().replace("== 15", "== 16")); sh(f"{N} gate --unit w1", d)
ck("a grant matching nothing is refused", sh(f"{N} grant --unit w1 tests_not_weakened --allow 'nope.py' --reason r", d).returncode != 0); sh("git checkout tests", d)
os.makedirs(f"{d}/lib/__pycache__", exist_ok=True); W(d, "lib/__pycache__/x.pyc", "x")
sh(f"{N} commit --unit - -m cachetest", d); ck("build caches are never committed", "pyc" not in sh("git ls-files", d).stdout, sh("git ls-files", d).stdout)
d = init(repo()); add_unit(d, "s2"); W(d, "lib/a3.py", "A = 1\n"); sh(f"{N} judge --unit s2 --by self --scores acceptance=.2,maintainable=.9,test_honesty=.9", d); W(d, "lib/a3.py", "A = 2\n"); sh(f"{N} judge --unit s2 --by self --scores acceptance=.9,maintainable=.9,test_honesty=.9", d)
ck("self-judging can recover from a failure", sh(f"{N} done --unit s2", d).returncode == 0)
d = init(repo()); ch = {"name": "c5", "flow": "a", "stages": {"a": {"goal": "g", "proof": "true", "writes": ["lib/a.py"], "attempts": 1}}}
Path(d, "c.json").write_text(json.dumps(ch)); sh(f"{N} commit -m c", d); sh(f"{N} chain start c.json a", d); A = Path(d, ".noether/run/wt/c5/a"); W(A, "lib/other.py", "A = 1\n"); sh(f"{N} commit -m x", A)
ck("a saturated stage cannot be reopened by the agent", sh(f"{N} chain start c.json a --reopen", d).returncode != 0)
d = init(repo()); ch = {"name": "c6", "flow": "a", "stages": {"a": {"goal": "g", "proof": "true", "writes": ["lib/a.py"]}}}
Path(d, "c.json").write_text(json.dumps(ch)); sh(f"{N} commit -m c", d); sh(f"{N} chain start c.json a", d); A = Path(d, ".noether/run/wt/c6/a"); W(A, "lib/a.py", "A = 1\n"); ck("stage certifies", stage_finish(A, "a").returncode == 0); ck("integrates", sh(f"{N} chain integrate c.json", d).returncode == 0)
W(d, "NOTES.txt", "x\n"); sh(f"{N} commit --unit - -m moved", d)
r = sh(f"{N} chain land c.json", d); ck("moved branch is explained", r.returncode != 0 and "--merge" in r.stderr, r.stdout + r.stderr)
r = sh(f"{N} chain land c.json --merge", d); ck("land --merge gates and lands", r.returncode == 0 and Path(d, "lib/a.py").exists(), r.stdout + r.stderr)
ck("land leaves no stage branches", "noether/c6/a" not in sh("git branch", d).stdout)
if shutil.which("node"):
    d = tempfile.mkdtemp(prefix="noe-"); W(d, "package.json", '{"scripts": {"test": "node --test"}}'); W(d, "a.test.js", "const t = require('node:test'); const a = require('assert');\nt.test('green', () => a.equal(1, 1));\nt.test('red', () => a.equal(1, 2));\n")
    for c in ("git init -q -b main", "git config user.email a@b", "git config user.name a", "git add -A", "git commit -q -m i"): sh(c, d)
    r = init(d); ck("node gets per-test tracking despite a red test", sh(f"{N} gate", d).returncode == 0 and J(f"{d}/.noether/baseline.json")["q"]["tests"] == ["green"])
    W(d, "a.test.js", "const t = require('node:test'); const a = require('assert');\nt.test('green', () => a.equal(1, 9));\nt.test('red', () => a.equal(1, 2));\n")
    ck("a node regression is vetoed", sh(f"{N} gate", d).returncode == 1)
# round two regressions
d = init(repo()); add_unit(d, "e1", proof="python3 -m pytest tests/test_skip.py -q")
W(d, "tests/test_skip.py", "import pytest\n\n\ndef test_s():\n    pytest.importorskip('nosuchmodule')\n"); sh(f"{N} judge --unit e1 --by e --scores acceptance=.9,maintainable=.9,test_honesty=.9", d)
r = sh(f"{N} done --unit e1", d); ck("a proof that only skips does not pass", r.returncode != 0 and "no test passed" in r.stdout, r.stdout + r.stderr)
d = init(repo()); add_unit(d, "e2"); W(d, "lib/z1.py", "Z = 1\n"); sh(f"{N} judge --unit e2 --by e1 --scores acceptance=.2,maintainable=.9,test_honesty=.9", d)
ck("a failed evaluator cannot re-judge the same tree", sh(f"{N} judge --unit e2 --by e1 --scores acceptance=.9,maintainable=.9,test_honesty=.9", d).returncode != 0)
d = repo(); Path(d, "lib/money.py").write_text(Path(d, "lib/money.py").read_text() + "\n\ndef double(x):\n    return x\n"); W(d, "tests/test_red.py", "from lib.money import double\n\ndef test_preexisting_failure():\n    assert double(2) == 4\n"); sh("git add -A && git commit -q -m red", d); init(d); add_unit(d, "e3")
W(d, "tests/test_red.py", "def test_preexisting_failure():\n    assert True\n"); r = sh(f"{N} gate --unit e3", d); ck("rewriting a never-green test until it passes is vetoed", r.returncode == 1 and "tests_not_weakened" in r.stdout, r.stdout); sh("git checkout tests", d)
Path(d, "tests/test_red.py").unlink(); r = sh(f"{N} gate --unit e3", d); ck("deleting a never-green test is vetoed", r.returncode == 1 and "tests_not_weakened" in r.stdout, r.stdout); sh("git checkout tests", d)
W(d, "tests/test_red.py", "from lib.money import double\n\ndef test_preexisting_failure():\n    assert double(2) == 2\n"); r = sh(f"{N} gate --unit e3", d); line = json.loads(r.stdout)["failures"][0]["why"][0]; g = sh(f"{N} grant --unit e3 tests_not_weakened --allow '{line}' --reason 'the expected value was wrong'", d)
ck("a wrong never-green test can be corrected under a named grant", g.returncode == 0 and sh(f"{N} gate --unit e3", d).returncode == 0, g.stdout + g.stderr); sh("git checkout tests", d)
Path(d, "lib/money.py").write_text(Path(d, "lib/money.py").read_text().replace("    return x\n", "    return x * 2\n")); r = sh(f"{N} gate --unit e3", d); ck("fixing the code behind a never-green test is free", r.returncode == 0, r.stdout)
sh("git checkout tests", d); W(d, "lib/k.py", "def f(:\n"); 
for i in range(4): W(d, "lib/k.py", f"def f({i}:\n"); sh(f"{N} gate --unit e3", d)
ck("gating is free", J(f"{d}/.noether/units/e3.json")["attempts"] == 0)
if shutil.which("node"):
    d = tempfile.mkdtemp(prefix="noe-"); W(d, "package.json", '{"scripts": {"test": "node --test"}}'); os.makedirs(f"{d}/t")
    W(d, "t/a.test.js", "const t = require('node:test'); const a = require('assert');\nt.test('same', () => a.equal(1, 1));\n")
    for c in ("git init -q -b main", "git config user.email a@b", "git config user.name a", "git add -A", "git commit -q -m i"): sh(c, d)
    init(d); W(d, "t/b.test.js", "const t = require('node:test'); const a = require('assert');\nt.test('same', () => a.equal(1, 1));\n"); W(d, "t/a.test.js", "const t = require('node:test'); const a = require('assert');\nt.test('same', () => a.equal(1, 2));\n")
    ck("a same-named test cannot mask a regression", sh(f"{N} gate", d).returncode == 1)
d = init(repo()); r = sh(f"{N} status | head -1", d); ck("piping status is quiet", "BrokenPipe" not in r.stderr, r.stderr)
# round three regressions
d = init(repo()); add_unit(d, "n1"); W(d, "tests/test_new.py", "def test_new():\n    assert 1 == 2\n")
r = sh(f"{N} gate --unit n1", d); ck("a new failing test fails the gate", r.returncode == 1 and "new failure" in r.stdout, r.stdout)
W(d, "tests/test_new.py", "def test_new():\n    assert 1 == 1\n"); ck("the same test passing is fine", sh(f"{N} gate --unit n1", d).returncode == 0)
d = init(repo()); add_unit(d, "a1"); add_unit(d, "a2"); W(d, "lib/q.py", "Q = 1\n"); finish(d, "a1"); head = sh("git rev-parse HEAD", d).stdout.strip()
W(d, "lib/q2.py", "Q = 2\n"); ck("the next unit starts at the last certified commit", head in sh(f"{N} brief --unit a2", d).stdout)
d = init(repo()); add_unit(d, "c9", proof="python3 -m pytest -qq tests/test_money.py"); W(d, "lib/q.py", "Q = 1\n"); r = finish(d, "c9"); ck("a quiet pytest proof is trusted", r.returncode == 0, r.stdout + r.stderr)
d = init(repo()); ch = {"name": "c3", "flow": "a", "stages": {"a": {"goal": "g", "proof": "true", "writes": ["lib/a.py"]}}}
Path(d, "c.json").write_text(json.dumps(ch)); sh(f"{N} commit -m c", d); sh(f"{N} chain start c.json a", d); A = Path(d, ".noether/run/wt/c3/a")
ck("a stage proof is changed in the chain file", sh(f"{N} unit reopen a --proof false", A).returncode != 0)
if shutil.which("node"):
    d = tempfile.mkdtemp(prefix="noe-"); W(d, "package.json", '{"scripts": {"test": "node --test checks/a.spec.js"}}'); os.makedirs(f"{d}/checks")
    W(d, "checks/a.spec.js", "const t = require('node:test'); const a = require('assert');\nt.test('only here', () => a.equal(1, 1));\n")
    for c in ("git init -q -b main", "git config user.email a@b", "git config user.name a", "git add -A", "git commit -q -m i"): sh(c, d)
    init(d); ck("the project's own test script is used", "only here" in " ".join(J(f"{d}/.noether/baseline.json")["q"]["tests"]))
d = init(repo()); hk = Path(d, ".git/hooks/pre-commit"); hk.unlink(); sh(f"{N} status", d); ck("the commit gate restores itself in a clone", hk.exists())
# architect regressions
d = init(repo()); W(d, "lib/money.py", "def total(items, tax_rate=0.0):\n    return round(sum(items) * (1 + tax_rate), 2)\n\n\ndef fee(x, cur=1):\n    return x + cur\n"); sh(f"{N} commit --unit - -m fee", d)
W(d, "lib/money.py", "def total(items, tax_rate=0.0):\n    return round(sum(items) * (1 + tax_rate), 2)\n\n\ndef fee(x=0, cur=1):\n    return x + cur\n"); ck("adding a default is compatible", sh(f"{N} gate --unit - --fresh", d).returncode == 0, sh(f"{N} gate --unit -", d).stdout); sh("git checkout lib", d)
d = init(repo()); W(d, "tests/test_data.py", "EXPECTED = 9\n\n\ndef test_d():\n    assert 9 == EXPECTED\n"); sh(f"{N} commit --unit - -m d", d); W(d, "tests/test_data.py", "EXPECTED = 10\n\n\ndef test_d():\n    assert 10 == EXPECTED\n")
r = sh(f"{N} gate --unit -", d); ck("changing an expected constant is flagged", r.returncode == 1 and "EXPECTED" in r.stdout, r.stdout)
d = init(repo()); W(d, "tests/test_cfg2.py", "pass" + 'word = "correct-horse-battery-staple"\n\n\ndef test_p():\n    assert password\n'); ck("a test fixture password is not a hard stop", sh(f"{N} gate --unit -", d).returncode == 0)
d = init(repo()); r = hook(d, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "git commit -m \"clean -n\""}}); ck("a commit message is not a flag", "deny" not in r, r)
# round four regressions
d = init(repo()); add_unit(d, "g1"); W(d, "tests/test_money.py", Path(d, "tests/test_money.py").read_text().replace("== 15", "== 16")); sh(f"{N} gate --unit g1", d)
ck("a file-wide grant is refused", sh(f"{N} grant --unit g1 tests_not_weakened --allow 'tests/*' --reason lazy", d).returncode != 0); sh("git checkout tests", d)
d = init(repo()); add_unit(d, "h1"); add_unit(d, "h2"); W(d, "lib/q.py", "Q = 1\n"); finish(d, "h1"); ck("the tree is clean after done", sh("git status --short", d).stdout.strip() == "", sh("git status --short", d).stdout)
r = sh(f"{N} commit --unit - -m nothing", d); ck("nothing to commit is not an error", r.returncode == 0 and "nothing to commit" in r.stdout, r.stdout + r.stderr)
d = init(repo()); add_unit(d, "s3"); W(d, "lib/a4.py", "A = 1\n"); sh(f"{N} judge --unit s3 --by self --scores acceptance=.2,maintainable=.9,test_honesty=.9", d)
r = sh(f"{N} done --unit s3", d); ck("a failed tree says to change the code", "change the code" in r.stdout, r.stdout + r.stderr)
d = init(repo()); ch = {"name": "c4", "flow": "a", "stages": {"a": {"goal": "g", "proof": "true", "writes": ["lib/a5.py", "tests/test_a5.py"]}}}
Path(d, "c.json").write_text(json.dumps(ch)); sh(f"{N} commit -m c", d); sh(f"{N} chain start c.json a", d); A = Path(d, ".noether/run/wt/c4/a"); W(A, "lib/a5.py", "A = 1\n"); W(A, "tests/test_a5.py", "def test_a5():\n    assert 1 == 1\n"); stage_finish(A, "a")
sh(f"{N} chain start c.json a --reopen", d); W(A, "tests/test_a5.py", "def test_a5():\n    assert True\n"); r = sh(f"{N} gate --fresh", A)
ck("a reopened stage keeps its own tests protected", r.returncode == 1 and "tests_not_weakened" in r.stdout, r.stdout + r.stderr)
# round five regressions
d = init(repo()); W(d, "lib/newmod.py", "def shiny(x):\n    return x\n"); sh(f"{N} commit --unit - -m new", d); W(d, "lib/newmod.py", "def _shiny(x):\n    return x\n")
r = sh(f"{N} gate --unit -", d); ck("a newly added public symbol is protected at once", r.returncode == 1 and "public_api" in r.stdout, r.stdout)
d = init(repo()); ch = {"name": "c2", "flow": "a", "stages": {"a": {"goal": "g", "proof": "true", "writes": ["lib/a.py"], "grants": [{"check": "tests", "allow": ["*"], "reason": "x"}]}}}
Path(d, "c.json").write_text(json.dumps(ch)); ck("a chain cannot grant a bare star", "bare *" in sh(f"{N} chain check c.json", d).stdout)
ck("hook catches combined no-verify", "deny" in hook(d, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "git commit -nm x"}}))
# final evaluator regressions
d = init(repo()); add_unit(d, "z1"); W(d, "lib/money.py", "def total(items, tax_rate=0.0):\n    return 0\n"); sh(f"{N} gate --unit z1", d)
ck("a prefixed star cannot slip through a grant", sh(f"{N} grant --unit z1 tests --allow 'lost: *' --reason lazy", d).returncode != 0); sh("git checkout lib", d)
d = init(repo()); add_unit(d, "z2"); W(d, "tests/test_new2.py", "def test_n():\n    assert 1 == 2\n"); r = sh(f"{N} gate --unit z2", d); line = json.loads(r.stdout)["failures"][0]["why"][0]
ck("a new failure can be granted from its printed line", sh(f"{N} grant --unit z2 tests --allow '{line}' --reason 'known, tracked'", d).returncode == 0 and sh(f"{N} gate --unit z2", d).returncode == 0)
d = init(repo()); b = J(f"{d}/.noether/baseline.json"); b["quarantine"] = {"tests": {"tests.test_money::test_total": 0}}; Path(d, ".noether/baseline.json").write_text(json.dumps(b)); W(d, "lib/money.py", "def total(items, tax_rate=0.0):\n    return 0\n")
r = sh(f"{N} gate --unit -", d); ck("a quarantined test failing is warned about", "not protected" in r.stdout and "test_total" in r.stdout, r.stdout + r.stderr)
if shutil.which("go"):
    d = tempfile.mkdtemp(prefix="noe-"); W(d, "go.mod", "module m\n\ngo 1.21\n"); W(d, "a.go", "package m\n\nfunc A() int { return 1 }\n"); W(d, "a_test.go", 'package m\n\nimport "testing"\n\nfunc TestA(t *testing.T) {\n\tif A() != 1 {\n\t\tt.Fail()\n\t}\n}\n\nfunc TestRed(t *testing.T) { t.Fail() }\n')
    for c in ("git init -q -b main", "git config user.email a@b", "git config user.name a", "git add -A", "git commit -q -m i"): sh(c, d)
    init(d); ck("go gets per-test tracking despite a red test", J(f"{d}/.noether/baseline.json")["q"]["tests"] == ["TestA"])
    W(d, "a.go", "package m\n\nfunc A() int { return 2 }\n"); r = sh(f"{N} gate", d); ck("a go regression is vetoed", r.returncode == 1 and "lost: TestA" in r.stdout, r.stdout + r.stderr)
if shutil.which("cargo"):
    d = tempfile.mkdtemp(prefix="noe-"); os.makedirs(f"{d}/src"); W(d, "Cargo.toml", '[package]\nname = "m"\nversion = "0.1.0"\nedition = "2021"\n'); W(d, "src/lib.rs", "pub fn a() -> i32 { 1 }\n#[cfg(test)]\nmod t {\n    #[test] fn ok() { assert_eq!(super::a(), 1); }\n    #[test] fn red() { assert_eq!(1, 2); }\n}\n"); W(d, ".gitignore", "target\n")
    for c in ("git init -q -b main", "git config user.email a@b", "git config user.name a", "git add -A", "git commit -q -m i"): sh(c, d)
    init(d); ck("rust gets per-test tracking despite a red test", any("ok" in x for x in J(f"{d}/.noether/baseline.json")["q"]["tests"]))
    W(d, "src/lib.rs", "pub fn a() -> i32 { 2 }\n#[cfg(test)]\nmod t {\n    #[test] fn ok() { assert_eq!(super::a(), 1); }\n    #[test] fn red() { assert_eq!(1, 2); }\n}\n"); r = sh(f"{N} gate", d); ck("a rust regression is vetoed", r.returncode == 1 and "lost:" in r.stdout, r.stdout + r.stderr)
print(f"\n{'ALL PASS' if not fails else 'FAILED: ' + str(fails)}")
sys.exit(1 if fails else 0)
