#!/usr/bin/env python3
"""ROLLING COMPOSE (COMPOSE-FAST 11-25, OWNER via COORD): publish a new die plan whenever new rows are READY, not at fixed cut times.

Integrators composed at fixed cuts (C1o 03:00, A5t8 04:00, c10 06:00) by hand-written chains of compose3 / apply_ops / row
scripts, then ran the full gate; a row that missed a cut waited hours.  This command reads the die's ALLFIX ledger (a directory of
ROW-READY json from row_gate.py --ledger DIR), applies every READY row not yet in the current plan, in a deterministic order, on the
CURRENT plan, normalizes, gates (row_gate.py, full strict bind unless --types) and publishes the gated fork as the new current plan.

  row_compose.py roll --die DIE --ledger DIR --pub DIR [--src TREE --base PLAN] --asbuilt AB [--types all] [--once | --watch SEC]
                      [--rt RT] [--env K=V ...] [--max-rows N] [--keep N]
  row_compose.py status --pub DIR

  --src/--base  the starting tree + plan (first round only; afterwards PUB/compose_state.json names the current published tree)
  order         READY rows sort by (order field of the ROW-READY, else 1000; its finished time; lane; key): the ledger alone decides
  apply         each row re-runs its intent (script / ops / merge) on the current plan; a row that no longer applies is dropped from
                the round and recorded REJECTED with the plan sha it failed on (it is retried once the current plan moves)
  gate          one row_gate.py gate run over the batch (fork, apply, normalize, PRE-DIFF vs the current plan, elab, R8 refresh,
                strict bind, latency) under ot-run --die
  publish       READY -> the round's fork becomes the current tree, its plan is copied to plan_roll_<die>_r<N>.json next to the base
                plan; PUB/current.json and PUB/published/r<N>.json name it (rows, shas, gate record).  Older published trees beyond --keep
                are deleted with ot-delete.
  bisect        NOT READY with several rows -> the next round takes the first half of the same batch (deterministic), down to one
                row; a single row that fails is REJECTED with the gate's reason.  A READY round resets the batch size.
  --watch SEC   loop: a round whenever the ledger holds READY rows not in the current plan; otherwise sleep SEC.
Exit (once): 0 published or nothing to do, 1 round not READY, 2 usage."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import row_gate as RG  # noqa: E402


def row_key(rr):
    return hashlib.sha256("".join((r.get("kind", "") + (r.get("sha256") or "") + (r.get("args") or "")) for r in rr.get("rows") or []).encode()).hexdigest()[:16]


def read_ledger(d):
    """-> [ROW-READY dict + _key/_file] READY entries, deterministic order"""
    out = []
    for p in sorted(Path(d).glob("*.json")):
        try:
            rr = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if rr.get("schema") != RG.SCHEMA or rr.get("verdict") != "READY" or not rr.get("rows"):
            continue
        rr["_key"], rr["_file"] = row_key(rr), str(p)
        out.append(rr)
    out.sort(key=lambda r: (int(r.get("order", 1000)), r.get("finished") or "", r.get("lane") or "", r["_key"]))
    seen, uniq = set(), []
    for r in out:
        if r["_key"] not in seen:
            seen.add(r["_key"])
            uniq.append(r)
    return uniq


def row_ids(r, spec=None):
    """the names a later row's `overrides` can use for this ledger row: its row_id, lane, key (full and 8 chars), spec file name"""
    return [x for x in (r.get("row_id"), r.get("lane"), r.get("_key"), (r.get("_key") or "")[:8],
                        os.path.basename(spec["path"]) if spec else None) if x]


def spec_of(rec):
    if rec["kind"] == "script":
        return f"script:{rec['path']}::{rec.get('args') or '{in} {out} {report}'}"
    if rec["kind"] == "ops":
        return f"ops:{rec['path']}"
    return f"merge:{rec['base']}:{rec['path']}"


def load_state(pub):
    try:
        return json.loads((Path(pub) / "compose_state.json").read_text())
    except (OSError, ValueError):
        return None


def save_state(pub, st):
    p = Path(pub) / "compose_state.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1) + "\n")
    os.replace(tmp, p)


def pending(st, ledger):
    cur = st["current"]["sha256"]
    out = []
    for r in read_ledger(ledger):
        k = r["_key"]
        if k in st["included"]:
            continue
        rej = st["rejected"].get(k)
        if rej and rej.get("plan_sha256") == cur:
            continue
        missing = [x["path"] for x in r["rows"] if not os.path.isfile(x["path"])]
        if missing:
            st["rejected"][k] = dict(plan_sha256=cur, why=f"row file gone: {missing[:2]}", lane=r.get("lane"))
            continue
        out.append(r)
    return out


