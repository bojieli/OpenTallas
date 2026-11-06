#!/usr/bin/env bash
# HBM-FORM-SPLIT part 29 bench: the real COLLQ bench (tb_hgi_coll_gq: 4 quadrants, F20 programmes, plain + QBG gather, golden VM images) with a shadow split
# composition bound beside each ot_hgi_coll_gq_issue. Shadow sees the same inputs; its outputs must equal the uncut issue's delayed 2 edges (plan pin faces of the issue tile),
# on every bit every edge after reset. run_p29.sh OUT: MUT 0 PASS (shadow clean, COLLQ PASS, quantisers fired), MUT 11/12/13 must report mismatches.
set -u
OUT=$(realpath -m "$1"); H=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd $H/../../../.. && pwd); cd $ROOT; mkdir -p $OUT
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}
P=rtl/hbm_accel/generic/collective/p2p; R=rtl/hbm_accel/cores_split/reform_1105s/gq; BB=physical/die_plan/hbm/over_cap_split/reform_1103
XQ=physical/hbm_xp_aq_tree13_1014; DLY=rtl/hdc/ot_hdc_delay.sv; REL=rtl/lib/ot_rst_relay.sv; TGT=rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
python3 tools/hgi_sim/collq_gather_1018.py vectors $OUT/vec > $OUT/vec.log 2>&1 || { tail -3 $OUT/vec.log; exit 1; }
python3 -I $BB/facewrap.py --top ot_hgi_coll_gqi_issue --clk-re '^clk$' --rst-re '^rst_n$' --out $OUT/issue__fs.sv $R/ot_hgi_coll_gqi_issue.sv $TGT $REL > $OUT/issue.json || exit 1
python3 -I $BB/facewrap.py --top ot_hgi_gq_aq_tile --clk-re '^clk$' --rst-re '^rst_n$' --out $OUT/aq__fs.sv $R/ot_hgi_gq_aq_tile.sv $XQ/ot_hbm_xp_aq_scale13.sv $DLY $REL > $OUT/aq.json || exit 1
python3 -I - $H/gq_issue__comp.sv $OUT/shadow.sv <<'P'
import re,sys
s=open(sys.argv[1]).read(); h=s[s.index("(\n    input  wire"):s.index(");\n    wire v0")+1]
ports=[]
for l in h.split("\n"):
    m=re.match(r"\s*(input|output)\s+(?:wire|reg)?\s*(\[[^\]]*\])?\s*(.*)",l)
    if m: ports+=[(m[1],m[2] or "",p.strip()) for p in m[3].split(",") if p.strip()]
outs=[p for p in ports if p[0]=="output"]
L=["`default_nettype none","module gq_shadow ("]+[",\n".join(f"    input wire {w} {n}" for d,w,n in ports)]+[");"]
for d,w,n in outs: L.append(f"    wire {w} d_{n}; reg {w} r1_{n}, r2_{n};")
conn=", ".join(f".{n}({('d_'+n) if d=='output' else n})" for d,w,n in ports)
L.append(f"    ot_hgi_gqi__comp #(.MUT(`OT_MUT)) u_d ({conn});")
L.append("    integer errs = 0, checks = 0, cyc = 0, q_fired = 0, aq_ref = 0; integer v0_only = 0;\n    always @(posedge clk) begin")
for d,w,n in outs: L.append(f"        r1_{n} <= {n}; r2_{n} <= r1_{n};")
L.append("        cyc <= rst_n ? cyc + 1 : 0;\n        if (u_d.vo0 || u_d.vo1) q_fired <= q_fired + 1; if (u_d.v0 && !u_d.v1) v0_only <= v0_only + 1;\n        if (cyc > 200) begin checks <= checks + 1;")
for d,w,n in outs: L.append(f"            if (r2_{n} !== d_{n}) begin errs <= errs + 1; if (errs < 5) $display(\"GQSHADOW MISMATCH %m cyc=%0d {n}\", cyc); end")
L.append("        end\n    end\n    final $display(\"GQSHADOW %m checks=%0d errs=%0d q_fired=%0d v0_only=%0d\", checks, errs, q_fired, v0_only);\nendmodule")
L.append("bind ot_hgi_coll_gq_issue gq_shadow u_shadow ("+", ".join(f".{n}({n})" for d,w,n in ports)+");")
L.append("`default_nettype wire")
open(sys.argv[2],"w").write("\n".join(L)+"\n")
P
LIB=("$P/ot_hgi_coll_gq.sv" "$P/ot_hgi_coll_ring_ag.sv" "$P/ot_hgi_coll_ring_ag_lane.sv" "$P/ot_hgi_coll_ring_b_stop.sv"
     "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv"
     rtl/hbm_accel/index/quad_1017/ot_hbm_idx_vm_share2_static.sv $TGT $REL $XQ/ot_hbm_xp_aq_tree13.sv $XQ/ot_hbm_xp_aq_scale13.sv
     rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv $DLY rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
FL=(--binary --timing -O2 -j 12 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style)
one() { M=$1; D=$OUT/m$M; "$V" "${FL[@]}" -DOT_MUT=$M -GVEC="\"$OUT/vec\"" --top-module tb_hgi_coll_gq --Mdir $D $P/tb_hgi_coll_gq.sv "${LIB[@]}" $R/ot_hgi_coll_gqi_issue.sv $R/ot_hgi_gq_aq_tile.sv $H/gq_issue__comp.sv $OUT/issue__fs.sv $OUT/aq__fs.sv $OUT/shadow.sv rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192_face/ot_hbm_face_reg.sv > $OUT/b$M.log 2>&1 || { tail -12 $OUT/b$M.log | cut -c1-220; return 2; }
  $D/Vtb_hgi_coll_gq > $OUT/s$M.log 2>&1; echo "MUT $M: $(grep -E '^COLLQ' $OUT/s$M.log | tail -1 | cut -c1-150)"; grep -E 'GQSHADOW .*checks' $OUT/s$M.log | cut -c1-120; grep -m3 'GQSHADOW MISMATCH' $OUT/s$M.log | cut -c1-120; }
for m in 0 11 12 13 14 15; do one $m & done; wait
