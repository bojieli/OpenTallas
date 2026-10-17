#!/bin/bash
# One cp2 / cp1 bench case per call (HBMA-HOST 2026-10-17, for closure-loop job benches; same sources and
# parameters as run_cp2.sh / run_static_cmd_target.sh).  usage: run_cp2_one.sh OUT CASE
#   CASE: status | status_mut<1-2> (die-shape join: NT67/NF105 d4f target list) | collar | collar_mut<1-7> | join_mut<1-2> | packet | packet_mut<1-3> | phy | phy_mut<1-2> | cmd | cmd_mut<1-2>
# Prints the bench's own PASS/FAIL line prefixed by "CP2_ONE <CASE>: ".
set -u
cd "$(dirname "$0")/../../.."
D=rtl/hbm_accel/host_static_20261015; O=${1:?out}; c=${2:?case}; mkdir -p "$O"
C="$D/tb_hbm_static_cfg_collar.sv $D/ot_hbm_static_cfg_collar.sv $D/ot_hbm_status_join.sv $D/ot_hbm_host_static_ingress.sv"
P="$D/tb_hbm_host_packet_static.sv $D/ot_hbm_host_packet_static.sv $D/ot_hbm_host_static_ingress.sv"
A="$D/tb_hbm_host_phy_adapt.sv $D/ot_hbm_host_phy_adapt.sv"
S="$D/tb_static_cmd_target.sv $D/ot_static_cmd_target.sv $D/ot_hbm_host_static_ingress.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv"
m=${c##*_mut}; [ "$m" = "$c" ] && m=0
case "$c" in
 collar|collar_mut*) a="-Ptb_hbm_static_cfg_collar.CMUT=$m $C";;
 join_mut*)          a="-Ptb_hbm_static_cfg_collar.JMUT=$m $C";;
 packet|packet_mut*) a="-Ptb_hbm_host_packet_static.MUT=$m $P";;
 phy|phy_mut*)       a="-Ptb_hbm_host_phy_adapt.MUT=$m $A";;
 cmd|cmd_mut*)       a="-DMUT=$m -DTGTPIN=1 $S";;
 status|status_mut*)
   printf '%s\n' "localparam integer NT=67;" "localparam integer NF=105;" \
    "localparam [NT*8-1:0] TGTS=536'hd7d6d5d4d3d2d1d0c7c6c5c4c3c2c1c0a5a4a2a0878685846f6e6d6c6a68666463626160575655545352515047464544434241403b3a39387877767574703736353430;" \
    > "$O/all_targets.svh"
   a="-I$O -Ptb_hbm_all_target_status.MUT=$m $D/tb_hbm_all_target_status.sv $D/ot_hbm_status_join.sv";;
 *) echo "CP2_ONE $c: unknown case"; exit 2;;
esac
iverilog -g2012 $a -o "$O/$c.vvp" > "$O/$c.build" 2>&1 || { echo "CP2_ONE $c: BUILD-ERR"; cat "$O/$c.build"; exit 1; }
r=$(vvp -n "$O/$c.vvp" | tee "$O/$c.log" | grep -E '(^|[^A-Z_])(PASS|FAIL|FATAL)' | tail -1)
echo "CP2_ONE $c: $r"
case "$r" in *FAIL*|*FATAL*) exit 1;; *PASS*) exit 0;; *) exit 1;; esac
