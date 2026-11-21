#!/usr/bin/env python3
"""event_adopt_diff.py -- ADOPT-DIFF (ADOPT-CENSUS-1800, FABLE-FLOW-1800 class 2): a die plan event's source tree against main.

An event tree is forked from the previous event's tree (S81 J5 = src_s81_pin_3c913dbdfb23_d8j5_1117_work, cut 11-17), so a fix
pushed to main after the pin never arrives unless a person carries it (J5 missed the seqhost hwin fix 8e20268b5d83 and the
OT_S81SL_LEP_RIP1 define).  This tool makes the lag a list, at event build and at apply:

  diff   three-way compare per file of the die scope: PIN (the tree's .src-manifest.json main_sha, or --pin), the EVENT tree, MAIN.
           LAG      tree == pin, main moved: the event did not touch the file; `carry` takes it from main automatically
           BOTH     tree != pin and main moved: the event edited a file main also changed; listed for the die owner with the
                    main commits (merge by hand or name a reason)
           CURRENT  tree == main already
         Only the paths main changed since the pin are read (git diff --raw pin main; no blob is fetched), the tree side is the
         git blob id of the tree file.  The event's own delta (overlay entries main did not touch) is counted, not listed.
         Then the PROVEN-FIX LEDGER (tools/autopilot/PROVEN_FIXES.tsv) is checked: every `commit` row of the die is carried by
         the tree (each file the fix touched is the fix's version, a later main version, or reverse-applies the fix patch), and
         is an ancestor of the die's tools pin when one is given; every `define` / `key` row is set for its types in a generated
         config.mk (--kit), falling back to the plan's verilog_defines (--plan) when no kit of the type is given.
  carry  a src_manifest delta pack (delta.json + files/) of the LAG paths only, taken from main; `--apply NEW_TREE` composes
         NEW_TREE = TREE + pack with src_manifest.delta_apply (hardlinked with --link).  BOTH paths are never touched.

It is a report, not a gate: exit 0 whatever it finds (2 on a usage / input error).  publish_apply.py apply runs `diff` on the
candidate tree before the switch and puts the one-line summary in its post.

  event_adopt_diff.py diff  --tree TREE [--repo GIT] [--main REF] [--pin SHA] [--die DIE] [--scope P ...] [--ledger TSV]
                            [--plan PLAN --plan-tools DIR] [--kit GEN_DIR|config.mk ...] [--tools-sha SHA] [--out DIR] [--fetch]
  event_adopt_diff.py carry --report OUT/adopt_diff.json --repo GIT --pack PACK_DIR [--apply NEW_TREE [--link]]

Stdlib only.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "PROVEN_FIXES.tsv"
WARM = "/srv/opentallas-scratch2/claude/warm/OpenTallas.git"
ZERO = "0" * 40
DEFAULT_SCOPE = ["tools", "rtl", "physical"]
MANIFEST = ".src-manifest.json"
LEDGER_COLS = ("id", "kind", "sha", "die", "types", "value", "note")
MAX_COMMITS_LISTED = 400          # BOTH paths whose main commits are named (the rest: counted)


def git(repo, *a, check=True, input_=None, timeout=900):
    r = subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, input=input_, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(a[:3])}: {r.stderr.strip()[-300:]}")
    return r.stdout


def rev(repo, ref):
    """full sha of a ref, '' when it does not resolve (a label such as 'j5tree')"""
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def blob_oid_bytes(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def tree_oid(tree, rel):
    """git blob id of TREE/rel (a symlink hashes its target text, as git stores it); None when absent"""
    p = os.path.join(tree, rel)
    if os.path.islink(p):
        return blob_oid_bytes(os.readlink(p).encode())
    if not os.path.isfile(p):
        return None
    with open(p, "rb") as f:
        return blob_oid_bytes(f.read())


def norm(oid):
    return None if not oid or oid == ZERO else oid


def die_scope(repo, main, scope, die):
    """(include prefixes, exclude prefixes): the manifest scope minus results/ and the die_plan dirs of the other dies"""
    inc = [s.rstrip("/") for s in scope if s.rstrip("/") != "results"]
    exc = []
    if die:
        for ln in git(repo, "ls-tree", "-d", "--name-only", main, "physical/die_plan/").splitlines():
            if ln.rstrip("/") != f"physical/die_plan/{die}":
                exc.append(ln.rstrip("/"))
    return inc, exc


def in_scope(path, inc, exc):
    def under(p, pre):
        return p == pre or p.startswith(pre + "/")
    return any(under(path, s) for s in inc) and not any(under(path, s) for s in exc)


def main_changes(repo, pin, main, inc):
    """[(path, pin_oid|None, main_oid|None)] of every path main changed since the pin inside inc (no blob is read)"""
    out = git(repo, "diff", "--raw", "-z", "--no-renames", "--no-abbrev", pin, main, "--", *inc)
    f = out.split("\0")
    res, i = [], 0
    while i < len(f) - 1:
        meta = f[i]
        if not meta.startswith(":"):
            i += 1
            continue
        parts = meta[1:].split()
        res.append((f[i + 1], norm(parts[2]), norm(parts[3])))
        i += 2
    return res


def classify(tree, changes, inc, exc):
    rows = []
    for path, old, new in changes:
        if not in_scope(path, inc, exc):
            continue
        t = tree_oid(tree, path)
        cls = "CURRENT" if t == new else "LAG" if t == old else "BOTH"
        rows.append(dict(path=path, cls=cls, pin=old, main=new, tree=t))
    return rows


def commits_for(repo, pin, main, paths, limit=MAX_COMMITS_LISTED):
    """{path: ['<h> <subject>', ...]} main commits since the pin that touched each path (first `limit` paths)"""
    out = {}
    for p in paths[:limit]:
        lines = git(repo, "log", "--format=%h %s", f"{pin}..{main}", "--", p, check=False).splitlines()
        out[p] = [ln[:120] for ln in lines]
    return out


# ---------------------------------------------------------------- ledger

def read_ledger(path):
    rows = []
    for n, ln in enumerate(Path(path).read_text().splitlines(), 1):
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        f = ln.split("\t")
        if f[0] == "id":
            continue
        if len(f) < 6:
            raise ValueError(f"{path}:{n}: {len(f)} fields, want {len(LEDGER_COLS)} ({', '.join(LEDGER_COLS)})")
        r = dict(zip(LEDGER_COLS, f + [""] * (len(LEDGER_COLS) - len(f))))
        if r["kind"] not in ("commit", "define", "key"):
            raise ValueError(f"{path}:{n}: kind {r['kind']!r} not commit/define/key")
        rows.append(r)
    return rows


def die_match(row, die):
    ds = [d.strip() for d in row["die"].split(",") if d.strip()]
    return not die or not ds or "*" in ds or die in ds


def types_match(globs, tn):
    gl = [g.strip() for g in (globs or "*").split(",") if g.strip()]
    return any(fnmatch.fnmatchcase(tn, g) for g in gl or ["*"])


def fix_files(repo, sha):
    """[(path, status)] the fix commit changed (first parent)"""
    out = git(repo, "diff-tree", "-r", "--no-commit-id", "--name-status", "--no-renames", "-z", f"{sha}^", sha)
    f = [x for x in out.split("\0") if x != ""]
    return [(f[i + 1], f[i]) for i in range(0, len(f) - 1, 2)]


def later_oids(repo, sha, main, paths):
    """{path: {oid}} the fix's own version and every later main version of each path"""
    res = {p: set() for p in paths}
    if not paths:
        return res
    out = git(repo, "log", "--raw", "--no-abbrev", "--no-renames", "--format=", f"{sha}^..{main}", "--", *paths, check=False)
    for ln in out.splitlines():
        if ln.startswith(":"):
            meta, _, p = ln.partition("\t")
            if p in res and norm(meta.split()[3]):
                res[p].add(meta.split()[3])
    return res


