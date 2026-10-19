#!/usr/bin/env bash
# MU-S81-2/SEQ (10-19): the multi-user host plane on the REAL seq_host parent the MU die binds (dsdv_seq_host_mux =
# dsdv_seq_host_mu NSLOT 47 around dsdv_seq_host + dsdv_mu_hwin, MU-S81-2/DIE ac336f805), booted with the compiled L0 programme (results/rtl/s81_mu_1018/
# prog_L0_mu) and the record calendars (results/arch/mu_s81_1018/calendar_{ar,mtp}.json, --phase-q 4), boot config over
# host CSR 0x15 (hslot / hwin) and 0x16 (hwin windows).  Verilator 5.050 (the closure daemon's pin).  Runs (tb_dsdv_seq_host_mu.sv, check_seq_host_mu.py):
#   ar / mtp      46 AR users x 2 periods (92 starts) / MTP 10 users + filler x 2 periods (22 starts): user 0 identical
#                 to its single run, single run = plain dsdv_seq_host + spare bits only (zero added latency), every
#                 start's {user, pos} in t_kd[31:1] on its KIT done edge, windows / replays per slot, no fault
#   f_uniform     the former one-period config (S 21,312) on the record calendar          -> t_mf[1] (integration gap)
#   f_offcal      one start 4 edges off its slot                                          -> t_mf[1]
#   f_dup         the same user in two slots while outstanding                            -> t_mf[1]
#   f_collide     slot 0 reused while its start is outstanding                            -> t_mf[0]
#   f_rl          RL one edge long: return mismatch                                       -> t_mf[2]
#   mutants (must FAIL): MU_MUT 1 user field dropped (ar), 2 collision check dropped (f_collide), 5 gap index stuck (ar)
#   regressions: MU_HOST_GATE (run_mu_host_bench.sh), MU_HWIN_GATE (run_mu_hwin_bench.sh), verilator -Wall lint
# Usage: run_seq_host_mu_bench.sh OUTDIR        Prints SEQHOST_MU_GATE PASS/FAIL.
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=$(realpath -m "${1:-$(mktemp -d)}"); mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | tee "$O/verilator_version.txt"
U=$R/rtl/dsrom_sys/s81_dv/unit; T=$U/test
P=$R/results/rtl/s81_mu_1018/prog_L0_mu; N=$(grep -c . $P/prog/host_boot.memh)
F="$R/rtl/lib/ot_async_fifo.sv $R/rtl/lib/ot_reset_sync.sv $R/rtl/lib/ot_rst_relay.sv $R/rtl/link/ot_link_afifo.sv
   $R/rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv $R/rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv $R/rtl/hdc/ingest/ot_hdc_kv_ingest.sv
   $R/rtl/hdc/ingest/ot_rom_host_ingest.sv $R/physical/rom_host_ingest/rtl/dsfd_host.sv
   $R/rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv
   $R/rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv $U/ot_dsdv_fixed_issue.sv $U/ot_dsdv_vstop.sv $U/dsdv_sh_sd.sv $U/dsdv_seq_host.sv
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $U/dsdv_mu_hslot.sv $U/dsdv_mu_hwin.sv"
sha256sum $F $T/tb_dsdv_seq_host_mu.sv $T/check_seq_host_mu.py $T/seq_host_mu_cases.py $P/prog/host_boot.memh \
  $R/results/arch/mu_s81_1018/calendar_ar.json $R/results/arch/mu_s81_1018/calendar_mtp.json > $O/sources.sha256
