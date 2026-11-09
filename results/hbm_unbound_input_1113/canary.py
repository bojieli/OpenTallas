import sys,json,copy,hashlib,shutil
from pathlib import Path
R=Path('/srv/opentallas-scratch3/claude/codex-hbm-unbound-1113')
S=Path('/srv/opentallas-scratch2/claude/kw35/src_cad9y/tools')
sys.path[:0]=[str(R),str(S/'die_plan'),str(S)]
import kit_dead_inputs as D
import die_port_bind as P
import face_guard as F
I=Path('/srv/opentallas-scratch3/claude/kw26-wave-1106/runs/hbm/kit-wave/hbm/d44v/items/q_su00__physical_v1')
K=I/'gen/q_su00__physical_v1'
m=json.loads((I/'rtl/kit_rtl.json').read_text());w=I/'rtl/hbm_arch_q_su00__physical_v1.sv'
module=next(x for x in P.parse_modules(w.read_text(),str(w))if x.name=='hbm_arch_q_su00__physical_v1')
rows=[dict(port=n,width=module.width(n,module.env()))for n in m['plan_buses_unbound'] if n in module.ports and module.ports[n][0]=='input']
assert rows==[dict(port='L1213_i',width=93)],rows
out=Path(m['bind_out']);native=out/'rtl/hbm_arch_q_su00__physical_v1.sv'
rc=m['dead_inputs']['proof']['receipt'];rc['unbound_input_buses']=rows
rc['unbound_source_proof']=D.unbound_receipt(rows,m['plan_buses_unbound'],out/'bind_report.json',native,'hbm_arch_q_su00__physical_v1')
m['unbound_input_buses']=rows
m['dead_inputs']['bits'] += [f'L1213_i[{i}]'for i in range(93)]
m['dead_inputs']['proof']['method']='Strict native source mapping + exact absent bound ABI + literal unread wrapper audit; not LEC/EQ'
D.refresh(m,w)
(R/'kit_rtl.json').write_text(json.dumps(m,indent=1)+'\n')
(R/'dead_inputs.json').write_text(json.dumps(m['dead_inputs'],indent=1)+'\n')
old=json.loads((K/'face_guard.json').read_text())
print('SOURCE_PROOF_PASS',len(m['dead_inputs']['bits']),json.dumps(rows))
# Read the retained placed netlist; do not alter source/physical checkpoints.
net=Path(old['netlist'])
if str(net).startswith('/work/'):net=K/str(net)[6:]
assert net.exists(),net
pins=json.loads((K/'pins.json').read_text())
sl=F.kit_strap_list(K);ft=F.read_ft1(K/'ft_stations.txt');bl=F.kit_bump_list(K)
text=(K/'constraint.sdc').read_text();ck=F.sdc_clock_ports(text);ex=F.sdc_clock_exports(text)
land=F.kit_land(K/'land_slots.json') if (K/'land_slots.json').exists() else None
pc,nc=F.kit_pad_clocks(K)
r=F.guard(net.read_text(),old['top'],pins=pins,ft1=ft,straps=sl,bumps=bl,clocks=ck,land=land,
          dead=m['dead_inputs']['bits'],exports=ex,pad_clocks=pc,native_clock_pins=nc,
          spare=F.kit_spare_list(K),timed=F.kit_timed_list(K))
r['netlist']=str(net);r['source_receipt']=str(R/'dead_inputs.json')
(R/'face_guard_private.json').write_text(json.dumps(r,indent=1)+'\n')
print('RETAINED_PLACE_FACE_GUARD',r['verdict'],r['checked'],r['ok'],r['fail_counts'])
assert r['verdict']=='PASS',r['fail_counts']
