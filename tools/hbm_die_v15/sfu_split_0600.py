#!/usr/bin/env python3
"""H-NETLIST 0600 (H-SU 697997629): sfucore_<q> = ot_hgi_sfu_core_split #(LWB15, LG_PATH24) + new sfup_<q> =
ot_hgi_sfu_programme_store #(PAGE_AW1) in the sfus_<q> slot. Host cfg/start/status nets move to sfup_<q>; io_word and
compiler_control run sfup -> sfucore point to point. Uniform +3 stream edges per invocation (compiler: SFU IO calendar
issue 3 edges earlier), status +2. Idempotent: run before complete_host_targets_2330.py (which adds the sfup fault bit).
"""
import json
from pathlib import Path
SP = Path(__file__).resolve().parent / 'v16_specs'
Q = ('SW', 'SE', 'NW', 'NE')
STORE_IN = {'cfg_we', 'cfg_stripe', 'cfg_addr', 'cfg_data', 'start_base', 'start_limit', 'start_loops', 'io_cfg_we',
            'io_cfg_stripe', 'io_cfg_addr', 'io_cfg_data', 'io_start_v', 'io_start_base', 'io_start_limit', 'io_start_loops'}
STORE_OUT = {'programme_active', 'programme_done', 'programme_ordinal', 'io_active', 'io_done', 'io_ordinal'}
B = 'H-NETLIST 0600 SFU split (H-SU 697997629, receipt results/rtl/hbm_sfu_split_1016/receipt.json)'
s = json.loads((SP / 'su_sfu.json').read_text())
names = {i['name'] for i in s['instances']}
for i in s['instances']:
    if i['name'] in {f'sfucore_{q}' for q in Q}:
        i.update(master='ot_hgi_sfu_core_split', source='rtl/hbm_accel/generic/peers/ot_hgi_sfu_core_split.sv',
                 params={'LWB': 15, 'LG_PATH': 24})
        i['note'] = 'SFU core minus both calendars (16 closed ot_su12_sfu lanes + 80 operand SRAMs); ' + B
for q in Q:
    if f'sfup_{q}' not in names:
        s['instances'].append(dict(name=f'sfup_{q}', master='ot_hgi_sfu_programme_store',
                                   source='rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store.sv', params={'PAGE_AW': 1},
                                   slot=f'sfus_{q}', owner='H-SU', note='SFU programme + IO calendars (22 1024x256 SRAMs), pin-registered; ' + B))
        s['clocks'] += [dict(inst=f'sfup_{q}', port='clk', domain='stream', kind='clock'),
                        dict(inst=f'sfup_{q}', port='rst_n', domain='stream', kind='reset')]
        for p, w in [('io_word', 471), ('compiler_control', 1742)]:
            s['edges'].append(dict(src=[f'sfup_{q}', p, 0, w], dst=[f'sfucore_{q}', p, 0, w], bits=w, clock='stream', basis=B))
for g in s.get('gaps', []):
    for a in g.get('affects', []):
        if a[0].startswith('sfucore_') and (a[1] in STORE_IN or a[1] in STORE_OUT):
            a[0] = 'sfup_' + a[0][8:]
(SP / 'su_sfu.json').write_text(json.dumps(s, indent=1) + '\n')
c = json.loads((SP / 'cp2.json').read_text())
for e in c['edges']:
    if e['dst'][0].startswith('sfucore_') and e['dst'][1] in STORE_IN:
        e['dst'] = ['sfup_' + e['dst'][0][8:]] + list(e['dst'][1:])
    if e['src'][0].startswith('sfucore_') and e['src'][1] in STORE_OUT:
        e['src'] = ['sfup_' + e['src'][0][8:]] + list(e['src'][1:])
(SP / 'cp2.json').write_text(json.dumps(c, indent=1) + '\n')
print('sfu_split_0600 applied')
