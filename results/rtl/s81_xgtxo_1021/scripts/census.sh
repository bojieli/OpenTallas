#!/bin/bash
# RG-FFN mapped census: census.sh <tag> <top> <defines or -> <rtl files relative to src...>
# synth as results/rtl/s81_rd_pair_cut_1019/sizing (yosys synth -flatten, dfflibmap/abc TT RVT, same dont_use) then
# tools/ref_tile/native_census.py (origin/main) on the mapped netlist.
tag=$1; top=$2; defs=$3; shift 3
S=$(pwd); C=$S/out_$tag; mkdir -p $C
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
DU=$(cat $S/dontuse.txt)
D=""; [ "$defs" != "-" ] && for d in $defs; do D="$D -D$d"; done
{ echo "read_verilog -sv -DSYNTHESIS $D $(for f in "$@"; do printf ' /src/%s' $f; done)"
  echo "hierarchy -check -top $top"
  # ORFS SYNTH_CANONICALIZE_TCL hook physical/common_flow/ot_keep_regs.tcl (keep on flops driving keep wires)
  echo "proc"
  echo 'select -set ot_kw w:* a:keep %i'
  echo 'select -set ot_kc @ot_kw %ci1 t:$*dff* t:$*dlatch* %u %i'
  echo 'techmap @ot_kc'
  echo 'select -set ot_kc @ot_kw %ci1 t:$*dff* t:$*dlatch* t:$_*DFF* t:$_*LATCH* %u %u %u %i'
  echo 'setattr -set keep 1 @ot_kc'
  echo 'select -clear'
  echo "synth -top $top -flatten"
  echo "dfflibmap -liberty $C/seq.lib"
  echo "abc -liberty $C/ao.lib -liberty $C/invbuf.lib -liberty $C/oa.lib -liberty $C/seq.lib -liberty $C/simple.lib $DU -D 833.333"
  echo "setundef -zero"; echo "splitnets -ports"; echo "opt_clean -purge"
  echo "tee -o $C/stat.txt stat -liberty $C/ao.lib -liberty $C/invbuf.lib -liberty $C/oa.lib -liberty $C/seq.lib -liberty $C/simple.lib"
  echo "write_verilog -noattr $C/mapped.v"; } > $C/synth.ys
start=$(date +%s)
docker run --rm -v $S/src:/src:ro -v $C:$C -w $C openroad/orfs:latest bash -lc "
 for p in SEQ_RVT_TT_nldm_220123:seq AO_RVT_TT_nldm_211120:ao INVBUF_RVT_TT_nldm_220122:invbuf OA_RVT_TT_nldm_211120:oa SIMPLE_RVT_TT_nldm_211120:simple; do
   f=\$(ls $L/asap7sc7p5t_\${p%%:*}.lib* | head -1); case \$f in *.gz) zcat \$f > $C/\${p##*:}.lib;; *) cp \$f $C/\${p##*:}.lib;; esac; done
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l $C/yosys.log -s $C/synth.ys"
rc=$?
python3 $S/src/tools/ref_tile/native_census.py --netlist $C/mapped.v --top $top --liberty $C/seq.lib --liberty $C/ao.lib --liberty $C/invbuf.lib --liberty $C/oa.lib --liberty $C/simple.lib --out $C/native_census.json > $C/census.log 2>&1
python3 - $C/native_census.json $tag <<'P'
import json,sys,collections
r=json.load(open(sys.argv[1])); v=r.get('violations',[])
rst=[c for c in r.get('driver_counts',[]) if c['driver']=='rst_n']
print('CENSUS',sys.argv[2],r.get('status'),'max',r.get('max_dynamic_loads'),'over32',len(v),'seq_over32',sum(1 for x in v if x['driver_role']=='sequential'),'rst_n_loads',rst[0]['loads'] if rst else 0,'errors',len(r.get('role_errors',[])))
for x in sorted(v,key=lambda x:-x['loads'])[:40]: print('  ',x['loads'],x['driver_role'],x['driver'],x['net'])
P
grep -E "Chip area|cells$" $C/stat.txt | head -3
echo "DONE $tag rc=$rc secs=$(($(date +%s)-start))"
