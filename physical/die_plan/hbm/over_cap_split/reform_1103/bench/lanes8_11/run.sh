#!/usr/bin/env bash
# DIE-HBM-61/SPLIT lanes8_11 lock-step: uncut kit core (ot_hbm_su_static_pgslice_lg__lanes8_11 = kit face shell around
# __fcore -> ot_hbm_su_pg_lanes4_core) vs split (same shell ports, face flops moved onto the two sub-blocks:
# __fcore copy -> ot_hbm_su_pg_lanes4_core__split -> 4 x ot_hbm_su_pg_lane1_core__fs).  run.sh KITRTL OUT [CYCLES]
# MUT 0 must PASS; MUT 1/2/3 must FAIL.  SRAM = bench model (sram_bench_model.sv), same on both sides.
set -u
KR=$1; O=$2; CYC=${3:-3000}; H=$(cd "$(dirname "$0")" && pwd); R=$H/../..; RT=$H/../../../../../../../rtl/hbm_accel/cores_split/reform_1103/ot_hbm_su_static_pgslice_lg__lanes8_11
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}; mkdir -p "$O"
T=ot_hbm_su_static_pgslice_lg__lanes8_11
LEAF=$(ls $KR/*.sv | grep -v "__fshell\|__wrap\|ot_hbm_su_pg_lanes4_core.sv")
python3 "$R/facewrap.py" --top ot_hbm_su_pg_lane1_core --clk-re "(^|_)clk(_|$)" --rst-re "(^|_)rst_n$" --out "$O/lane1__fs.sv" $RT/ot_hbm_su_pg_lane1_core.sv $LEAF "$H/sram_bench_model.sv" > "$O/lane1_ports.json" || exit 1
python3 "$R/facewrap.py" --top $T --out "$O/ref_unused__fs.sv" $KR/*.sv "$H/sram_bench_model.sv" > "$O/ref_ports.json" || exit 1
# DUT top: the kit shell with its face flops turned into wires (they move onto the sub-blocks) + the __fcore copy
sed -e "s/^module $T (/module ${T}__split (/" -e "s/ot_hbm_face_reg #/ot_hbm_face_wire #/" -e "s/${T}__fcore u_fcore/${T}__fcore_split u_fcore/" $KR/${T}__fshell.sv > "$O/dut_top.sv"
sed -e "s/module ${T}__fcore (/module ${T}__fcore_split (/" -e "s/ot_hbm_su_pg_lanes4_core u_core/ot_hbm_su_pg_lanes4_core__split #(.MUT(\`OT_MUT)) u_core/" $KR/${T}__wrap.sv > "$O/dut_fcore.sv"
cat > "$O/face_wire.sv" <<'EOV'
module ot_hbm_face_wire #(parameter integer W = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    assign q = d;
endmodule
EOV
grep -c "ot_hbm_face_wire #" "$O/dut_top.sv" > "$O/dut_face_wires.txt"
python3 - "$O/ref_ports.json" "$O/spec.json" "$T" "$CYC" <<'EOP'
import json, sys
p = json.load(open(sys.argv[1]))
ports = p['ports']; T = sys.argv[3]
spec = dict(ref=T, dut=T + '__split', ports=ports, clocks=p['clk'], resets=p['rst'], reset_cycles=10, warmup=150,
            cycles=int(sys.argv[4]), stim={}, hold={}, shift={})
# lane_id straps: replica constants at the parent (hold)
for n in ports:
    if 'lane_id' in n:
        spec['hold'][n] = "11'd%d" % (8 + int(n.split('_')[2]) if n.split('_')[2].isdigit() else 8)
json.dump(spec, open(sys.argv[2], 'w'), indent=1)
EOP
python3 "$R/lockstep_gen.py" "$O/spec.json" "$O/tb.sv"
for M in ${MUTS:-0 1 2 3}; do
  rm -rf "$O/obj_m$M"; $V --binary -j 16 -Wno-fatal -Wno-lint -Wno-style -DOT_MUT=$M --top-module tb -Mdir "$O/obj_m$M" -o sim \
    "$O/tb.sv" $KR/*.sv "$H/sram_bench_model.sv" $RT/*.sv "$O/lane1__fs.sv" "$O/dut_top.sv" "$O/dut_fcore.sv" "$O/face_wire.sv" > "$O/build_m$M.log" 2>&1 || { tail -20 "$O/build_m$M.log"; exit 2; }
  "$O/obj_m$M/sim" > "$O/sim_m$M.log" 2>&1; echo "MUT $M: $(grep LOCKSTEP "$O/sim_m$M.log")"
done
sha256sum $KR/*.sv $RT/*.sv "$H/sram_bench_model.sv" > "$O/sources.sha256"
