#!/usr/bin/env python3
# ruff: noqa
# fmt: off
# type: ignore
"""noether: a conservation gate for long-horizon coding agents. Stdlib only.

Constructs. Check: a function of repo state with an order. Harness: checks + scope + budgets.
Loop: bounded work units, each with a proof. Agent: an untrusted worker with a declared footprint.
Skill: a capability bound to an agent. Receipt: what a harness certifies. Chain: seq/par/nest of stages.

Order (commit iff state >= baseline, pointwise):
  pass: exit 0 | keep: baseline lines subset of current | none: no lines | max: <= base+eps | min: >= base-eps
Baselines are high-water marks, so eps bounds total drift. Soft axes never average: each must clear its threshold.
"""
import argparse, ast, fnmatch, hashlib, json, math, os, re, shutil, subprocess as sp, sys, signal, tempfile, time, shlex, textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

VOLATILE = [".noether/baseline.json", ".noether/log.jsonl", ".noether/units"]
ROOT = N = RUN = None
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)/|(_test|\.test|\.spec|_spec)\.[a-z]+$|(^|/)test_[^/]*$")
ASSERT = re.compile(r"\b(assert\w*|expect\(|require\.|should\.|t\.(Error|Fatal)\w*|pytest\.raises)")
TEST_DATA = re.compile(r"^[A-Z][A-Z0-9_]*\s*=")
SKIPPED = re.compile(r"(@pytest\.mark\.(skip|xfail)|@unittest\.skip|\b(it|test|describe)\.(skip|only)\(|\bxit\(|t\.Skip\()")
SECRET = {"aws": r"AKIA[0-9A-Z]{16}", "private_key": r"-----BEGIN [A-Z ]*PRIVATE KEY", "github": r"gh[pousr]_[A-Za-z0-9]{30,}",
          "slack": r"xox[abprs]-[A-Za-z0-9-]{10,}", "anthropic_openai": r"sk-[A-Za-z0-9_-]{24,}", "stripe": r"[sr]k_(live|test)_[A-Za-z0-9]{16,}",
          "assigned": r"(?i)(api[_-]?key|secret|token|passw(or)?d)[\w-]*\s*[:=]\s*['\"][A-Za-z0-9_/+=-]{16,}['\"]"}


def die(msg, code=1):
    print(msg, file=sys.stderr); sys.exit(code)
def git(*a, cwd=None, env=None):
    return sp.run(["git", "-c", "core.quotePath=false", *a], cwd=cwd or ROOT, env=env, text=True, capture_output=True)
def G(*a, cwd=None, env=None):
    r = git(*a, cwd=cwd, env=env)
    if r.returncode: die(f"git {' '.join(a)}: {r.stderr.strip()}", 3)
    return r.stdout.strip()
def rd(p, default=None):
    try: return json.loads(Path(p).read_text())
    except (OSError, ValueError): return default
def wr(p, obj):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")
def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()[:16]
def log(event, **kw):
    with open(N / "log.jsonl", "a") as f: f.write(json.dumps({"e": event, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **kw}, sort_keys=True) + "\n")
def events():
    try: return [json.loads(l) for l in open(N / "log.jsonl") if l.strip()]
    except OSError: return []
def locate(path=None):
    global ROOT, N, RUN
    r = sp.run(["git", "rev-parse", "--show-toplevel"], cwd=path, text=True, capture_output=True)
    if r.returncode: die("not a git repository: run `git init` and make a first commit", 3)
    ROOT = Path(r.stdout.strip()); N = ROOT / ".noether"; RUN = N / "run"
def common():
    return Path(G("rev-parse", "--path-format=absolute", "--git-common-dir")) / "noether"
def ready():
    if not (N / "harness.json").exists(): die("no harness here: run `noether.py init`", 3)
    hk = Path(G("rev-parse", "--path-format=absolute", "--git-common-dir")) / "hooks" / "pre-commit"
    if not hk.exists():  # hooks and merge drivers do not travel with a clone
        hk.parent.mkdir(exist_ok=True); hk.write_text("#!/bin/sh\nexec python3 .noether/noether.py precommit\n"); hk.chmod(0o755); G("config", "merge.ours.driver", "true")
def hermetic(extra=None):
    e = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE")}
    e.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPYCACHEPREFIX=tempfile.mkdtemp(prefix="noether-pyc-"), **(extra or {}))
    return e
def hrun(cmd, cwd=None, timeout=3600):
    e = hermetic()
    try: return sp.run(cmd, shell=True, cwd=cwd or ROOT, env=e, capture_output=True, text=True, timeout=timeout)
    finally: shutil.rmtree(e["PYTHONPYCACHEPREFIX"], ignore_errors=True)
def write_reds(names):
    RUN.mkdir(parents=True, exist_ok=True); (RUN / "red.txt").write_text("\n".join(sorted(names)))
def item(v):
    return v.split(": ", 1)[1] if ": " in v else v
def code_tree(use_index=False):
    """Hash of the code state: everything except the harness's own volatile records."""
    with tempfile.TemporaryDirectory() as d:
        real = Path(os.environ.get("GIT_INDEX_FILE") or ROOT / G("rev-parse", "--git-path", "index"))
        idx = os.path.join(d, "i")
        if real.exists(): shutil.copy2(real, idx)  # keep mtime: a newer index makes git trust racily-clean entries
        e = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}; e["GIT_INDEX_FILE"] = idx
        if not use_index: G(*ADD, env=e)
        G("rm", "-r", "-q", "--cached", "--ignore-unmatch", *VOLATILE, env=e)
        return G("write-tree", env=e)
ADD = ["add", "-A", "--", ".", ":(exclude,glob)**/__pycache__/**", ":(exclude,glob)**/*.pyc"]
def base_rev():
    return os.environ.get("NOETHER_BASE", "HEAD")
def touched(a, b):
    return [p for p in G("diff", "--name-only", a, b).splitlines() if not p.startswith(".noether/")]
def match(item, pats):
    return any(item == p or fnmatch.fnmatch(item, p) for p in pats)


# ---- probes: built-in measurements of state, used as check commands
def probe_pytest(args):
    with tempfile.TemporaryDirectory() as d:
        x = os.path.join(d, "r.xml")
        r = sp.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={x}", *args], cwd=ROOT, capture_output=True, text=True)
        if r.returncode == 5: return
        if not os.path.exists(x): die(r.stdout[-800:] + r.stderr[-800:], 2)
        reds = []
        for tc in ET.parse(x).getroot().iter("testcase"):
            name = f"{tc.get('classname')}::{tc.get('name')}"
            if any(ch.tag in ("failure", "error") for ch in tc): reds.append(name)
            elif not any(ch.tag == "skipped" for ch in tc): print(name)
        write_reds(reds)
def probe_pyapi(_):
    for f in G("ls-files", "--cached", "--others", "--exclude-standard", "*.py").splitlines():
        parts = f[:-3].split("/")
        if f.startswith(".noether/") or TEST_PATH.search(f) or any(p.startswith("_") and p != "__init__" for p in parts): continue
        if not (ROOT / f).exists(): continue
        mod = ".".join(p for p in parts if p != "__init__")
        def emit(name, n):
            a = n.args
            names = a.posonlyargs + a.args + a.kwonlyargs; req = len(a.posonlyargs + a.args) - len(a.defaults) + sum(d is None for d in a.kw_defaults)
            print(name)
            for k in range(req, len(names) + 1): print(f"{name}/required<={k}")
            for p in names: print(f"{name}:{p.arg}")
        for n in ast.parse((ROOT / f).read_text()).body:
            if getattr(n, "name", "_").startswith("_"): continue
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)): emit(f"{mod}.{n.name}", n)
            elif isinstance(n, ast.ClassDef):
                print(f"{mod}.{n.name}")
                for m in n.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and (not m.name.startswith("_") or m.name == "__init__"):
                        emit(f"{mod}.{n.name}.{m.name}", m)
def _diff():
    out, cur, gone, old = [], None, None, 0
    for l in G("diff", "-U0", "--no-color", base_rev(), code_tree()).splitlines():
        h = re.match(r"@@ -(\d+)", l)
        if h: old = int(h.group(1))
        elif l.startswith("--- "): gone = l[6:] if l.startswith("--- a/") else None
        elif l.startswith("+++ "): cur = l[6:] if l.startswith("+++ b/") else gone
        elif cur and not cur.startswith(".noether/") and l[:1] in "+-" and not l.startswith(("---", "+++")):
            out.append((cur, l[0], l[1:].strip(), old)); old += l[0] == "-"
    return out
def probe_secrets(_):
    d = _diff()
    for f, sign, text, _ in d:
        if sign == "+":
            for rule, rx in SECRET.items():
                if re.search(rx, text) and not (rule == "assigned" and TEST_PATH.search(f)): print(f"{f}: {rule} {hashlib.sha256(text.encode()).hexdigest()[:8]}")
    if shutil.which("gitleaks"):
        r = sp.run(["gitleaks", "stdin", "--redact", "--no-banner"], input=G("diff", base_rev(), code_tree()), text=True, capture_output=True)
        if r.returncode: print("gitleaks: findings in diff")