def patch_applies(repo, sha, path, tree, reverse):
    pt = git(repo, "diff", f"{sha}^", sha, "--", path, check=False)
    if not pt.strip():
        return False
    args = ["git", "apply", "--check"] + (["-R"] if reverse else []) + ["-"]
    r = subprocess.run(args, cwd=tree, input=pt, capture_output=True, text=True)
    return r.returncode == 0


def check_commit(repo, row, tree, main, inc, exc, tools_sha=""):
    sha = rev(repo, row["sha"])
    if not sha:
        return dict(verdict="UNKNOWN-SHA", detail=f"{row['sha']} does not resolve in {repo}")
    files = [(p, st) for p, st in fix_files(repo, sha) if in_scope(p, inc, exc)]
    later = later_oids(repo, sha, main, [p for p, _ in files])
    miss, div, ok = [], [], []
    for p, st in files:
        t = tree_oid(tree, p)
        if st == "D":
            (ok if t is None else miss).append(p)
            continue
        if t is not None and t in later[p]:
            ok.append(p)
        elif t is None:
            miss.append(p)
        elif patch_applies(repo, sha, p, tree, reverse=True):
            ok.append(p)                       # an edited copy that still carries the fix hunks
        elif patch_applies(repo, sha, p, tree, reverse=False):
            miss.append(p)
        else:
            div.append(p)
    v = "MISSING" if miss else "DIVERGED" if div else "CARRIED" if files else "OUT-OF-SCOPE"
    out = dict(verdict=v, files=len(files), missing=miss, diverged=div)
    if tools_sha:
        ts = rev(repo, tools_sha)
        if not ts:
            out["tools_pin"] = f"UNRESOLVED ({tools_sha!r} is not a commit: the lag cannot be measured)"
        else:
            anc = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", sha, ts]).returncode == 0
            out["tools_pin"] = "HAS" if anc else f"MISSING (not an ancestor of tools pin {ts[:12]})"
            if not anc and any(p.startswith("tools/") for p, _ in files):
                out["verdict"] = "MISSING" if v == "CARRIED" else v
    detail = []
    if miss:
        detail.append("missing " + ", ".join(miss[:6]) + (f" +{len(miss) - 6}" if len(miss) > 6 else ""))
    if div:
        detail.append("diverged " + ", ".join(div[:4]))
    if out.get("tools_pin") and out["tools_pin"] != "HAS":
        detail.append("tools pin " + out["tools_pin"])
    out["detail"] = "; ".join(detail)
    return out


