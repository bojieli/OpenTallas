#!/usr/bin/env bash
# FORM-COLL 11-05: replay buffer landing (RBL) proof, CORE_CRED 12, Verilator 5.050.
#   $1 outdir, $2 mode: miter (RBL = 0 pair + RBL = 1 shadow lanes, cycle check) | loop (RBL = 1 pair vs safe4 reference,
#   transactional), $3 mutant: 0 | WR (group 0 never writes) | RP (read index misses the landing edge) | SEL (selects miss it) |
#   IN (fresh word misses it).  Passes on COLL_REACH7 PASS.
set -euo pipefail
O=$(realpath -m "${1:?outdir}"); MODE=${2:-miter}; M=${3:-0}; mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
S=rtl/dsrom_sys/s81_ph
SRCS=(rtl/link/ot_link_crc32.sv rtl/lib/ot_rst_relay_tree3.sv $S/coll/ot_s81ph_ckbuf.sv rtl/lib/ot_sram_oldread_b64.sv rtl/lib/ot_sram_showahead_b64.sv rtl/common/ot_link_credit_rx_b64.sv rtl/common/ot_link_credit_tx_rc.sv $S/ot_s81ph_link_ep_safe4.sv $S/ot_s81ph_link_gbx_safe3.sv $S/coll/ot_s81ph_coll_lane_safe4.sv)
D=(-DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF -DOT_COLL_REACH8 -DOT_COLL_REACH8N -DOT_S81PH_COLL_TF_CLEANUP)
case "$MODE" in miter) D+=(-DOT_COLL_RBL_MITER);; loop) D+=(-DOT_COLL_RBL_DUT);; *) exit 2;; esac
[ "$M" = 0 ] || D+=(-DOT_COLL_RBL_MUT_$M)
for N in physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1; do SRCS+=("$N/$(basename "$N").v"); done
"$V" --version
"$V" --binary --timing -j "${J:-4}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-MULTIDRIVEN "${D[@]}" -GCORE_CRED=12 --top-module tb_coll_reach7 --Mdir "$O/obj" "${SRCS[@]}" $S/test/tb_coll_reach7.sv > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 2; }
set +e
"$O/obj/Vtb_coll_reach7" > "$O/run.log" 2>&1
rc=$?
set -e
tail -14 "$O/run.log" | cut -c1-240
echo "sim exit $rc"
grep -q '^COLL_REACH7 PASS' "$O/run.log"
