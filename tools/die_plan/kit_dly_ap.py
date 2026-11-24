#!/usr/bin/env python3
"""kit_dly_ap.py -- KV-PV-CAP 11-23 (COORD INV-PER-FLOP ruling 21:2x): alternating-polarity delay lines, kit RTL post-pass at GEN,
opt-in per plan type (partition_types[t].dly_alt_pol = {"min_d": 2}).
Why (measured): ASAP7 has only QN flops (DFFHQNx1), so every Q a flop drives costs an inverter.  A pure flop-to-flop delay line
(ot_dp_dly) therefore maps to D flops + D inverters: kv3_pv_v3 D28 synth 425.6k = 195.8k sequential + 171.7k INV; the D29/A3 pv
types are over the 400k OpenROAD run cap on the same count.  Stored with alternating polarity (stage i holds the data inverted
when i is odd), the inverter between two stages is a double inversion that ABC removes: a D-stage line maps to D flops and 0
inverters (D even) or 1 inverter (D odd).  Measured with the ASAP7 SEQ lib (dfflibmap + abc): 16 x 8 stages 128 flops + 128 INV
-> 128 flops + 0 INV; 16 x 7 stages 112 + 112 -> 112 + 16.
Same cycles, same function: ot_dp_dly_ap #(.W, .D) is cycle-exact to ot_dp_dly #(.W, .D) (q(t) = d(t - D)), reset-less like it,
so bind, bind_latency, LATCHECK and the R8 table are untouched (the pass runs on the kit's staged bound RTL).  LEC is kit RTL vs
netlist, both after this pass.  Instance and register names are unchanged (u_<x>.r[i]), so siting passes keep working.
Selected: every `ot_dp_dly` / `ot_dp_dly_keep` instance of the staged *_bound.sv files with D >= min_d (default 2) -> ot_dp_dly_ap /
ot_dp_dly_keep_ap (keep on the stage flops instead of the stage wires, so tail copies stay separate and lose the inverter too).
D = 1 lines (no inner hop) are left as bound.
Hold: the inverter gave a same-tap zero-logic pair about 7 ps of FF hold (35 + 7 - 2 = 40 ps, gen_phys.dly_lockup_r2r_margin);
without it about 33 ps, still >= 0 at the hold gate.  A type that uses this keeps its r2r repair target below that
(budgets.r_dly_lockup.<base>.r2r_margin_ps), or the pre-route rr pass would pad every pair back.
Usage: kit_dly_ap.py BOUND.sv [--min-d 2] [--out OUT.sv]"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kit_zl_lockup import instances  # noqa: E402

AP_MODULE = """
// KV-PV-CAP kit_dly_ap.py: ot_dp_dly with alternating stage polarity (cycle-exact to ot_dp_dly; no inverter between stages on
// QN-only flop libraries).  Stage i holds d(t - i - 1), inverted when i is odd.
module ot_dp_dly_ap #(parameter integer W = 1, parameter integer D = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    reg [W-1:0] r [0:D-1];
    integer i;
    always @(posedge clk) begin
        r[0] <= d;
        for (i = 1; i < D; i = i + 1) r[i] <= ~r[i-1];
    end
    assign q = (D % 2 == 0) ? ~r[D-1] : r[D-1];
endmodule
"""
AP_KEEP_MODULE = """
// KV-PV-CAP kit_dly_ap.py: ot_dp_dly_keep at alternating polarity.  The keep sits on the stage flops (the process), not on the
// stage wires: a kept wire is a flop Q, which a QN-only library can only make with an inverter; kept flops still stop Yosys
// from folding two tail copies of one trunk (measured: 2 x 16 x 8 copies stay 256 flops, 0 inverters).
module ot_dp_dly_keep_ap #(parameter integer W = 1, parameter integer D = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    reg [W-1:0] r [0:D-1];
    integer i;
    (* keep *) always @(posedge clk) begin
        r[0] <= d;
        for (i = 1; i < D; i = i + 1) r[i] <= ~r[i-1];
    end
    assign q = (D % 2 == 0) ? ~r[D-1] : r[D-1];
endmodule
"""
DEFAULTS = dict(min_d=2)


def cfg_of(t):
    """plan partition_types[t].dly_alt_pol -> config (absent / false -> None; true -> defaults)"""
    v = (t or {}).get("dly_alt_pol")
    if not v:
        return None
    return dict(DEFAULTS, **(v if isinstance(v, dict) else {}))


def _param(params, key, default=1):
    m = re.search(r"\.%s\(\s*(\d+)\s*\)" % key, params)
    return int(m.group(1)) if m else default


def apply(txt, min_d=2):
    """-> (new text, stats).  Renames selected ot_dp_dly instances to ot_dp_dly_ap and appends the cell once."""
    if "module ot_dp_dly_ap" in txt or "module ot_dp_dly_keep_ap" in txt:
        raise ValueError("kit_dly_ap: file already carries ot_dp_dly_ap (pass applied twice)")
    edits, st = [], dict(selected=0, keep_selected=0, bits=0, stages=0, inv_removed_est=0, kept_d1=0)
    for mt, params, name, s, e, lp in instances(txt):
        if mt not in ("ot_dp_dly", "ot_dp_dly_keep"):
            continue
        w, d = _param(params, "W"), _param(params, "D")
        if d < max(2, min_d):
            st["kept_d1"] += 1
            continue
        k = txt.find(mt, s, lp)
        if k < 0 or not re.fullmatch(r"\s*", txt[s:k]) or not re.match(mt + r"\s*#", txt[k:]):
            raise ValueError(f"kit_dly_ap: unexpected instance text at {name}")
        edits.append((k, mt))
        st["selected" if mt == "ot_dp_dly" else "keep_selected"] += 1
        st["bits"] += w
        st["stages"] += w * d
        st["inv_removed_est"] += w * (d if d % 2 == 0 else d - 1)
    out = txt
    for k, mt in sorted(edits, reverse=True):
        out = out[:k] + mt + "_ap" + out[k + len(mt):]
    if edits:
        out = out.rstrip("\n") + "\n" + AP_MODULE + AP_KEEP_MODULE
    return out, st


def apply_kit(rtl_dir, cfg):
    """gen_phys entry (partition_types[t].dly_alt_pol): every staged *_bound.sv; in place (tmp + rename) -> {file: stats}"""
    out = {}
    for f in sorted(Path(rtl_dir).glob("*_bound.sv")):
        src = f.read_text()
        if "ot_dp_dly" not in src:
            continue
        txt, st = apply(src, min_d=int(cfg.get("min_d", 2)))
        if txt != src:
            tmp = f.with_name(f.name + ".dap_tmp")
            tmp.write_text(txt)
            tmp.replace(f)
        out[f.name] = st
    return out


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        raise SystemExit(__doc__)

    def opt(k, d=None):
        return argv[argv.index(k) + 1] if k in argv else d
    src = Path(argv[0])
    txt, st = apply(src.read_text(), min_d=int(opt("--min-d", 2)))
    if opt("--out"):
        Path(opt("--out")).write_text(txt)
    print(json.dumps(st))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
