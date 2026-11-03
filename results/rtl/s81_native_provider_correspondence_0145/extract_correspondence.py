from pathlib import Path
import json,re,hashlib
r=Path('/srv/opentallas-scratch2/claude/die-s81-47/bind_ev2/out')
files=['col_h10_r0_p1__t1__cl574cc59d.sv','col_h10_r1__t1__cl95b37463.sv','col_h10_r2__t1__cl1f5d6c2a.sv']
schedule=json.loads(Path('/srv/opentallas-scratch2/claude/codex-ds-bf-selectors-2200/col_h10_l4_lp_asb_x_schedule.json').read_text())
names=json.loads((r/'bind_names.json').read_text());rows=[]
for f in files:
 p=r/'rtl'/f;s=p.read_text();cells={}
 for m in re.finditer(r'^    (\w+)\s*(?:#\(([^\n]*?)\)\s*)?(\w+)\s*\(\s*\n(.*?)^    \);',s,re.M|re.S):
  typ,params,name,ports=m.groups();ports=dict(re.findall(r'\.(\w+)\(([^\n]*)\)(?:,|$)',ports,re.M));params=dict(re.findall(r'\.(\w+)\((.*?)\)(?:,|$)',params or ''))
  cells[name]=dict(type=typ,params=params,ports=ports)
 def bit0(v):return re.sub(r'\[0(?::0)?\]$','',v)
 q=[(k,v)for k,v in cells.items()if v['type']=='ot_v41_rom_elem_q_qxpq_w10_gb']
 for name,c in q:
  qp=c['ports'];banks=[(k,v)for k,v in cells.items()if bit0(v['ports'].get('o_go',''))==bit0(qp['go'])];assert len(banks)==1,(name,banks)
  bn,b=banks[0];bp=b['ports'];seqs=[(k,v)for k,v in cells.items()if bit0(v['ports'].get('go_e',''))==bit0(bp['i_go'])];assert len(seqs)==1,(name,seqs)
  sn,seq=seqs[0];sp=seq['ports'];idx=int(re.search(r'e(\d+)$',name)[1]);station=f'e{idx}';orig=[v for k,v in names.items()if k.endswith('.'+name)and v.startswith('u_f_0L01.')];assert len(orig)==1,(name,orig)
  params={k:v for k,v in c['params'].items()if k!='INSTANCE'}
  row=dict(station=station,bound_leaf=orig[0],part_type=p.stem,part_source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),Q_type=c['type'],Q_params=params,Q_ports={k:qp[k]for k in ['clk','rst_n','go','go_tag','cfg_v','cfg_a','cfg_d','bank_free','sh_free']},bank_instance=bn,bank_type=b['type'],bank_ports=bp,sequencer_instance=sn,sequencer_type=seq['type'],sequencer_params=seq['params'],sequencer_ports=sp,tag_direct_from_CFG7=(qp['go_tag'].removesuffix('[1:0]')==sp['go_tag'].removesuffix('[1:0]')),clock_net_identical=(bit0(qp['clk'])==bit0(sp['clk'])==bit0(bp['ck'])),reset_net_identical=(bit0(qp['rst_n'])==bit0(sp['rst_n'])==bit0(bp['rs'])),retained_schedule_station=schedule['station_inputs'][station],measured_component_coverage=(idx==0),native_provider_qualified=False)
  rows.append(row)
assert len(rows)==12 and len({v['station']for v in rows})==12
qparams={json.dumps(v['Q_params'],sort_keys=True)for v in rows};seqtypes={v['sequencer_type']for v in rows};banktypes={v['bank_type']for v in rows}
report=dict(status='DISABLED_CURRENT_ALL12_PROVIDER_SOURCE_CORRESPONDENCE',rows=sorted(rows,key=lambda v:int(v['station'][1:])),stations=12,Q_param_classes=len(qparams),sequencer_types=sorted(seqtypes),sequencer_param_classes=len({json.dumps(v['sequencer_params'],sort_keys=True)for v in rows}),bank_types=sorted(banktypes),port_normalization='Whole one-bit GO/clock/reset port vs[0]/[0:0], whole two-bit go_tag vs[1:0]; no other alias inference',all_tag_direct=all(v['tag_direct_from_CFG7']for v in rows),all_clock_net_identical=all(v['clock_net_identical']for v in rows),all_reset_net_identical=all(v['reset_net_identical']for v in rows),native_measured_stations=['e0'],production_flags_changed=False,source_qualification_adopted=False,physical_clock_reset_qualified=False,scope='Exact current bound leaf/control/bank source join; identical source permits candidate logical GO/TAG proof reuse, not physical/native-global qualification',holds=['per-station actual physical clock/reset sampling','current bound input transport and R8 membership','actual source epochs and operand arrival readiness','other station parameter/field shape cadence qualification','retained schedule source closure vs active canonical cohort'])
print(json.dumps(report,indent=2))
