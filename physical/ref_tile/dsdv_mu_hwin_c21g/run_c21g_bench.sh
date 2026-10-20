#!/usr/bin/env bash
# S81-HWIN21g kit bench: dsdv_mu_hwin_capture_1019 CFG_RELAY=1 (rtl/, the synthesized DUT) on the raw config ports, mitered every
# cycle against the frozen HWIN21cb 072dd6141 source (tools/hwin_private_package_1019/sim copies, sha256-pinned below, renamed
# dsdv_mu_hwin_cbref_1019) and the 1e057 anchor dsdv_mu_hwin, both fed z^-1 f_mw / z^-1 f_mc (config edge shifted +1).
# Verilator 5.050 (daemon version).  Usage (cwd = repo root): run_c21g_bench.sh OUTDIR {ns47|ns2|norelay|eastcopy|mut2}
#  ns47 / ns2: MUWIN PASS (no CBREF_MITER / EARLY_MITER fatal).  norelay: DUT CFG_RELAY=0 on the raw ports; eastcopy: relay
#  copy 1 forced 0; mut2: early-capture mechanism mutant EC_MUT=2 -- all must stop with a CBREF_MITER / EARLY_MITER fatal.
set -u
O=$(realpath -m "$1"); V=$2; mkdir -p "$O"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
S=tools/hwin_private_package_1019/sim; U=$S/rtl/dsrom_sys/s81_dv/unit; R=rtl/dsrom_sys/s81_dv/unit
K=physical/ref_tile/dsdv_mu_hwin_c21g
declare -A PIN=([dsdv_mu_hwin_capture_1019]=fd37205500ff5ca79b8112dd19d075a112280e5d3817b0c81173ee9024314254
 [dsdv_mu_hwin_capture_mem_1019]=01fe5414845ec1afc78be06102178f463818689b84477d8d9b5d0dcc3069ad41
 [dsdv_mu_hwin_capture_early_1019]=6d6d6fc593d7f6d4cc28a2298647b4a3e2f7946091656f151786d5fd5d3ee14f)
mkdir -p "$O/cbref"
for f in "${!PIN[@]}"; do
  h=$(sha256sum < "$U/$f.sv" | cut -c1-64)
  [ "$h" = "${PIN[$f]}" ] || { echo "CBREF_SOURCE_MISMATCH $f $h"; exit 3; }
  sed 's/dsdv_mu_hwin_capture_1019/dsdv_mu_hwin_cbref_1019/g' "$U/$f.sv" > "$O/cbref/${f/capture/cbref}.sv"
done
# the DUT mem/early files are unchanged from HWIN21cb; only the top gained CFG_RELAY (default 0)
for f in dsdv_mu_hwin_capture_mem_1019 dsdv_mu_hwin_capture_early_1019; do
  cmp -s "$U/$f.sv" "$R/$f.sv" || { echo "DUT_SOURCE_MISMATCH $f"; exit 3; }; done
grep -q 'parameter integer CFG_RELAY' "$R/dsdv_mu_hwin_capture_1019.sv" || { echo "DUT_NO_CFG_RELAY"; exit 3; }
files=("$S/rtl/lib/ot_rst_relay.sv" "$S/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv"
 "$S/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
 "$S/physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v"
 "$U/dsdv_mu_hslot.sv" "$U/dsdv_mu_mem.sv" "$U/dsdv_mu_mem_early_capture.sv" "$U/dsdv_mu_hwin.sv"
 "$R/dsdv_mu_hwin_capture_1019.sv" "$R/dsdv_mu_hwin_capture_mem_1019.sv" "$R/dsdv_mu_hwin_capture_early_1019.sv"
 "$O/cbref/dsdv_mu_hwin_cbref_1019.sv" "$O/cbref/dsdv_mu_hwin_cbref_mem_1019.sv" "$O/cbref/dsdv_mu_hwin_cbref_early_1019.sv"
 "$K/tb_dsdv_mu_hwin_cfg_relay.sv")
case $V in
 ns47)     D=(+define+NSLOT_TEST=47 +define+MIN_D);;
 ns2)      D=(+define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D);;
 norelay)  D=(+define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D +define+NORELAY_MUTANT);;
 eastcopy) D=(+define+NSLOT_TEST=2 +define+MIN_D +define+EAST_COPY_MUTANT);;
 mut2)     D=(+define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D +define+EC_MUT=2);;
 *) echo "unknown variant $V"; exit 2;;
esac
verilator --version | tee "$O/verilator_version.txt"
verilator --binary --timing --x-initial unique --x-assign unique -j "${J:-4}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style \
  +define+OT_MEM_NO_INIT --top-module tb_dsdv_mu_hwin_cfg_relay "${D[@]}" "${files[@]}" \
  --Mdir "$O/obj" -o tb > "$O/build.log" 2>&1 || { echo "BUILD_FAIL $V"; tail -20 "$O/build.log"; exit 1; }
rc=0
"$O/obj/tb" +verilator+rand+reset+2 +verilator+seed+1 +reset_phase=0 +rx_shift=-1 +release_word_stage=1 > "$O/run.log" 2>&1 || rc=$?
cat "$O/run.log"; echo "TB_RC $rc"
[ $rc -eq 0 ] && grep -q '^MUWIN PASS' "$O/run.log"
