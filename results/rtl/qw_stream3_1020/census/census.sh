#!/bin/bash
# quick yosys 0.68 mapped census (ASAP7 RVT TT, merged liberty for ABC); authoritative census = ORFS gate
set -uo pipefail
cd "$(dirname "$0")/src"; OUT=../out/${CTAG:-census}; mkdir -p $OUT
L=$HOME/.local/opentallas-pdk-asap7/lib/NLDM; Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys
python3 - $L $OUT/combined.lib <<'PYMERGE'
import re,sys
from pathlib import Path
files=sorted(Path(sys.argv[1]).glob('*RVT_TT*.lib'))
first=next(x for x in files if '_SEQ_' in x.name); files=[first]+[x for x in files if x!=first]
base=first.read_text();start=re.search(r'\bcell\s*\(',base).start()
header=base[:start];cells=[];templates=[];seen=set(re.findall(r'(?:lu_table_template|power_lut_template)\s*\(([^)]+)\)',header))
for f in files:
 s=f.read_text();i=re.search(r'\bcell\s*\(',s).start();cells.append(s[i:s.rfind('}')])
 for m in re.finditer(r'(?:lu_table_template|power_lut_template)\s*\(([^)]+)\)',s[:i]):
  if m.group(1) in seen:continue
  seen.add(m.group(1));b=s.index('{',m.end());depth=1;e=b+1
  while depth:
   depth+=(s[e]=='{')-(s[e]=='}');e+=1
  templates.append(s[m.start():e])
Path(sys.argv[2]).write_text(header+'\n'.join(templates)+'\n'+'\n'.join(cells)+'\n}\n')
PYMERGE
C=$OUT/combined.lib
cat > $OUT/synth.ys <<YS
read_liberty -lib $C
read_verilog -sv rtl/qwen_dv/qfd_dv_stream_tile.sv
hierarchy -check -top qfd_dv_stream_tile
proc
select -set ot_kw w:* a:keep %i
select -set ot_kc @ot_kw %ci1 t:\$*dff* t:\$*dlatch* %u %i
techmap @ot_kc
select -set ot_kc @ot_kw %ci1 t:\$*dff* t:\$*dlatch* t:\$_*DFF* t:\$_*LATCH* %u %u %u %i
setattr -set keep 1 @ot_kc
select -clear
synth -top qfd_dv_stream_tile -flatten
dfflibmap -liberty $C
abc -liberty $C
opt_clean
stat -liberty $C
write_verilog -noattr $OUT/net.v
YS
$Y -q -l $OUT/yosys.log -s $OUT/synth.ys > /dev/null 2>&1
echo "yosys exit $?" > $OUT/status
NL=""; for f in $L/*RVT_TT*.lib; do NL="$NL --liberty $f"; done
python3 tools/ref_tile/native_census.py --netlist $OUT/net.v --top qfd_dv_stream_tile $NL --out $OUT/native_census.json > $OUT/census.log 2>&1
echo "census exit $?" >> $OUT/status
cat $OUT/status; tail -3 $OUT/census.log
