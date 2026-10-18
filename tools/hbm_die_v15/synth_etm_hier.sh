#!/bin/bash
# HBM-IDXETM (2026-10-18): HIERARCHICAL SYNTH-ESTIMATE timing view -- same view as synth_etm.sh (ideal clocks at
# 833.333 ps, TT+FF, ASAP7 RVT NLDM, no wires; labelled synth_<corner>.lib, counted SYNTH, never REAL), built without
# flattening the parent: every CHILD module (repeated, plain-named, e.g. ot_hbm_idx_chunk_owned_native = 16 x 2.29 M
# cells inside ot_hbm_idx_score_static) is characterised ONCE with write_timing_model, then the parent is linked with
# the child as a liberty cell (etm_hier_split.py) and modelled again.  Standalone OpenSTA (`sta`): no LEF needed.
#   synth_etm_hier.sh <src root> <synth out dir> <name> <child[,child..]|->
#     reads <out>/<name>.netlist.v, <name>.ys (top), <name>.files.json (mapped macro libs), like synth_etm.sh
#     writes <out>/<top>_synth_{tt,ff}.lib, <out>/etm.log, <out>/hier/{split.json,<child>_synth_{tt,ff}.lib,...}
#   CHILD "-" = flat in the same tool (the reference for etm_lib_compare.py).
#   ETM_CHILD_UNC=0|1 (default 0): clock uncertainty while characterising the child (the parent applies the
#   uncertainty once at the child's setup/hold pins; 1 = also inside the child, to show which matches flat).
#   ETM_TOP=<module>: override the top read from <name>.ys (reduced verification configurations).
set -u
SRC=$(readlink -f $1); OUT=$(readlink -f $2); NAME=$3; CHILDREN=$4
T=$(dirname $(readlink -f $0))
TOP=${ETM_TOP:-$(grep -m1 -o 'hierarchy -check -top [A-Za-z0-9_]*' $OUT/$NAME.ys | awk '{print $NF}')}
sed -E 's/^(\s*)(wire|input|output|inout) signed /\1\2 /' $OUT/$NAME.netlist.v > $OUT/$NAME.sta.v
python3 $T/etm_clock_merge.py netlist $OUT/$NAME.sta.v $TOP ${ETM_CLK_BUS_MAX:-32} $OUT/etm_clocks.json || exit 15
H=$OUT/hier; rm -rf $H; mkdir -p $H
if [ "$CHILDREN" = "-" ]; then
  cp $OUT/$NAME.sta.v $H/parent.v; echo '{"children": {}}' > $H/split.json
else
  python3 $T/etm_hier_split.py split $OUT/$NAME.sta.v $TOP $CHILDREN $H || exit 17
  for c in ${CHILDREN//,/ }; do
    python3 $T/etm_clock_merge.py netlist $H/child_$c.v $c ${ETM_CLK_BUS_MAX:-32} $H/clocks_$c.json || exit 15
  done
fi
python3 - "$OUT/$NAME.files.json" "$H" "$TOP" "$CHILDREN" "$OUT/etm_clocks.json" "${ETM_CHILD_UNC:-0}" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); H = sys.argv[2]; top = sys.argv[3]
children = [c for c in sys.argv[4].split(',') if c and c != '-']; unc_child = sys.argv[6] == '1'
macro_libs = []
for m in d['macros']:
    b = m['file'][:-len('_bb.v')] if m['file'].endswith('_bb.v') else m['file'].rsplit('.', 1)[0]
    if b not in macro_libs:
        macro_libs.append(b)

