#!/usr/bin/env python3
"""QC-TYPES-10/CTLM 11-08: plan event qc53v4w_ctlmfq = v4w (e5dc7eacb745) minus the 4 tt_ctlm hard cores
u_bound.u_core.u_gi.u_cal.g_fifo[0..3].u_fifo (ot_sram_1r1w_64x512_m1_r2c2), which the CALREG[0] FQREG cpub39_1 no longer has.
usage: mk_plan_ctlmfq.py V4W_JSON OUT_JSON"""
import json,sys,hashlib,copy
src,out=sys.argv[1:3]
raw=open(src,'rb').read(); assert hashlib.sha256(raw).hexdigest().startswith('e5dc7eacb745'),'base must be v4w e5dc7eacb745'
d=json.loads(raw); base=copy.deepcopy(d)
hc=d['partition_types']['tt_ctlm']['hard_cores']
gone=[f'u_bound.u_core.u_gi.u_cal.g_fifo[{i}].u_fifo' for i in range(4)]
keep=[h for h in hc if h['inst'] not in gone]
assert len(hc)-len(keep)==4 and all(h['module']=='ot_sram_1r1w_64x512_m1_r2c2' for h in hc if h['inst'] in gone)
d['partition_types']['tt_ctlm']['hard_cores']=keep
note=d['partition_types']['tt_ctlm'].get('note','')
d['partition_types']['tt_ctlm']['note']=note+' | QC-TYPES-10/CTLM 11-08: CALREG[0] FQREG cpub39_1 (u_gi.u_cal ring + nx_q), the 4 g_fifo 64x512 SRAMs removed from hard_cores; 0 pin cycles, 0 edges'
# indentation: keep the base file's style
ind=1 if raw[:4]==b'{\n "' else (2 if raw[:5]==b'{\n  "' else None)
txt=json.dumps(d,indent=ind)+('\n' if raw.endswith(b'\n') else '')
open(out,'w').write(txt)
# proof: every other key identical
b2=copy.deepcopy(base); n2=json.loads(txt)
b2['partition_types']['tt_ctlm']['hard_cores']=keep; b2['partition_types']['tt_ctlm']['note']=n2['partition_types']['tt_ctlm']['note']
assert b2==n2
diffs=[k for k in base if base[k]!=n2.get(k)]; tdiff=[k for k in base['partition_types'] if base['partition_types'][k]!=n2['partition_types'][k]]
print('PLAN', hashlib.sha256(txt.encode()).hexdigest(), 'top-level keys changed', diffs, 'types changed', tdiff,
      'tt_ctlm keys changed', [k for k in base['partition_types']['tt_ctlm'] if base['partition_types']['tt_ctlm'][k]!=n2['partition_types']['tt_ctlm'][k]],
      'hard_cores', len(hc), '->', len(keep), 'indent', ind)
