#!/usr/bin/env python3
"""Complete v16 host target coverage using existing programme-target/status masters.
Run after cp1_spec_gen.py/cp2_spec_gen.py. Idempotent; no on-die execution handshake.
"""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SP = ROOT / 'tools/hbm_die_v15/v16_specs'
Q = ('SW', 'SE', 'NW', 'NE')
def read(n): return json.loads((SP / (n + '.json')).read_text())
def write(n, d): (SP / (n + '.json')).write_text(json.dumps(d, indent=1) + '\n')
s = dict(region='host_completion', instances=[], edges=[], clocks=[], straps=[], gaps=[],
         notes=['Four VM HBM-fill calendars use existing ot_static_program_target PCW10, TARGET56..59. '
                'Host status uses one existing parameterised pin-registered join for all67 admitted targets; '
                'no empty-participation child join can veto a launch. Native physical timing/placement remains open.'])
for k, q in enumerate(Q):
    n, g = f'cp_fill_{q}', f'vmfc_{q}'
    s['instances'].append(dict(name=n, master='ot_static_program_target',
        source='rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv',
        params=dict(TARGET=f"8'd{56+k}", PCW=10), slot=None, owner='H-NETLIST',
        note='Host F20 fill-calendar programme collar. Two transport edges; compiler co-launches VM fills with service-group K windows.'))
    s['clocks'].append(dict(inst=n, port='clk', domain='stream', kind='clock'))
    def e(src, dst, w): s['edges'].append(dict(src=src, dst=dst, bits=w, clock='stream',
        basis='Existing ot_static_program_target PCW10 port ABI -> ot_vms_calendar_static W89 fill calendar'))
    for p,w in [('cfg_v',1),('cfg_target',8),('cfg_addr',12),('cfg_data',256),('desc_v',1),
                ('desc_base',12),('desc_limit',13),('desc_loops',16),('launch_v',1)]:
        e(['host_cp_ingress',p],[n,p],w)
    for a,b,w in [('program_cfg_we','cfg_we',1),('program_cfg_addr','cfg_addr',10),
                  ('program_cfg_data','cfg_data',256),('program_start_v','start_v',1),
                  ('program_start_base','start_base',10),('program_start_limit','start_limit',11),
                  ('program_start_loops','start_loops',16)]: e([n,a],[g,b],w)
    e([g,'active'],[n,'program_active'],1)
# One existing standard-width calendar per quadrant drives all local endpoint RX pins.
# W187 matches the current universal calendar hardening class; unused high bits stay outputs.
links=dict(SW=('S0','S1','S2'),SE=('S3','S4'),NW=('N0','N1'),NE=('N2','N3'))
for k,q in enumerate(Q):
    n,g=f'cp_ep_{q}',f'epcal_{q}'
    s['instances'] += [dict(name=n,master='ot_static_program_target',
        source='rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv',
        params=dict(TARGET=f"8'd{132+k}",PCW=10),slot=None,owner='H-NETLIST',note='Endpoint RX calendar host collar, existing master'),
        dict(name=g,master='ot_vms_calendar_static',
        source='rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv',
        params=dict(W=187),slot=None,owner='H-NETLIST',note='Standard W187 programme calendar; 19 RX-control bits per local endpoint, high bits unused outputs. Compiler arm/read/release slots; no ready-driven rescheduling.')]
    for i in (n,g): s['clocks'].append(dict(inst=i,port='clk',domain='stream',kind='clock'))
    for p,w in [('cfg_v',1),('cfg_target',8),('cfg_addr',12),('cfg_data',256),('desc_v',1),
                ('desc_base',12),('desc_limit',13),('desc_loops',16),('launch_v',1)]: e(['host_cp_ingress',p],[n,p],w)
    for a,b,w in [('program_cfg_we','cfg_we',1),('program_cfg_addr','cfg_addr',10),
                  ('program_cfg_data','cfg_data',256),('program_start_v','start_v',1),
                  ('program_start_base','start_base',10),('program_start_limit','start_limit',11),
                  ('program_start_loops','start_loops',16)]: e([n,a],[g,b],w)
    e([g,'active'],[n,'program_active'],1)
    for j,lk in enumerate(links[q]):
        lo=j*19
        for port,w in [('rx_arm_v',1),('rx_arm_bank',1),('rx_block_words',7),('rx_release_v',1),
                       ('rx_release_bank',1),('rx_slot_v',1),('rx_slot_bank',1),('rx_slot_index',6)]:
            e([g,'calendar',lo,lo+w],['ep_'+lk,port],w);lo+=w
        assert lo==(j+1)*19
