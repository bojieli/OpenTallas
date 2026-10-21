from pathlib import Path
import json
O=Path.cwd()
def rows(case):
 result={}
 for line in(O/case/'replay.log').read_text().splitlines():
  if not line.startswith('OBS '):continue
  d=dict(x.split('=',1)for x in line.split()[1:]if '='in x)
  result[int(d['qt'])]=d
 return result
def bank(d,name):return int(next(v for k,v in d.items()if 'g_bank__BRA__0__KET__'in k and k.endswith('__DOT__'+name)),16)
def val(d,name):return int(next(v for k,v in d.items()if k.endswith(name)),16)
good=rows('drain1');identity=rows('absent_reader_identity');lifetime=rows('missing_control_lifetime');drain=rows('old_drain_gap');fill=rows('old_fill_deadline')
assert val(identity[2699],'sfault')==0 and val(identity[2700],'sfault')==1
assert all(val(good[t],'sfault')==0 for t in [2699,2700,2724])
assert val(lifetime[2724],'sfault')==0
assert val(lifetime[2724],'vm_we__BRA__0__KET__')==0 and val(good[2724],'vm_we__BRA__0__KET__')==1
assert bank(drain[2725],'w_pin')==1 and bank(drain[2725],'r_pin')&32
assert bank(good[2725],'w_pin')==1 and bank(good[2725],'r_pin')==0
assert bank(good[2726],'w_pin')==0 and bank(good[2726],'r_pin')&32
assert bank(fill[2692],'r_pin')&15==15 and bank(fill[2695],'w_pin')==1
assert all(bank(fill[t],'w_pin')==0 for t in range(2660,2695))
proof=dict(absent_reader_identity='first sticky slice fault qt2700 after qualified reader qt2699',missing_control_lifetime='qt2724 expected output vm_we1 but0, slice fault0',old_drain_gap='qt2725 held bank0 write and read5 target row1 together: actual macro qt2726 OLD-read',old_fill_deadline='qt2692 held operand reads reach macro before first FILL write held qt2695')
(O/'causal_predicates.json').write_text(json.dumps(proof,indent=2));print('CAUSAL_PREDICATES PASS four independent repair omissions')
