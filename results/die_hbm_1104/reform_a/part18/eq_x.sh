#!/usr/bin/env bash
# eq_x.sh REPO T KITRTL BASE X KINDS OUT [EPOCHS]: uncut kit core vs composition; MUT 0 must PASS, MUT 1-5 FAIL.
set -u
REPO=$1; T=$2; KR=$3; BASE=$4; X=$5; KINDS=$6; O=$7; EP=${8:-40}
RX=$REPO/rtl/hbm_accel/cores_split/reform_1104a/lane_x; B=$REPO/physical/die_plan/hbm/over_cap_split/reform_1103; H=$B/bench/lanes8_11
P=$REPO/results/die_hbm_1104/reform_a/part18; V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}; mkdir -p "$O"
LEAF=$(ls $KR/*.sv | grep -v "__fshell\|__wrap\|${BASE}.sv")
XF="$RX/ot_hbm_su_static_lane_x.sv $RX/ot_hbm_su_static_lane_pinreg_x.sv"
python3 "$B/facewrap.py" --top $X --clk-re "(^|_)clk(_|$)" --rst-re "(^|_)rst_n$" --pass-param XS --out "$O/x__fs.sv" $RX/$X.sv $XF $LEAF "$H/sram_bench_model.sv" > "$O/x_ports.json" || exit 1
python3 "$B/facewrap.py" --top ot_hbm_su_pg_sfu_s_core --clk-re "^clk$" --rst-re "^rst_n$" --out "$O/s__fs.sv" $RX/ot_hbm_su_pg_sfu_s_core.sv $LEAF "$H/sram_bench_model.sv" > "$O/s_ports.json" || exit 1
python3 "$B/facewrap.py" --top $T --out "$O/ref_unused__fs.sv" $KR/*.sv "$H/sram_bench_model.sv" > "$O/ref_ports.json" || exit 1
sed -e "s/^module $T (/module ${T}__split (/" -e "s/ot_hbm_face_reg #/ot_hbm_face_wire #/" -e "s/${T}__fcore u_fcore/${T}__fcore_split u_fcore/" $KR/${T}__fshell.sv > "$O/dut_top.sv"
sed -e "s/module ${T}__fcore (/module ${T}__fcore_split (/" -e "s/$BASE u_core/${BASE}__splitx #(.MUT(\`OT_MUT)) u_core/" $KR/${T}__wrap.sv > "$O/dut_fcore.sv"
grep -q "${BASE}__splitx" "$O/dut_fcore.sv" || { echo no composition in fcore; exit 1; }
cat > "$O/face_wire.sv" <<'EOV'
module ot_hbm_face_wire #(parameter integer W = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    assign q = d;
endmodule
EOV
python3 "$P/eq_x.py" "$O/ref_ports.json" $KR/${T}__wrap.sv $T ${T}__split "$KINDS" "$O/tb.sv" $EP || exit 2
for M in ${MUTS:-0 1 2 3 4 5}; do
  rm -rf "$O/obj_m$M"; $V --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -DOT_MUT=$M --top-module tb -Mdir "$O/obj_m$M" -o sim \
    "$O/tb.sv" $KR/*.sv "$H/sram_bench_model.sv" $XF $RX/$X.sv $RX/ot_hbm_su_pg_sfu_s_core.sv $RX/${BASE}__splitx.sv "$O/x__fs.sv" "$O/s__fs.sv" "$O/dut_top.sv" "$O/dut_fcore.sv" "$O/face_wire.sv" > "$O/build_m$M.log" 2>&1 || { tail -20 "$O/build_m$M.log" | cut -c1-300; exit 3; }
  "$O/obj_m$M/sim" > "$O/sim_m$M.log" 2>&1; echo "MUT $M: $(grep -c MISMATCH "$O/sim_m$M.log") $(grep XEQ "$O/sim_m$M.log")"; grep MISMATCH "$O/sim_m$M.log" | head -3 | cut -c1-120
  rm -rf "$O/obj_m$M"
done
sha256sum $KR/*.sv $RX/*.sv "$H/sram_bench_model.sv" "$O/tb.sv" > "$O/sources.sha256"
