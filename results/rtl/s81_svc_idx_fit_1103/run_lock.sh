#!/usr/bin/env bash
# DIE-S81-51/MEM idx fit gate (2026-11-03): old-vs-new lockstep of dsdv_idx_rg3 (kit portfix178 source, 13 x 1024x256)
# against dsdv_idx_rg3_fit (tools/die_plan/s81_svc_idx_fit.py) inside the S81-IDX3R campaign bench tb_dsdv_idx_rg3:
# every reader is an idx_lock (tb_idx_lock.sv) comparing all outputs every edge; reader 0 also runs the behavioural
# fit control (m0, must match) and 7 size mutants (m1..m7, each must mismatch).  Macro models for ref + fit.
# Run from the repo root on a fleet host (heavy: via ot-run).  Usage: run_lock.sh OUT [JOBS]
set -u
O=$(realpath -m "$1"); J=${2:-6}; P=results/rtl/s81_svc_idx_fit_1103
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=$O/lock; mkdir -p "$D"
python3 -I - "$PWD" "$D" <<'PY'
import sys, re
from pathlib import Path
root, d = Path(sys.argv[1]), Path(sys.argv[2]); sys.path.insert(0, str(root / 'tools/die_plan'))
import s81_svc_idx_fit as F
src = (root / 'physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_rg3.sv').read_text()
fit = F.fit_source(src); (d / 'dsdv_idx_rg3_fit.sv').write_text(fit)
MUTS = {1: ('.WORDS(768), .BITS(256)) u_h0', '.WORDS(512), .BITS(256)) u_h0'),          # h0 rows 512..767 lost
        2: ('.WORDS(256), .BITS(256)) u_h1', '.WORDS(128), .BITS(256)) u_h1'),          # h1 row bit 7 aliased
        3: ('.WORDS(128), .BITS(MW + 1)) u_mq', '.WORDS(64), .BITS(MW + 1)) u_mq'),     # mq ring 64 < 123
        4: ('.BITS(IW)) u_iq', '.BITS(IW - 1)) u_iq'),                                  # iq top data bit
        5: ('.BITS(SW)) u_sq', '.BITS(SW - 22)) u_sq'),                                 # sq meta field (top bit is w[15], 0 in bench)
        6: ('.WORDS(LFD <= 256 ? 256 : 1024), .BITS(256)) u_mem', '.WORDS(64), .BITS(256)) u_mem'),   # list 64 (bench lists 128 words)
        7: ('.WORDS(768), .BITS(256)) u_h0', '.WORDS(256), .BITS(256)) u_h0')}          # h0 scan/gather rows aliased
for k, (a, b) in MUTS.items():
    assert fit.count(a) == 1, k
    (d / ('dsdv_idx_rg3_fit_m%d.sv' % k)).write_text(
        fit.replace(a, b).replace('module dsdv_idx_rg3_fit #(', 'module dsdv_idx_rg3_fit_m%d #(' % k))
tb = (root / 'rtl/dsrom_sys/s81_dv/idx/test/tb_dsdv_idx_rg3.sv').read_text()
assert tb.count('dsdv_idx_rg3 #(.MUT(MUT)') == 1
(d / 'tb_dsdv_idx_rg3.sv').write_text(tb.replace('dsdv_idx_rg3 #(.MUT(MUT)', 'idx_lock #(.LK(r == 0), .MUT(MUT)'))
print('generated fit', F.sha12(fit))
PY
[ $? -eq 0 ] || { echo "IDXLOCK_GATE FAIL generate"; exit 2; }
M2=physical/asap7_memory_macros_v2
SRC=(rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv rtl/hdc/v41x/ot_hdc_v41x_idx.sv
     rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv
     rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv
     rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv rtl/hdc/v41x/ot_hdc_v41x_idx_chunk_el.sv
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
     $M2/ot_sram_1r1w_256x256_m1_r0c0/ot_sram_1r1w_256x256_m1_r0c0.v $M2/ot_sram_1r1w_768x256_m2_r0c0/ot_sram_1r1w_768x256_m2_r0c0.v
     $M2/ot_sram_1r1w_1024x35_m4_r0c0/ot_sram_1r1w_1024x35_m4_r0c0.v $M2/ot_sram_1r1w_1024x39_m4_r0c0/ot_sram_1r1w_1024x39_m4_r0c0.v
     $M2/ot_sram_1r1w_128x23_m1_r0c0/ot_sram_1r1w_128x23_m1_r0c0.v
     rtl/dsrom_sys/s81_ph/ot_s81ph_afifo.sv rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_ctrl_pcr.sv rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g.sv rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_rg3.sv
     rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_v.sv
     rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_rg3.sv
     $P/dsdv_idx_fit_mem.sv "$D"/dsdv_idx_rg3_fit.sv "$D"/dsdv_idx_rg3_fit_m[1-7].sv $P/tb_idx_lock.sv "$D/tb_dsdv_idx_rg3.sv")
