from pathlib import Path
import json,sys
R=Path('/srv/opentallas-scratch2/claude/codex-hbm-inj-reconcile-1106')
sys.path.insert(0,str(R)); import face_shell
f=R/'rtl/ot_hgi_coll_inj_idx_join_rg.sv'
a=face_shell.analyze([f], 'ot_hgi_coll_inj_idx_join_rg__fcore',params={'INJLAT':12},workdir=R/'analysis',log=R/'analysis.log')
(R/'def_use.json').write_text(json.dumps(a,indent=2)+'\n')
expected={'inj_rd_r1':[1],'idx_tx_h_r1':list(range(102,132))}
for p,bits in expected.items():
 assert all(i in a['unread_in'].get(p,[]) for i in bits),(p,a['unread_in'].get(p))
 assert all(a['in_fanout'][f'{p}[{i}]']==0 for i in bits)
assert a['in_fanout']['idx_tx_h_r1[101]']>0
assert a['in_fanout']['inj_rd_r1[0]']>0
print('EXACT_BARE_CORE_DEAD_INPUTS PASS31; low-bit live controls PASS', {p:a['unread_in'][p] for p in expected})