def gate_cmd(a, st, batch, out, plan_name):
    cmd = [sys.executable, "-I", str(HERE / "row_gate.py"), "gate", "--die", a.die, "--src", st["current"]["tree"],
           "--base", st["current"]["plan"], "--asbuilt", a.asbuilt, "--out", str(out), "--types", a.types,
           "--lane", f"ROLL-{a.die}", "--keep-fork", "--drop-failed-rows", "--plan-name", plan_name, "--mem", str(a.mem)]
    if a.rt:
        cmd += ["--rt", a.rt]
    if getattr(a, "tap_manifest", None):
        cmd += ["--tap-manifest", str(Path(a.tap_manifest).resolve())]
    meta = [dict(group=gi, ids=row_ids(r, x), overrides=list(r.get("overrides") or [])) for gi, r in enumerate(batch) for x in r["rows"]]
    mp = Path(str(out) + ".rowmeta.json")
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(json.dumps(meta) + "\n")
    wp = Path(a.pub) / "writers.json"
    cmd += ["--row-meta", str(mp), "--prior-writes", str(wp)]
    for e in a.env:
        cmd += ["--env", e]
    for r in batch:
        for x in r["rows"]:
            cmd += ["--row", spec_of(x)]
    if a.local:
        cmd.append("--local")
    return cmd


def compose_drops(prev, tree, rel, applied):
    """-> dict(intended, unnamed): plan paths the composed plan lost against the current one; the rows' ledger field intended_drops
    (drop-list lines) names the intended ones.  Writes <tree>/<rel>.drop_list (the list COMPOSEDROP reads next to the plan)"""
    import compose_drop_guard as CDG
    try:
        pl = json.loads((Path(prev["tree"]) / prev["plan"]).read_text())
        nw = json.loads((Path(tree) / rel).read_text())
    except (OSError, ValueError, KeyError):
        return dict(intended=[], unnamed=[])
    lines = [str(x) for r in applied for x in (r.get("intended_drops") or [])]
    text, named, unnamed = CDG.emit_drop_list(pl, nw, CDG.load_drop_list_lines(lines))
    try:
        (Path(str(Path(tree) / rel) + ".drop_list")).write_text(text)
    except OSError:
        pass
    return dict(intended=named, unnamed=unnamed)


