#!/bin/bash
# S81/SVCG face_guard (gh_* 2-beat fold pins) + yosys cell delta of dsdv_svc_sx: FH = 0 (full-width fold faces) vs FH
# pairs; closed relay stations dsfd_dvrly_276_* + the hardened half row dsdv_svc_sx_hrow are black boxes (macros in the kit)
set -e
W=/srv/opentallas-scratch2/claude/wt/s81-svcg; O=/srv/opentallas-scratch2/claude/s81-svcg/fg
mkdir -p $O; cd $W
D=rtl/dsrom_sys/s81_dv/svc_rs
run() {  # name FH_GO FH_GI : a pure-wire wrapper top fixes the parameters (yosys hierarchy -chparam asserts here)
  n=$1; go=$2; gi=$3
  python3 - $O/$n.sv $go $gi <<'PW'
import sys
out, go, gi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); F = "nesw"
n = out.rsplit("/", 1)[1][:-3]
P = ["input wire ck", "input wire rst", "input wire [3:0] sid", "input wire l_v", "input wire [2131:0] l_d",
     "input wire [3:0] gi_v", "input wire [4*2132-1:0] gi_d", "output wire [3:0] go_v", "output wire [4*2132-1:0] go_d",
     "input wire [3:0] si_v", "input wire [4*1076-1:0] si_d", "output wire [3:0] so_v", "output wire [4*1076-1:0] so_d",
     "output wire rt_v", "output wire [2131:0] rt_d", "output wire t_v", "output wire [19:0] t_tag", "output wire [127:0] t_y",
     "output wire [3:0] t_f", "output wire fault"]
A = []
for f in range(4):
    if gi >> f & 1: P.append(f"input wire [1067:0] gh_i_{F[f]}"); A.append(f"assign ghi[{1068*f+1067}:{1068*f}] = gh_i_{F[f]};")
    else: A.append(f"assign ghi[{1068*f+1067}:{1068*f}] = 1068'd0;")
    if go >> f & 1: P.append(f"output wire [1067:0] gh_o_{F[f]}"); A.append(f"assign gh_o_{F[f]} = gho[{1068*f+1067}:{1068*f}];")
c = ", ".join(f".{x}({x})" for x in ["ck", "rst", "sid", "l_v", "l_d", "gi_v", "gi_d", "go_v", "go_d", "si_v", "si_d", "so_v",
                                      "so_d", "rt_v", "rt_d", "t_v", "t_tag", "t_y", "t_f", "fault"])
open(out, "w").write(f"module sxw_{n} (" + ",\n  ".join(P) + ");\n  wire [4*1068-1:0] ghi, gho;\n  " + "\n  ".join(A) +
    f"\n  dsdv_svc_sx #(.FH_GO(4'd{go}), .FH_GI(4'd{gi})) u ({c}, .gh_i(ghi), .gh_o(gho));\nendmodule\n")
PW
  { echo "read_verilog -sv -lib -DSYNTHESIS -I$D rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv"
    echo "read_verilog -sv -lib -DSYNTHESIS -I$D $D/dsdv_svc_sx_hrow.sv"
    echo "read_verilog -sv -DSYNTHESIS -I$D $D/dsdv_svc_sx.sv"
    echo "read_verilog -sv $O/$n.sv"
    echo "hierarchy -check -top sxw_$n"
    echo "synth -top sxw_$n"
    echo "flatten"
    echo "opt_clean -purge"
    echo "tee -o $O/$n.stat stat"
    echo "write_verilog -noexpr -noattr $O/$n.v"; } > $O/$n.ys
  docker run --rm --name oth-s81svcg-fg-$n-$$ -m 16g -u $(id -u):$(id -g) -v $W:$W -v $O:$O -w $W openroad/orfs:asap7lock \
    /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l $O/$n.log -s $O/$n.ys
}
run fh00 0 0
run fh11 1 1
run fh44 4 4
run fh01 1 0
run fh40 0 4
python3 - <<PY
import sys, json, re
sys.path.insert(0, "tools/die_plan")
import face_guard as G
out = {}
for n in ["fh11", "fh44", "fh01", "fh40"]:
    r = G.guard(open("$O/%s.v" % n).read(), "sxw_" + n, skip_re=r"^(?!gh_).*")
    out[n] = dict(verdict=r["verdict"], checked=r["checked"], ok=r["ok"], fail_counts=r["fail_counts"],
                  fails={k: v[:8] for k, v in r["fails"].items()})
    print("FACE_GUARD", n, r["verdict"], "bits", r["checked"], "ok", r["ok"], "fails", r["fail_counts"])
json.dump(out, open("$O/face_guard.json", "w"), indent=1)
def cells(n):
    tt = open("$O/%s.stat" % n).read()
    tt = tt[tt.rfind("=== sxw_"):]
    tot = int(re.search(r"(\d+) cells", tt).group(1))
    ty = {k: int(v) for v, k in re.findall(r"^\s+(\d+)\s+(\S+)$", tt, re.M) if not k.endswith(("wires", "bits", "ports", "cells"))}
    ff = sum(v for k, v in ty.items() if "DFF" in k)
    st = sum(v for k, v in ty.items() if k.startswith("dsfd_dvrly"))
    return tot, ff, st, ty
base = cells("fh00")
for n in ["fh00", "fh01", "fh40", "fh11", "fh44"]:
    c = cells(n); print("CELLS", n, "total", c[0], "dff", c[1], "stations", c[2], "| delta vs fh00: cells", c[0] - base[0],
                        "dff", c[1] - base[1], "stations", c[2] - base[2], "(station = 276 b closed macro)")
    json.dump(c[3], open("$O/%s_types.json" % n, "w"), indent=1)
PY
