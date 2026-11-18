#!/usr/bin/env python3
"""hold_eco_internal.py -- sizing + gate of the post-route INTERNAL-endpoint hold stage (HOLD-FLOW-R 11-16, closure lever 1).

Why: pre-route hold repair closes to 0 on the GRT estimate and extraction then moves short paths by 9-17 ps, so every
route ends with internal FF hold of -9 .. -69 ps on 6 .. 858 endpoints (QC coll_n / W0 / H16 / H17 / P3, HEAD hw4 / host_e,
S81 halves) while those endpoints keep 170-430 ps of TT setup room.  Proven by hand on QC coll_n: 80 HB4 cells at 64 capture
pins, 144 nets re-routed, DRC 0, TT -1.39, FF hold -58.19 -> +0.47.  This file is the generic form.

  plan  ENDPOINTS.tsv OUT.tsv   size the insert per capture pin (selected: slack < 2 ps; sized to +10)
  gate  BEFORE.json AFTER.json  accept / refuse the stage result (DRC 0, TT >= -42, internal FF hold >= 0)

ENDPOINTS.tsv (written by hold_eco_internal_dump.tcl, header line required), tab separated:
  endpoint  startpoint  start_kind  end_kind  ff_hold_slack_ps  tt_setup_slack_ps
kind is reg | port | macro. Timed signal inputs of macros are capture pins too. Optional seventh field `net` identifies
the original capture net, so unmodified siblings of a selected sink can be reported for post-route review. A path that
starts at an input port or ends at an output port is the parent's and never gets a cell (no port-only padding).
OUT.tsv (read by hold_eco_internal_insert.tcl via OT_PRD_HOLD_PLAN): capture_pin<TAB>n_hb4, then a comment trailer.
Sizing: need = target - slack.  One HB4 covers need <= DOUBLE_OVER_PS (25), else ceil(need / HB4_FF_PS) and at least two.
Each HB4 costs HB4_TT_MAX_PS of TT setup.  The count is cut to what the endpoint's TT slack can pay inside TT_FLOOR_PS
(-42, the gate); a cut endpoint is counted as partial, and one that cannot pay even one cell is skipped and listed.
"""
import json
import math
import sys

TARGET_PS = 10.0          # hold repair target (the size each selected endpoint is repaired to); the gate stays FF hold >= 0
SELECT_PS = 2.0           # endpoints selected: FF hold slack below this (failing + a 2 ps guard band), not everything under TARGET_PS
HB4_FF_PS = 29.8         # FF MIN delay of one HB4xp67 (coll_n pilot model 29.81 at the conservative slew domain)
HB4_TT_MAX_PS = 132.8     # TT max delay of one HB4xp67 at the observed slews (coll_n pilot model: 132.796; 171.24 is the slew <= 320 bound)
DOUBLE_OVER_PS = 25.0     # need above this gets two cells at least
MAX_PER_ENDPOINT = 4
TT_FLOOR_PS = -42.0       # gate: routed TT WNS >= -42
CAPTURE_PINS = ("D", "RESETN", "SETN")
# SRAM signal capture pins of the ot_sram_1r1w* macros (the dump labels macro pins "reg"): write data, mask, address and enables.
# lep_pair vE KCRED28 11-18: one of 12 internal ends was u_m/w_addr_in[3] (-2.3 ps) and the whole ECO was refused on it.
SRAM_CAPTURE_PREFIXES = ("wd_in", "w_addr_in", "r_addr_in", "w_mask_in", "w_ce_in", "r_ce_in")
KINDS = ("reg", "port", "macro")
MAX_ABS_SLACK_PS = 1e5      # a row beyond this is a unit error (seconds x1e12 twice), never a real slack
NO_TT_PATH_PS = 1e6         # hold_eco_internal_dump.tcl writes this when the endpoint has no TT path


def capture_pin(endpoint, kind="reg"):
    """A known flop capture pin or an STA-proven macro signal capture."""
    pin = endpoint.rsplit("/", 1)[-1]
    return (kind == "macro" and "/" in endpoint) or pin in CAPTURE_PINS or pin.startswith(SRAM_CAPTURE_PREFIXES)


def need_to_cells(need, hb4_ff=HB4_FF_PS, double_over=DOUBLE_OVER_PS, cap=MAX_PER_ENDPOINT):
    if need <= 0:
        return 0
    n = math.ceil(need / hb4_ff)
    if need > double_over:
        n = max(n, 2)
    return min(max(n, 1), cap)


