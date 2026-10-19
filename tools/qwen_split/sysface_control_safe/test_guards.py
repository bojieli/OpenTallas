#!/usr/bin/env python3
"""Negative controls for errors a mechanical physical-source transform can make."""
import copy,json
from pathlib import Path
from check_graph import check
from generate import generate
p=Path('cold');original=json.loads((p/'original.json').read_text());candidate=json.loads((p/'generated/graph.json').read_text());receipt=json.loads((p/'generated/receipt.json').read_text())
check(original,candidate,receipt)
passed=[]
def negative(label,mutate):
 c=copy.deepcopy(candidate);r=copy.deepcopy(receipt);mutate(next(iter(c['modules'].values())),r)
 try:check(original,c,r)
 except (AssertionError,KeyError):passed.append(label);return
 raise AssertionError('accepted corrupt candidate '+label)
copy_name=receipt['copies'][0]['cell'];buf_name=receipt['buffers'][0]['cell']
for port in ['D','C','R']:
 negative('copied_'+port,lambda m,r,port=port:m['cells'][copy_name]['connections'].__setitem__(port,['0']))
negative('enable_priority',lambda m,r:m['cells'][copy_name].__setitem__('type','$_DFF_P_'))
negative('lost_equation',lambda m,r:m['cells'].pop(copy_name))
negative('reset_short',lambda m,r:m['cells'][next(x['cell'] for x in r['forest'] if x['depth']==3)]['connections'].__setitem__('R',[next(x['q'] for x in r['forest'] if x['depth']==1)]))
negative('buffer_cycle',lambda m,r:m['cells'][buf_name]['connections'].__setitem__('A',m['cells'][buf_name]['connections']['Y']))
negative('abstract_buffer',lambda m,r:m['cells'][buf_name].__setitem__('type','fake_buf'))
negative('untyped_buffer_pin',lambda m,r:m['cells'][buf_name]['port_directions'].pop('A'))
manifest=copy.deepcopy(receipt['manifest']);manifest['parameters']['COLD_START_OFS']+=1
try:generate(original,manifest)
except AssertionError:passed.append('unsupported_profile')
else:raise AssertionError('unsupported profile accepted')
assert len(passed)==10
print('SYSFACE_SAFE_GUARDS_PASS positives1 negatives10 '+','.join(passed))