DEF_RE = re.compile(r"^\s*(?:export\s+)?VERILOG_DEFINES\s*[:+?]?=\s*(.*)$")
KEY_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*[:+?]?=\s*(.*)$")


def config_mk(path):
    """(defines set, {KEY: value}) of a generated config.mk"""
    defs, keys = set(), {}
    for ln in Path(path).read_text(errors="replace").splitlines():
        m = DEF_RE.match(ln)
        if m:
            for tok in m.group(1).split():
                if tok.startswith("-D"):
                    defs.add(tok[2:].split("=", 1)[0])
                elif tok.startswith("+define+"):
                    defs.update(x.split("=", 1)[0] for x in tok[8:].split("+") if x)
            continue
        m = KEY_RE.match(ln)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return defs, keys


def kit_configs(kits):
    """{type: config.mk path} from gen dirs (gen/<type>/config.mk), item dirs (newest gen) or config.mk paths"""
    res = {}
    for k in kits or []:
        p = Path(k)
        if p.name == "config.mk" or (p / "config.mk").is_file():
            cands = [p if p.name == "config.mk" else p / "config.mk"]
        else:       # an item dir (gen/<type>, attempt_N/gen/<type>) or a kit-wave items root (<item>/...)
            cands = [c for pat in ("gen/*/config.mk", "attempt_*/gen/*/config.mk", "*/gen/*/config.mk", "*/attempt_*/gen/*/config.mk")
                     for c in p.glob(pat)]
        for c in sorted((c for c in cands if c.is_file()), key=lambda x: x.stat().st_mtime):
            res[c.parent.name] = str(c)          # newest gen of each type wins
    return res