def tcl(path, design, verilog, clocks, c, C, extra_libs, unc, libname, outlib, tag):
    L = []
    for f in ('AO_RVT_{C}_nldm_211120', 'INVBUF_RVT_{C}_nldm_220122', 'OA_RVT_{C}_nldm_211120',
              'SIMPLE_RVT_{C}_nldm_211120', 'SEQ_RVT_{C}_nldm_220123'):
        L.append(f'read_liberty /tmp/lib/asap7sc7p5t_{f.format(C=C)}.lib')
    L += [f'read_liberty /src/{b}_{c}.lib' for b in macro_libs] + [f'read_liberty {x}' for x in extra_libs]
    L += [f'read_verilog {verilog}', f'link_design {design}', 'set n 0',
          'foreach p [list ' + ' '.join('{' + k + '}' for k in clocks) + '] '
          '{ create_clock -name ck_$n -period 833.333 [get_ports $p]; incr n }', f'puts "OT_ETM_CLOCKS_{tag} $n"']
    if unc:
        L += ['set_clock_uncertainty -setup 60 [all_clocks]', 'set_clock_uncertainty -hold 25 [all_clocks]']
    L += [f'report_checks -path_delay {"max" if c == "tt" else "min"} -group_path_count 3 > {H}/etm_worst_{tag}_{c}.rpt',
          f'write_timing_model -library_name {libname} {outlib}', f'puts OT_ETM_DONE_{tag}_{c}',
          f'puts "OT_ETM_PEAK_{tag}_{c} [exec grep VmHWM /proc/[pid]/status]"']
    open(path, 'w').write('\n'.join(L) + '\n')

order = []
for c, C in (('tt', 'TT'), ('ff', 'FF')):
    for ch in children:
        ck = json.load(open(f'{H}/clocks_{ch}.json'))['clocks']
        tcl(f'{H}/etm_{ch}_{c}.tcl', ch, f'{H}/child_{ch}.v', ck, c, C, [], unc_child, f'{ch}_synth_{c}',
            f'{H}/{ch}_synth_{c}.lib', ch)
        order.append(f'{H}/etm_{ch}_{c}.tcl')
    ck = json.load(open(sys.argv[5]))['clocks']
    tcl(f'{H}/etm_top_{c}.tcl', top, f'{H}/parent.v', ck, c, C, [f'{H}/{ch}_synth_{c}.lib' for ch in children], True,
        f'{top}_synth_{c}', f'/out/{top}_synth_{c}.lib', 'top')
    order.append(f'top_{c}')
open(f'{H}/order.txt', 'w').write('\n'.join(order) + '\n')
PY
[ $? -eq 0 ] || exit 18
# children libs are restored per bit (lib post-pass) before the parent reads them
RUN=""
for c in tt ff; do
  for ch in ${CHILDREN//,/ }; do [ "$ch" = "-" ] && continue
    RUN="$RUN sta -no_init -no_splash -exit /out/hier/etm_${ch}_$c.tcl >> /out/etm.log 2>&1 || exit 21; python3 /tools/etm_clock_merge.py lib /out/hier/${ch}_synth_$c.lib /out/hier/clocks_$ch.json >> /out/etm.log || exit 22;"
  done
  RUN="$RUN sta -no_init -no_splash -exit /out/hier/etm_top_$c.tcl >> /out/etm.log 2>&1 || exit 23;"
done
sed -i "s#$H#/out/hier#g" $H/*.tcl
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
: > $OUT/etm.log
docker run --rm --name hdie15-etmh-$NAME-$$ --cpus=2 --memory=${MEMG:-24}g -v $SRC:/src:ro -v $OUT:/out -v $T:/tools:ro -w /out openroad/orfs:asap7lock bash -lc "
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; export PATH=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin:\$PATH; mkdir -p /tmp/lib
  for f in \$(ls $L | grep -E 'RVT_(TT|FF)'); do b=\${f%.gz}; case \$f in *.gz) zcat $L/\$f > /tmp/lib/\$b;; *) cp $L/\$f /tmp/lib/\$b;; esac; done
  $RUN true"
rc=$?
if [ $rc -eq 0 ]; then
  for c in tt ff; do python3 $T/etm_clock_merge.py lib $OUT/${TOP}_synth_$c.lib $OUT/etm_clocks.json >> $OUT/etm.log || rc=16; done
fi
echo "$NAME etm_hier rc=$rc children=$CHILDREN $(grep -E 'OT_ETM_(CLOCKS|DONE|PEAK|CLOCK_)' $OUT/etm.log | tr '\n' ' ')"
exit $rc