def probe_weaken(_):
    strip = lambda s: re.sub(r"\s+(#|//).*$", "", s)
    d = [(f, s, strip(x), n) for f, s, x, n in _diff()]
    addset = {x for _, s, x, _ in d if s == "+"}
    for f, sign, text, line in d:
        if not TEST_PATH.search(f) and Path(f).name not in ("conftest.py", "pytest.ini", "tox.ini"): continue
        if sign == "-" and (ASSERT.search(text) or TEST_DATA.match(text)) and text not in addset: print(f"{f}: removed or edited: {text[:100]}")
        if sign == "+" and SKIPPED.search(text): print(f"{f}: skip: {text[:100]}")
def probe_passing(args):
    """Print group 1 of each line matching a regex: the passing tests of any runner with line output."""
    i = args.index("--"); rx, bad, cmd = args[0], args[1] if i == 2 else None, args[i + 1:]
    r = sp.run(cmd, cwd=ROOT, text=True, capture_output=True); out_ = r.stdout + r.stderr
    if r.returncode == 127: die("command not found", 2)
    names = lambda x: {m.group(1).strip() for m in re.finditer(x, out_, re.M)}
    found = sorted(names(rx) - (names(bad) if bad else set())); failed = names(bad) if bad else set()
    if bad: write_reds(failed)
    if not found and r.returncode and not failed: die((r.stdout + r.stderr)[-800:], 2)
    print("\n".join(found))
def probe_count(args):
    rx, cmd = args[0], args[args.index("--") + 1:]
    r = sp.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if r.returncode == 127: die("command not found", 2)
    print(sum(1 for l in (r.stdout + r.stderr).splitlines() if re.search(rx, l)))
PROBES = {"pytest": probe_pytest, "pyapi": probe_pyapi, "secrets": probe_secrets, "weaken": probe_weaken, "count": probe_count, "passing": probe_passing}


# ---- the conserved vector and its order
def measure(c, cwd=None, runs=1):
    vals, reds = [], set()
    for _ in range(runs):
        try:
            r = hrun(c["cmd"], cwd=cwd, timeout=c.get("timeout", 3600))
        except sp.TimeoutExpired:
            return None, "did not finish"
        reds |= set(_read(RUN / "red.txt").splitlines())
        if r.returncode == 127: return None, "did not run: command not found"
        if c["class"] == "pass":
            if r.returncode: OUTPUT[c["id"]] = (r.stdout + r.stderr).strip()[-300:]; return False, None
            vals.append(True); continue
        if r.returncode: return None, f"did not run (exit {r.returncode}): {(r.stderr or r.stdout)[-300:]}"
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        if c["class"] in ("keep", "none"): vals.append(sorted(set(lines)))
        else:
            try: vals.append(float(lines[-1]))
            except (IndexError, ValueError): return None, "did not produce a number"
    if runs > 1 and reds: write_reds(reds)
    if c["class"] == "keep": return sorted(set.intersection(*map(set, vals))), None
    return vals[0], None
OUTPUT = {}
def violations(c, val, base, allow):
    k, eps = c["class"], c.get("eps", 0)
    ok = lambda i: match(i, allow)
    if k == "pass": return [] if (val or "*" in allow) else ["check failed: " + OUTPUT.get(c["id"], "")]
    if k == "none": return [i for i in val if not ok(i)]
    if k == "keep": return [f"lost: {i}" for i in base or [] if i not in set(val) and not ok(i)]
    if k == "max": return [f"{val} > {base} + {eps}"] if val > base + eps else []
    return [f"{val} < {base} - {eps}"] if val < base - eps else []
def high_water(c, val, base):
    k = c["class"]
    return val if k == "keep" else min(base, val) if k == "max" else max(base, val) if k == "min" else base


# ---- state
def harness():
    return rd(N / "harness.json")
def h_sha():
    return hashlib.sha256((N / "harness.json").read_bytes() + (N / "noether.py").read_bytes()).hexdigest()[:16]
def baseline():
    return rd(N / "baseline.json", {"q": {}, "harness_sha": "", "protected": []})
def stage_ctx():
    return rd(RUN / "stage.json", {})
EXTRA = []
def all_checks():
    return harness()["checks"] + stage_ctx().get("checks", []) + EXTRA
def unit_path(u):
    return N / "units" / f"{u}.json"
def start_of(u):
    s = u["start"]
    if not s.startswith("after:"): return s
    r = git("log", "-1", "--format=%H", "--fixed-strings", f"--grep=noether: unit {s[6:]} passed")
    return r.stdout.strip() or G("rev-parse", "HEAD")
def units():
    return sorted((rd(p) for p in (N / "units").glob("*.json")), key=lambda u: (u["seq"], u["id"]))
def get_unit(uid=None):
    if uid == "-": return None  # commit outside any unit: checks apply, unit scope does not
    uid = uid or stage_ctx().get("stage")
    if uid:
        u = rd(unit_path(uid))
        if not u: die(f"no unit {uid}")
        return u
    return next((u for u in units() if u["status"] == "open"), None)
def halt_file():
    c = stage_ctx().get("chain")
    return common() / c / "HALT" if c else None
def scope_for(u):
    st = stage_ctx()
    return st.get("writes") or (u or {}).get("scope") or harness().get("scope") or ["**"]


def deflake(c, viol, b):
    """A kept item failed. It is excused only if it also flakes on the unchanged baseline; excused by item, not by check."""
    suspects = {item(v) for v in viol if v.startswith(("lost: ", "new failure: "))}
    with tempfile.TemporaryDirectory() as d:
        wt = os.path.join(d, "w")
        if git("worktree", "add", "--detach", "-q", wt, "HEAD").returncode: return viol, []
        try:
            os.makedirs(f"{wt}/.noether", exist_ok=True); shutil.copy(N / "noether.py", f"{wt}/.noether/noether.py")
            passed, failed = set(), set()
            for _ in range(c.get("flake_runs", 4)):
                val, err = measure(c, cwd=wt)
                if err: return viol, []
                passed |= suspects & set(val); failed |= suspects - set(val)
                if passed & failed == suspects: break
        finally:
            git("worktree", "remove", "--force", wt)
    flaky = passed & failed
    return [v for v in viol if item(v) not in flaky], sorted(flaky)


def evaluate(u=None, grants=None, use_cache=True, base_scope=True):
    h, b, sha = harness(), baseline(), h_sha()
    tree = code_tree(); uid = (u or {}).get("id")
    cache = rd(RUN / "gate.json", {})
    hf0 = halt_file() if base_scope else None
    gk = digest([(u or {}).get("grants", []), bool(hf0 and hf0.exists()), G("rev-parse", "--abbrev-ref", "HEAD")])
    if use_cache and (cache.get("tree"), cache.get("unit"), cache.get("sha"), cache.get("gk")) == (tree, uid, sha, gk): return cache
    fails, q, halt, warnings, flaky = [], {}, False, [], {}
    hf = halt_file() if base_scope else None
    if hf and hf.exists(): halt = True; fails.append({"id": "chain", "why": ["a stage in this chain hit a hard stop"]})
    if b["harness_sha"] != sha: fails.append({"id": "integrity", "why": ["harness.json or noether.py changed outside `learn`/`rehash`"]})
    active = {c["id"] for c in all_checks() if c.get("mode", "veto") == "veto"}
    if set(b["protected"]) - active: fails.append({"id": "integrity", "why": [f"protected check removed or demoted: {sorted(set(b['protected']) - active)}"]})
    allow = {}
    for g in (grants if grants is not None else (u or {}).get("grants", [])): allow.setdefault(g["check"], []).extend(g["allow"])
    red = None
    for c in all_checks():
        if c["id"] == "tests": (RUN / "red.txt").unlink(missing_ok=True)
        val, err = measure(c)
        v = [err] if err else violations(c, val, b["q"].get(c["id"], [] if c["class"] in ("keep", "none") else 0), allow.get(c["id"], []))
        if c["id"] == "tests" and not err and (RUN / "red.txt").exists():
            red = _read(RUN / "red.txt").splitlines(); known = set(b.get("red", [])) | set(b["q"].get("tests", []))
            v += [f"new failure: {i}" for i in red if i not in known and not match(i, allow.get("tests", []))]
        quarantined = set(b.get("quarantine", {}).get(c["id"], []))
        if v and not err and c["class"] == "keep": v = [x for x in v if item(x) not in quarantined]
        if v and not err and c.get("flaky") and c["class"] == "keep":
            v, fl = deflake(c, v, b)
            if fl: flaky[c["id"]] = fl; quarantined |= set(fl)
        if not err and c["class"] == "keep":
            for i in sorted(x for x in quarantined if x not in set(val)): warnings.append(f"flaky on the unchanged code, so not protected: {i}")
        if c.get("mode") == "shadow" and c["id"] == "tests": warnings.append("tests are in shadow mode: nothing protects behaviour")
        if c.get("mode", "veto") == "shadow":
            if v: log("shadow_fire", check=c["id"], tree=tree, why=v[:3])
            continue
        if v:
            fails.append({"id": c["id"], "why": v[:15] + ([f"see: {c['cmd']}"] if c["class"] in ("max", "min") else []), "count": len(v)})
            halt = halt or c.get("on_fail") == "halt"
        elif not err: q[c["id"]] = val
    if base_scope:
        out = [p for p in touched(base_rev(), tree) if not match(p, scope_for(u))]
        if out: fails.append({"id": "scope", "why": out[:15], "count": len(out)})
    hidden = [f for f in G("ls-files", "-oi", "--exclude-standard").splitlines() if (TEST_PATH.search(f) or f.endswith("conftest.py")) and not re.search(r"(^|/)(\.noether|\.venv|venv|node_modules|site-packages|__pycache__)/|\.pyc$", f)]
    res = {"ok": not fails, "halt": halt, "tree": tree, "unit": uid, "sha": sha, "gk": gk, "failures": fails, "q": q, "flaky": flaky, "red": red, "warnings": warnings + [f"gitignored test file can affect this gate but is not committed: {f}" for f in hidden[:10]] + (["detached HEAD: commits here belong to no branch"] if G("rev-parse", "--abbrev-ref", "HEAD") == "HEAD" else [])}
    wr(RUN / "gate.json", res)
    if halt and hf and not hf.exists(): hf.parent.mkdir(parents=True, exist_ok=True); hf.write_text(tree); log("halt", unit=uid, failures=[x["id"] for x in fails])
    with open(RUN / "gates.jsonl", "a") as f: f.write(json.dumps({"ok": res["ok"], "unit": uid}) + "\n")
    return res