def plan_defines(plan, tools):
    """{type: [defines]} from the plan (schema.Plan resolves templates and overlays)"""
    import contextlib
    import io
    sys.path.insert(0, str(tools))
    try:
        import schema as S
        raw = json.loads(Path(plan).read_text())
        with contextlib.redirect_stdout(io.StringIO()):
            P = S.Plan(raw, str(plan))
        placed = {p.get("type") for p in raw.get("partitions") or []}
        return {tn: list(t.get("verilog_defines") or []) for tn, t in P.types.items() if not placed or tn in placed}
    finally:
        sys.path.remove(str(tools))


def has_define(defs, name):
    """name present; a bare-name selector (319f91aaf1: RIP1 for OT_S81SL_LEP_RIP1) also counts"""
    return name in defs or any(name.endswith("_" + d) for d in defs if d and "_" not in d)


def check_define(row, kitcfg, pdefs, gen_env=None):
    kind, val = row["kind"], row["value"].strip()
    types = sorted(set(kitcfg) | set(pdefs or {}))
    matched = [t for t in types if types_match(row["types"], t)]
    if not matched:
        return dict(verdict="NO-TYPE", detail=f"no type matches {row['types']} in the kits / plan given", types=[])
    bad, src = [], {}
    for t in matched:
        if t in kitcfg:
            defs, keys = config_mk(kitcfg[t])
            src[t] = "config.mk"
        else:
            defs, keys = set(pdefs.get(t) or []), dict(gen_env or {})
            src[t] = "plan" if kind == "define" else "die_gen_env"
        if kind == "define":
            ok = has_define(defs, val)
        else:
            k, _, want = val.partition("=")
            ok = k in keys and (not want or str(keys[k]).strip() == want.strip())
        if not ok:
            bad.append(t)
    v = "MISSING" if bad else "CARRIED"
    return dict(verdict=v, types=matched, missing_types=bad, source=sorted(set(src.values())),
                detail=(f"{len(bad)}/{len(matched)} types lack {val} ({', '.join(bad[:6])}{' ...' if len(bad) > 6 else ''}; "
                        f"read from {', '.join(sorted(set(src[t] for t in bad)))})") if bad else f"{len(matched)} types carry {val}")