python3 $T/seq_host_mu_cases.py --root $R --out $O/cases > /dev/null || { echo "SEQHOST_MU_GATE FAIL (cases)"; exit 2; }
bad=0
build() { local n=$1; shift
  verilator --binary --timing -j "${OT_THREADS:-8}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT \
    --top-module tb_dsdv_seq_host_mu "$@" --Mdir "$O/obj_$n" -o tb $F $T/tb_dsdv_seq_host_mu.sv > "$O/build_$n.log" 2>&1 \
    || { echo "BUILD_FAIL $n"; grep -m5 %Error "$O/build_$n.log"; bad=1; return 2; }
}
run() { local b=$1 n=$2 c=$3
  [ -x "$O/obj_$b/tb" ] || { echo "NO_BUILD $b for $n"; bad=1; return; }
  "$O/obj_$b/tb" +dir=$P +n=$N +cyc=3000 +timeout=4000000 +mu=$O/cases/$c.mu +cfg=$O/cases/$c.cfg > "$O/run_$n.log" 2>&1
}
CK="python3 $T/check_seq_host_mu.py"
pass() { local n=$1 c=$2; $CK --dir $P --plain $O/run_plain_$c.log --single $O/run_single_$c.log --multi $O/run_$n.log --mu $O/cases/$c.mu; }
build mux; build plain +define+PLAIN
for m in 1 2 5; do build mut$m +define+MU_MUT=$m; done
for c in ar mtp; do
  run plain plain_$c ${c}_single; run mux single_$c ${c}_single; run mux $c $c
  pass $c $c || bad=1
done
for f in "f_uniform 1" "f_offcal 1" "f_dup 1" "f_collide 0" "f_rl 2"; do set -- $f
  run mux $1 $1; $CK --multi $O/run_$1.log --fault $2 || bad=1
done
# mutants: each must FAIL its check (fail regexes as in the witness logs)
run mut1 mut1_ar ar;       pass mut1_ar ar > $O/mut1_check.txt 2>&1;           cat $O/mut1_check.txt
grep -q '^SEQHOST_MU FAIL' $O/mut1_check.txt && echo "mutant 1 (user field dropped) detected (FAIL as required)" || { echo "mutant 1 NOT detected"; bad=1; }
run mut2 mut2_collide f_collide; $CK --multi $O/run_mut2_collide.log --fault 0 > $O/mut2_check.txt 2>&1; cat $O/mut2_check.txt
grep -q '^SEQHOST_MU FAULT0 FAIL' $O/mut2_check.txt && echo "mutant 2 (collision check dropped) detected (FAIL as required)" || { echo "mutant 2 NOT detected"; bad=1; }
run mut5 mut5_ar ar;       pass mut5_ar ar > $O/mut5_check.txt 2>&1;           cat $O/mut5_check.txt
grep -q '^SEQHOST_MU FAIL' $O/mut5_check.txt && echo "mutant 5 (gap index stuck) detected (FAIL as required)" || { echo "mutant 5 NOT detected"; bad=1; }
# lint of the changed leaf and the die master on the real unit sources
for t in "dsdv_mu_hslot -GNSLOT=47" "dsdv_mu_hwin -GNSLOT=47" "dsdv_seq_host_mux -Wno-fatal"; do set -- $t
  verilator --lint-only -Wall -Wno-fatal --top-module $1 $2 $F > "$O/lint_$1.log" 2>&1
  W=$(grep -E '^%(Warning|Error)' "$O/lint_$1.log" | grep -E 'dsdv_mu_h(slot|win)\.sv' | grep -v -E 'Warning-(DECLFILENAME|UNUSEDSIGNAL|UNUSEDPARAM|PINCONNECTEMPTY)')
  if grep -q '^%Error' "$O/lint_$1.log" || [ -n "$W" ]; then echo "lint $1 FAIL: $W"; grep -m5 '^%Error' "$O/lint_$1.log"; bad=1
  else echo "lint $1 clean (verilator -Wall: 0 errors, 0 unwaived warnings in dsdv_mu_hslot.sv / dsdv_mu_hwin.sv)"; fi
done
# regressions of the leaf benches on the changed RTL (one gap word = the former uniform period)
bash $T/run_mu_host_bench.sh $O/reg_host > $O/reg_host.txt 2>&1; tail -1 $O/reg_host.txt; grep -q '^MU_HOST_GATE PASS' $O/reg_host.txt || bad=1
bash $T/run_mu_hwin_bench.sh $O/reg_hwin > $O/reg_hwin.txt 2>&1; tail -1 $O/reg_hwin.txt; grep -q '^MU_HWIN_GATE PASS' $O/reg_hwin.txt || bad=1
[ $bad = 0 ] && echo "SEQHOST_MU_GATE PASS" || echo "SEQHOST_MU_GATE FAIL"
exit $bad
