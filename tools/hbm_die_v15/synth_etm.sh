#!/bin/bash
# H-DIE r3 (2026-10-15): SYNTH-ESTIMATE timing view of one synthesized die master (tools/hbm_die_v15/synth_master.sh
# output) -- write_timing_model of the mapped gate netlist at TT and FF (ASAP7 RVT NLDM + the mapped SRAM macro libs),
# ideal clocks at 833.333 ps on every clock port (clk, clk_*, *_clk, pg_clk), no wire load.  This is an ESTIMATE
# (pre-placement, no CTS, no wires) used only where no closed view exists; it is labelled synth_<corner>.lib and
# view_inventory.py counts it as SYNTH, never as REAL.
#   synth_etm.sh <src root> <synth out dir> <name>      -> <out>/<top>_synth_{tt,ff}.lib, <out>/etm.log
set -u
SRC=$(readlink -f $1); OUT=$(readlink -f $2); NAME=$3
TOP=$(grep -m1 -o 'hierarchy -check -top [A-Za-z0-9_]*' $OUT/$NAME.ys | awk '{print $NF}')
python3 - "$OUT/$NAME.files.json" "$OUT/etm.tcl" "$TOP" "$NAME" <<'PY'
import json, sys, os
d = json.load(open(sys.argv[1])); tcl = sys.argv[2]; top = sys.argv[3]; name = sys.argv[4]
macro_libs = {}
for m in d['macros']:
    base = m['file'][:-len('_bb.v')] if m['file'].endswith('_bb.v') else m['file'].rsplit('.', 1)[0]
    macro_libs[base] = 1
P = '/OpenROAD-flow-scripts/flow/platforms/asap7/lef'
L = [f'read_lef {P}/asap7_tech_1x_201209.lef', f'read_lef {P}/asap7sc7p5t_28_R_1x_220121a.lef']
L += [f'read_lef /src/{b}.lef' for b in macro_libs]
L += ['define_corners tt ff']
N = '/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM'
for c, C in (('tt', 'TT'), ('ff', 'FF')):
    for f in ('AO_RVT_{C}_nldm_211120', 'INVBUF_RVT_{C}_nldm_220122', 'OA_RVT_{C}_nldm_211120',
              'SIMPLE_RVT_{C}_nldm_211120', 'SEQ_RVT_{C}_nldm_220123'):
        L.append(f'read_liberty -corner {c} /tmp/lib/asap7sc7p5t_{f.format(C=C)}.lib')
    for b in macro_libs:
        L.append(f'read_liberty -corner {c} /src/{b}_{c}.lib')
L += [f'read_verilog /out/{name}.netlist.v', f'link_design {top}',
      'set ck [get_ports -quiet {clk clk_* *_clk *_clk_* pg_clk*}]',
      'set n 0',
      'foreach p $ck { create_clock -name ck_$n -period 833.333 $p; incr n }',
      'puts "OT_ETM_CLOCKS $n"',
      'set_clock_uncertainty -setup 60 [all_clocks]', 'set_clock_uncertainty -hold 25 [all_clocks]',
      'report_checks -corner tt -path_delay max -group_path_count 3 > /out/etm_worst_tt.rpt',
      f'write_timing_model -corner tt -library_name {top}_synth_tt /out/{top}_synth_tt.lib',
      f'write_timing_model -corner ff -library_name {top}_synth_ff /out/{top}_synth_ff.lib',
      'puts OT_ETM_DONE']
open(tcl, 'w').write('\n'.join(L) + '\n')
PY
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
docker run --rm --name hdie15-etm-$NAME-$$ --cpus=2 --memory=${MEMG:-24}g -v $SRC:/src:ro -v $OUT:/out -w /out openroad/orfs:asap7lock bash -lc "
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; mkdir -p /tmp/lib
  for f in \$(ls $L | grep -E 'RVT_(TT|FF)'); do b=\${f%.gz}; case \$f in *.gz) zcat $L/\$f > /tmp/lib/\$b;; *) cp $L/\$f /tmp/lib/\$b;; esac; done
  openroad -no_init -exit /out/etm.tcl > /out/etm.log 2>&1"
rc=$?
echo "$NAME etm rc=$rc $(grep -E 'OT_ETM_(CLOCKS|DONE)' $OUT/etm.log | tr '\n' ' ')"
exit $rc
