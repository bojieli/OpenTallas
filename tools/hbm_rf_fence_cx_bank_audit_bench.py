#!/usr/bin/env python3
"""Small topology fixture gate. This is not an actual mapped-bank PASS."""
import copy, json
from hbm_rf_fence_cx_bank_audit import audit

def fixture():
    rows = []
    def pin(cell, master, p, direction, net): rows.append([cell, master, p, direction, net])
    for skid, tail in [('u_cap', 18), ('u_hw', 9)]:
        for b in range(65):
            pre = '%s.banked.bank[%d].local_slice.' % (skid,b)
            for role in ('s_v', 'out_v', 'in_ready'):
                c = pre + role + '$_DFF_PN0_'
                pin(c,'DFFASRHQNx1','D','INPUT','input')
                pin(c,'DFFASRHQNx1','QN','OUTPUT',pre+role)
            for role in ('s_d','out_d'):
                for bit in range(64 if b<64 else tail):
                    c = pre+role+'[%d]$_DFF_P_' % bit
                    g = pre+role+'_gate[%d]' % bit
                    pin(g,'AO21x1','A','INPUT',pre+'s_v')
                    if role=='out_d': pin(g,'AO21x1','B','INPUT',pre+'out_v')
                    pin(g,'AO21x1','Y','OUTPUT',g+'_net')
                    pin(c,'DFFHQNx1','D','INPUT',g+'_net')
                    pin(c,'DFFHQNx1','QN','OUTPUT',c+'_q')
    return rows
r = fixture()
results = {'positive': audit(r)['status']}
mutants = {}
mutants['missing_bank'] = [x for x in r if not x[0].startswith('u_hw.banked.bank[64].')]
m = copy.deepcopy(r)
for x in m:
    if x[0].startswith('u_hw.banked.bank[1].') and x[1]=='AO21x1' and x[2]=='A':
        x[4]='u_hw.banked.bank[0].local_slice.s_v'
mutants['globalized_capture'] = m
m = copy.deepcopy(r)
for x in m:
    if x[0]=='u_cap.banked.bank[1].local_slice.s_v$_DFF_PN0_' and x[3]=='OUTPUT':
        x[4]='u_cap.banked.bank[0].local_slice.s_v'
mutants['shared_control_output'] = m
for name,m in mutants.items():
    try: audit(m)
    except ValueError as e: results[name] = {'status':'REJECTED','reason':str(e)}
    else: raise RuntimeError('mutant survived '+name)
print(json.dumps(results,indent=2))
