#!/usr/bin/env python3
"""core_tap_census.py -- CORE-TAP-BUDGET 11-24 (FABLE-RC-ALL 701c4a59, QC-CBX-CLOCK 11-24): static, report-only census of
the hard-core clock taps of one or more die plans.  It never blocks, holds or approves (owner r703).

  core_tap_census.py --plan DIE=PLAN.json[,DIE=PLAN.json...] [--root DIE=TREE ...] [--types GLOB] --out OUT.tsv [--json OUT.json]

Two defects, one row per (type, core tap port, core pin):

(A) OWNER / LEGACY PATH.  gen_phys.core_mean_contract_options takes the mean-contract path only when every early core
    tap carries budget_owner SIGNED... (all taps, with insertion_ff_ps) or parent_budget...; any other owner, or none,
    sends the type to the legacy path: core_latency.txt (OT_CORE_LAT, the pin target tap_balance.tcl aims the core clock
    pin at) carries the liberty ETM max_clock_tree_path, while the tap rows (core_taps.txt, the SDC source latency)
    carry the plan insertion_ps.  err_ps = pin target - tap insertion (TT), read from the files gen_phys writes for
    the kit (core_latency_files in a temp dir), so it is the number the kit would use.  HEAD West hd_lep0N_w: ETM
    612.07 vs tap 553.42 = +58.65.  The selected view's SIGNED contract mean (core_clock_contract.load, require_signed)
    is listed beside it when the view carries one, with plan - contract.

(B) TAP-OFFSET SPAN.  clock.tap_offset.per_port_ps rows on CORE tap ports carry the tap's declared early delivery in the
    raw offset; gen_phys.tap_offset_span_ps takes W = max(o+u) - min(o-u) over RAW rows (QC cbx_q10__cl89936551:
    -449.95 -> W 510.2) and applies -W to every port without a row.  W_res = the same span with core-tap rows taken
    on their residual (o + insertion - common + lead, the R-CLOCK-7 basis tap_offset_table checks).  W_raw - W_res is
    the window the tool adds; reported per type (QC-CBX-CLOCK owns the tool fix).
"""
import argparse
import contextlib
import fnmatch
import gzip
import io
import json
import math
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = ["die", "plan_sha12", "type", "placed", "core_taps", "path", "owner_class", "port", "tap", "inst", "module", "pin",
          "tap_ins_TT", "tap_ins_FF", "pin_target_TT", "pin_basis", "err_TT", "contract_TT", "contract_FF",
          "plan_minus_contract_TT", "plan_minus_contract_FF", "contract_source", "offset_core_rows", "W_raw", "W_res",
          "W_extra", "signed_whatif", "note"]


def owner_class(tp):
    o = str(tp.get("budget_owner", "") or "")
    if not o:
        return "NONE"
    if o.startswith("SIGNED"):
        return "SIGNED" if "insertion_ff_ps" in tp else "SIGNED-noFF"
    if o.startswith("parent_budget"):
        return "parent_budget" if "insertion_ff_ps" in tp else "parent_budget-noFF"
    return "OTHER:" + o[:40].replace("\t", " ")


def read_plan(path):
    b = Path(path).read_bytes()
    if str(path).endswith(".gz"):
        b = gzip.decompress(b)
    import hashlib
    return json.loads(b), hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def tree_root(plan):
    p = Path(plan).resolve()
    for a in p.parents:
        if a.name == "physical" and (a / "die_plan").is_dir():
            return a.parent
    return None


def offset_spans(GP, S, P, tn):
    """(n core-tap offset rows, W_raw, W_res) of a type; (0, 0, 0) without clock.tap_offset rows."""
    try:
        tab = GP.tap_offset_table(P, tn)
    except Exception as e:  # noqa: BLE001 -- report, never stop
        return None, None, None, f"tap_offset_table {type(e).__name__}: {str(e)[:120]}"
    if not tab:
        return 0, 0.0, 0.0, ""
    w_raw = GP.tap_offset_span_ps(P, tn)
    t = P.types[tn]
    core = {cn: ctp for cn, _x, _y, ctp in S.core_taps(P, tn)}
    span = 0.0
    for c in ("TT", "FF"):
        vals = []
        for n, r in tab.items():
            o = r[c]
            if n in core:
                o += S.core_tap_insertion_ps(core[n], c) - S.common_latency_ps(P, c, t) + S.core_tap_lead_ps(t, c)
            vals.append((o - r["tol"], o + r["tol"]))
        span = max(span, max(h for _l, h in vals) - min(lo for lo, _h in vals))
    w_res = math.ceil(span * 10 - 1e-9) / 10.0
    return sum(n in core for n in tab), w_raw, w_res, ""