def ledger_check(a, repo, tree, main, inc, exc):
    rows = [r for r in read_ledger(a.ledger) if die_match(r, a.die)]
    kitcfg = kit_configs(a.kit)
    pdefs = {}
    if any(r["kind"] != "commit" for r in rows) and a.plan:
        try:
            pdefs = plan_defines(a.plan, a.plan_tools or str(Path(tree) / "tools/die_plan"))
        except Exception as e:  # noqa: BLE001 -- a report never stops on one source
            print(f"ADOPT-DIFF plan read failed: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr)
    gen_env = json.loads(Path(a.gen_env).read_text()) if a.gen_env else {}
    out = []
    for r in rows:
        if r["kind"] == "commit":
            res = check_commit(repo, r, tree, main, inc, exc, a.tools_sha)
        else:
            res = check_define(r, kitcfg, pdefs, gen_env)
        out.append(dict(r, **res))
    return out


# ---------------------------------------------------------------- commands

def load_pin(tree, pin):
    if pin:
        return pin
    m = Path(tree) / MANIFEST
    if not m.is_file():
        raise SystemExit(f"ADOPT-DIFF: {tree} has no {MANIFEST}; pass --pin")
    with open(m) as f:                      # 45-50 MB on die trees: one json load
        return json.load(f)["main_sha"]


def overlay_count(tree):
    m = Path(tree) / MANIFEST
    try:
        with open(m) as f:
            return len(json.load(f).get("overlay") or {})
    except (OSError, ValueError):
        return None


def summary_line(die, tree, rep):
    c = rep["counts"]
    miss = [r["id"] for r in rep["ledger"] if r["verdict"] in ("MISSING", "DIVERGED", "UNKNOWN-SHA")]
    tops = ", ".join(f"{k} {v}" for k, v in sorted(rep["lag_by_top"].items(), key=lambda kv: -kv[1])[:5])
    return (f"ADOPT-DIFF {die or '?'} {Path(tree).name}: pin {rep['pin'][:12]} -> main {rep['main'][:12]} ({rep['main_commits']} commits): "
            f"LAG {c.get('LAG', 0)} (carry automatically; {tops or 'none'}), BOTH {c.get('BOTH', 0)} (die owner), CURRENT {c.get('CURRENT', 0)}; "
            f"ledger {len(rep['ledger'])} rows, {len(miss)} missing" + (f": {', '.join(miss)}" if miss else "") + ".")


def cmd_diff(a):
    repo = a.repo
    if a.fetch:
        subprocess.run(["git", "-C", repo, "fetch", "-q", "origin", "+refs/heads/main:refs/remotes/origin/main"], capture_output=True, timeout=600)
    tree = os.path.abspath(a.tree)
    main = rev(repo, a.main)
    if not main:
        print(f"ADOPT-DIFF: main ref {a.main} does not resolve in {repo}", file=sys.stderr)
        return 2
    pin_in = load_pin(tree, a.pin)
    pin = rev(repo, pin_in)
    if not pin:
        print(f"ADOPT-DIFF: pin {pin_in!r} does not resolve in {repo} (a label is not a pin)", file=sys.stderr)
        return 2
    inc, exc = die_scope(repo, main, a.scope, a.die)
    t0 = time.time()
    rows = classify(tree, main_changes(repo, pin, main, inc), inc, exc)
    counts, lag_top = {}, {}
    for r in rows:
        counts[r["cls"]] = counts.get(r["cls"], 0) + 1
        if r["cls"] == "LAG":
            top = "/".join(r["path"].split("/")[:2])
            lag_top[top] = lag_top.get(top, 0) + 1
    both = [r["path"] for r in rows if r["cls"] == "BOTH"]
    cm = commits_for(repo, pin, main, both)
    for r in rows:
        if r["path"] in cm:
            r["commits"] = cm[r["path"]]
    led = ledger_check(a, repo, tree, main, inc, exc) if a.ledger else []
    rep = dict(schema="opentallas.adopt_diff.v1", die=a.die, tree=tree, pin=pin, main=main, scope=inc, exclude=exc,
               main_commits=int(git(repo, "rev-list", "--count", f"{pin}..{main}").strip() or 0),
               event_delta=overlay_count(tree), counts=counts, lag_by_top=lag_top, rows=rows, ledger=led,
               at=time.strftime("%Y-%m-%d %H:%M:%S"), seconds=round(time.time() - t0, 1))
    rep["summary"] = summary_line(a.die, tree, rep)
    if a.out:
        o = Path(a.out)
        o.mkdir(parents=True, exist_ok=True)
        (o / "adopt_diff.json").write_text(json.dumps(rep, indent=1))
        with open(o / "adopt_diff.tsv", "w") as f:
            f.write("class\tpath\tpin\tmain\ttree\tmain_commits\n")
            for r in sorted(rows, key=lambda r: (r["cls"], r["path"])):
                f.write(f"{r['cls']}\t{r['path']}\t{(r['pin'] or '-')[:12]}\t{(r['main'] or '-')[:12]}\t{(r['tree'] or '-')[:12]}\t"
                        f"{' | '.join(r.get('commits') or [])[:400]}\n")
        with open(o / "ledger.tsv", "w") as f:
            f.write("id\tkind\tsha\ttypes\tvalue\tverdict\tdetail\n")
            for r in led:
                f.write(f"{r['id']}\t{r['kind']}\t{r['sha']}\t{r['types']}\t{r['value']}\t{r['verdict']}\t{r.get('detail', '')}\n")
    print(rep["summary"])
    for r in led:
        if r["verdict"] != "CARRIED":
            print(f"  LEDGER {r['id']} {r['kind']} {r['verdict']}: {r.get('detail', '')}")
    return 0


def cmd_carry(a):
    """pack = the LAG paths at main (src_manifest delta format), optionally composed into a new tree"""
    rep = json.loads(Path(a.report).read_text())
    repo, main = a.repo, rep["main"]
    lag = [r for r in rep["rows"] if r["cls"] == "LAG"]
    pack = Path(a.pack)
    if pack.exists():
        print(f"CARRY refused: {pack} exists", file=sys.stderr)
        return 2
    (pack / "files").mkdir(parents=True)
    add, delete = {}, []
    if lag:   # one batched read of the main blobs (a partial clone fetches them in one go through diff)
        git(repo, "diff", "--numstat", rep["pin"], main, "--", *[r["path"] for r in lag if r["main"]][:20000], check=False)
    for r in lag:
        if not r["main"]:
            delete.append(r["path"])
            continue
        blob = subprocess.run(["git", "-C", repo, "cat-file", "blob", r["main"]], capture_output=True, check=True).stdout
        mode = git(repo, "ls-tree", main, "--", r["path"]).split()[0]
        dest = pack / "files" / r["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
        add[r["path"]] = {"sha256": hashlib.sha256(blob).hexdigest(), "exec": mode == "100755", "link": mode == "120000"}
    tree = rep["tree"]
    old, ovl = {}, {}
    mf = Path(tree) / MANIFEST
    if mf.is_file():
        with open(mf) as f:
            m = json.load(f)
        old = dict(old_manifest_hash=m.get("manifest_hash"), old_main=m.get("main_sha"), scope=m.get("scope"))
        ovl = m.get("overlay") or {}
    # the composed tree = main + the event's own delta: new_main is main, the carried (LAG) files equal main, the files the event
    # had already carried by hand (CURRENT) leave the overlay, BOTH files and the event delta stay overlay (they differ from main)
    cur = sorted(r["path"] for r in rep["rows"] if r["cls"] == "CURRENT" and r["path"] in ovl)
    d = dict(old, new_main=main, add=add, delete=delete, overlay_drop=cur, overlay_add={},
             carried_from=main, source="event_adopt_diff carry", both=[r["path"] for r in rep["rows"] if r["cls"] == "BOTH"])
    (pack / "delta.json").write_text(json.dumps(d, indent=0, sort_keys=True))
    print(f"CARRY pack {pack}: {len(add)} files from main {main[:12]}, {len(delete)} deletions; BOTH paths untouched")
    if a.apply:
        sys.path.insert(0, str(HERE))
        import src_manifest as SM
        SM.delta_apply(str(pack), tree, a.apply, link=a.link)
        print(f"CARRY tree {a.apply} composed (run src_manifest.py publish on it before use)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    d = sp.add_parser("diff")
    d.add_argument("--tree", required=True)
    d.add_argument("--repo", default=WARM)
    d.add_argument("--main", default="refs/remotes/origin/main")
    d.add_argument("--pin", default="", help="pin sha (default: the tree's .src-manifest.json main_sha)")
    d.add_argument("--die", default="")
    d.add_argument("--scope", nargs="+", default=DEFAULT_SCOPE)
    d.add_argument("--ledger", default=str(LEDGER), help="'' = no ledger check")
    d.add_argument("--plan", default="")
    d.add_argument("--plan-tools", default="", help="die_plan tools dir for schema.Plan (default TREE/tools/die_plan)")
    d.add_argument("--kit", nargs="*", default=[], help="kit gen dirs / item dirs / config.mk files (define + key rows)")
    d.add_argument("--gen-env", default="", help="JSON file {KEY: value} = the die's die_gen_env (key rows without a kit)")
    d.add_argument("--tools-sha", default="", help="the die's tools pin (kit_wave dies.<die>.tools_sha); a label reports UNRESOLVED")
    d.add_argument("--out", default="")
    d.add_argument("--fetch", action="store_true")
    c = sp.add_parser("carry")
    c.add_argument("--report", required=True)
    c.add_argument("--repo", default=WARM)
    c.add_argument("--pack", required=True)
    c.add_argument("--apply", default="", help="compose NEW_TREE = report tree + pack (src_manifest.delta_apply)")
    c.add_argument("--link", action="store_true")
    a = ap.parse_args(argv)
    try:
        return cmd_diff(a) if a.cmd == "diff" else cmd_carry(a)
    except (RuntimeError, ValueError) as e:
        print(f"ADOPT-DIFF error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
