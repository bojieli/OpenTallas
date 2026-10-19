#!/usr/bin/env bash
# MU-DIE-S81/MUWIN (10-19): the COMPILED multi-user window / replay table on the real MU seq_host master.
# dsdv_seq_host_mux (GEN mu2: dsdv_seq_host_mu NSLOT 47 = real dsdv_seq_host + gap-table dsdv_mu_hslot, + dsdv_mu_hwin
# NEV 8 NEP 4 NRT 2; RTL of MU-S81-2/SEQ 5dd45e769, staged in $MU2) is booted with a compiled MU layer programme
# (dv_layer_compile --mu-cal --mu-ctx --mu-win: prog/job0 host_boot.memh) and the COMPILER's boot config
# (prog/mu_cfg.cfg: CSR 0x15 slot gap table + RL, CSR 0x16 hwin event rows / per-slot {land, ab}); users start on f_ks at
# their calendar starts (dv_mu_win.py cases).  dv_mu_win.py check: every compiled TX window (mu_c) and landing replay
# (mu_rc) of every start appears on its end-slice port on EXACTLY the compiled edge (f_ks capture + 1 + D) with the
# start's {pos, user} and the slot's {land, ab}; nothing else on the MU ports; t_mf 0000; no issuer fault.
#   base            users of --users (default 0,1,2) x 2 periods                       -> MUWIN_PROG PASS
#   mut_winshift    one TX window row's D + 1 (window moved one edge)                  -> must FAIL (missing/unexpected)
#   mut_replaydrop  one replay row never loaded (replay dropped)                       -> must FAIL (missing)
# Usage: run_mu_win_prog_bench.sh PROG MU2 OUTDIR [users]     (Verilator 5.050, the closure daemon's pin)
# PROG = compiled programme dir; MU2 = dir holding dsdv_mu_hslot.sv / dsdv_mu_hwin.sv / tb_dsdv_seq_host_mu.sv of
# 5dd45e769.  Prints MU_WIN_PROG_GATE PASS/FAIL.
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
P=$(realpath $1); M=$(realpath $2); O=$(realpath -m $3); US=${4:-0,1,2}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | tee "$O/verilator_version.txt"
U=$R/rtl/dsrom_sys/s81_dv/unit; T=$U/test
HB=$P/prog/host_boot.memh; [ -f $HB ] || HB=$P/prog/job0/host_boot.memh
mkdir -p $O/pd/prog; cp $HB $O/pd/prog/host_boot.memh; N=$(grep -c . $O/pd/prog/host_boot.memh)
F="$R/rtl/lib/ot_async_fifo.sv $R/rtl/lib/ot_reset_sync.sv $R/rtl/lib/ot_rst_relay.sv $R/rtl/link/ot_link_afifo.sv
   $R/rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv $R/rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv $R/rtl/hdc/ingest/ot_hdc_kv_ingest.sv
   $R/rtl/hdc/ingest/ot_rom_host_ingest.sv $R/physical/rom_host_ingest/rtl/dsfd_host.sv
   $R/rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv
   $R/rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv $U/ot_dsdv_fixed_issue.sv $U/ot_dsdv_vstop.sv $U/dsdv_sh_sd.sv $U/dsdv_seq_host.sv
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $M/dsdv_mu_hslot.sv $M/dsdv_mu_hwin.sv"
python3 $R/tools/s81_dv/dv_mu_win.py cases --prog $P --out $O/cases --users $US > $O/cases.log || { echo "MU_WIN_PROG_GATE FAIL (cases)"; exit 2; }
sha256sum $F $M/tb_dsdv_seq_host_mu.sv $R/tools/s81_dv/dv_mu_win.py $0 $HB $P/prog/mu_win.json $P/prog/mu_cfg.cfg $P/prog/calendar.json $O/cases/* > $O/sources.sha256
RL=$(python3 -c "import json;print(json.load(open('$P/prog/mu_win.json'))['RL'])")
verilator --binary --timing -j "${OT_THREADS:-8}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT \
  --top-module tb_dsdv_seq_host_mu --Mdir "$O/obj" -o tb $F $M/tb_dsdv_seq_host_mu.sv > "$O/build.log" 2>&1 \
  || { echo "BUILD_FAIL"; grep -m5 %Error "$O/build.log"; echo "MU_WIN_PROG_GATE FAIL"; exit 3; }
bad=0
for c in base mut_winshift mut_replaydrop; do
  "$O/obj/tb" +dir=$O/pd +n=$N +cyc=$((RL + 200)) +timeout=40000000 +mu=$O/cases/mu.mu +cfg=$O/cases/$c.cfg > "$O/run_$c.log" 2>&1
  python3 $R/tools/s81_dv/dv_mu_win.py check --prog $P --log $O/run_$c.log --mu $O/cases/mu.mu --out $O/check_$c.json > $O/check_$c.txt 2>&1
  cat $O/check_$c.txt
done
grep -q '^MUWIN_PROG PASS' $O/check_base.txt || bad=1
grep -q '^MUWIN_PROG FAIL.*\(missing\|unexpected\) MC' $O/check_mut_winshift.txt && echo "mutant winshift detected (FAIL as required)" || { echo "mutant winshift NOT detected"; bad=1; }
grep -q '^MUWIN_PROG FAIL.*missing MR' $O/check_mut_replaydrop.txt && echo "mutant replaydrop detected (FAIL as required)" || { echo "mutant replaydrop NOT detected"; bad=1; }
[ $bad = 0 ] && echo "MU_WIN_PROG_GATE PASS" || echo "MU_WIN_PROG_GATE FAIL"
exit $bad
