#!/usr/bin/env python3
"""CLOSED STANDS submit gate (owner 2026-10-12 19:00 "M5 cap narrowed"; gate 2026-10-13, el1013-rule-enforcement).

Measured 10-12/10-13: 128 failed jobs in 24 h on 81 blocks that had ALREADY closed, 74 of them M5 re-routes of closed
tiles.  The rule: M5 is the default for NEW tiles; a closed tile is routed again only when a die window needs the
tracks; a fully closed tile stands.  This module judges ONE new job spec against the loop's job history:

  block identity   spec "block" (top module) + parameter set (kit.env PARAMS for a ref_tile kit, else the route
                   command's --param / master cfg, tools/closure_loop/rtl_boundary.py recipe).  Two parameter sets that
                   are both known, non-empty and different are different blocks (the gate does not apply); a set that
                   cannot be read counts as the same block.
  closed           a CLOSED job that still counts (not revoked) and whose record / view is published
                   (publish.branch_commit).
  verdict          NA (no such closed job, or no route stage), EXEMPT (loop successor of a job that is not CLOSED),
                   PASS (a verified "reroute_reason"), REFUSE.

Constants and the rule text live in tools/textbook_lint.py (CLOSED_STANDS_KINDS, DIE_WINDOW_CUT_MIN,
CLOSED_STANDS_INSTEAD).  Pure: git access comes in as show(commit, path) / blob(commit, path); never raises on a
malformed spec."""
from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _p in (str(HERE), str(HERE.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import rtl_boundary  # noqa: E402
import textbook_lint as TL  # noqa: E402

KIT_RE = re.compile(r"ref_route\.sh\s+(\S+)/kit\.env")
GEOM_KEYS = ("FW", "FH", "PINS", "PINEX", "PIN_H", "PIN_V")           # outline + pin faces / pin layers of a kit
HOLD_RERUN_RE = re.compile(r"-(hs|ls)(-[a-z0-9]{1,4})?$")              # hold-overlay / submit-lint re-runs of one job
LOOP_CLASSES_NM = ("g1", "g2")


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _commit(j):
    return str(j.get("commit_full") or ((j.get("spec") or {}).get("source") or {}).get("commit") or "")


def pin_wrapper_args(text):
    """Actual RTL-generation knobs, distinct from physical placement/hold knobs.

    Read the generated EXTRA array as a whole: _cfg_vars stops at parentheses
    inside quoted regexes. Unknown shell construction is not evidence of change.
    """
    match = re.search(r'^EXTRA=\((.*)\)\s*$', text, re.M)
    if not match:
        return None if 'OT_PIN_REGS=' in text else {'enable': False}
    try:
        tokens = shlex.split(match[1])
    except ValueError:
        return None
    values = dict(t.split('=', 1) for t in tokens if '=' in t and t.split('=', 1)[0] in
                  ('OT_PIN_REGS', 'OT_PIN_REGS_CLOCK', 'OT_PIN_REGS_EXCLUDE', 'OT_PIN_REGS_RESET'))
    if values.get('OT_PIN_REGS', '0') == '0':
        return {'enable': False}
    if values.get('OT_PIN_REGS') != '1' or not values.get('OT_PIN_REGS_CLOCK'):
        return None
    if any(re.search(r'\$[A-Za-z_{(]|`', v) for v in values.values()):
        return None
    return dict(enable=True, clock=values['OT_PIN_REGS_CLOCK'],
                exclude=values.get('OT_PIN_REGS_EXCLUDE', ''), reset=values.get('OT_PIN_REGS_RESET', ''))


def route_recipe(spec, show):
    """{"top", "sources", "params", "geom"} of the job's route at its source commit, or None when it cannot be read"""
    try:
        cmd = ((spec.get("stages") or {}).get("route") or {}).get("cmd") or ""
        commit = str((spec.get("source") or {}).get("commit") or "")
        m = KIT_RE.search(cmd)
        if m:
            text = show(commit, f"{m.group(1)}/kit.env")
            if text is None:
                return None
            v = rtl_boundary._cfg_vars(text)
            srcs = shlex.split(v.get("SRCS", "''"))[0].split() if v.get("SRCS") else []
            ptoks = shlex.split(v.get("PARAMS", "()").strip("()")) if v.get("PARAMS") else []
            geom = {k: ln.split("=", 1)[1].strip() for ln in text.splitlines()
                    for k in GEOM_KEYS if ln.startswith(k + "=")}
            return {"top": spec.get("block"), "sources": srcs, "params": rtl_boundary._params(ptoks), "geom": geom,
                    "pin_wrapper": pin_wrapper_args(text)}
        r = rtl_boundary.recipe(spec, show)
        return dict(r, geom={}) if r else None
    except Exception:  # noqa: BLE001
        return None


def published(j):
    p = j.get("publish") if isinstance(j.get("publish"), dict) else {}
    return bool(p.get("branch_commit") or p.get("merge_commit"))


def successor_parent(spec, name, by_name):
    """the job this one is a loop successor of -- auto-react (the parent's record must list it: a spec cannot claim it
    by its own fields), submit-lint requeue, or a -hs / -ls re-run named after it -- else None"""
    blk = spec.get("block")
    par = spec.get("auto_react_parent")
    if par and par in by_name:
        pj = by_name[par]
        listed = []
        for v in (pj.get("auto_react") or {}).values():
            listed += v if isinstance(v, list) else [v]
        if name in listed and (pj.get("spec") or {}).get("block") == blk:
            return pj
    rq = (spec.get("submit_lint") or {}).get("requeued_from") if isinstance(spec.get("submit_lint"), dict) else None
    m = HOLD_RERUN_RE.search(str(name))
    for cand in (rq, str(name)[:m.start()] if m else None):
        pj = by_name.get(cand) if cand else None
        if pj and (pj.get("spec") or {}).get("block") == blk and _commit(pj)[:9] == _commit({"spec": spec})[:9]:
            return pj
    return None


def rtl_compare(new_rec, new_commit, closed_job, closed_rec, blob):
    """("same" | "differs" | "unknown", detail): the new job's RTL sources against the closed job's commit.  Same when
    every source path holds the same blob at the closed commit, or when the closed job's own source list holds the same
    set of blobs (a snapshot under another path is still the same RTL)."""
    cc = _commit(closed_job)
    if not new_rec or not new_rec.get("sources"):
        return "unknown", "the new job's RTL sources cannot be read from its route command"
    new_wrapper, old_wrapper = new_rec.get('pin_wrapper'), (closed_rec or {}).get('pin_wrapper')
    wrapper_changed = new_wrapper is not None and old_wrapper is not None and new_wrapper != old_wrapper
    if not wrapper_changed and cc and new_commit and (cc.startswith(new_commit) or new_commit.startswith(cc)):
        return "same", f"same source commit {cc[:9]}"
    new = {s: blob(new_commit, s) for s in sorted(set(new_rec["sources"]))}
    if any(v is None for v in new.values()):
        return "unknown", f"source missing at {new_commit[:9]}: {[k for k, v in new.items() if v is None][:3]}"
    if not cc or blob(cc, "") is None:
        return "unknown", f"closed commit {cc[:9] or '?'} is not in the object store"
    if wrapper_changed:
        return 'differs', ('generic pin-wrapper RTL generation differs: '
                           f'{old_wrapper} -> {new_wrapper}; core sources may remain unchanged')
    if {s: blob(cc, s) for s in new} == new:
        return "same", f"{len(new)} RTL source file(s) byte-identical at {cc[:9]} and {new_commit[:9]}"
    if closed_rec and closed_rec.get("sources"):
        old = [blob(cc, s) for s in sorted(set(closed_rec["sources"]))]
        if None not in old and sorted(old) == sorted(new.values()):
            return "same", f"the closed job's {len(old)} RTL source file(s) hold the same content (other paths)"
    changed = [s for s in new if blob(cc, s) != new[s]]
    return "differs", f"{len(changed)} of {len(new)} RTL source file(s) differ from {cc[:9]}: {', '.join(changed[:3])}"


def evidence_gap_of(j, bench_gap):
    """why the closed job's evidence is incomplete (bench + mutant, routed verdict), or None when it is complete"""
    b = j.get("benches") or {}
    ok = {k: v.get("expect") for k, v in b.items() if isinstance(v, dict) and v.get("ok") is True}
    gap = bench_gap(ok) if ok else "no loop benches ran"
    if gap:
        return gap
    m = j.get("metrics") or {}
    if not (_num(m.get("ff_ps")) and (_num(m.get("ss_ps")) or _num(m.get("tt_ps"))) and _num(m.get("drc"))):
        return "no routed verdict (TT / FF slack and DRC count) on record"
    return None


def _same_params(a, b):
    """True (equal), False (both known, non-empty, different), None (cannot tell)"""
    if a is None or b is None:
        return None
    pa, pb = a.get("params") or {}, b.get("params") or {}
    if pa == pb:
        return True
    return False if pa and pb else None


def check(spec, name, jobs, show, blob, closure_counts=None, bench_gap=None, exists=None):
    """the gate.  jobs: the loop's job records (history); closure_counts(job) -> the CLOSED still counts; bench_gap:
    closure_loop.bench_evidence_gap; exists(path) -> the cited figure's source file is there.
    {"verdict": NA|EXEMPT|PASS|REFUSE, "message", "closed": [names], "kind", "facts"}"""
    out = {"verdict": "NA", "message": "", "closed": [], "kind": None, "facts": {}}
    if "route" not in (spec.get("stages") or {}):
        out["message"] = "no route stage"
        return out
    blk = spec.get("block")
    counts = closure_counts or (lambda x: x.get("status") == "CLOSED")
    closed = [x for x in jobs if (x.get("spec") or {}).get("block") == blk and x.get("name") != name
              and x.get("status") == "CLOSED" and counts(x) and published(x)]
    if not closed:
        out["message"] = f"no CLOSED job of {blk} with a published view"
        return out
    by_name = {x.get("name"): x for x in jobs if (x.get("spec") or {}).get("block") == blk}
    par = successor_parent(spec, name, by_name)
    if par is not None and par.get("status") != "CLOSED":
        out.update(verdict="EXEMPT", message=f"loop successor of {par['name']} ({par.get('status')}, not CLOSED)")
        return out
    new_rec = route_recipe(spec, show)
    new_commit = str((spec.get("source") or {}).get("commit") or "")
    recs = {x["name"]: route_recipe(x.get("spec_submitted") or x["spec"], show) for x in closed}
    same = [x for x in closed if _same_params(new_rec, recs[x["name"]]) is not False]
    closed.sort(key=lambda x: str(x.get("finished_at") or x.get("updated") or ""))
    same.sort(key=lambda x: str(x.get("finished_at") or x.get("updated") or ""))
    if not same:
        out["message"] = (f"{len(closed)} CLOSED job(s) of {blk} have another parameter set "
                          f"(new {(new_rec or {}).get('params')}; e.g. {closed[-1]['name']} "
                          f"{(recs[closed[-1]['name']] or {}).get('params')}): a different block")
        return out
    out["closed"] = [x["name"] for x in same]
    last = same[-1]
    rtl = {x["name"]: rtl_compare(new_rec, new_commit, x, recs[x["name"]], blob) for x in same}
    gaps = {x["name"]: (evidence_gap_of(x, bench_gap) if bench_gap else None) for x in same}
    facts = out["facts"] = {
        "closed_job": last["name"], "closed_commit": _commit(last)[:9], "params": (new_rec or {}).get("params"),
        "rtl": rtl[last["name"]][0], "rtl_detail": rtl[last["name"]][1], "evidence_gap": gaps[last["name"]]}
    head = (f"{blk} is CLOSED with a published view ({last['name']} @ {facts['closed_commit']}"
            + (f" and {len(same) - 1} more" if len(same) > 1 else "") + ")")
    measured = (f"measured: RTL vs the closed commit {facts['rtl']} ({facts['rtl_detail']}); closed evidence "
                + (f"gap: {facts['evidence_gap']}" if facts["evidence_gap"] else "complete (bench + mutant, routed verdict)"))

    def refuse(why):
        out.update(verdict="REFUSE", message=f"{head}: {why}; {measured}. {TL.CLOSED_STANDS_INSTEAD}")
        return out

    def admit(why):
        out.update(verdict="PASS", message=f"{head}; reroute_reason {out['kind']}: {why}")
        return out

    rr = spec.get("reroute_reason")
    if not isinstance(rr, dict) or rr.get("kind") not in TL.CLOSED_STANDS_KINDS:
        return refuse("the spec carries no \"reroute_reason\"" if rr is None else
                      f"\"reroute_reason\" must be an object with \"kind\" one of {', '.join(TL.CLOSED_STANDS_KINDS)}")
    kind = out["kind"] = rr["kind"]
    txt = lambda k, n=1: isinstance(rr.get(k), str) and len(rr[k].strip()) >= n  # noqa: E731
    if kind == "die_window":
        cut, ovf = rr.get("cut"), rr.get("grt_overflow")
        if not txt("slot", 3):
            return refuse("die_window needs \"slot\": the contract slot the tile sits in")
        if not txt("source", 3):
            return refuse("die_window needs \"source\": the file the cut / GRT overflow figure was measured in")
        if exists is not None and not exists(rr["source"].strip()):
            return refuse(f"die_window source file {rr['source']!r} does not exist (absolute path, or a path on the "
                          f"job's commit / origin/main)")
        has_ovf = (_num(ovf) and ovf > 0) or (isinstance(ovf, list) and len(ovf) > 0)
        if _num(cut) and cut > TL.DIE_WINDOW_CUT_MIN:
            return admit(f"slot {rr['slot']} under a die window with fine cut {cut} > {TL.DIE_WINDOW_CUT_MIN} "
                         f"({rr['source']})")
        if has_ovf:
            return admit(f"slot {rr['slot']} under die-GRT overflow {ovf} ({rr['source']})")
        if _num(cut):
            return refuse(f"die_window cut {cut} is not above {TL.DIE_WINDOW_CUT_MIN}: the window does not need the "
                          f"tracks, the closed view stands")
        return refuse("die_window needs the measured figure: \"cut\" (fine cut, a number > "
                      f"{TL.DIE_WINDOW_CUT_MIN}) or \"grt_overflow\" (die-GRT overflow over the tile, > 0)")
    if kind == "slot_change":
        cite = next((str(c).strip() for c in (rr.get("contract"), rr.get("slot_change_request"),
                                              spec.get("slot_change_request")) if isinstance(c, str) and len(c.strip()) >= 8), None)
        if not cite:
            return refuse("slot_change needs \"contract\" (contract file + version) or \"slot_change_request\" (the "
                          "die lead's SLOT CHANGE REQUEST line)")
        g = (new_rec or {}).get("geom") or {}
        eq = [x["name"] for x in same if g and ((recs[x["name"]] or {}).get("geom") or {}) == g]
        if eq:
            return refuse(f"slot_change claimed, but the kit's outline and pin faces ({', '.join(sorted(g))}) equal "
                          f"those of closed {eq[-1]} (a layer-cap change alone is die_window, not slot_change)")
        return admit(f"outline / pin faces differ from the closed view per {cite[:200]!r}"
                     + ("" if g else " (not verifiable: no kit.env geometry)"))
    if kind == "param_change":
        ps = rr.get("params")
        if not ((isinstance(ps, (dict, list)) and len(ps) > 0) or txt("params", 3)):
            return refuse("param_change needs \"params\": the elaborated parameters that differ, with their values")
        eq = [x["name"] for x in same if (new_rec or {}).get("params") and _same_params(new_rec, recs[x["name"]]) is True]
        if eq:
            return refuse(f"param_change claimed, but the parameter set {new_rec['params']} equals that of closed {eq[-1]}")
        return admit(f"elaborated parameters differ: {str(ps)[:300]}")
    if kind == "rtl_change":
        eq = [n for n, (st, _) in rtl.items() if st == "same"]
        if eq:
            return refuse(f"rtl_change claimed, but the RTL is the same as closed {eq[-1]}'s ({rtl[eq[-1]][1]})")
        if rtl[last["name"]][0] == "unknown" and "new job's RTL sources" in rtl[last["name"]][1]:
            return refuse("rtl_change cannot be verified: " + rtl[last["name"]][1] + " (state them in the spec: "
                          "\"rtl_boundary\": {\"top\": ..., \"sources\": [...]})")
        unv = [n for n, (st, _) in rtl.items() if st == "unknown"]
        return admit(rtl[last["name"]][1] + (f" (not verifiable against {', '.join(unv[:3])})" if unv else " (verified)"))
    if kind == "pin_register":
        pc = rr.get("pair_cost_ps")
        if not txt("source", 3):
            return refuse("pin_register needs \"source\": the pin-register audit JSON the view was judged in "
                          "(tools/hier_contract/pinreg_audit.py v2, insertion-compensated)")
        if exists is not None and not exists(rr["source"].strip()):
            return refuse(f"pin_register source file {rr['source']!r} does not exist (absolute path, or a path on the "
                          f"job's commit / origin/main)")
        if not txt("cell", 3):
            return refuse("pin_register needs \"cell\": the audited cell (the view's lib cell)")
        if not txt("fix", 20):
            return refuse("pin_register needs \"fix\": what the new kit changes so the pin flops sit at the pins "
                          "(kit recipe 2, RTL pin flops, a split): a re-route of the same kit repeats the defect")
        # tile defect (header 10-13 die clock delivery rule): launch > 220 ps or capture > 190 ps beyond the boundary
        # clock (phi - R, first-load Liberty) is a defect of the VIEW whatever the pair it meets -- the die budget is
        # one fixed budget per face, so a view that spends more than its share is re-built, not waived.
        lw, cp = rr.get("launch_ps"), rr.get("capture_ps")
        if (_num(lw) and lw > TL.PIN_LAUNCH_MAX_PS) or (_num(cp) and cp > TL.PIN_CAPTURE_MAX_PS):
            return admit(f"{rr['cell']} is a pin-register tile defect: worst launch {lw} ps (> {TL.PIN_LAUNCH_MAX_PS}) / "
                         f"capture {cp} ps (> {TL.PIN_CAPTURE_MAX_PS}) at phi - R ({rr['source']}); fix: "
                         f"{rr['fix'].strip()[:200]}")
        if not _num(pc):
            return refuse("pin_register needs the measured \"pair_cost_ps\" (o + s of the view in the audit) or the "
                          f"view's worst \"launch_ps\" > {TL.PIN_LAUNCH_MAX_PS} / \"capture_ps\" > {TL.PIN_CAPTURE_MAX_PS}")
        if pc <= TL.PIN_REGISTER_PAIR_MAX_PS:
            return refuse(f"pin_register pair cost {pc} ps is not above {TL.PIN_REGISTER_PAIR_MAX_PS} ps: the view "
                          f"closes a hop within its reach (relay within the reach), the closed view stands")
        return admit(f"{rr['cell']} is a pin-register violation: pair cost {pc} ps > {TL.PIN_REGISTER_PAIR_MAX_PS} ps "
                     f"({rr['source']}); fix: {rr['fix'].strip()[:200]}")
    if kind == "native_launch":
        # (el1014-root-macro-edge, 2026-10-14) a CLOSED view over the native launch budget (TT launch > 220 ps at phi - R)
        # because its kit is older than the recipe-2 output stage (main 36de4b87f: one launch flop per output pin, HB2
        # pad, pin registers kept).  Re-kit of the SAME block: same RTL, same outline / pin faces, only the output stage
        # changes -- the gate verifies all three (tools/ref_tile/rekit_native_launch.py writes such a job).
        lw = rr.get("launch_ps")
        if not txt("source", 3):
            return refuse("native_launch needs \"source\": the native pin audit JSON the view failed in "
                          "(results/arch/native_pin_audit_*/<design>.json)")
        if exists is not None and not exists(rr["source"].strip()):
            return refuse(f"native_launch source file {rr['source']!r} does not exist (absolute path, or a path on the "
                          f"job's commit / origin/main)")
        if not txt("cell", 3):
            return refuse("native_launch needs \"cell\": the audited cell (the view's lib cell)")
        if not _num(lw) or lw <= TL.PIN_LAUNCH_MAX_PS:
            return refuse(f"native_launch needs the view's measured worst \"launch_ps\" > {TL.PIN_LAUNCH_MAX_PS} "
                          f"(got {lw!r}); a capture-only miss is pin_register")
        if rtl[last["name"]][0] == "differs":
            return refuse("native_launch is a re-kit of the closed RTL, but " + rtl[last["name"]][1]
                          + " (a changed block is rtl_change)")
        g_new = (new_rec or {}).get("geom") or {}
        g_old = (recs[last["name"]] or {}).get("geom") or {}
        moved = sorted(k for k in ("FW", "FH", "PINS") if g_new.get(k) != g_old.get(k))
        if g_new and g_old and moved:
            return refuse(f"native_launch keeps the closed outline and pin faces, but {', '.join(moved)} differ from "
                          f"closed {last['name']} (a moved outline / pin plan is slot_change)")
        m = KIT_RE.search(((spec.get("stages") or {}).get("route") or {}).get("cmd") or "")
        kd = m.group(1) if m else None
        if kd:
            env = show(new_commit, f"{kd}/kit.env") or ""
            gpl = show(new_commit, f"{kd}/pre_gpl.tcl") or ""
            if env and not (re.search(r"^RECIPE=([2-9]|\d\d)", env, re.M) and "pin_reg_split.tcl" in gpl
                            and "OT_KEEP_PIN_REGS=1" in env):
                return refuse(f"native_launch: the kit {kd} at {new_commit[:9]} does not carry the recipe-2 output stage "
                              f"(RECIPE=2, pin_reg_split.tcl in pre_gpl.tcl, OT_KEEP_PIN_REGS=1): a re-route of the same "
                              f"output stage repeats the launch miss")
            old_gpl = show(_commit(last), f"{kd}/pre_gpl.tcl") or ""
            # (Q-DVM 2026-10-15) a closed recipe-2 kit that ran WITHOUT the output hold pad (spec outhold false: no
            # leaf_iohold.tcl) leaves FF out-min to hold repair, whose BUF chains land on the launch path (qfd_xcst_*_m5
            # m5c: 6 x BUFx2 per pin, launch 224.7..235.5).  Re-kitting the same block WITH the pad is a different output
            # stage, not a repeat; a closed kit that already had both still refuses.
            if "pin_reg_split.tcl" in old_gpl and ("leaf_iohold.tcl" in old_gpl or "leaf_iohold.tcl" not in gpl):
                return refuse(f"native_launch: closed {last['name']} already had the recipe-2 output stage; the launch "
                              f"miss has another cause (pin_register with the measured fix)")
        return admit(f"{rr['cell']} TT launch {lw} ps > {TL.PIN_LAUNCH_MAX_PS} at phi - R ({rr['source']}); same RTL "
                     f"({rtl[last['name']][0]}), same outline / pins, kit re-generated with the recipe-2 output stage")
    # evidence_gap
    if not txt("why_route", 20):
        return refuse("evidence_gap needs \"why_route\": why a ROUTE is needed (a missing bench is bound to the closed "
                      "job, a missing view is re-exported from the closed run: neither needs a route)")
    full = [n for n, gp in gaps.items() if gp is None]
    if bench_gap and full:
        return refuse(f"evidence_gap claimed, but closed {full[-1]} has a behavioural bench + mutant and a routed verdict")
    return admit(f"closed evidence gap ({gaps[last['name']]}); route needed because: {rr['why_route'].strip()[:300]}")


# ------------------------------------------------------------------------------------------------------- replay
def replay(hours=24.0, state=None):
    """what the gate would have decided for every job the loop ingested in the last `hours`, against the history as it
    stood when each job was created (closures finished before it).  Read-only."""
    import collections
    import datetime as dt
    import closure_loop as cl
    import submit_lint
    if state:
        cl.STATE = Path(state)
    jobs = cl.all_jobs()
    git_ = submit_lint.Git(cl.REPO)
    memo_s, memo_b = {}, {}
    show = lambda c, p: memo_s[(c, p)] if (c, p) in memo_s else memo_s.setdefault((c, p), git_.show(c, p))  # noqa: E731
    blob = lambda c, p: memo_b[(c, p)] if (c, p) in memo_b else memo_b.setdefault((c, p), git_.blob(c, p))  # noqa: E731
    rv = cl.revoked_closures()
    ts = lambda s: dt.datetime.fromisoformat(s) if s else None  # noqa: E731
    now = dt.datetime.now().astimezone()
    by_block = collections.defaultdict(list)
    for x in jobs:
        by_block[(x.get("spec") or {}).get("block")].append(x)
    rows = []
    for j in jobs:
        t0 = ts(j.get("created"))
        if t0 is None or (now - t0).total_seconds() > hours * 3600:
            continue
        spec = j.get("spec_submitted") or j["spec"]
        hist = [x for x in by_block[spec.get("block")]
                if x.get("status") != "CLOSED" or (ts(x.get("finished_at") or x.get("updated")) or now) < t0]
        res = check(spec, j["name"], hist, show, blob, closure_counts=lambda x: cl.closure_counts(x, rv),
                    bench_gap=cl.bench_evidence_gap, exists=None)
        rows.append({"job": j["name"], "block": spec.get("block"), "created": j.get("created"), "status": j["status"],
                     "verdict": res["verdict"], "kind": res.get("kind"), "closed": res.get("closed", [])[-1:],
                     "rtl": (res.get("facts") or {}).get("rtl"), "evidence_gap": (res.get("facts") or {}).get("evidence_gap")})
    return rows


def main(argv=None):
    import argparse
    import collections
    import json
    ap = argparse.ArgumentParser(description="CLOSED STANDS gate: replay over the loop's job history (read-only)")
    ap.add_argument("cmd", choices=["replay"])
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--state")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rows = replay(a.hours, a.state)
    ref = [r for r in rows if r["verdict"] == "REFUSE"]
    by = collections.Counter(r["verdict"] for r in rows)
    st = collections.Counter(r["status"] for r in ref)
    summary = {"hours": a.hours, "jobs": len(rows), "by_verdict": dict(by), "refused": len(ref),
               "refused_blocks": len({r["block"] for r in ref}), "refused_by_final_status": dict(st.most_common()),
               "refused_by_rtl": dict(collections.Counter(r["rtl"] for r in ref)),
               "refused_closed_evidence_complete": sum(1 for r in ref if not r["evidence_gap"])}
    print(json.dumps(summary, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps({"summary": summary, "rows": rows}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