def charge(u, res):
    """Looking at the gate is free. A failed commit, brief or done costs one attempt per distinct tree."""
    if not u or res["ok"] or u.get("failed_tree") == res["tree"] or all(x["id"] == "chain" for x in res["failures"]): return
    u["attempts"] += 1; u["failed_tree"] = res["tree"]; log("reject", unit=u["id"], tree=res["tree"], failures=[x["id"] for x in res["failures"]])
    if u["attempts"] >= u["max_attempts"]: u["status"] = "halted"; log("saturated", unit=u["id"])
    wr(unit_path(u["id"]), u)
def show(res, u=None):
    out = {k: res[k] for k in ("ok", "halt", "failures", "warnings") if res.get(k) is not None and res.get(k) != []}
    if u: out["unit"] = u["id"]; out["attempts"] = f"{u['attempts']}/{u['max_attempts']}"; out["status"] = u["status"]
    print(json.dumps(out, indent=1))
def rc(res, u=None):
    return 2 if res.get("halt") or (u and u["status"] == "halted") else 0 if res["ok"] else 1
def advance_baseline(res):
    b = baseline(); cs = {c["id"]: c for c in harness()["checks"]}
    for k, v in res["q"].items():
        if k in cs: b["q"][k] = high_water(cs[k], v, b["q"].get(k, v))
    if res.get("red") is not None: b["red"] = res["red"]
    qq = b.setdefault("quarantine", {}); flaky = res.get("flaky", {})
    for k, items in flaky.items(): qq.setdefault(k, {}).update({i: 0 for i in items}); log("quarantine", check=k, items=items)
    for k, items in qq.items():  # a flaky test is protected again only after five straight passing commits
        cur = set(res["q"].get(k, []))
        for i in [i for i in items if i not in flaky.get(k, [])]:
            items[i] = items[i] + 1 if i in cur else 0
            if items[i] >= 5: del items[i]
    b["harness_sha"] = h_sha(); wr(N / "baseline.json", b)


# ---- commands: single loop
def detect():
    checks, warn = [], []
    py = any(not f.startswith(".noether/") for f in G("ls-files", "*.py").splitlines()) or list(ROOT.glob("*.py"))
    me = "python3 .noether/noether.py probe"
    def add(i, k, cmd, **kw):
        if not any(c["id"] == i for c in checks): checks.append({"id": i, "class": k, "cmd": cmd, "mode": "veto", **kw})
    if py and sp.run([sys.executable, "-m", "pytest", "--version"], capture_output=True).returncode == 0:
        add("tests", "keep", f"{me} pytest", protected=True, authorizable=True, flaky=True)
    if py: add("public_api", "keep", f"{me} pyapi", protected=True, authorizable=True)
    if py and shutil.which("mypy") and ((ROOT / "mypy.ini").exists() or "tool.mypy" in _read(ROOT / "pyproject.toml")):
        add("type_errors", "max", f"{me} count ': error:' -- mypy --exclude '^\\.noether' .")
    if py and shutil.which("ruff") and ((ROOT / "ruff.toml").exists() or (ROOT / ".ruff.toml").exists() or "tool.ruff" in _read(ROOT / "pyproject.toml")): add("lint", "max", f"{me} count '^[^ ].*:[0-9]+:[0-9]+:' -- ruff check --extend-exclude .noether --output-format=concise .")
    pkg = rd(ROOT / "package.json", None)
    script = (pkg or {}).get("scripts", {}).get("test", "no test specified")
    if "node --test" in script: add("tests", "keep", f"{me} passing '^\\s*ok \\d+ - (.+)$' '^\\s*not ok \\d+ - (.+)$' -- sh -c {shlex.quote(script.replace('node --test', 'node --test --test-reporter=tap', 1))}", protected=True, authorizable=True, flaky=True)
    elif pkg and "no test specified" not in script: add("tests", "pass", "npm test --silent", protected=True, authorizable=True)
    if (ROOT / "tsconfig.json").exists() and shutil.which("tsc"): add("type_errors", "max", f"{me} count 'error TS' -- tsc --noEmit")
    if (ROOT / "go.mod").exists(): add("tests", "keep", f"{me} passing '--- PASS: (\\S+)' '--- FAIL: (\\S+)' -- go test -v ./...", protected=True, authorizable=True, flaky=True); add("vet", "pass", "go vet ./...")
    if (ROOT / "Cargo.toml").exists(): add("tests", "keep", f"{me} passing '^test (\\S+) \\.\\.\\. ok' '^test (\\S+) \\.\\.\\. FAILED' -- cargo test", protected=True, authorizable=True, flaky=True)
    add("secrets", "none", f"{me} secrets", protected=True, on_fail="halt", authorizable=True)
    add("tests_not_weakened", "none", f"{me} weaken", protected=True, authorizable=True)
    if not any(c["id"] == "tests" for c in checks): warn.append("no test runner detected: nothing conserves behaviour; add one with `learn add`")
    if not shutil.which("gitleaks"): warn.append("gitleaks not installed: secrets uses the built-in pattern scan, which is weaker")
    return checks, warn
def _read(p):
    try: return Path(p).read_text()
    except OSError: return ""
def cmd_init(a):
    locate()
    if git("rev-parse", "HEAD").returncode: die("repository has no commits: make one first", 3)
    if (N / "harness.json").exists() and not a.force: die("already initialised (use --force to re-detect)")
    if [l for l in git("status", "--porcelain").stdout.splitlines() if "__pycache__" not in l and ".pyc" not in l] and not a.dirty: die("commit or stash your changes first, so the baseline is the committed state (or pass --dirty)")
    (RUN).mkdir(parents=True, exist_ok=True); (N / "units").mkdir(exist_ok=True)
    (N / ".gitignore").write_text("run/\n"); (N / ".gitattributes").write_text("baseline.json merge=ours\nlog.jsonl merge=union\n")
    G("config", "merge.ours.driver", "true")
    if Path(__file__).resolve() != (N / "noether.py").resolve(): shutil.copy(__file__, N / "noether.py")
    checks, warn = detect()
    h = {"version": 1, "checks": checks, "scope": ["**"], "loop": {"attempts": 12, "judge_attempts": 3},
         "axes": [{"id": "acceptance", "threshold": 0.6, "rubric": "The change fully meets the unit's goal, including edge cases the goal implies."},
                  {"id": "maintainable", "threshold": 0.6, "rubric": "A maintainer can follow it; it fits the existing structure; no needless churn."},
                  {"id": "test_honesty", "threshold": 0.6, "rubric": "Tests assert behaviour and would fail if the feature broke."}]}
    wr(N / "harness.json", h); (N / "log.jsonl").touch()
    if a.force: log("repin")
    q, red = {}, []
    for c in checks:
        val, err = measure(c, runs=2 if c.get("flaky") else 1)
        if c["id"] == "tests": red = _read(RUN / "red.txt").splitlines()
        if err or (c["class"] == "pass" and not val):
            c["mode"] = "shadow"; c.pop("protected", None); warn.append(f"{c['id']}: {'did not run' if err else 'fails at baseline'}; left in shadow mode: {err or ''}"[:200])
        elif c["class"] == "none": q[c["id"]] = []
        else: q[c["id"]] = val
    wr(N / "harness.json", h)
    wr(N / "baseline.json", {"q": q, "red": red, "harness_sha": h_sha(), "protected": [c["id"] for c in checks if c.get("protected")]})
    hk = Path(G("rev-parse", "--path-format=absolute", "--git-common-dir")) / "hooks" / "pre-commit"
    hk.parent.mkdir(exist_ok=True)
    if not hk.exists() or "noether" in _read(hk): hk.write_text('#!/bin/sh\nexec python3 .noether/noether.py precommit\n'); hk.chmod(0o755)
    else: warn.append("a pre-commit hook already exists; add `python3 .noether/noether.py precommit` to it")
    if a.claude: install_claude()
    print(json.dumps({"checks": {c["id"]: c["class"] + ("" if c["mode"] == "veto" else " (shadow)") for c in checks},
                      "warnings": warn, "next": "python3 .noether/noether.py commit -m 'noether: init'"}, indent=1))
