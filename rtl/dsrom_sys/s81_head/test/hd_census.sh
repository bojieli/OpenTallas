#!/usr/bin/env bash
# HD-CTL 10-21: yosys parse + hierarchy -check of a head-die master, then the PRE-GATE native census
# (tools/ref_tile/native_census.py from origin/main, ASAP7 RVT TT Liberty; physical/common_flow/ot_keep_regs.tcl as the gate synth) on a yosys/ABC-mapped netlist in which the
# hard children (closed or kit-owned tiles and SRAM macros) are black boxes with port-derived abstract Liberty cells
# (clock pins = ck / clk; every other child pin is a dynamic load).  The census therefore covers this master's own glue.
# usage (cwd = synced src root holding rtl/, physical/, tools/): hd_census.sh TOP OUTDIR LIBDIR
set -u; top=${1:?top}; O=${2:?out}; L=${3:?libdir}; mkdir -p $O; O=$(cd $O && pwd)
Y=yosys; [ -x ~/.local/opentallas-tools/yosys-0.68/bin/yosys ] && Y=~/.local/opentallas-tools/yosys-0.68/bin/yosys
F=rtl/dsrom_sys/s81_head/test/hd_files.f
SRC=$(grep -v '^+' $F | grep -v '^physical/' | tr '\n' ' ')
MAC=$(grep '^physical/' $F | tr '\n' ' ')   # SRAM macro models: read as -lib (port shells, hard macros)
HARD="dsfd_mtp_seq dsfd_coll_lane_w_safe8_ntf ot_s81sl_lep_mu_ab dsdv_mu_land"
LIBS=$(ls $L/asap7sc7p5t_*RVT_TT*.lib); AL=""; for f in $LIBS; do AL="$AL -liberty $f"; done
cat > $O/parse.ys <<YS
read_verilog -lib $MAC
read_verilog -sv -DSYNTHESIS -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF $SRC
hierarchy -check -top $top
tee -o $O/parse_stat.txt stat
YS
$Y -q -l $O/parse.log $O/parse.ys > /dev/null 2>&1; rc=$?; echo "PARSE_HIER_CHECK $top rc=$rc"
[ $rc = 0 ] || { grep -m5 -i error $O/parse.log; exit 1; }
{ echo "read_verilog -lib $MAC"; echo "read_verilog -sv -DSYNTHESIS -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF $SRC"
  for h in $HARD; do echo "blackbox $h"; done
  echo "hierarchy -top $top"; echo "tcl physical/common_flow/ot_keep_regs.tcl"
  echo "synth -top $top -noshare"
  echo "dfflibmap -liberty $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib"
  echo "abc $AL"
  echo "opt_clean -purge"
  echo "tee -o $O/map.ys.stat.txt stat"
  echo "write_json $O/map.ys.mapped.json"
  echo "write_verilog -noattr $O/map.ys.mapped.v"; } > $O/map.ys
$Y -q -l $O/map.log $O/map.ys > /dev/null 2>&1; rc=$?; echo "MAP $top rc=$rc"; [ $rc = 0 ] || { grep -m5 -i error $O/map.log; exit 1; }
# abstract Liberty for the black-box hard children (ports from the mapped json)
python3 - $O/map.ys.mapped.json $O/hard.lib <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))['modules']
out = ['library(hd_hard_abstract) {']
for name, m in d.items():
    if not str(m.get('attributes', {}).get('blackbox', '0')).strip('0'):
        continue
    out.append(f'  cell({name}) {{')
    for pn, p in m['ports'].items():
        dr = p['direction']; w = len(p['bits'])
        ck = 'true' if pn in ('ck', 'clk', 'ck_K', 'ck_ML', 'ckv') else 'false'
        if w == 1:
            out.append(f'    pin({pn}) {{ direction : {dr}; clock : {ck}; }}')
        else:
            out.append(f'    bus({pn}) {{ direction : {dr}; clock : {ck}; pin({pn}[{w-1}:0]) {{ direction : {dr}; }} }}')
    out.append('  }')
out.append('}')
open(sys.argv[2], 'w').write('\n'.join(out) + '\n')
PY
lb=""; for f in $LIBS $O/hard.lib; do lb="$lb --liberty $f"; done
python3 tools/ref_tile/native_census.py --netlist $O/map.ys.mapped.v --top $top --out $O/census.json $lb > $O/census.log 2>&1
python3 - $O/census.json <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
print('CENSUS', r.get('top'), r.get('status'), 'max_dynamic_loads', r.get('max_dynamic_loads'), 'roots', r.get('roots_examined'),
      'violations', len(r.get('violations', [])), 'role_errors', len(r.get('role_errors', [])),
      'constant_output_bits', len(r.get('constant_output_bits', [])))
for e in r.get('role_errors', [])[:8]: print('  ERR', e)
for v in sorted(r.get('violations', []), key=lambda v: -v['loads'])[:15]: print('  VIOL', v['loads'], v['driver_role'], v['driver'], v['net'])
PY
grep -E "Number of cells|DFF|ot_sram|dsfd|dsdv|lep_mu" $O/map.ys.stat.txt | tail -12
