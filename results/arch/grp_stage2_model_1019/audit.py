#!/usr/bin/env python3
"""Bounded read-only source identity/analytical-accounting audit, no EDA."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
for name,expected in json.loads((HERE/'inputs.json').read_text()).items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
m=json.loads((HERE/'model.json').read_text())
assert sum(v['count']*v['used_state_bits_each'] for v in m['logical_state_per_variant'].values())==16053
assert 28*4744+4*4251==149836
assert 16053+1092+4744==21889 and 16053+1092+4251==21396
bits=json.loads((HERE/'o_pc_bits.json').read_text())['all_four_ports_each_variant']
assert len(bits)==128 and sum(v['original_clock']=='ck' for v in bits.values())==33
s=(ROOT/'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_private0.sv').read_text()
for name,body in re.findall(r'module (\w+).*?\n\);(.*?)endmodule',s,re.S):
    for fault in ['w_slg__fault','w_lcal__fault','w_fcal__fault','w_phase__fault_hbm']:
        assert len(re.findall(r'\b'+fault+r'\b',body))==2,(name,fault)
    assert 'assign y__est__0_1 = x__est;' in body
    assert 'w_phase__layer_h, w_phase__epoch_h, w_phase__ctrl_go_h, w_lcal__r_sector' in body
b=json.loads((HERE/'boundary.json').read_text())
assert [(v['input_bits'],v['output_bits']) for v in b.values()]==[(1701,3047),(1479,2776)]
chains=json.loads((HERE/'selected_chains.json').read_text())
for name,c in chains.items():
    assert len(c['groups'])==32
    assert sum(len(i['EST_consumers']) for i in c['groups'])==128
    assert max(len(i['downstream_control_path_from_consumer_to_root']) for i in c['groups'])==8
h=json.loads((HERE/'health_delta.json').read_text())
assert 128+64+128+32==h['collector_candidate']['source_plus_collector_FF_floor']==352
assert len(h['rows'])==4
print('PASS exact hashes; source-only omitted-fault references; logical state; ABI; 128-bit domains; two 32-group/128-PC chain ledgers; health delta arithmetic')