def install_claude():
    p = ROOT / ".claude" / "settings.json"; s = rd(p, {}) or {}
    cmd = 'python3 "$CLAUDE_PROJECT_DIR/.noether/noether.py" hook'
    entry = lambda m: {"matcher": m, "hooks": [{"type": "command", "command": cmd}]}
    hooks = s.setdefault("hooks", {})
    deny = s.setdefault("permissions", {}).setdefault("deny", [])  # native rules, enforced by Claude Code rather than by this script
    deny += [r for r in ("Edit(.noether/**)", "Write(.noether/**)") if r not in deny]
    for ev, m in (("PreToolUse", "Bash"), ("SessionStart", "compact|resume")):
        if not any(cmd in json.dumps(x) for x in hooks.get(ev, [])): hooks.setdefault(ev, []).append(entry(m))
    wr(p, s)
def cmd_hook(_):
    try: ev = json.load(sys.stdin)
    except ValueError: return 0
    name = ev.get("hook_event_name"); locate(ev.get("cwd"))
    if not (N / "harness.json").exists(): return 0
    if name == "SessionStart": cmd_status(argparse.Namespace(done=False)); return 0
    if name != "PreToolUse": return 0
    t, ti = ev.get("tool_name"), ev.get("tool_input", {})
    def say(d, why): print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": d, "permissionDecisionReason": why}}))
    if t == "Bash":
        c = ti.get("command", ""); bare = re.sub(r"\"[^\"]*\"|'[^']*'", "", c)
        if re.search(r"\bgit\s+(-\S+\s+)*commit\b.*(--no-v\w*|\s-[a-zA-Z]*n[a-zA-Z]*\b)", bare) or "core.hooksPath" in c: say("deny", "Bypassing the conservation gate is not allowed. Use noether.py commit.")
        elif re.search(r"(noether\.py\b.*|(^|[;&|]\s*)n\s+)\b(grant|rehash|learn\s+(promote|retire)|unit\s+reopen|chain\s+resume|init\s.*--force)\b", c, re.S): say("ask", "This changes what the harness conserves. A person should approve it.")
    return 0
def cmd_precommit(_):
    locate(); ok = rd(RUN / "commit_ok.json", {}).get("tree")
    if ok and ok == code_tree(use_index=True): return 0
    die("noether: commit refused. Run `python3 .noether/noether.py commit -m ...` so the gate binds to this exact tree.")
def _commit(msg, tree, warnings=()):
    for w in warnings: print("warning: " + w, file=sys.stderr)
    if code_tree() != tree: die("the tree changed while checks ran: " + git("status", "--short").stdout.strip()[:300] + "\nIgnore these files, or have the test or proof clean up after itself.")
    wr(RUN / "commit_ok.json", {"tree": tree})
    G(*ADD)
    if not git("diff", "--cached", "--quiet").returncode: print("nothing to commit"); return G("rev-parse", "HEAD")
    G("commit", "-q", "-m", msg)
    return G("rev-parse", "HEAD")
def cmd_gate(a):
    locate(); ready(); u = get_unit(a.unit); res = evaluate(u, use_cache=not a.fresh)
    show(res, u); return rc(res, u)
def cmd_commit(a):
    locate(); ready(); u = get_unit(a.unit); res = evaluate(u)
    if not res["ok"]: charge(u, res); show(res, u); return rc(res, u) or 1
    before_b = _read(N / "baseline.json"); advance_baseline(res)
    try: print(_commit(a.message, res["tree"], res.get("warnings", []))); return 0
    except SystemExit:
        (N / "baseline.json").write_text(before_b); raise
def cmd_unit(a):
    locate(); ready()
    if a.op == "reopen":
        if a.proof and stage_ctx(): die("this proof belongs to the chain file: change it there, commit, then `chain start --reopen`")
        u = get_unit(a.id); u["reopened"] = u.get("reopened", 0) + 1; u.update(status="open", attempts=0, judge_fails=0, **{k: v for k, v in (("scope", a.scope), ("goal", a.goal), ("proof", a.proof)) if v}); wr(unit_path(a.id), u); log("reopen", unit=a.id); print(f"unit {a.id} reopened"); return 0
    if not a.proof: die("--proof: a command that exits 0 only when this unit is really done")
    h = harness(); seq = max([u["seq"] for u in units()] or [0]) + 1
    if unit_path(a.id).exists(): die(f"unit {a.id} exists")
    wr(unit_path(a.id), {"id": a.id, "goal": a.goal, "proof": a.proof, "scope": a.scope or [], "seq": seq, "status": "open", "attempts": 0, "judge_fails": 0,
                         "max_attempts": a.attempts or h["loop"]["attempts"], "start": G("rev-parse", "HEAD"), "grants": []})
    print(f"unit {a.id} added"); return 0
def cmd_brief(a):
    locate(); ready(); u = get_unit(a.unit); h = harness()
    if not u:
        held = [x["id"] for x in units() if x["status"] == "halted"]
        die(f"unit {held[0]} is halted: tell a person" if held else "no open unit")
    if u["status"] != "open": die(f"unit {u['id']} is {u['status']}: tell a person")
    res = evaluate(u)
    if not res["ok"]: charge(u, res); show(res, u); print("Fix these before asking for an evaluation.", file=sys.stderr); return rc(res, u) or 1
    print(f"You are a fresh evaluator. Assume the work is flawed until shown otherwise. Do not edit anything.\n\nGOAL: {u['goal']}\nPROOF COMMAND: {u['proof']}\n\nInspect the change with: git diff {start_of(u)} -- . ':(exclude).noether' (plus untracked files via git status -- . ':(exclude).noether').\n\nScore each axis 0 to 1 on its own:")
    for x in h["axes"]: print(f"- {x['id']} (must reach {x['threshold']}): {x['rubric']}")
    if u["grants"]: print(f"\nGRANTS IN FORCE, which you should weigh: {[(g['check'], g['allow'], g['reason']) for g in u['grants']]}")
    print(f"\nFinish by running from {ROOT}:\n  python3 .noether/noether.py judge --unit {u['id']} --by <your-agent-id> --scores id=score,id=score --note '<one line on the weakest axis>'")
    return 0
def waived(u):
    return {g["check"] for g in u["grants"] if g.get("axis")}
def cmd_judge(a):
    locate(); ready(); tree = code_tree(); h = harness(); u = get_unit(a.unit)
    scores = {k: float(v) for k, v in (p.split("=") for p in a.scores.split(","))}
    missing = [x["id"] for x in h["axes"] if x["id"] not in scores]
    if missing: die(f"score every axis; missing {missing}")
    p = RUN / "judges" / f"{a.unit}.json"; d = rd(p, {})
    if d.get("tree") != tree: d = {"tree": tree, "samples": []}
    if a.by in d.get("failed", []) or any(s["by"] == a.by for s in d["samples"]): die(f"evaluator {a.by} already judged this tree; use a fresh evaluator, or change the code")
    bad = [f"{x['id']}={scores[x['id']]}" for x in h["axes"] if scores[x["id"]] < x["threshold"] and x["id"] not in waived(u)]
    log("judge", unit=a.unit, tree=tree, by=a.by, scores=scores, passed=not bad, note=a.note or "")
    if bad:
        u["judge_fails"] += 1; d["samples"] = []; d.setdefault("failed", []).append(a.by); wr(p, d)
        if u["judge_fails"] >= h["loop"]["judge_attempts"]: u["status"] = "halted"; log("saturated", unit=a.unit, why="judges")
        wr(unit_path(a.unit), u)
        print(json.dumps({"ok": False, "below_threshold": bad, "note": a.note or "", "fresh_samples_needed_next": 1 if a.by == "self" else min(3, 1 + u["judge_fails"]), "status": u["status"]}, indent=1))
        return 2 if u["status"] == "halted" else 1
    d["samples"].append({"by": a.by, "scores": scores}); wr(p, d); print(f"{len(d['samples'])} sample(s) for this tree"); return 0
