#!/bin/bash
# find dbg_r hierarchical refs that do not exist in the RTL: lint-only build with a stub gate (dbg_g only)
set -u
S=/srv/opentallas-scratch2/claude/lec-icg2-1026/sim; K=/srv/opentallas-scratch2/claude/lec-icg-1026/kits/ot_v41_rom_elem_q_qxpq_w10_gb_gbcgr8
W=$S/$1
N=$(grep -o 'NDBG = [0-9]*' $W/dbg_rtl.svh | awk '{print $3}')
sed -n '/^module gl_ot_v41_rom_elem_q_qxpq_w10_gb(/,/;/p' $W/gate.v > $W/stub.v
python3 - $W/gate.v $W/stub_full.v $N <<'PY'
import re,sys
src=open(sys.argv[1]).read(); n=int(sys.argv[3])
m=re.search(r'\nmodule gl_ot_v41_rom_elem_q_qxpq_w10_gb\((.*?)\nendmodule', src, re.S).group(0)
i=m.index(');')
hdr=m[:i+2]; rest=m[i+2:]
decl=[l for l in rest.split('\n') if re.match(r'\s*(input|output)\b', l)]
open(sys.argv[2],'w').write(hdr+'\n'+'\n'.join(decl)+f'\n  wire [{n-1}:0] dbg_g = 0;\nendmodule\n')
PY
RTL=$(grep '^export VERILOG_FILES' $K/config.mk | sed 's/.*= //; s#/work/rtl/#'$K'/rtl/#g' | tr ' ' '\n' | grep -v '_bb\.v$' | tr '\n' ' ')
docker run --rm --memory 32g -u $(id -u):$(id -g) -v $S:$S -v $K:$K:ro -w $W --entrypoint verilator verilator/verilator:v5.032 \
  --lint-only --timing -Wno-fatal -Wno-lint -Wno-style --error-limit 100000 -DSYNTHESIS --top-module tb_lecicg2 -I$W -I$K/rtl \
  $S/cells.v $RTL $W/stub_full.v $S/tb_lecicg2.sv > $W/lint.log 2>&1
grep -o "dbg_rtl.svh:[0-9]*" $W/lint.log | sort -u | sed 's/.*://' > $W/badlines.txt
python3 - $W <<'PY'
import sys,re
w=sys.argv[1]
bad=set(int(x) for x in open(w+'/badlines.txt'))
lines=open(w+'/dbg_rtl.svh').read().split('\n')
names={int(l.split('\t')[0]): l.split('\t')[2] for l in open(w+'/dbg_names.tsv') if l.strip()}
out=[]
for ln in bad:
    m=re.match(r'assign dbg_r\[(\d+)\]', lines[ln-1]); out.append(names[int(m.group(1))])
open(w+'/drop.txt','w').write('\n'.join(out)+'\n')
print('bad rtl refs', len(out))
PY
grep -v "dbg_rtl.svh" $W/lint.log | grep -m5 "%Error"
