#!/usr/bin/env bash
# S81-BKSEL-RTL 11-25: lockstep bench, dsdv_bk_selids (per-slice cnt / wv / w1v copies) vs the pre-slice module (J9 v2 form, 9617ad7537cc),
# random + directed jobs, MUT 0/1/2, 4 seeds each; a mutant (go = cnt > 1) must FAIL.  usage: run_bk_selids_slice_lock.sh <outdir> <old_ids.sv> [seeds]
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd); O=$1; OLD=$2; SEEDS=${3:-"1 2 3 4"}
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
F=$R/physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_l20s.sv
mkdir -p "$O"; python3 -I - "$F" "$O" <<"PY"
import sys
t=open(sys.argv[1]).read(); o=sys.argv[2]
i=t.index("(* keep_hierarchy = 1 *) module dsdv_bk_selids_sl"); j=t.index("endmodule",t.index("module dsdv_bk_selids #("))+9
open(o+"/new_ids.sv","w").write(t[i:j]+"\n")
open(o+"/mut_ids.sv","w").write((t[i:j]).replace("cnt != 5'd0;","cnt > 5'd1;")+"\n")
PY
cat > "$O/rrd.sv" <<"EOV"
module dsdv_bk_rrd #(parameter integer D = 0) (input wire ck, input wire d, output wire q);
    generate if (D == 0) begin : g_w
        assign q = d;
    end else begin : g_r
        (* keep = "true" *) reg [D-1:0] r;
        always @(posedge ck) r <= (D == 1) ? d : {r[(D > 1 ? D - 2 : 0):0], d};
        assign q = r[D-1];
    end endgenerate
endmodule
EOV
bad=0
for v in new mut; do for m in 0 1 2; do
  [ $v = mut ] && [ $m != 0 ] && continue
  $VL --binary -j "${J:-4}" -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_ids_lock -GMUT=$m -Mdir "$O/obj_${v}$m" "$O/rrd.sv" "$OLD" "$O/${v}_ids.sv" "$R/rtl/dsrom_sys/s81_dv/unit/test/tb_dsdv_bk_selids_slice_lock.sv" > "$O/build_${v}$m.log" 2>&1 || { echo BUILD_FAIL $v$m; bad=1; continue; }
  for s in $SEEDS; do
    L=$("$O/obj_${v}$m/Vtb_ids_lock" +seed=$s | grep LOCKSTEP); echo "$v $L"
    if [ $v = new ]; then case "$L" in *PASS) ;; *) bad=1;; esac; else case "$L" in *FAIL) ;; *) bad=1;; esac; fi
  done
done; done
[ $bad = 0 ] && echo BK_SELIDS_SLICE_LOCK PASS || echo BK_SELIDS_SLICE_LOCK FAIL
exit $bad