def judged(u, tree):
    """Every fresh evaluator must clear every axis. Each failed attempt raises how many must."""
    d = rd(RUN / "judges" / f"{u['id']}.json", {}); s = d.get("samples", []) if d.get("tree") == tree else []
    if not s and d.get("tree") == tree and d.get("failed"): return None, "this tree failed its evaluation: change the code, then judge again"
    need = 1 if any(o["by"] == "self" for o in s) else min(3, 1 + u["judge_fails"])
    return s if len(s) >= need else None, f"need {need} fresh evaluator sample(s) for this tree, have {len(s)}: spawn an evaluator with `brief`"
def cmd_done(a):
    locate(); ready(); u = get_unit(a.unit)
    if not u or u["status"] != "open": die("no open unit" if not u else f"unit is {u['status']}")
    res = evaluate(u)
    if not res["ok"]: charge(u, res); show(res, u); return rc(res, u) or 1
    tree = res["tree"]
    if not touched(start_of(u), tree): die("no change since the unit started; nothing to certify")
    if stage_ctx().get("nested") and not rd(common() / stage_ctx()["nested"] / "state.json", {}).get("landed"): die("run and land the nested chain first")
    try: pr = hrun(u["proof"]); proof_rc, out = pr.returncode, pr.stdout + pr.stderr
    except sp.TimeoutExpired: proof_rc, out = 1, "proof timed out"
    if not proof_rc and re.search(r"\bpytest\b", u["proof"]) and not re.search(r"\b[1-9]\d* passed", out) and re.search(r"\b(\d+ skipped|\d+ deselected|no tests ran)\b", out): proof_rc, out = 1, "the proof ran pytest but no test passed (skipped or not collected)\n" + out
    if proof_rc:
        if u.get("failed_tree") != tree: u["attempts"] += 1; u["failed_tree"] = tree
        if u["attempts"] >= u["max_attempts"]: u["status"] = "halted"; log("saturated", unit=u["id"], why="proof")
        wr(unit_path(u["id"]), u); print(json.dumps({"ok": False, "proof": "failed", "output": out[-1500:], "status": u["status"]}, indent=1)); return 2 if u["status"] == "halted" else 1
    samples, info = judged(u, tree)
    if samples is None: print(json.dumps({"ok": False, "judges": info}, indent=1)); return 1
    st = stage_ctx(); means = {k: round(sum(o["scores"][k] for o in samples) / len(samples), 3) for k in samples[0]["scores"]}
    if st.get("nested"): st["evidence"] = [r.get("digest") for r in map(rd, sorted((common() / st["nested"] / "receipts").glob("*.json")))]
    excused = {g["check"] for g in u["grants"] if not g.get("axis")}
    rec = {"unit": u["id"], "base": start_of(u), "tree": tree, "harness_sha": res["sha"], "claims": sorted(set(res["q"]) - excused) + ["proof"], "touched": touched(start_of(u), tree),
           "grants": u["grants"], "judges": {"means": means, "by": [o["by"] for o in samples]}, "attempts": u["attempts"], "reopened": u.get("reopened", 0), "evidence": st.get("evidence", []), "agent": st.get("agent"), "warnings": res.get("warnings", []) + (["this unit's proof proves nothing"] if u["proof"].strip() in ("true", ":") else []), "decision": "PASSED"}
    if all(o["by"] == "self" for o in samples): rec["self_judged"] = True
    before_u, before_b = _read(unit_path(u["id"])), _read(N / "baseline.json")
    log_before = _read(N / "log.jsonl"); later = [v for v in units() if v["status"] == "open" and v["id"] != u["id"]]; later_before = [_read(unit_path(v["id"])) for v in later]
    u.update(status="passed", receipt=rec); wr(unit_path(u["id"]), u); log("unit_done", unit=u["id"], grants=len(u["grants"]))
    for v in later: v["start"] = f"after:{u['id']}"; wr(unit_path(v["id"]), v)
    advance_baseline(res)
    try: head = _commit(f"noether: unit {u['id']} passed\n\n{u['goal']}", tree, res.get("warnings", []))
    except SystemExit:
        unit_path(u["id"]).write_text(before_u); (N / "baseline.json").write_text(before_b); (N / "log.jsonl").write_text(log_before)
        for v, old in zip(later, later_before): unit_path(v["id"]).write_text(old)
        raise
    if st.get("chain"):
        rec = dict(rec, head=head, stage=st["stage"]); rec["digest"] = digest(rec); wr(common() / st["chain"] / "receipts" / f"{st['stage']}.json", rec)
    print(json.dumps({"ok": True, "head": head, "claims": rec["claims"], "grants": len(u["grants"]), "warnings": rec["warnings"]}, indent=1)); return 0
def cmd_grant(a):
    locate(); ready(); u = get_unit(a.unit); c = next((x for x in all_checks() if x["id"] == a.check), None)
    if not u: die("no open unit")
    if a.axis:
        if any(g.get("axis") for g in u["grants"]): die("one waived axis per unit; ask a person to reconsider the unit instead")
    elif not c or not c.get("authorizable"): die(f"{a.check} is not authorizable")
    if not a.allow and not a.axis: die("name exactly what is excused with --allow PATTERN")
    g = rd(RUN / "gate.json", {}); printed = next((f for f in g.get("failures", []) if f["id"] == a.check), None)
    if a.allow and not a.axis:
        a.allow = [re.sub(r"^(lost|new failure): ", "", x) for x in a.allow]
        if "*" in a.allow and c and c["class"] != "pass": die("name what is excused; a bare * would excuse everything")
        if c and c["class"] == "none" and any(": " not in pat for pat in a.allow): die("a pattern here must include the printed text after the file name, so it cannot excuse a whole file")
        if not printed: die("run `gate` first, then grant from the lines it prints for this check")
        items = [re.sub(r"^(lost|new failure): ", "", x) for x in printed["why"]]
        for pat in a.allow:
            if printed["count"] <= 15 and not any(match(i, [pat]) for i in items): die(f"--allow {pat!r} matches nothing the gate printed. Patterns match those lines, for example: {items[0]!r}")
    if a.check == "secrets" and any(re.search(r"[*?\[]", p) for p in a.allow): die("secrets: excuse one finding at a time, exactly as the gate printed it")
    u["grants"].append({"check": a.check, "allow": a.allow or [], "reason": a.reason, "axis": bool(a.axis)}); wr(unit_path(u["id"]), u)
    log("grant", unit=u["id"], check=a.check, allow=a.allow, reason=a.reason); print("granted, and recorded in the receipt"); return 0
def cmd_rehash(_):
    locate(); ready(); b = baseline(); b["harness_sha"] = h_sha(); wr(N / "baseline.json", b); log("rehash", sha=b["harness_sha"]); return 0
def wilson(x, n, z=1.96):
    if not n: return 0.0
    p = x / n; c = z * z
    return (p + c / (2 * n) - z * math.sqrt(p * (1 - p) / n + c / (4 * n * n))) / (1 + c / n)
def cmd_learn(a):
    locate(); ready(); h = harness(); ev = events()
    if a.op in ("add", "promote", "retire") and baseline()["harness_sha"] != h_sha(): die("the harness was edited outside noether; a person must review it and run rehash")
    find = lambda: next((c for c in h["checks"] if c["id"] == a.id), None) or die(f"no check {a.id}")
    def save():
        wr(N / "harness.json", h); b = baseline(); b["harness_sha"] = h_sha(); wr(N / "baseline.json", b)
    if a.op == "add":
        if any(c["id"] == a.id for c in h["checks"]): die("id exists")
        if a.why is None: die("--why: name the observed failure this would have caught")
        h["checks"].append({"id": a.id, "class": a.cls, "cmd": a.cmd, "mode": "shadow", "why": a.why, "authorizable": True}); save(); log("add", check=a.id, why=a.why); print("added in shadow mode: it logs would-be vetoes and blocks nothing")
    elif a.op == "confirm":
        if not any(e["e"] == "shadow_fire" and e["check"] == a.id for e in ev): die("nothing to confirm: this check has not fired")
        log("confirm", check=a.id, real=a.real == "yes")
    elif a.op == "promote":
        c = find(); xs = [e for e in ev if e["e"] == "confirm" and e["check"] == a.id]; fires = len({json.dumps(e.get("why")) for e in ev if e["e"] == "shadow_fire" and e["check"] == a.id})
        n, x = min(len(xs), fires), min(sum(e["real"] for e in xs), fires); lb = wilson(x, n)
        if lb < 0.5: die(f"not enough evidence: {x}/{n} confirmed, Wilson lower bound {lb:.2f} < 0.5")
        val, err = measure(c)
        if err: die(err)
        if c["class"] == "none" and val: die(f"fix the {len(val)} existing violation(s) first, or it would block unrelated work")
        b = baseline(); c["mode"] = "veto"
        if c["class"] != "pass": b["q"][a.id] = [] if c["class"] == "none" else val
        wr(N / "baseline.json", b); save(); log("promote", check=a.id, lb=round(lb, 2)); print("promoted to veto")
    elif a.op == "retire":
        c = find()
        if c.get("protected"): die("protected: a check that never fires is working")
        h["checks"].remove(c); save(); log("retire", check=a.id); print("retired")
    else: log("note", text=a.id); print("noted")
    return 0
