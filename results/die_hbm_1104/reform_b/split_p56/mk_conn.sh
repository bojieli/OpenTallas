#!/bin/bash
# conn json of the part 56 composition: mk_conn.sh REPO SPLITDIR  (yosys on PATH or YOSYS env)
set -eu
R=$1; D=$2; C=ot_hbm_svc_vm_kshare_splitstrap__v8e478a; Y=${YOSYS:-yosys}; T=$(mktemp -d /tmp/kshconn.XXXX)
python3 -I - "$R" "$T/bb.sv" <<'P'
import re,sys
s=open(sys.argv[1]+'/rtl/hbm_accel/loader/service_native/ot_hbm_svc_vmks_forms.sv').read()
o=[]
for m in ['ot_hbm_svc_vmks_t0','ot_hbm_svc_vmks_t1']:
    b=re.search(r'module '+m+r' #\(.*?\) \((.*?)\);',s,re.S).group(1)
    o.append('(* blackbox *) module %s(%s);\nendmodule\n'%(m,b))
open(sys.argv[2],'w').write(''.join(o))
P
$Y -q -p "read_verilog -sv $T/bb.sv $D/${C}__p56comp.sv $D/${C}__p56glue.sv; hierarchy -top $C; proc; flatten; opt_clean; write_json $T/n.json" > $T/y.log 2>&1 || { tail -5 $T/y.log; exit 1; }
python3 -I $R/results/die_hbm_1103/reform/split_p6/split_conn.py $T/n.json $C $D/$C.conn.json
python3 -I - $D/$C.conn.json <<'P'
import json,sys
c=json.load(open(sys.argv[1]));print(c['top'])
for s in c['subs']:
    b=s['bits'];print(s['inst'],s['module'],'bits',len(b),'seam',sum(1 for v in b.values() if v['peer']),'to top',sum(1 for v in b.values() if v.get('top')or v.get('pins')))
P
rm -rf $T