# Universal calendar fields are zero-extended whole packed fields by the compiler.
# Connect each original quadrant ABI to its low contiguous field bits, preserving its lane packing.
s['drop_v15_edges']=[]
for q,widths in dict(SW=(8,4,8,16,4),SE=(2,1,2,8,2),NE=(2,1,2,8,2)).items():
    for field,w in zip(('client_seq','response_enable','response_seq','bank_client','hub_ring_client'),widths):
        s['drop_v15_edges'].append(f'calendar_{q}_{field}')
        e([f'calendar_{q}',field,0,w],[f'hb_vms_{q}',field,0,w],w)
        s['edges'][-1]['basis']='Universal W187 field contains zero-extended original per-quadrant packed value (tools/hbm_vm_static_calendar.py pack); exact low-field slice preserves all original client lane bits.'
write('host_completion',s)
# Extend the existing root, preserving its original target/fault ordering and host fault pins.
c = read('cp2')
root = next(i for i in c['instances'] if i['name']=='host_status')
# Remove prior completion suffix when repeated.
original_nt, original_nf = 11, 19
c['edges'] = [e for e in c['edges'] if not (e['dst'][:2] in
    [['host_status','t_ready'],['host_status','t_active'],['host_status','t_fault']] and
    e['dst'][2] >= (original_nf if e['dst'][1]=='t_fault' else original_nt))]
base_targets = [48,52,53,54,55,112,116,117,118,119,120]
rows = []
for n, r in read('cp1')['status_outputs'].items():
    rows.append((r['target'],r['configured'],r['active'],[r['fault']] + ([r['target_fault']] if 'target_fault' in r else [])))
for k,q in enumerate(Q):
    rows.append((56+k,[f'cp_fill_{q}','configured'],[f'vmfc_{q}','active'],
                 [[f'cp_fill_{q}','fault'],[f'vmfc_{q}','fault']]))
    rows.append((108+k,[f'hc_tgt_{q}','configured'],[f'hc_{q}','program_active'],
                 [[f'hc_tgt_{q}','fault'],[f'hc_{q}','fault']]))
for k,q in enumerate(Q):
    rows.append((132+k,[f'cp_ep_{q}','configured'],[f'epcal_{q}','active'],
                 [[f'cp_ep_{q}','fault'],[f'epcal_{q}','fault']]+[['ep_'+lk,'fault'] for lk in links[q]]))
rows.sort()
nt,nf=original_nt,original_nf
for t,ready,active,faults in rows:
    for p, src, bit in [('t_ready',ready,nt),('t_active',active,nt)]:
        c['edges'].append(dict(src=src+[0,1],dst=['host_status',p,bit,bit+1],bits=1,
                              clock='stream',basis=f'TARGET{t} real collar/calendar status; static install/launch interlock only'))
    for src in faults:
        c['edges'].append(dict(src=src+[0,1],dst=['host_status','t_fault',nf,nf+1],bits=1,
                              clock='stream',basis=f'TARGET{t} actual sticky fault to host status'))
        nf+=1
    nt+=1
all_targets=base_targets+[r[0] for r in rows]
assert len(all_targets)==len(set(all_targets))==67
root['params'].update(NT=nt,NF=nf,TGTS=f"{8*nt}'h"+''.join(f'{t:02x}' for t in reversed(all_targets)))
root['note']='All67 actual admitted host targets: participation-filtered ready, active and fault from real collars/calendars. Existing pin-registered parameterised master; no dynamic production scheduling. Physical closure remains open.'
write('cp2',c)
h=read('host_misc')
for i in h['instances']:
    if i['name']=='host_cp_ingress':
        i['params']['TARGET_MASK']=f"256'h{sum(1<<t for t in all_targets):x}"
write('host_misc',h)
# This gap is now a real seven-port collar per quadrant, not a declaration-only closure.
v=read('vmsm');v['gaps']=[g for g in v['gaps'] if g['id']!='G-VMFILL-CAL'];write('vmsm',v)
print(f'HOST_TARGET_COVERAGE {nt} targets, {nf} faults, 4 fill collars and 4 endpoint calendars')

i=read('idxcoll');i['gaps']=[g for g in i['gaps'] if g['id']!='G-CIL-EPRXCAL'];write('idxcoll',i)