def run_round(a, st, run=None):
    """one round -> 'idle' | 'published' | 'not-ready'"""
    run = run or subprocess.run
    pend = pending(st, a.ledger)
    if not pend:
        save_state(a.pub, st)
        return "idle"
    lim = min(x for x in (st.get("batch_limit"), a.max_rows, len(pend)) if x)
    batch = pend[:lim]
    n = st["round"] + 1
    out = Path(a.pub) / "rounds" / f"r{n:03d}"
    plan_name = f"plan_roll_{a.die}_r{n:03d}.json"
    print(f"ROLL r{n:03d}: {len(batch)} of {len(pend)} pending row set(s) on {st['current']['sha256'][:12]}: "
          + ", ".join(f"{r.get('lane')}:{r['_key'][:8]}" for r in batch), flush=True)
    rc = run(gate_cmd(a, st, batch, out, plan_name)).returncode
    st["round"] = n
    try:
        rr = json.loads((out / "ROW-READY.json").read_text())
    except (OSError, ValueError):
        rr = dict(verdict="NOT-READY", why=[f"gate rc {rc}, no ROW-READY"], rows=[])
    # map the gate's per-spec records back to the ledger row sets
    i, applied, dropped = 0, [], []
    recs = rr.get("rows") or []
    for r in batch:
        mine = recs[i:i + len(r["rows"])]
        i += len(r["rows"])
        (dropped if (not mine or any(m.get("dropped") or m.get("rc") for m in mine)) else applied).append(r)
    cur = st["current"]["sha256"]
    for r in dropped:
        st["rejected"][r["_key"]] = dict(plan_sha256=cur, why="does not apply on the current plan", lane=r.get("lane"), round=n)
    hist = dict(round=n, rows=[r["_key"] for r in batch], applied=[r["_key"] for r in applied], verdict=rr.get("verdict"),
                why=rr.get("why"), out=str(out), seconds=(rr.get("seconds") or {}).get("total"))
    st["history"].append(hist)
    if rr.get("verdict") == "READY" and applied:
        tree = out / "tree"
        rel = rr["plan"]["rel"]
        prev = dict(st["current"])
        drops = compose_drops(prev, tree, rel, applied)       # P-COMPOSE-DROP: explicit drop list next to the plan
        if drops["unnamed"] and os.environ.get("OT_COMPOSE_DROP") != "warn":
            st["rejected"].update({r["_key"]: dict(plan_sha256=st["current"]["sha256"], round=n, lane=r.get("lane"),
                                                   why=f"COMPOSEDROP {len(drops['unnamed'])} unnamed drop(s): {drops['unnamed'][:3]}") for r in applied})
            st["batch_limit"] = None
            save_state(a.pub, st)
            print(f"ROLL r{n:03d} NOT PUBLISHED: {len(drops['unnamed'])} drop(s) no row names (intended_drops): {drops['unnamed'][:5]}", flush=True)
            return "not-ready"
        try:                                             # P-ROW-SILENT-OVERWRITE: later rounds check against the keys this round's rows wrote
            wf = Path(a.pub) / "writers.json"
            wd = json.loads(wf.read_text()) if wf.is_file() else {}
            for rw in json.loads((out / "ROW-WRITES.json").read_text()).get("rows") or []:
                for p in rw.get("writes") or []:
                    wd.setdefault(p, []).append(rw.get("ids") or [])
            wf.write_text(json.dumps(wd) + "\n")
        except (OSError, ValueError):
            pass
        st["current"] = dict(tree=str(tree), plan=rel, sha256=rr["plan"]["sha256"], round=n, published=RG.utc())
        st["included"] += [r["_key"] for r in applied]
        st["batch_limit"] = None
        st.setdefault("published", []).append(dict(round=n, tree=str(tree), plan=rel, sha256=rr["plan"]["sha256"]))
        pubd = Path(a.pub) / "published"
        pubd.mkdir(parents=True, exist_ok=True)
        (pubd / f"r{n:03d}.json").write_text(json.dumps(dict(rr, previous=prev, ledger_rows=[dict(key=r["_key"], lane=r.get("lane"),
                                                                                                 file=r["_file"]) for r in applied]),
                                                         indent=1, default=str) + "\n")
        (Path(a.pub) / "current.json").write_text(json.dumps(st["current"], indent=1) + "\n")
        for old in st["published"][:-a.keep]:
            if old.get("tree") and os.path.isdir(old["tree"]) and not old.get("deleted") and Path(old["tree"]).is_relative_to(Path(a.pub)):
                RG.ot_delete(old["tree"], str(Path(a.pub) / "cleanup.log"))
                old["deleted"] = True
        save_state(a.pub, st)
        print(f"ROLL r{n:03d} PUBLISHED {rel} sha {rr['plan']['sha256'][:12]} in {tree} ({len(applied)} row set(s), "
              f"{len(dropped)} dropped)", flush=True)
        return "published"
    if not applied and dropped:                          # every row of the batch no longer applies: rejected above, nothing to gate
        if (out / "tree").is_dir():
            RG.ot_delete(out / "tree", str(Path(a.pub) / "cleanup.log"))
        save_state(a.pub, st)
        print(f"ROLL r{n:03d}: {len(dropped)} row set(s) do not apply on {cur[:12]}; REJECTED until the plan moves", flush=True)
        return "dropped"
    if len(applied) > 1:
        st["batch_limit"] = max(1, len(applied) // 2)
    elif len(applied) == 1:
        st["rejected"][applied[0]["_key"]] = dict(plan_sha256=cur, why="; ".join(rr.get("why") or [])[:500], lane=applied[0].get("lane"), round=n)
        st["batch_limit"] = None
    if (out / "tree").is_dir():
        RG.ot_delete(out / "tree", str(Path(a.pub) / "cleanup.log"))
    save_state(a.pub, st)
    print(f"ROLL r{n:03d} NOT READY: {'; '.join(rr.get('why') or [])[:400]} (next batch limit {st.get('batch_limit')})", flush=True)
    return "not-ready"


def init_state(a):
    st = load_state(a.pub)
    if st:
        return st
    if not a.src or not a.base:
        raise SystemExit("row_compose: first round needs --src and --base")
    src = os.path.realpath(a.src)
    st = dict(die=a.die, round=0, included=[], rejected={}, history=[], batch_limit=None,
              current=dict(tree=src, plan=a.base, sha256=RG.sha(Path(src) / a.base), round=0, published=None))
    Path(a.pub).mkdir(parents=True, exist_ok=True)
    save_state(a.pub, st)
    return st


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("roll")
    r.add_argument("--die", required=True)
    r.add_argument("--ledger", required=True)
    r.add_argument("--pub", required=True)
    r.add_argument("--src")
    r.add_argument("--base")
    r.add_argument("--asbuilt", required=True)
    r.add_argument("--types", default="all")
    r.add_argument("--rt")
    r.add_argument("--env", action="append", default=[])
    r.add_argument("--tap-manifest", type=Path, help="native placed sink bins manifest for per-cut tap derivation")
    r.add_argument("--mem", type=int, default=160)
    r.add_argument("--max-rows", type=int, default=0, help="at most N row sets per round (0 = all pending)")
    r.add_argument("--keep", type=int, default=2, help="published trees kept")
    r.add_argument("--local", action="store_true", help="gate here instead of under ot-run --die")
    m = r.add_mutually_exclusive_group()
    m.add_argument("--once", action="store_true")
    m.add_argument("--watch", type=int, default=0)
    s = sub.add_parser("status")
    s.add_argument("--pub", required=True)
    s.add_argument("--ledger")
    a = ap.parse_args(argv)
    if a.cmd == "status":
        st = load_state(a.pub)
        if not st:
            print("no compose state")
            return 2
        print(json.dumps(dict(current=st["current"], included=len(st["included"]), rejected=st["rejected"],
                              last=st["history"][-3:], pending=[f"{x.get('lane')}:{x['_key'][:8]}" for x in pending(st, a.ledger)] if a.ledger else None),
                         indent=1))
        return 0
    st = init_state(a)
    if not a.watch:
        return 1 if run_round(a, st) == "not-ready" else 0
    while True:
        res = run_round(a, st)
        if res in ("idle", "dropped"):
            time.sleep(a.watch)


if __name__ == "__main__":
    sys.exit(main())
