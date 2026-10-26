"""measured per-stage decomposition: cell delay, wire delay, wire cap vs plan segment length."""
import json, sys
sys.path.insert(0, sys.path[0])
from common import *
from pathlib import Path as _P
W = str(_P(__file__).resolve().parents[2] / "qc_su_kits") + "/"
D = str(_P(__file__).resolve().parents[1] / "meas") + "/"
BUILDS = {"prog_r1": (W + "r2/prog_m0.ab.tcl", W + "r2/prog_m0.ab.json", W + "r2/prog_m0.geo"),
          "prog_r3": (W + "r3/out/prog_m0_r3.gate.asbuilt.tcl", W + "r3/out/prog_m0_r3.gate.asbuilt.json", W + "r2/prog_m0.geo"),
          "btab_r4": (W + "r4/btab_m0_r4/btab_ls_k6_L3.gate.asbuilt.tcl", W + "r4/btab_m0_r4/btab_ls_k6_L3.gate.asbuilt.json", W + "r2/btab_m0.geo")}
def main():
  for b, (sp, aj, geo) in BUILDS.items():
    S = parse_spec(sp); A = json.load(open(aj)); seg = A["seg_um"]
    stg = parse_stage(D + b + "/meas_stage_TT.tsv"); nets = parse_nets(D + b + "/netcap_TT.txt")
    # net wire cap vs sum of plan segs per driver net
    kids = {}
    for n, v in list(S["tree"].items()) + list(S["leaves"].items()):
        kids.setdefault(v["par"], []).append(n)
    rows = []
    for drv, ch in kids.items():
        net = "ot_ms_root_n" if drv == "root" else f"ot_ms_{drv}_n"
        L = sum(seg[x] for x in ch)
        cw = nets.get(net, {}).get("cw")
        rows.append((drv, net, len(ch), L, cw, cw / L if cw and L else None))
    cpu = [r[4] / r[3] for r in rows if r[4] and r[3] > 5]
    print(b, "driver nets", len(rows), "wire cap/um plan-seg: mean %.4f min %.4f max %.4f (model c %.4f)" % (sum(cpu)/len(cpu), min(cpu), max(cpu), 0.5*(1.78475e-1+1.64264e-1)*0.9))
    for r in sorted(rows, key=lambda r: -r[3])[:6]:
        print("   ", r[0], "fo", r[2], "plan_um %.1f" % r[3], "cw %.2f" % (r[4] or -1), "c/um %.4f" % (r[5] or -1))

if __name__ == "__main__":
    main()