def contract_means(CC, core, root):
    try:
        con = CC.load(core, root, require_signed=True)
    except Exception as e:  # noqa: BLE001
        return None, f"no signed contract: {str(e)[:100]}"
    return con, "; ".join(sorted({str(v.get("contract_source")) for v in con.values()}))[:160]


def signed_whatif(GP, P, tn, root, cons):
    """would SIGNED rows (budget_owner SIGNED + the view contract TT/FF means on every core tap) generate?  'OK', or
    the refusal; '' when some core tap has no signed contract for its pin (the row cannot be written from a contract)."""
    import copy
    ck = P.types[tn].get("clock") or {}
    taps = ck.get("taps") or []
    keep = copy.deepcopy(taps)
    try:
        for tp in taps:
            if tp.get("kind") != "core":
                continue
            c = cons.get(tp.get("name"))
            if not c:
                return ""
            tp["insertion_ps"], tp["insertion_ff_ps"] = c
            tp["budget_owner"] = "SIGNED (census what-if)"
        opts = GP.core_mean_contract_options(P, tn)
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            GP.core_latency_files(P, tn, Path(td), root, **opts)
        return "OK" if opts["mean_contract"] else "LEGACY"
    except Exception as e:  # noqa: BLE001
        return f"FAIL {type(e).__name__}: {str(e)[:140]}"
    finally:
        taps[:] = keep


def type_rows(die, sha, P, tn, root, GP, S, CC, placed):
    t = P.types[tn]
    ck = t.get("clock") or {}
    taps = [tp for tp in ck.get("taps", []) or [] if tp.get("kind") == "core"]
    if not taps or ck.get("core_taps") not in ("early", "internal"):
        return []
    base = dict(die=die, plan_sha12=sha, type=tn, placed="yes" if tn in placed else "no", core_taps=ck.get("core_taps"))
    try:
        opts = GP.core_mean_contract_options(P, tn)
        path = ("signed_mean" if opts["require_signed"] else "parent_budget_mean") if opts["mean_contract"] else "legacy"
        perr = ""
    except Exception as e:  # noqa: BLE001
        opts, path, perr = None, "ERROR", f"{type(e).__name__}: {str(e)[:160]}"
    n_off, w_raw, w_res, oerr = offset_spans(GP, S, P, tn)
    base.update(offset_core_rows=n_off, W_raw=w_raw, W_res=w_res,
                W_extra=round(w_raw - w_res, 1) if w_raw is not None else None)
    rows_lat, taps_k, gerr = [], [], ""
    if opts is not None:
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            try:
                r = GP.core_latency_files(P, tn, Path(td), root, **opts)
                rows_lat, taps_k = r["rows"], r["taps"]
            except Exception as e:  # noqa: BLE001
                gerr = f"core_latency_files {type(e).__name__}: {str(e)[:160]}"
    if not taps_k:     # internal core taps, or gen refused: still list every plan core tap with its owner
        try:
            taps_k = GP.core_tap_rows(P, tn) if ck.get("core_taps") == "early" else []
        except Exception as e:  # noqa: BLE001
            gerr = (gerr + f" | core_tap_rows {type(e).__name__}: {str(e)[:100]}").strip(" |")
    by_port = {cn: ctp for cn, _x, _y, ctp in S.core_taps(P, tn)} if ck.get("core_taps") == "early" else {}
    hc = {h["inst"]: h for h in t.get("hard_cores", []) or []}
    phys = {GP.content_physical_identity(h)[0]: h for h in hc.values() if "physical_inst" in h or "physical_master" in h}
    out = []
    note = "; ".join(x for x in (perr, oerr, gerr) if x)
    if not taps_k:
        for tp in taps:
            out.append(dict(base, path=path, owner_class=owner_class(tp), tap=tp.get("name"), port="", inst="", module="",
                            pin="", tap_ins_TT=tp.get("insertion_ps"), tap_ins_FF=tp.get("insertion_ff_ps"), note=note))
        return out
    con_cache, tap_con = {}, {}
    for port, inst, pin, _early, ins in taps_k:
        tp = by_port.get(port) or {}
        core = hc.get(inst) or phys.get(inst) or {}
        rr = [r for r in rows_lat if r["inst"] == inst and (pin == "*" or r["pin"] == pin)]
        for r in rr or [dict(pin=pin, rise_ps=None, basis="")]:
            row = dict(base, path=path, owner_class=owner_class(tp) if tp else "GROUP", port=port, tap=tp.get("name", ""),
                       inst=inst, module=core.get("module", ""), pin=r["pin"], tap_ins_TT=round(ins, 2),
                       tap_ins_FF=round(S.core_tap_insertion_ps(tp, "FF"), 2) if tp else None,
                       pin_target_TT=r.get("rise_ps"), pin_basis=r.get("basis", ""), note=note)
            if r.get("rise_ps") is not None:
                row["err_TT"] = round(float(r["rise_ps"]) - ins, 2)
            if core:
                key = core.get("lib")
                if key not in con_cache:
                    con_cache[key] = contract_means(CC, core, root)
                con, src = con_cache[key]
                row["contract_source"] = src
                if con and r["pin"] in con:
                    cm = con[r["pin"]]["corners"]
                    row["contract_TT"], row["contract_FF"] = cm["tt"]["mean_ps"], cm["ff"]["mean_ps"]
                    row["plan_minus_contract_TT"] = round(ins - cm["tt"]["mean_ps"], 2)
                    if tp:
                        row["plan_minus_contract_FF"] = round(S.core_tap_insertion_ps(tp, "FF") - cm["ff"]["mean_ps"], 2)
                        tap_con.setdefault(tp.get("name"), (cm["tt"]["mean_ps"], cm["ff"]["mean_ps"]))
            if path == "signed_mean" and row.get("err_TT") is None:
                row["err_TT"] = 0.0     # gen_phys refuses a signed-mean kit whose tap differs from the selected mean
            out.append(row)
    if path in ("legacy", "ERROR") and ck.get("core_taps") == "early":
        w = signed_whatif(GP, P, tn, root, tap_con)
        for row in out:
            row["signed_whatif"] = w
    return out


