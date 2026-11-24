"""adv_unseated_chain.py -- PRECHECK ADV-UNSEATED-CHAIN (COORD 11-24, FABLE-RC-QC 17187dad; report only).

ADV-SEATLINE judges registers that HAVE a plan seat (internal_stations regs_um / ft slots).  QC cbf_q11 lanes carry fixed_cycles register stages
whose registers have NO plan seat at all: lane c_W5_bf_11__a00 y_o22 -> na_i00 fixed 4 (514 bits) while y_o22 has no internal_stations row.
The kit places those stages itself, inside the source partition near the source pin window.

FORM (revised after FABLE-RC-QC 17187dad): the unseated chains are NOT plan lanes (lane fixed_cycles = source + destination stations, all seated); they are
ot_dp_dly #(.W, .D>=2) delay pipes the bind instantiates in the type's BOUND module (u_d<D>_<core>_<pin>): this check scans the bound RTL
(bind_out= / OT_ADV_BIND_OUT / plan-of-record sibling, as ADV-GHOST-MACRO).  The pin window of one pipe is not mapped to its pin: the LENIENT window
is the widest bus window of the type.  (The original plan-lane reading below found nothing on cbf_q11.)

Per lane (old reading): unseated stages u = fixed_cycles - (regs_um stations of the source bus row + of the destination bus row) when u >= 2 (a multi-stage
chain); bits = u x lane width; the window = the source bus' pin window (bus.window_um: its length L along the face) and the corridor depth
DEPTH_UM (17 um: the strip depth QC saw packing the sle_ctl hc1_o seat; my parameter, not a plan rule).
  NEED   cells = bits x (1 + LOGIC_X) x CELL_UM2 / UTIL  um2 (LOGIC_X 0 for a pure relay chain is the lower bound; default 1.0 as in ADV-SEATLINE)
  FLAG AREA    need > L x DEPTH_UM
  FLAG NARROW  sqrt(need) > L                        (the sqrt rule: the window is narrower than a square of the needed area)
Per type: chains flagged / chains, worst bits, need vs window.  findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

CHECK = "ADV-UNSEATED-CHAIN"
LOGIC_X = 1.0
CELL_UM2 = 0.25
UTIL = 0.6
DEPTH_UM = 17.0
MAX_LINES = 25


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def chain_need_um2(bits, logic_x=LOGIC_X):
    return bits * (1.0 + logic_x) * CELL_UM2 / UTIL


def judge(bits, win_len, depth=DEPTH_UM, logic_x=LOGIC_X):
    """-> (area_flag, narrow_flag, need um2, window um2)"""
    need = chain_need_um2(bits, logic_x)
    return need > win_len * depth, math.sqrt(need) > win_len, need, win_len * depth


DLY_RE = re.compile(r"\bot_dp_dly\s*#\s*\(\s*\.W\(\s*(\d+)\s*\)\s*,\s*\.D\(\s*(\d+)\s*\)\s*\)\s*(\w+)")


def dly_chains(text):
    """[(instance, W, D)] multi-stage ot_dp_dly delay pipes of a bound module body (the kit places their stages itself)"""
    return [(n, int(w), int(d)) for w, d, n in DLY_RE.findall(text) if int(d) >= 2]


def _findings(raw, plan_path, tree=None, **kw):
    """RTL form: the unseated chains of cbf_q11 are ot_dp_dly #(.W(514), .D(8)) delay pipes in the BOUND RTL, not plan lanes / stations."""
    depth = float(kw.get("depth_um") or os.environ.get("OT_ADV_UNSEATED_DEPTH_UM") or DEPTH_UM)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import adv_ghost_macro as G
    types = raw.get("partition_types") or {}
    used = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    bdir, _n = G._choose_bind(raw, plan_path, tree, kw, types)
    if not bdir:
        return [_w("NOT-RUN: no bound RTL (bind_out= / OT_ADV_BIND_OUT; the delay pipes exist only in the bound RTL)")]
    out, nt, nflag, nchain = [], 0, 0, 0
    for tn, t in sorted(types.items()):
        if not isinstance(t, dict) or t.get("hard") is True or (used and tn not in used) or not t.get("module"):
            continue
        pth, _m = G._bound_path(bdir, t["module"], tn)
        if not pth:
            continue
        nt += 1
        ch = dly_chains(Path(pth).read_text(errors="replace"))
        wins = [abs(b["window_um"][1] - b["window_um"][0]) for b in t.get("buses") or [] if isinstance(b, dict) and b.get("window_um")]
        if not ch or not wins:
            continue
        L = max(wins)                      # lenient: the widest pin window of the type (the pipe's own pin is not mapped)
        bad = []
        for n, w, d in ch:
            nchain += 1
            af, nf, need, win = judge(w * d, L, depth)
            if af or nf:
                bad.append((w * d, n, w, d, need, win, nf))
        if bad:
            bad.sort(reverse=True)
            nflag += len(bad)
            x = bad[0]
            out.append((x[0], _w(f"{tn}: {len(bad)} unseated delay pipe(s) over the widest pin window (worst {x[1]}: {x[2]} bits x {x[3]} stages = {x[0]:,} register bits needs {x[4]:.0f} um2 vs "
                                  f"{L:.0f} um x {depth:g} um = {x[5]:.0f} um2" + (", narrower than sqrt(need)" if x[6] else "") +
                                  "); the plan has no seat for these stages, the kit places the stages itself and drops them at the pin column (QC cbf_q11 n_y strip); fix: seat the stages (relay sites) across the channel")))
    out.sort(key=lambda x: -x[0])
    lines = [m for _, m in out[:MAX_LINES]]
    lines.append(_w("summary", f"{len(out)} of {nt} bound types have unseated ot_dp_dly delay pipes (D>=2) needing more than their widest pin window x {depth:g} um ({nflag} of {nchain} pipes); "
                               f"bound RTL {bdir}; window = widest bus window of the type (lenient), depth {depth:g} um and 2x cells are my parameters"))
    return lines


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import json
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], None, bind_out=sys.argv[2] if len(sys.argv) > 2 else None):
        print(ln)
