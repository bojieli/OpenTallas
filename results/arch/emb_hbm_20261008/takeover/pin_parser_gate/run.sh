#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/scratch/codex/emb-pin-parser-gate
python3 - <<'PY'
import subprocess,json
from pathlib import Path
records={}
for name in ['qfd_emb_strip_bus92','qfd_emb_far92','qfd_emb_station92']:
 out=subprocess.check_output(['bash','-c','source "$1"; printf "%s\\n" "${PINS[@]}"','bash',name+'.env'],text=True).splitlines()
 pats=[x.rpartition('=')[0] for x in out[1::2]]
 if name=='qfd_emb_strip_bus92':
  ports=['clk','rst_n','fault']+[f'{n}[{i}]' for n,w in [('link_i',525),('link_o',525),('fault_code',8),('ce_cnt',32),('ue_info',32)] for i in range(w)]+[f'{p}{k}[{i}]' for k in range(32) for p,w in [('cmd',288),('ret',260)] for i in range(w)]
 elif name=='qfd_emb_far92':ports=['ck','lclk','rst_n','fault']+[f'{n}[{i}]' for n,w in [('hub_i',528),('hub_o',528),('emb_i',525),('emb_o',525),('kv_i',525),('kv_o',525)] for i in range(w)]
 else:ports=['clk','rst_n']+[f'{n}[{i}]' for n,w in [('cmd_i',288),('cmd_o',288),('ret_i',260),('ret_o',260)] for i in range(w)]
 t='set pats [list '+' '.join('{'+p+'}' for p in pats)+']\nset ports [list '+' '.join('{'+p+'}' for p in ports)+']\nset bad 0\nforeach port $ports {set n 0;foreach pat $pats {if {[regexp -- $pat $port]} {incr n}};if {$n!=1} {incr bad}}\nputs "ports [llength $ports] bad $bad"\nif {$bad} {exit 1}\n'
 Path(name+'.tcl').write_text(t)
 records[name]=subprocess.check_output(['tclsh'],input=t,text=True).strip()
Path('gate.json').write_text(json.dumps({'verdict':'PASS','scope':'Tcl ARE parser and exhaustive actual wrapper/station port inventory; no route/fp placement claim','records':records},indent=2)+'\n')
print(records)
PY