def cmd_status(a):
    locate(); ready(); us = units(); h = harness(); open_ = [u for u in us if u["status"] == "open"]
    if a.done: return 0 if us and all(u["status"] == "passed" for u in us) else 1
    g = rd(RUN / "gate.json", {}); rate = [json.loads(l)["ok"] for l in _read(RUN / "gates.jsonl").splitlines()][-20:]
    ev = events(); st = stage_ctx(); tree = code_tree()
    print(f"HARNESS v{h['version']} @ {h_sha()}  head {G('rev-parse', '--short', 'HEAD')}  branch {G('rev-parse', '--abbrev-ref', 'HEAD')}" + (f"  chain {st['chain']}/{st['stage']}" if st.get("chain") else ""))
    done_n = sum(u["status"] == "passed" for u in us)
    print(f"UNITS: {done_n} passed; " + ("; ".join(f"{u['id']}={u['status']}({u['attempts']}/{u['max_attempts']})" for u in us if u["status"] != "passed") or ("none open" if us else "none. Add with `unit add`.")))
    if common().exists():
        for sf in sorted(common().glob("*/state.json")):
            s = rd(sf, {})
            if not s.get("landed"): print(f"CHAIN IN FLIGHT: {sf.parent.name}: integrated {s.get('integrated', [])}")
    if open_: u = open_[0]; print(f"CURRENT: {u['id']}: {u['goal']}\nPROOF: {u['proof']}\nSCOPE: {scope_for(u)}\nGRANTS: {u['grants'] or 'none'}")
    for u in open_[1:]: print(f"LATER: {u['id']}: {u['goal']}")
    if g: print(f"LAST GATE: {'pass' if g['ok'] else 'REJECT'}{' (stale: tree changed since)' if g['tree'] != tree else ''}: {json.dumps(g['failures'])[:900]}")
    print("WORKING TREE: " + (git("status", "--short").stdout.strip()[:400] or "clean"))
    if rate:
        r = 1 - sum(rate) / len(rate); print(f"GATE RUNS REJECTED (last {len(rate)}): {r:.0%}" + ("  STRANGLING: stop and tell a person; never loosen a check to get through" if r > .85 and len(rate) >= 10 else ""))
    shadow = [c["id"] for c in h["checks"] if c.get("mode") == "shadow"]
    for w in g.get("warnings", []) if g else []: print("WARNING: " + w)
    if shadow: print(f"SHADOW: {shadow}")
    dec = [e for e in ev if e["e"] == "decision"]
    for i, e in enumerate(dec):
        if i >= len(dec) - 3 or (open_ and e.get("unit") == open_[0]["id"]): print("DECIDED: " + describe(e))
    tail = [e for e in ev if e["e"] not in ("shadow_fire", "decision")][-5:]
    if tail: print("LOG: " + " | ".join(textwrap.shorten(f"{e['e']} {describe(e)}", 140, placeholder=" ...") for e in tail))
    chains = [sf.parent.name for sf in sorted(common().glob("*/state.json")) if not rd(sf, {}).get("landed")] if common().exists() else []
    print("NEXT: " + ("work the current unit, then brief, judge, done" if open_ else f"chain next <file> (chain {chains[0]} is in flight)" if chains else "all units resolved" if us else "unit add ..."))
    return 0
def cmd_decide(a):
    locate(); ready(); u = get_unit(a.unit); log("decision", what=a.what, why=a.why, unit=(u or {}).get("id")); print("logged"); return 0
def describe(e):
    k = e["e"]; u = f"[{e['unit']}] " if e.get("unit") else ""
    if k == "decision": return f"{u}{e['what']} (because {e['why']})"
    if k == "judge": return f"{u}{e['by']} {'passed' if e['passed'] else 'FAILED'} {e['scores']}" + (f": {e['note']}" if e.get("note") else "")
    return u + ", ".join(f"{x}={v}" for x, v in e.items() if x not in ("e", "ts", "unit", "tree"))
def cmd_log(a):
    locate(); ready()
    kinds = {"decisions": {"decision"}, "judgments": {"judge", "reject", "grant", "unit_done", "saturated", "promote", "retire", "quarantine", "integrate", "shadow_fire", "confirm"}}.get(a.only)
    rows = sorted((e for e in events() if not kinds or e["e"] in kinds), key=lambda e: e.get("ts", ""))
    for e in rows[-a.n if a.n else 0:]: print(f"{e.get('ts', '-'):<21}{e['e']:<12} {describe(e)}")
    return 0
def cmd_goal(_):
    locate(); ready(); n = sum(u["status"] == "open" for u in units())
    print(f"`python3 .noether/noether.py status --done` exits 0, as shown by running it, with no check removed or demoted. Stop if any unit becomes halted, or after {max(40, n * 25)} turns.")
    return 0


# ---- chains: seq (;), par (|), nest (a stage whose worker is another chain)
def parse_flow(s):
    toks = re.findall(r"[;|()]|[\w.-]+", s); pos = [0]
    def peek(): return toks[pos[0]] if pos[0] < len(toks) else None
    def take(): pos[0] += 1; return toks[pos[0] - 1] if pos[0] <= len(toks) else None
    def atom():
        if peek() == "(":
            take(); n = seq()
            if take() != ")": die("flow: missing )")
            return n
        if peek() in (None, ")", ";", "|"): die(f"flow: unexpected {peek()}")
        return take()
    def par():
        xs = [atom()]
        while peek() == "|": take(); xs.append(atom())
        return xs[0] if len(xs) == 1 else ("par", xs)
    def seq():
        xs = [par()]
        while peek() == ";": take(); xs.append(par())
        return xs[0] if len(xs) == 1 else ("seq", xs)
    n = seq()
    if peek(): die(f"flow: trailing {peek()}")
    return n
def flow_deps(n, pre=frozenset()):
    if isinstance(n, str): return {n: set(pre)}, [n]
    d, order, p = {}, [], set(pre)
    for c in n[1]:
        dd, o = flow_deps(c, p if n[0] == "seq" else pre); d.update(dd); order += o
        if n[0] == "seq": p |= set(o)
    return d, order
def lit(p):
    return re.split(r"[*?\[]", p)[0]
def overlap(xs, ys):
    return [(x, y) for x in xs for y in ys if lit(x).startswith(lit(y)) or lit(y).startswith(lit(x))]
def typecheck(cfg, base_dir=".", depth=0):
    """A chain is well typed or it does not start. Returns (deps, order, errors)."""
    errs = []; S = cfg.get("stages", {})
    deps, order = flow_deps(parse_flow(cfg["flow"]))
    if set(order) != set(S): errs.append(f"flow and stages differ: {sorted(set(order) ^ set(S))}")
    if len(order) != len(set(order)): errs.append("a stage appears twice in flow")
    if errs: return deps, order, errs
    for s, d in S.items():
        have = set().union(*[set(S[p].get("provides", [])) | {p} for p in deps[s]], set())
        if set(d.get("needs", [])) - have: errs.append(f"{s} needs {sorted(set(d.get('needs', [])) - have)}, which no earlier stage provides")
        if not d.get("writes"): errs.append(f"{s}: declare its write footprint")
        if not d.get("proof") and not d.get("chain"): errs.append(f"{s}: needs a proof command")
        if d.get("agent") and d["agent"] not in cfg.get("agents", {}): errs.append(f"{s}: unknown agent {d['agent']}")
        for c in d.get("harness", {}).get("add_checks", []):
            if c.get("class") not in ("pass", "none"): errs.append(f"{s}: added checks must be class pass or none")
        if d.get("harness", {}).get("remove") or d.get("harness", {}).get("loosen"): errs.append(f"{s}: a stage may only add to its parent's harness")
        cls = {c["id"]: c["class"] for c in harness()["checks"]}
        for g in d.get("grants", []):
            if g["check"] == "secrets": errs.append(f"{s}: secrets cannot be excused")
            if "*" in g.get("allow", []) and cls.get(g["check"]) != "pass": errs.append(f"{s}: a bare * would excuse everything in {g['check']}")
            if cls.get(g["check"]) == "none" and any(": " not in x for x in g.get("allow", [])): errs.append(f"{s}: a pattern for {g['check']} must include the printed text after the file name")
        if d.get("chain"):
            if depth >= 2: errs.append(f"{s}: nesting deeper than 3 levels")
            p = Path(base_dir) / d["chain"]; sub = rd(p)
            if not sub: errs.append(f"{s}: cannot read nested chain {p}"); continue
            _, _, e2 = typecheck(sub, p.parent, depth + 1); errs += [f"{s}/{x}" for x in e2]
            for w in [w for t in sub["stages"].values() for w in t.get("writes", [])]:
                if not any(lit(w).startswith(lit(x)) for x in d["writes"]): errs.append(f"{s}: nested write {w} is outside the parent's footprint")
            if sub.get("budget", {}).get("attempts", 0) > d.get("attempts", 10 ** 9): errs.append(f"{s}: nested budget exceeds the stage's attempts")
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            if a in deps[b] or b in deps[a]: continue
            A, B = S[a], S[b]
            if overlap(A["writes"], B["writes"]): errs.append(f"{a} | {b}: write footprints overlap; use ';' instead")
            for x, y, label in ((A.get("reads", []), B["writes"], f"{a} reads what {b} writes"), (B.get("reads", []), A["writes"], f"{b} reads what {a} writes")):
                if overlap(x, y): errs.append(f"{label}; use ';' instead")
    cap = cfg.get("budget", {}).get("attempts")
    tot = sum(d.get("attempts", 12) for d in S.values())
    if cap is not None and tot > cap: errs.append(f"stage attempts sum to {tot}, over the chain budget {cap}")
    return deps, order, errs