def read_endpoints(text):
    rows = []
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    if not lines or lines[0].split("\t")[0] != "endpoint":
        raise ValueError("endpoints file needs the header line: endpoint startpoint start_kind end_kind ff_hold_slack_ps tt_setup_slack_ps")
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) not in (6, 7):
            raise ValueError(f"bad endpoint row (6 or 7 tab fields): {ln!r}")
        e, s, sk, ek, ff, tt = f[:6]
        if sk not in KINDS or ek not in KINDS:
            raise ValueError(f"bad kind in {ln!r}")
        ffv, ttv = float(ff), float(tt)
        if not (math.isfinite(ffv) and math.isfinite(ttv)):
            raise ValueError(f"non finite slack in {ln!r}")
        if abs(ffv) > MAX_ABS_SLACK_PS or (abs(ttv) > MAX_ABS_SLACK_PS and ttv != NO_TT_PATH_PS):
            raise ValueError(f"slack outside +-{MAX_ABS_SLACK_PS:g} ps (wrong time unit?) in {ln!r}")
        rows.append(dict(endpoint=e, startpoint=s, start_kind=sk, end_kind=ek, ff=ffv, tt=ttv,
                         net=f[6] if len(f) == 7 else ""))
    return rows


def plan(rows, target=TARGET_PS, select=SELECT_PS, hb4_ff=HB4_FF_PS, hb4_tt=HB4_TT_MAX_PS, tt_floor=TT_FLOOR_PS,
         double_over=DOUBLE_OVER_PS, cap=MAX_PER_ENDPOINT, pad_siblings=True):
    """-> {cells: [(capture_pin, n)], skipped: [(endpoint, reason)], summary}.  The worst path to a pin sets its need."""
    worst = {}
    skipped = []
    for r in rows:
        e = r["endpoint"]
        if r["start_kind"] == "port" or r["end_kind"] == "port":
            skipped.append((e, "port path: the parent's, no cell"))
            continue
        if not capture_pin(e, r["end_kind"]):
            skipped.append((e, "not a supported capture pin (D/RESETN/SETN/SRAM signal inputs)"))
            continue
        if r["ff"] >= select:
            continue
        cur = worst.get(e)
        if cur is None or r["ff"] < cur["ff"]:
            worst[e] = r
    cells = []
    partial = 0
    for e in sorted(worst):
        r = worst[e]
        n = need_to_cells(target - r["ff"], hb4_ff, double_over, cap)
        afford = int(math.floor((r["tt"] - tt_floor) / hb4_tt)) if r["tt"] > tt_floor else 0
        if afford < 1:
            skipped.append((e, f"TT slack {r['tt']:.2f} - 1 x {hb4_tt:g} < {tt_floor:g}"))
            continue
        if afford < n:
            partial += 1
            n = afford
        cells.append((e, n))
    # SHARED NETS (bksel 11-17): re-routing a net after padding some of its sinks shortened it and the unpadded sink lost 14 ps
    # (+10.3 -> -4.1).  Per touched net: pad EVERY capture sink or none.  A sibling gets max(1, cells for its own need), cut to its
    # TT room; one that cannot pay a cell drops the whole net (reported), so nothing is half-padded.
    dropped = []
    if pad_siblings:
        worst_all = {}
        for r in rows:
            e = r["endpoint"]
            if r["start_kind"] == "port" or r["end_kind"] == "port" or not capture_pin(e, r["end_kind"]) or not r.get("net"):
                continue
            if e not in worst_all or r["ff"] < worst_all[e]["ff"]:
                worst_all[e] = r
        sel_net = {e: worst_all[e]["net"] for e, _ in cells if e in worst_all}
        for net in sorted(set(sel_net.values())):
            sibs = sorted(e for e, r in worst_all.items() if r["net"] == net and e not in sel_net)
            add, ok = [], True
            for e in sibs:
                r = worst_all[e]
                afford = int(math.floor((r["tt"] - tt_floor) / hb4_tt)) if r["tt"] > tt_floor else 0
                if afford < 1:
                    ok = False
                    skipped.append((e, f"net {net}: sibling cannot pay one cell (TT {r['tt']:.2f}); the whole net is left unpadded"))
                    break
                add.append((e, min(max(1, need_to_cells(target - r["ff"], hb4_ff, double_over, cap)), afford)))
            if ok:
                cells.extend(add)
            else:
                dropped.append(net)
                gone = [e for e, n_ in cells if sel_net.get(e) == net]
                cells = [(e, n_) for e, n_ in cells if sel_net.get(e) != net]
                for e in gone:
                    skipped.append((e, f"net {net} left unpadded: a sibling sink cannot be padded"))
        cells.sort()
    selected = {e for e, _ in cells}
    touched = {r.get("net") for r in rows if r["endpoint"] in selected and r.get("net")}
    siblings = {}
    for r in rows:
        e = r["endpoint"]
        if (r.get("net") in touched and e not in selected and r["start_kind"] != "port"
                and r["end_kind"] != "port" and capture_pin(e, r["end_kind"])):
            if e not in siblings or r["ff"] < siblings[e]["ff"]:
                siblings[e] = r
    total = sum(n for _, n in cells)
    return dict(cells=cells, skipped=skipped, siblings=list(siblings.values()),
                capture_kinds={r["endpoint"]: r["end_kind"] for r in rows if r["endpoint"] in selected}, summary=dict(
        endpoints=len(cells), hb4=total, partial=partial, skipped=len(skipped), target_ps=target,
        unmodified_touched_siblings=len(siblings), nets_left_unpadded=len(dropped), pad_siblings=pad_siblings,
        touched_net_coverage="reported" if all(r.get("net") for r in rows if r["endpoint"] in selected) else "not_measured",
        worst_ff_ps=min([r["ff"] for r in worst.values()] or [0.0]),
        selected_over_negative=f"{len(cells)} of {sum(1 for r in rows if r['ff'] < 0 and r['start_kind'] != 'port' and r['end_kind'] != 'port')}"))


