"""cb_ring_flops.py (QC-CB-GEN-1115): FIRM ring flops of a cb landing band (the n the strip density OT_CLAND_STRIP_DENS and gen_cb_strip.py use).

The plan band record carries only ring_width / width / padded_data_storage_flops (2880 for every ring) and cannot tell the CA variants
apart.  The count is a function of the bound landing instance (ot_dp_clk_landing_cas W, DEPTH ...), so it is MEASURED, not assumed:
  strip_flops  the 'flops' of the kit place log line "OT_CLAND strip density ring:<band>+x+ff...: ..., N flops" (34 rings, 11-15)
  synth_flops  flops of the landing module in the Yosys netlist 1_2_yosys.v (measure_netlist(), run on cbn_q01__cld9ff4c40)
  by_params    the bound RTL instance (module, W, DEPTH) that each class has; cbx_q10 a22_i / bc_i20 / bc_i30 are
               ot_dp_clk_landing_cas W 515/517/517 DEPTH 8 = the cbn_q01 a00_i / bc_i02 instance parameters, whose synth count is measured
Table: tools/die_plan/cb_ring_flops.json.   python3 -I tools/die_plan/cb_ring_flops.py measure NETLIST.v   prints the per-instance synth counts"""
import json
import re
import sys
from pathlib import Path

TABLE = Path(__file__).with_name("cb_ring_flops.json")


def band_class(bn, ring_width):
    if ring_width <= 64 and "serdes" in bn:
        return "serdes_small"
    if bn.startswith("rsf"):
        return "rsf_i"
    if bn.startswith("bc_i"):
        return "bc_i"
    if bn.startswith("nb_i"):
        return "nb_i"
    if re.match(r"^(na_i|a\d+_i)", bn):
        return "na_i"
    return None


def ring_flops(tn, bn, band, table=None):
    """(flops, how) of band bn of type tn; how = 'measured' | 'scaled' (unmeasured serdes flit rings: ring_width/576 of the family bc ring)"""
    t = table or json.loads(TABLE.read_text())
    fam = tn.split("_")[0]
    fam = t["alias"].get(fam, fam)
    rw = band["ring_width"]
    cls = band_class(bn, rw)
    row = t["strip_flops"].get(fam, {})
    if cls in row:
        return float(row[cls]), "measured"
    if cls is None or rw > 64 and "serdes" in bn:
        return float(row["bc_i"]) * rw / 576.0, "scaled"
    raise KeyError(f"no measured ring flops for {tn} {bn} (class {cls}, family {fam})")


def measure_netlist(path):
    """{cland instance suffix: flops} from a Yosys netlist (hierarchical, DFF cells counted recursively through module instances)"""
    txt = Path(path).read_text()
    mods = {}
    for m in re.finditer(r"^module\s+(\S+)\s*\(.*?^endmodule", txt, re.S | re.M):
        body = m.group(0)
        mods[m.group(1).lstrip("\\")] = (len(re.findall(r"^\s*DFF\w*\s", body, re.M)),
                                          [a.lstrip("\\") for a, _ in re.findall(r"^\s+(\\?\S+)\s+(\\?\S+)\s+\(", body, re.M)])

    def tot(n, depth=0):
        if n not in mods or depth > 20:
            return 0
        d, inst = mods[n]
        return d + sum(tot(a, depth + 1) for a in inst)
    out = {}
    for m in re.finditer(r"^\s+(\\?\S+)\s+\\u_bound\.u_cland_(\w+)\s+\(", txt, re.M):
        mod = m.group(1).lstrip("\\")
        if mod in mods:
            out[m.group(2)] = tot(mod)
    return out


if __name__ == "__main__":
    if sys.argv[1] == "measure":
        for k, v in sorted(measure_netlist(sys.argv[2]).items()):
            print(k, v)