def chain_load(path):
    cfg = rd(path)
    if not cfg: die(f"cannot read {path}")
    deps, order, errs = typecheck(cfg, Path(path).parent)
    if errs: print(json.dumps({"well_typed": False, "errors": errs}, indent=1)); sys.exit(1)
    return cfg, deps, order, common() / cfg["name"]
def chain_state(cfg, d):
    st = rd(d / "state.json")
    if not st:
        head = G("rev-parse", "HEAD"); int_ = f"noether/{cfg['name']}/int"
        if "harness.json" not in G("ls-tree", "--name-only", "HEAD", ".noether/"): die("commit .noether first: `noether.py commit -m 'noether: init'`", 3)
        G("branch", "-f", int_, head)
        st = {"base": head, "int": int_, "target": G("rev-parse", "--abbrev-ref", "HEAD"), "integrated": []}; wr(d / "state.json", st)
    return st
def verify_receipt(cfg, d, st, s):
    r = rd(d / "receipts" / f"{s}.json")
    if not r: return None, "no receipt"
    body = {k: v for k, v in r.items() if k != "digest"}
    if digest(body) != r.get("digest"): return r, "digest mismatch"
    at_head = json.loads(git("show", f"{r['head']}:.noether/units/{s}.json").stdout or "{}")
    if at_head.get("status") != "passed" or (at_head.get("receipt") or {}).get("tree") != r["tree"]: return r, "no passed unit at this head"
    if git("rev-parse", "--verify", "-q", f"noether/{cfg['name']}/{s}").stdout.strip() != r["head"]: return r, "branch moved after the receipt"
    if r["harness_sha"] != _sha_at(st["int"]): return r, "stale: harness changed"
    out = [p for p in touched(G("merge-base", st["int"], r["head"]), r["head"]) if not match(p, cfg["stages"][s]["writes"])]
    if out: return r, f"wrote outside footprint: {out[:5]}"
    return r, None
def _sha_at(rev):
    return hashlib.sha256(sp.run(["git", "show", f"{rev}:.noether/harness.json"], cwd=ROOT, capture_output=True).stdout + sp.run(["git", "show", f"{rev}:.noether/noether.py"], cwd=ROOT, capture_output=True).stdout).hexdigest()[:16]
