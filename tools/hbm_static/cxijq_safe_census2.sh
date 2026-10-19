#!/bin/bash
# LH-SU 10-19: generic-Yosys census over EVERY module (the r2 census read only the top, so copy internals were unchecked).
# Proves the 8 COPY_ID paramods (64 onehot + 20 ctl + 4 reset each = 512 kept onehot) survive, and lists every net > 32 loads.
set -euo pipefail
mkdir -p census
sha256sum rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv > census/source.sha256
yosys -Q -T -p 'read_verilog -sv -DSYNTHESIS rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv; chparam -set SAFE_GATHER 1 ot_hbm_su_static_cxport_ij_q; hierarchy -top ot_hbm_su_static_cxport_ij_q; synth -top ot_hbm_su_static_cxport_ij_q -noabc; stat; write_json census/synth.json' > census/yosys.log 2>&1
python3 - <<'CENSUS'
import json,collections
mods=json.load(open('census/synth.json'))['modules']
out={'modules':{}, 'over32':[]}
for mn,m in mods.items():
 loads=collections.Counter();drivers={};names=collections.defaultdict(list)
 for n,o in m['netnames'].items():
  for b in o['bits']:
   if isinstance(b,int):names[b].append(n)
 for n,c in m['cells'].items():
  for p,bits in c['connections'].items():
   if c['port_directions'][p]=='input':loads.update(b for b in bits if isinstance(b,int))
   else:
    for b in bits:drivers[b]=(n,c['type'])
 ct=collections.Counter(c['type'] for c in m['cells'].values())
 ff=sum(v for k,v in ct.items() if 'DFF' in k)
 out['modules'][mn]={'cells':len(m['cells']),'ff':ff,'max_loads':max(loads.values()) if loads else 0,
   'paramod_children':sum(v for k,v in ct.items() if k.startswith('$paramod'))}
 for b,v in loads.most_common():
  if v<=32: break
  out['over32'].append({'module':mn,'bit':b,'loads':v,'driver':drivers.get(b),'names':names[b][:3]})
copies=[k for k in mods if 'ot_hbm_cxijq_sel_copy' in k]
out['sel_copies']=len(copies); out['onehot_ff_total']=sum(out['modules'][k]['ff'] for k in copies)
json.dump(out,open('census/fanout_all.json','w'),indent=1)
print(json.dumps(out,indent=1))
CENSUS
echo CENSUS2_DONE
