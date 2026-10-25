#!/usr/bin/env python3
"""apply_D.py STAGED_TREE [--mode dfi-core|hbm-lanes] [--pd PD.json ...] [--dry]: KV boot fix D on a staged vehicle tree.

Finding D (TOK-QK/D 10-24): bind.py registered every lane on its partition's DEFAULT clock.  The kvpc <-> HBM PHY lanes
(po / pi / front / return faces), the kvpc ki/ko chain, fo -> fi and ctrl_kc ko are in the HBM domain at BOTH ends (the
leaves' hck / pll_hbm pins), but the pc partitions registered them on the core clock: two bare crossings per lane
(HBM -> core -> HBM).  With the real HBM clock (0.977 GHz) one PHY return reached a controller twice (f_raw).
tools/die_plan/lane_clock_audit.py on kv43abc: 201 such lanes (type level), 81,464 die bits, 0 other bare crossings.

Two design forms (the TOK-QK lead / owner decision 14 picks one):

--mode dfi-core (DEFAULT, owner decision 14: the kvs_pc HBM controller runs on the die clock)
    The HBM PHY's DFI clock is the core clock (ratio-locked 1:1; the PHY's own PLL makes the HBM clock -- industry DFI
    practice, the controller runs on the DFI clock).  Every clk_clk_hbm_<Q> consumer in the bound top (pc*, phy*, hroot
    partitions) is wired to clk_core and the four clk_clk_hbm_<Q> top inputs are removed.  No crossing remains on the die
    for these lanes; no lane register changes.  (An async FIFO on the raw DFI po / pi bus is NOT a valid alternative: the
    write data rides a separate beat WL PHY edges after its column and returns arrive exactly RL PHY edges after RD.)
    The controller calendar constants (RL / WL / timing in DFI clocks) must be compiled for the 833 ps DFI clock: lane
    KV's DFI-ratio check.  Bench consequence: tb_kvslice drives no HBM clock (build.sh defines KV_DFI_CORE).

--mode hbm-lanes (fallback if the DFI-ratio check fails: the controller stays on the HBM clock)
    Same rule as tools/die_plan/bind.py lane_clock "endpoint" (lane KV's rebind uses it natively): every lane register
    of a lane whose launching and capturing leaf ports are all in domain X (lane_clock_audit WRONG_CLOCK) moves to X:
      * ot_dp_st / ot_dp_dly .clk -> the partition's X clock port, .rst_n / .ea -> X's own synchronised reset
        (ot_reset_sync u_rst_sync_<x>, one per partition and domain, as bind.py emits);
      * an in-bus epoch now in X reaches the partition's default-domain epoch check (ot_dp_efault) through ot_dp_lsync
        (2-flop level synchroniser; the epoch is a level); lane data never crosses.
    0 register stages added or removed; widths / expressions unchanged.  Refuses (nothing written) when a register
    carries lanes of different domains or a type lacks the X clock port.

Idempotent in both modes (a fixed tree is left alone).  Prints every change; writes STAGED_TREE/fixD.json.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

H = Path(__file__).resolve().parent
R = H.parents[3]
sys.path.insert(0, str(R / "tools" / "die_plan"))
PD_DEFAULT = R / "physical" / "die_plan" / "qwen_kvsys" / "bind" / "port_domains_kv43.json"
MARK = "TOK-QK/D"


def dfi_core(V, dry):
    p = V / "src" / "bind__rtl" / "qwen_kvsys_bound_top.sv"
    s = p.read_text()
    if f"{MARK} dfi-core" in s:
        print(f"apply_D: {V}: already D (dfi-core); 0 files changed")
        return 0
    qs = sorted(set(re.findall(r"input  wire (clk_clk_hbm_\w+);", s)))
    if not qs:
        sys.exit("apply_D: top has no clk_clk_hbm_<Q> input (nothing written)")
    n = {}
    for q in qs:
        n[q] = len(re.findall(rf"\(\s*{q}\s*\)", s))
        s = re.sub(rf"\(\s*{q}\s*\)", f"(clk_core)", s)
        s = s.replace(f"    input  wire {q};\n", "", 1)
        s = s.replace(f" {q},", "", 1)
    if re.search(r"clk_clk_hbm_[A-Z]", s):
        sys.exit("apply_D: clk_clk_hbm_<Q> still referenced after the rewire (nothing written)")
    s = s.replace("module qwen_kvsys_bound_top (",
                  f"// {MARK} dfi-core (owner decision 14): the HBM PHY DFI clock is the core clock (ratio-locked 1:1, the PHY PLL\n"
                  f"// makes the HBM clock); every former clk_clk_hbm_<Q> consumer (pc*, phy*, hroot) runs on clk_core: no on-die\n"
                  f"// crossing on the kvpc <-> PHY lanes, the ki/ko chain, fo and ctrl_kc ko.\nmodule qwen_kvsys_bound_top (", 1)
    for q in qs:
        print(f"  CHANGED {p.name}: {n[q]} pin(s) {q} -> clk_core; top input {q} removed")
    if dry:
        return 0
    p.write_text(s)
    (V / "bound_top.sha256").write_text(hashlib.sha256(p.read_bytes()).hexdigest() + "\n")
    (V / "fixD.json").write_text(json.dumps(dict(fix="D", mode="dfi-core", clocks=n), indent=1) + "\n")
    print(f"apply_D: dfi-core: {sum(n.values())} clock pins of {len(qs)} HBM clocks -> clk_core; 0 lane registers changed")
    return 0


def lsync_cell():
    import bind
    t = bind.CELLS
    i = t.index("// ot_dp_lsync")
    return t[i:t.index("endmodule", i) + len("endmodule")] + "\n"


def hbm_lanes(V, pds, dry):
    import lane_clock_audit as LA
    import bind
    rd = V / "src" / "bind__rtl"
    A = LA.Audit(rd, pds, [])
    A.analyse()
    lanes = A.lane_ends()
    want, keep = {}, defaultdict(set)
    lanes_fixed = defaultdict(list)
    for (mt, p), r in lanes.items():
        if LA.classify(r) == "WRONG_CLOCK":
            x = next(iter({k for k in r["up"] if k}))
            for (t, e, role) in r["regs"]:
                if role != x:
                    if want.get((t, e), x) != x:
                        sys.exit(f"apply_D: {t}.{e} wanted on {want[(t, e)]} and {x} (nothing written)")
                    want[(t, e)] = x
            lanes_fixed[mt].append(dict(port=p, bits=r["bits"], domain=x,
                                        regs=sorted(f"{t}.{e}" for (t, e, ro) in r["regs"] if ro != x)))
        else:
            for (t, e, role) in r["regs"]:
                keep[(t, e)].add(role)
    bad = [(k, keep[k], v) for k, v in want.items() if keep.get(k) and keep[k] != {v}]
    if bad:
        sys.exit(f"apply_D: registers shared with lanes of another domain (nothing written): {bad[:8]}")
    if not want:
        print(f"apply_D: {V}: no WRONG_CLOCK lane (already D, or nothing to do); 0 files changed")
        return 0
    by_type = defaultdict(dict)
    for (t, e), x in want.items():
        by_type[t][e] = x
    files = {}
    srcs = {}
    for f in rd.glob("*.sv"):
        for m in re.findall(r"^module (\w+)", f.read_text(errors="replace"), re.M):
            srcs[m] = f
    for mt, elems in sorted(by_type.items()):
        f = srcs[mt]
        s = files[f][0] if f in files else f.read_text()
        inv = {}
        for port, role in A.roles[mt].items():
            inv.setdefault(role, port)
        add_decl, add_body, n = [], [], 0
        for e, x in sorted(elems.items()):
            if x not in inv:
                sys.exit(f"apply_D: {mt} has no clock port of domain {x} for {e} (nothing written)")
            ck = inv[x]
            rs = f"rst_n_{bind.sv_id(ck[4:] if ck.startswith('clk_') else ck)}"
            m = re.search(rf"^(    ot_dp_(?:st|dly) #\(.*?\) {re.escape(e)} \(.*?\);)", s, re.M)
            if not m:
                sys.exit(f"apply_D: {mt}: register {e} not found (nothing written)")
            line = m.group(1)
            new = line.replace(".clk(clk)", f".clk({ck})", 1)
            new = new.replace(".rst_n(rst_n)", f".rst_n({rs})", 1).replace(".ea(rst_n)", f".ea({rs})", 1)
            mm = re.search(r"\.eq\((\w+)_eq\)", new) or re.search(r"\.q\(\{(\w+)_eq, ", new)
            if mm and not (e.startswith("u_bin_") and f"u_lpad_{mm.group(1)}" in s):
                nb = mm.group(1)       # the lane epoch leaves the lane domain here -> the default-domain epoch check
                new = new.replace(f"{nb}_eq", f"{nb}_eqd")
                add_decl.append(f"    wire {nb}_eqd;  // {MARK}: lane epoch in {x}")
                add_body.append(f"    ot_dp_lsync #(.W(1), .S(2)) u_eqs_{nb} (.clk(clk), .rst_n(rst_n), .a({nb}_eqd), "
                                f".q({nb}_eq));  // {MARK}: lane epoch -> default-domain epoch check")
            if new == line:
                sys.exit(f"apply_D: {mt}: {e} unchanged by the rewrite: {line[:160]} (nothing written)")
            s = s.replace(line, new + f"  // {MARK}: lane endpoints in {x}", 1)
            n += 1
            if f"wire {rs};" not in s and not any(d.startswith(f"    wire {rs};") for d in add_decl):
                add_decl.append(f"    wire {rs};")
                add_body.insert(0, f"    ot_reset_sync #(.ASYNC_STAGES(2)) u_rst_sync_{rs[6:]} (.clk({ck}), .async_rst_n(arst_n), "
                                   f".sync_rst_n({rs}));  // {MARK}: lane domain {x}")
        anchor = re.search(r"^    ot_reset_sync #\(\.ASYNC_STAGES\(\d+\)\) u_rst_sync \(.*$", s, re.M)
        if not anchor:
            sys.exit(f"apply_D: {mt}: no partition reset synchroniser line (nothing written)")
        s = s[:anchor.start()] + "\n".join(add_decl) + "\n" + anchor.group(0) + "\n" + "\n".join(add_body) + s[anchor.end():]
        files[f] = (s, n)
        print(f"  CHANGED {f.name} ({mt}): {n} lane register(s) re-clocked to {sorted(set(elems.values()))}, "
              f"{len(add_body)} cell(s) added")
    bc = rd / "bind_cells.sv"
    bct = bc.read_text()
    if "module ot_dp_lsync" not in bct:
        k = bct.rfind("`default_nettype wire")
        bct = (bct[:k] + lsync_cell() + bct[k:]) if k >= 0 else bct + lsync_cell()
        files[bc] = (bct, 0)
        print(f"  CHANGED {bc.name}: + ot_dp_lsync")
    if dry:
        print(json.dumps(dict(registers=len(want), types=len(by_type)), indent=1))
        return 0
    for f, (s, _n) in files.items():
        f.write_text(s)
    (V / "fixD.json").write_text(json.dumps(dict(fix="D", mode="hbm-lanes", pd=pds, registers=len(want),
                                                 types=dict(sorted(lanes_fixed.items()))), indent=1) + "\n")
    print(f"apply_D: hbm-lanes: {len(want)} lane registers in {len(by_type)} partition types re-clocked "
          f"({sum(len(v) for v in lanes_fixed.values())} in-bus lanes); 0 register stages added")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("staged")
    ap.add_argument("--mode", choices=("dfi-core", "hbm-lanes"), default="dfi-core")
    ap.add_argument("--pd", action="append")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    V = Path(a.staged).resolve()
    if a.mode == "dfi-core":
        return dfi_core(V, a.dry)
    return hbm_lanes(V, a.pd or [str(PD_DEFAULT)], a.dry)


if __name__ == "__main__":
    sys.exit(main())