def cmd_chain(a):
    locate(); ready(); cfg, deps, order, d = chain_load(a.file); S = cfg["stages"]
    if a.op == "check": print(json.dumps({"well_typed": True, "order": order, "deps": {k: sorted(v) for k, v in deps.items()}}, indent=1)); return 0
    if a.op == "start" and rd(d / "state.json", {}).get("landed"): shutil.rmtree(d)  # a landed chain name can be run again
    st = chain_state(cfg, d); br = lambda s: f"noether/{cfg['name']}/{s}"; wt = lambda s: N / "run" / "wt" / cfg["name"] / s
    if a.op == "next":
        info = {}
        for s in order:
            r, why = verify_receipt(cfg, d, st, s) if s not in st["integrated"] else ({}, None)
            info[s] = "integrated" if s in st["integrated"] else "certified" if r and not why else "stale: " + why if r else "halted" if rd(wt(s) / ".noether/units" / f"{s}.json", {}).get("status") == "halted" else "running" if wt(s).exists() else "ready" if deps[s] <= set(st["integrated"]) else "waiting"
        out = {"stages": info, "start": [s for s in order if info[s] == "ready"], "integrate": [s for s in order if info[s] == "certified" and deps[s] <= set(st["integrated"])], "all_integrated": set(order) == set(st["integrated"])}
        if (d / "HALT").exists(): out["HALT"] = "a stage hit a hard stop: start nothing, integrate nothing, tell a person"
        print(json.dumps(out, indent=1)); return 2 if "HALT" in out else 0
    if a.op == "start":
        s = a.stage; c = S[s]
        if (d / "HALT").exists(): die("chain halted", 2)
        if not deps[s] <= set(st["integrated"]): die(f"{s} waits on {sorted(deps[s] - set(st['integrated']))}")
        p = wt(s)
        if not p.exists():
            existing = git("show", f"{st['int']}:.noether/units/{s}.json")
            if existing.returncode == 0 and json.loads(existing.stdout).get("status") == "open": die(f"an open unit is already named {s}; rename the stage")
            G("worktree", "add", "-q", "-B", br(s), str(p), st["int"])
            sub = rd(Path(a.file).parent / c["chain"]) if c.get("chain") else None
            wr(p / ".noether/run/stage.json", {"chain": cfg["name"], "nested": sub and sub["name"], "stage": s, "agent": cfg.get("agents", {}).get(c.get("agent", "")), "writes": c["writes"], "checks": c.get("harness", {}).get("add_checks", []), "evidence": []})
            wr(p / ".noether/units" / f"{s}.json", {"id": s, "goal": c.get("goal", ""), "proof": c.get("proof", "true"), "scope": c["writes"], "seq": 1, "status": "open", "attempts": 0, "judge_fails": 0, "max_attempts": c.get("attempts", 12), "start": G("rev-parse", "HEAD", cwd=p), "grants": c.get("grants", [])})
        elif a.reopen:
            if rd(p / ".noether/units" / f"{s}.json", {}).get("status") == "halted": die(f"{s} is halted. A person decides whether it continues: run `unit reopen {s}` in its worktree")
            log("reopen", unit=s, chain=cfg["name"])
            r = git("-c", "core.hooksPath=/dev/null", "merge", "--no-edit", st["int"], cwd=p)
            if r.returncode: print(f"merge needs resolving in {p}: {r.stdout[-300:]}")
            own = rd(p / ".noether/baseline.json", {}); merged_b = json.loads(G("show", st["int"] + ":.noether/baseline.json"))  # the integration line's ratchet now binds this stage
            start_b = json.loads(G("show", st["base"] + ":.noether/baseline.json"))["q"].get("tests", [])
            if "tests" in own.get("q", {}): merged_b["q"]["tests"] = sorted(set(merged_b["q"].get("tests", [])) | (set(own["q"]["tests"]) - set(start_b)))  # and the tests it added stay protected
            wr(p / ".noether/baseline.json", merged_b)
            u = rd(p / ".noether/units" / f"{s}.json"); u.update(status="open", judge_fails=0, start=G("rev-parse", "HEAD", cwd=p)); wr(p / ".noether/units" / f"{s}.json", u)
            (d / "receipts" / f"{s}.json").unlink(missing_ok=True)
        ag = cfg.get("agents", {}).get(c.get("agent", ""), {})
        nest = f"\nYour worker is a nested chain: run it from your worktree with `chain next {c['chain']}`; land it, then prove and finish this stage." if c.get("chain") else ""
        print(f"Spawn one agent{' with ' + json.dumps(ag) if ag else ''} and give it this brief:\n---\nWork only in {p}. You are stage '{s}' of chain '{cfg['name']}'.\nGOAL: {c.get('goal', '')}\nYOU MAY WRITE: {c['writes']}\nYOU RELY ON: {c.get('reads', [])}\nDONE MEANS: `{c.get('proof', '')}` exits 0.\nCertified by others: {c.get('needs', [])}.{nest}\nLoop: edit; `python3 .noether/noether.py brief`, then have a fresh agent judge from it; `... done`. `gate` and `commit -m` are optional checkpoints.\nReport only the final `done` output.\n---")
        return 0
    if a.op == "integrate":
        todo = [s for s in order if s not in st["integrated"] and deps[s] <= set(st["integrated"]) and (not a.only or s in a.only)]
        if not todo: print("nothing to integrate"); return 0
        if (d / "HALT").exists(): die("chain halted", 2)
        for s in todo:
            r, why = verify_receipt(cfg, d, st, s)
            if why: print(json.dumps({"ok": False, "stage": s, "receipt": why, "hint": "integrate only certified stages with --only"}, indent=1)); return 1
        for l in G("worktree", "list", "--porcelain").splitlines():
            if l.startswith("worktree ") and "/noether-int-" in l: git("worktree", "remove", "--force", l[9:]); shutil.rmtree(Path(l[9:]).parent, ignore_errors=True)
        git("worktree", "prune")
        tmp = tempfile.mkdtemp(prefix="noether-int-"); w = f"{tmp}/w"; G("worktree", "add", "-q", "--detach", w, st["int"]); G("config", "merge.ours.driver", "true")
        old = (ROOT, N, RUN); before = G("rev-parse", st["int"]); merged = []
        try:
            for s in todo:
                r = git("-c", "core.hooksPath=/dev/null", "merge", "--no-ff", "--no-edit", "-m", f"noether: integrate {s}", br(s), cwd=w)
                if r.returncode: git("merge", "--abort", cwd=w); print(json.dumps({"ok": False, "stage": s, "conflict": "TEXT", "detail": (r.stdout + r.stderr)[-400:]}, indent=1)); return 1
                merged.append(s); locate(w); RUN.mkdir(parents=True, exist_ok=True)
                G("checkout", before, "--", ".noether/baseline.json", cwd=w)  # only integration moves the integration line's ratchet
                if git("diff", "--cached", "--quiet", cwd=w).returncode: G("-c", "core.hooksPath=/dev/null", "commit", "-q", "--amend", "--no-edit", cwd=w)
                EXTRA[:] = [c for x in st["integrated"] + merged for c in S[x].get("harness", {}).get("add_checks", [])]
                os.environ["NOETHER_BASE"] = before
                grants = [g for x in merged for g in rd(N / "units" / f"{x}.json", {}).get("grants", [])]
                res = evaluate(None, grants=grants, use_cache=False, base_scope=False)
                bad_proofs = {}
                for x in order:
                    if (x in st["integrated"] or x in merged) and S[x].get("proof"):
                        pr = hrun(S[x]["proof"], cwd=w)
                        if pr.returncode: bad_proofs[x] = (pr.stdout + pr.stderr)[-500:]
                if not res["ok"] or bad_proofs:
                    print(json.dumps({"ok": False, "conflict": "PROOF" if res["ok"] and len(st["integrated"]) + len(merged) == 1 else "SEMANTIC", "merged_so_far": merged, "failures": res["failures"], "proofs_failed": bad_proofs, "fix": "nothing was integrated. `chain start --reopen` a stage, or sequence them with ';'"}, indent=1)); return 1
            log("integrate", chain=cfg["name"], stages=merged); advance_baseline(res); G("add", "-A", cwd=w)
            if git("diff", "--cached", "--quiet", cwd=w).returncode: G("-c", "core.hooksPath=/dev/null", "commit", "-q", "--amend", "--no-edit", cwd=w)
            head = G("rev-parse", "HEAD", cwd=w)
            locate(old[0]); G("update-ref", f"refs/heads/{st['int']}", head, before)
            st["integrated"] += merged; wr(d / "state.json", st)
            print(json.dumps({"ok": True, "integrated": merged, "head": head, "remaining": [s for s in order if s not in st["integrated"]]}, indent=1)); return 0
        finally:
            EXTRA.clear(); os.environ.pop("NOETHER_BASE", None); ROOT_, _, _ = old; locate(ROOT_); git("worktree", "remove", "--force", w); shutil.rmtree(tmp, ignore_errors=True)
    if a.op == "resume":
        (d / "HALT").unlink(missing_ok=True); log("halt_cleared", chain=cfg["name"]); print("resumed; the stage that halted must be clean before it can pass"); return 0
    if a.op == "land":
        if set(order) != set(st["integrated"]): die(f"not all stages integrated: {sorted(set(order) - set(st['integrated']))}")
        lg = N / "log.jsonl"; cur, at_head = _read(lg), git("show", "HEAD:.noether/log.jsonl").stdout; extra = cur[len(at_head):] if cur.startswith(at_head) else ""
        git("checkout", "--", ".noether/log.jsonl", ".noether/baseline.json")
        if git("merge-base", "--is-ancestor", "HEAD", st["int"]).returncode:
            if not a.merge:
                if extra: lg.write_text(cur)
                die(f"{st['target']} moved since the chain started. Run `chain land {a.file} --merge` to gate the combination, then land it.")
            grants = [g for s in order for g in rd(wt(s) / ".noether/units" / f"{s}.json", {}).get("grants", [])]
            r = git("-c", "core.hooksPath=/dev/null", "merge", "--no-commit", "--no-ff", st["int"])
            if r.returncode and "Automatic merge went well" not in r.stdout: git("merge", "--abort"); die(f"land: text conflict: {(r.stdout + r.stderr)[-300:]}")
            res = evaluate(None, grants=grants, use_cache=False, base_scope=False)
            if not res["ok"]: git("merge", "--abort"); show(res); return 1
            advance_baseline(res); head = _commit(f"noether: land {cfg['name']}", res["tree"])
        else:
            r = git("merge", "--ff-only", st["int"])
            if r.returncode: die(f"land: uncommitted changes block it: {r.stderr.strip()[-300:]}")
        if extra: open(lg, "a").write(extra)
        st["landed"] = True; wr(d / "state.json", st); print("landed")
        for s in order: git("worktree", "remove", "--force", str(wt(s))); git("branch", "-D", br(s))
        git("branch", "-D", st["int"]); shutil.rmtree(N / "run" / "wt" / cfg["name"], ignore_errors=True)
        return 0


def main():
    if hasattr(signal, "SIGPIPE"): signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    if len(sys.argv) > 2 and sys.argv[1] == "probe":
        locate(); PROBES[sys.argv[2]](sys.argv[3:]); return 0
    p = argparse.ArgumentParser(prog="noether.py"); s = p.add_subparsers(dest="cmd", required=True)
    def sub(n, f, *args):
        q = s.add_parser(n); q.set_defaults(f=f)
        for names, kw in args: q.add_argument(*names, **kw)
        return q
    U = (["--unit"], {})
    sub("init", cmd_init, (["--force"], {"action": "store_true"}), (["--dirty"], {"action": "store_true"}), (["--claude"], {"action": "store_true"}))
    sub("status", cmd_status, (["--done"], {"action": "store_true"})); sub("goal", cmd_goal)
    sub("decide", cmd_decide, (["what"], {}), (["--why"], {"required": True}), U); sub("log", cmd_log, (["--only"], {"choices": ["decisions", "judgments"]}), (["-n"], {"type": int})); sub("hook", cmd_hook); sub("precommit", cmd_precommit); sub("rehash", cmd_rehash)
    sub("gate", cmd_gate, U, (["--fresh"], {"action": "store_true"})); sub("commit", cmd_commit, U, (["-m", "--message"], {"required": True}))
    sub("unit", cmd_unit, (["op"], {"choices": ["add", "reopen"]}), (["id"], {}), (["--goal"], {}), (["--proof"], {}), (["--scope"], {"nargs": "+", "action": "extend"}), (["--attempts"], {"type": int}))
    sub("brief", cmd_brief, U); sub("judge", cmd_judge, (["--unit"], {"required": True}), (["--by"], {"required": True}), (["--scores"], {"required": True}), (["--note"], {})); sub("done", cmd_done, U)
    sub("grant", cmd_grant, U, (["check"], {}), (["--allow"], {"nargs": "*"}), (["--axis"], {"action": "store_true"}), (["--reason"], {"required": True}))
    sub("learn", cmd_learn, (["op"], {"choices": ["add", "confirm", "promote", "retire", "note"]}), (["id"], {}), (["--cls"], {"default": "pass", "choices": ["pass", "keep", "none", "max", "min"]}), (["--cmd"], {}), (["--why"], {}), (["--real"], {"choices": ["yes", "no"]}))
    sub("chain", cmd_chain, (["op"], {"choices": ["check", "next", "start", "integrate", "land", "resume"]}), (["file"], {}), (["stage"], {"nargs": "?"}), (["--only"], {"nargs": "*"}), (["--reopen"], {"action": "store_true"}), (["--merge"], {"action": "store_true"}))
    a = p.parse_args(); return a.f(a) or 0


if __name__ == "__main__":
    sys.exit(main())