def write_plan(p, out):
    with open(out, "w") as f:
        f.write("# hold_eco_internal plan: capture_pin\tn_hb4\n")
        for e, n in p["cells"]:
            tag = "\tmacro" if p.get("capture_kinds", {}).get(e) == "macro" else ""
            f.write(f"{e}\t{n}{tag}\n")
        for r in p.get("siblings", []):
            f.write(f"# reroute sibling {r['endpoint']} net={r['net']} ff_ps={r['ff']:.3f}; post-route hold must be measured\n")
        for e, why in p["skipped"]:
            f.write(f"# skipped {e}: {why}\n")
        f.write("# summary " + json.dumps(p["summary"], sort_keys=True) + "\n")


def read_plan(text):
    out = []
    for ln in text.splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        fields = ln.split("\t")
        if len(fields) not in (2, 3) or (len(fields) == 3 and fields[2] != "macro"):
            raise ValueError(f"bad plan row {ln!r}")
        e, n = fields[:2]
        if int(n) < 1 or not capture_pin(e, fields[2] if len(fields) == 3 else "reg"):
            raise ValueError(f"bad plan row {ln!r}")
        out.append((e, int(n)))
    return out


def gate(before, after, tt_floor=TT_FLOOR_PS):
    """before / after: {drc, tt_wns_ps, ff_internal_wns_ps, ff_internal_endpoints}.  -> (ok, [why])"""
    why = []
    if int(after["drc"]) != 0:
        why.append(f"DRC {after['drc']} != 0")
    if float(after["tt_wns_ps"]) < tt_floor:
        why.append(f"TT WNS {after['tt_wns_ps']} < {tt_floor:g}")
    if float(after["ff_internal_wns_ps"]) < 0:
        why.append(f"internal FF hold {after['ff_internal_wns_ps']} < 0 on {after.get('ff_internal_endpoints')} endpoints")
    if before is not None and float(after["ff_internal_wns_ps"]) < float(before["ff_internal_wns_ps"]):
        why.append("internal FF hold got worse")
    return not why, why


def main(argv):
    if len(argv) >= 4 and argv[1] == "plan":
        rows = read_endpoints(open(argv[2]).read())
        p = plan(rows)
        write_plan(p, argv[3])
        print(json.dumps(p["summary"], sort_keys=True))
        return 0
    if len(argv) == 4 and argv[1] == "gate":
        ok, why = gate(json.load(open(argv[2])), json.load(open(argv[3])))
        print("HOLD_ECO_INTERNAL " + ("PASS" if ok else "FAIL " + "; ".join(why)))
        return 0 if ok else 1
    print(__doc__.split("\n\n")[0], file=sys.stderr)
    print("usage: hold_eco_internal.py plan ENDPOINTS.tsv OUT.tsv | gate BEFORE.json AFTER.json", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