def census(die, plan, root, tools, types="*"):
    for p in (str(tools),):
        if p not in sys.path:
            sys.path.insert(0, p)
    import schema as S
    import gen_phys as GP
    import core_clock_contract as CC
    raw, sha = read_plan(plan)
    P = S.Plan(raw, plan)
    root = Path(root) if root else tree_root(plan)
    if root:
        os.environ["OT_REPO_ROOT"] = str(root)
    placed = {p.get("type") for p in raw.get("partitions") or []}
    globs = [g for g in types.split(",") if g]
    rows = []
    for tn in sorted(P.types):
        if not any(fnmatch.fnmatchcase(tn, g) for g in globs):
            continue
        try:
            rows += type_rows(die, sha, P, tn, root, GP, S, CC, placed)
        except Exception as e:  # noqa: BLE001
            rows.append(dict(die=die, plan_sha12=sha, type=tn, path="ERROR", note=f"{type(e).__name__}: {str(e)[:200]}"))
    return rows


def summary(rows):
    """per (die, type): path, owner classes, worst |err_TT|, W_extra -- the lines to post."""
    by = {}
    for r in rows:
        k = (r["die"], r["type"])
        s = by.setdefault(k, dict(die=r["die"], type=r["type"], placed=r.get("placed"), path=r.get("path"), owners=set(),
                                  n=0, err=None, W_extra=r.get("W_extra"), pmc=None, whatif=r.get("signed_whatif")))
        s["owners"].add(r.get("owner_class") or "")
        s["n"] += 1
        e = r.get("err_TT")
        if e is not None and (s["err"] is None or abs(e) > abs(s["err"])):
            s["err"] = e
        m = r.get("plan_minus_contract_TT")
        if m is not None and (s["pmc"] is None or abs(m) > abs(s["pmc"])):
            s["pmc"] = m
    return [dict(v, owners=",".join(sorted(v["owners"]))) for _k, v in sorted(by.items())]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="append", required=True, help="DIE=PLAN.json (repeat or comma-separate)")
    ap.add_argument("--root", action="append", default=[], help="DIE=TREE: view root (default: the tree above physical/)")
    ap.add_argument("--tools", default=str(HERE.parent / "die_plan"))
    ap.add_argument("--types", default="*")
    ap.add_argument("--out", required=True)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    plans = [x.split("=", 1) for p in a.plan for x in p.split(",") if x]
    roots = dict(x.split("=", 1) for x in a.root)
    rows = []
    for die, plan in plans:
        rows += census(die, plan, roots.get(die), a.tools, a.types)
    with open(a.out, "w") as f:
        f.write("\t".join(FIELDS) + "\n")
        for r in rows:
            f.write("\t".join("" if r.get(k) is None else str(r.get(k)) for k in FIELDS) + "\n")
    sm = summary(rows)
    if a.json:
        Path(a.json).write_text(json.dumps(dict(rows=rows, summary=sm), indent=1, default=str) + "\n")
    for s in sm:
        if s["path"] != "signed_mean" or (s["W_extra"] or 0) > 0:
            print(f"CORE-TAP {s['die']} {s['type']} placed={s['placed']} path={s['path']} owners={s['owners']} rows={s['n']} "
                  f"err_TT={s['err']} plan-contract_TT={s['pmc']} W_extra={s['W_extra']}")
    print(f"CORE-TAP-CENSUS {len(sm)} types with core taps, {sum(s['path'] == 'legacy' for s in sm)} legacy, "
          f"{sum(s['path'] == 'ERROR' for s in sm)} error, {sum((s['W_extra'] or 0) > 0 for s in sm)} W_extra>0 -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
