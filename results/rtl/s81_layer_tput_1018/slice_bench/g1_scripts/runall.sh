#!/bin/bash
S=/home/ubuntu/scratch/s81-lbgap/g1; R=/srv/opentallas-scratch/claude/s81-lbgap-g1
for c in ${VARS:-tt ff mshift mnogate}; do /home/ubuntu/bin/ot-run --mem 8 --threads 8 --dir $R -- env J=8 bash run_dv_slice.sh K_$c out_$c +IN=$R/K_$c/in.txt +OUT=$R/K_$c/out.txt +NCYC=300 +TRACE=$R/out_$c/trace.txt > $S/run_$c.log 2>&1 & done; wait
for c in ${VARS:-tt ff mshift mnogate}; do echo "== $c"; grep -h "TB_DV_SLICE\|DV_SLICE cycles\|NOT RUN\|build rc" $S/run_$c.log | sort -u | cut -c1-100 | head -6
  for h in ot-epyc4 ot-epyc5; do ssh -o ControlPath=none $h "test -f $R/out_$c/trace.txt && cat $R/out_$c/trace.txt" ; done > $S/tr_$c.txt 2>/dev/null
  python3 - $S/cut_ld_$c/tb_ports.json $S/tr_$c.txt <<'P'
import json,sys
P=json.load(open(sys.argv[1])); nm={p['index']:p['port'] for p in P}
for l in open(sys.argv[2]):
    c,p,v=l.split()
    if 'lnd' in nm[int(p)] or 'fault' in nm[int(p)]: print('  ', c, nm[int(p)], v.lstrip('0') or '0')
P
done
