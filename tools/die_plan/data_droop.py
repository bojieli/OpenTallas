#!/usr/bin/env python3
"""DATA DROOP DERATE per class (METHODOLOGY 12.4a b2, OWNER 10-27 ~18:1x; SPICE basis lane LIB-VDROOP-CHECK).

At the 35 mV die PG budget (TT 0.700 -> 0.665 V; FF -5 %) die-level STA charges DATA paths a LATE derate per class:
  logic  RVT logic cells + flop clk->Q             TT +10 %   FF +8 %   (SPICE: 10-stage RVT chain +9.4/+9.9 %, DFF
                                                                       clk->QN +8.9 %; FF chain +7.7/+8.2 %)
  wire   wire/repeater segments (M8/M9 repeated)  TT +5 %    FF +4 %   (SPICE: 405-um M8 BUFx12f stage +5.0/+4.7 %;
                                                                       FF +3.7/+3.5 %)
replacing the flat +5.1 % (die_ci_margins.json ir: 5 % drop x alpha-power sensitivity 1.022) data term.
  * SETUP ONLY: a late derate on the data arrival.  It is never credited to hold (no data droop speed-up credit; the
    early data derate stays as it was).
  * The CLOCK keeps the shared-droop rule (12.4a b1: differential only, 0 inside one mesh / PDN region) -- not here.
  * Core sign-off (signoff.py) is unchanged (60 ps uncertainty covers core-internal droop); signoff.py droop-check
    reports a 0.665 V re-time of a core as INFO only.

Modes (die_sta_related.py --data-droop, die_ci margins data_droop.mode):
  class  the owner table above (default for die-level gate numbers)
  flat   the old stated term: every data cell +ir (5.1 %) late, both classes the same (control / reproduction)
  none   no data droop term (byte-identical pre-b2 die_sta_related output)

CLASSIFICATION (netlist + SPEF): a cell instance is WIRE class when it is a repeater -- a buffer / inverter / hold
buffer master (wire_class.cells_re, default ^(BUF|INV|HB)) -- whose DRIVEN net (SPEF *D_NET with *I inst:pin O) has a
total net capacitance >= wire_class.min_wire_cap_ff (default 40 fF ~ 200 um of M8/M9 at ~0.2 fF/um = half of a 405-um
repeated stage, the SPICE wire-dominated vehicle).  Every other cell is LOGIC class (incl. flops: clk->Q).  The SPEF
carries no layer, so 'routed on M8/M9' is proxied by the driven wire load; a repeater on a short net stays logic (the
more pessimistic class).

    data_droop.py classify --netlist 6_final.v --spef 6_final.spef [--margins die_ci_margins.json] [--out cls.json]
    data_droop.py table [--margins ...]
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODES = ("class", "flat", "none")
DEFAULT = {
    "mode": "class",
    "budget_mv": 35.0,
    "late_frac": {"logic": {"TT": 0.10, "FF": 0.08}, "wire": {"TT": 0.05, "FF": 0.04}},
    "setup_only": True,
    "wire_class": {"cells_re": "^(BUF|INV|HB)", "min_wire_cap_ff": 40.0},
}


STATED_IR = {"vdd_v": 0.70, "vdd_drop_frac": 0.05, "vt_v": 0.25, "alpha": 1.3, "pdnsim": None}


def margins(path=None):
    """die_ci_margins.json (or path); a standalone kit bundle without it gets the stated ir + the b2 DEFAULT block."""
    p = Path(path or HERE / "die_ci_margins.json")
    if path is None and not p.is_file():
        return {"ir": dict(STATED_IR), "data_droop": json.loads(json.dumps(DEFAULT))}
    return json.loads(p.read_text())


def block(m):
    """the data_droop block of a margins dict (DEFAULT when the margins predate 12.4a b2)."""
    b = json.loads(json.dumps(DEFAULT))
    b.update(m.get("data_droop") or {})
    return b


def flat_frac(m):
    """the old stated data term: vdd_drop_frac x alpha-power sensitivity (die_ci.ir_factor - 1, = 0.0511)."""
    ir = m["ir"]
    v, vt, a = ir.get("vdd_v", 0.7), ir["vt_v"], ir["alpha"]
    drop = ir["vdd_drop_frac"]
    if (ir.get("pdnsim") or {}).get("worst_drop_mv") is not None:
        drop = ir["pdnsim"]["worst_drop_mv"] / 1000.0 / v
    return round(drop * (a * v / (v - vt) - 1.0), 4)


def fracs(m, mode, corner):
    """{'logic': f, 'wire': f} late fraction of a data cell delay at corner (SS -> the TT row, information only)."""
    if mode not in MODES:
        raise SystemExit(f"data_droop: mode {mode!r} not in {MODES}")
    if mode == "none":
        return {"logic": 0.0, "wire": 0.0}
    if mode == "flat":
        f = flat_frac(m)
        return {"logic": f, "wire": f}
    b = block(m)
    c = corner.upper() if corner.upper() in ("TT", "FF") else "TT"
    out = {k: float(b["late_frac"][k][c]) for k in ("logic", "wire")}
    if min(out.values()) < 0:
        raise SystemExit("data_droop: negative late fraction would relax setup")
    return out


# ------------------------------------------------------------------- die_sta_related endpoint models (zero-logic pairs)
def launch_data_ps(model):
    """data part of a launch endpoint arc (ps), all LOGIC class: the declared register clk->Q (seam-wire load folded in
    as driver load) or kit clk->q; a core ETM clk->out minus the core's own max clock insertion (the clock part keeps
    the shared-droop rule)."""
    etm = model.get("etm")
    if etm:
        ck = (etm.get("clock_tree_path_ps") or {}).get("max_clock_tree_path", 0.0)
        return max(0.0, float(model["clkq_max"]) - float(ck))
    return max(0.0, float(model["clkq_max"]))


def capture_data_ps(model):
    """data part of a capture endpoint (ps): a core ETM input setup constraint + its min clock insertion = the core's
    internal input data path (+ flop setup, a <=1.4 ps droop term per SPICE, kept: conservative); a kit setup_ps
    as declared (positive part); the declared bare register: 0 (setup change at 35 mV <= 1.4 ps, LIB-VDROOP)."""
    etm = model.get("etm")
    if etm:
        ck = (etm.get("clock_tree_path_ps") or {}).get("min_clock_tree_path", 0.0)
        return max(0.0, float(model["setup"]) + float(ck))
    if model.get("name", "").startswith("kit:"):
        return max(0.0, float(model["setup"]))
    return 0.0


def model_late_ps(model_a, model_b, fr):
    """setup penalty (ps) of one launch x capture endpoint combination; wire-class segments of a model (kit
    'wire_max_ps', repeated die stages) take the wire fraction."""
    w = float(model_a.get("wire_max_ps", 0.0)) + float(model_b.get("wire_in_ps", 0.0))
    return fr["logic"] * (launch_data_ps(model_a) + capture_data_ps(model_b)) + fr["wire"] * w


# ------------------------------------------------------------------------------------- netlist + SPEF classification
_INST = re.compile(r"^\s*([A-Za-z_][\w$]*)\s+(\\\S+|[A-Za-z_][\w$.\[\]]*)\s*\(", re.M)
_KW = {"module", "input", "output", "inout", "wire", "reg", "assign", "endmodule", "supply0", "supply1", "parameter",
       "localparam", "always", "initial", "tri", "logic"}


def _canon(n):
    n = n.strip()
    if n.startswith("\\"):
        n = n[1:]
    return n.replace("\\", "")


def netlist_cells(path):
    """{instance: master} of a flat structural Verilog netlist (all modules; the routed 6_final.v is flat)."""
    out = {}
    for m in _INST.finditer(Path(path).read_text(errors="replace")):
        cell, inst = m.group(1), m.group(2)
        if cell in _KW:
            continue
        out[_canon(inst)] = cell
    return out


_CU = {"PF": 1e3, "FF": 1.0, "NF": 1e6, "UF": 1e9}


def spef_drivers(path):
    """[(net, total C fF, [(inst, pin) driver connections])] of every SPEF *D_NET (name map resolved)."""
    nmap, unit, out = {}, 1.0, []
    cur = None
    sec = None
    with open(path, errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("//"):
                continue
            if s.startswith("*C_UNIT"):
                p = s.split()
                unit = float(p[1]) * _CU[p[2].upper()]
                continue
            if s.startswith("*NAME_MAP"):
                sec = "map"
                continue
            if sec == "map" and s.startswith("*") and len(s.split()) == 2 and not s.startswith("*D_NET") \
                    and s.split()[0][1:].isdigit():
                k, v = s.split()
                nmap[k] = _canon(v)
                continue
            if s.startswith("*D_NET"):
                sec = "net"
                p = s.split()
                name = nmap.get(p[1], _canon(p[1]))
                cur = (name, float(p[2]) * unit, [])
                out.append(cur)
                continue
            if s.startswith("*CONN"):
                sec = "conn"
                continue
            if s.startswith("*CAP") or s.startswith("*RES") or s.startswith("*END"):
                sec = "net" if not s.startswith("*END") else None
                continue
            if sec == "conn" and s.startswith("*I"):
                p = s.split()
                if len(p) >= 3 and p[2] == "O":
                    ref = p[1]
                    if ":" in ref:
                        i, pin = ref.rsplit(":", 1)
                        i = nmap.get(i, _canon(i)) if i.startswith("*") else _canon(i)
                        cur[2].append((i, pin))
    return out


def classify(netlist, spef, m=None):
    """{'wire': sorted instances, 'n_cells', 'n_wire', 'n_logic', 'rule'} (see module docstring)."""
    b = block(m or margins())
    rx = re.compile(b["wire_class"]["cells_re"])
    cmin = float(b["wire_class"]["min_wire_cap_ff"])
    cells = netlist_cells(netlist)
    wire = set()
    for _net, c_ff, drv in spef_drivers(spef):
        if c_ff < cmin:
            continue
        for inst, _pin in drv:
            mstr = cells.get(inst)
            if mstr and rx.search(mstr):
                wire.add(inst)
    return dict(wire=sorted(wire), n_cells=len(cells), n_wire=len(wire), n_logic=len(cells) - len(wire),
                rule=dict(cells_re=b["wire_class"]["cells_re"], min_wire_cap_ff=cmin,
                          basis="METHODOLOGY 12.4a b2: repeater master driving >= min_wire_cap_ff of wire = wire class"))


def _tcl_name(n):
    """OpenSTA get_cells pattern of one exact instance name: glob brackets escaped, braced for Tcl."""
    return "{" + n.replace("[", "\\[").replace("]", "\\]") + "}"


def derate_tcl(fr, wire_insts=(), base_late=1.0, chunk=500):
    """OpenSTA lines: LATE data cell derate base_late x (1 + logic) on every cell, then base_late x (1 + wire) on the
    wire-class instances (OpenSTA object form; the later, more specific setting wins).  Clock and early derates are
    not touched here (shared clock droop; no hold credit)."""
    lines = [f"set_timing_derate -late -data -cell_delay {base_late * (1.0 + fr['logic']):.4f}"]
    wl = list(wire_insts)
    for i in range(0, len(wl), chunk):
        objs = " ".join(_tcl_name(x) for x in wl[i:i + chunk])
        lines.append(f"set_timing_derate -late -data -cell_delay {base_late * (1.0 + fr['wire']):.4f} "
                     f"[get_cells -quiet [list {objs}]]")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("classify")
    c.add_argument("--netlist", required=True)
    c.add_argument("--spef", required=True)
    c.add_argument("--margins")
    c.add_argument("--out")
    t = sub.add_parser("table")
    t.add_argument("--margins")
    a = ap.parse_args(argv)
    m = margins(a.margins)
    if a.cmd == "classify":
        r = classify(a.netlist, a.spef, m)
        txt = json.dumps(r, indent=1) + "\n"
        if a.out:
            Path(a.out).write_text(txt)
        print(json.dumps({k: v for k, v in r.items() if k != "wire"}))
        return 0
    print(json.dumps({md: {c_: fracs(m, md, c_) for c_ in ("TT", "FF")} for md in MODES}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