if [ ! -x "$D/obj/Vtb_dsdv_idx_rg3" ]; then
  "$VL" --version > "$D/build.log"; sha256sum "${SRC[@]}" >> "$D/build.log"
  "$VL" --binary --timing -j ${VL_J:-24} --build-jobs ${VL_BJ:-48} --top-module tb_dsdv_idx_rg3 -O2 +define+S81CTRL_NATIVE32 --output-split 20000 --output-split-cfuncs 2000 \
    -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O1" -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-TIMESCALEMOD -Wno-BLKSEQ \
    -Wno-INITIALDLY -GMUT=0 -GSRAM_MACRO=1 --Mdir "$D/obj" "${SRC[@]}" >> "$D/build.log" 2>&1 \
    || { echo "IDXLOCK_GATE FAIL build"; grep -m5 '%Error' "$D/build.log"; exit 2; }
fi
CASES=("pass_l20|+N=87382 +B=13 +T0=400 +P=3" "pass_small|+N=4096 +B=13 +T0=400 +P=3" "pass_gs|+GATHER=1 +N=256 +T0=1500 +P=3"
       "pass_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4" "pass_g2048s2|+GATHER=1 +N=2048 +T0=1500 +P=4 +SEED=2"
       "pass_open6|+N=4096 +B=13 +T0=400 +P=3 +OPEN=6" "closed_g2048p3|+GATHER=1 +N=2048 +T0=1500 +P=3")
n=0
for c in "${CASES[@]}"; do
  ( /usr/bin/time -v "$D/obj/Vtb_dsdv_idx_rg3" ${c#*|} > "$D/${c%%|*}.log" 2>&1 ) &
  n=$((n + 1)); if [ $n -ge "$J" ]; then wait -n; n=$((n - 1)); fi
done
wait
python3 -I - "$D" "${CASES[@]%%|*}" <<'PY'
import re, sys, json
from pathlib import Path
d = Path(sys.argv[1]); cases = sys.argv[2:]; bad = []; tot = {}; mut = {}; maxcyc = 0; res = {}
for c in cases:
    t = (d / (c + '.log')).read_text()
    v = re.findall(r'^TB_IDXRD (PASS|FAIL)$', t, re.M); v = v[-1] if v else 'NONE'
    exp = 'PASS' if c.startswith('pass_') else 'FAIL'
    if v != exp: bad.append('%s verdict %s' % (c, v))
    rows = re.findall(r'^IDXLOCK sid (\d+) cyc (\d+) mis (\d+) (.*)$', t, re.M)
    if len(rows) != 8: bad.append('%s readers %d' % (c, len(rows)))
    for sid, cyc, mis, rest in rows:
        if int(mis): bad.append('%s sid %s mis %s' % (c, sid, mis))
        maxcyc = max(maxcyc, int(cyc))
        for k, x in re.findall(r'(\w+) (\d+)', rest): tot[k] = tot.get(k, 0) + int(x)
    for m, x in re.findall(r'^IDXLOCK_MUT sid \d+ m(\d+) mis (\d+)$', t, re.M): mut[int(m)] = mut.get(int(m), 0) + int(x)
    res[c] = dict(verdict=v, cyc=max([int(r[1]) for r in rows] or [0]), stats=(re.findall(r'^TB_IDXRD_STATS .*$', t, re.M) or [''])[-1])
if mut.get(0, -1) != 0: bad.append('behavioural control m0 mis %s' % mut.get(0))
for m in range(1, 8):
    if mut.get(m, 0) == 0: bad.append('mutant m%d not detected' % m)
for k, x in tot.items():
    if x == 0: bad.append('coverage %s = 0' % k)
if maxcyc < 20000: bad.append('longest case %d < 20000 cycles' % maxcyc)
rep = dict(cases=res, coverage=tot, mutants=mut, max_cycles=maxcyc, bad=bad, gate='PASS' if not bad else 'FAIL')
(d / 'gate.json').write_text(json.dumps(rep, indent=1) + '\n')
for c, r in res.items(): print('IDXLOCK_CASE', c, r['verdict'], 'cyc', r['cyc'])
print('IDXLOCK coverage', tot); print('IDXLOCK mutants', mut); print('IDXLOCK max_cycles', maxcyc)
print('IDXLOCK_GATE', rep['gate'], '; '.join(bad[:8])); sys.exit(0 if not bad else 1)
PY
