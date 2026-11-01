from pathlib import Path
import json,re,sys
k=Path('/work');d=json.load(open(sys.argv[1]))
top=(k/'rtl/s81p_col_h10_r0_p4__t1.sv').read_text()
ids=dict(re.findall(r'\.(P_\w+_INSTANCE)\("([^"]*)"\)',top));records=[]
for mn,m in d['modules'].items():
 for cell,c in m.get('cells',{}).items():
  t=c['type'];p=c.get('parameters',{})
  if t not in ['ot_v41_rom_elem_q_qxpq_w10_gb','dsfd_bf_front_roots','ot_v41_bf_col']:continue
  value=p.get('INSTANCE','')
  if t=='ot_v41_rom_elem_q_qxpq_w10_gb':
   key='P_'+cell.removeprefix('u_bound.u_')+'_INSTANCE';assert value==ids[key],(cell,value,key)
  else:assert value in ['', ' '],(cell,value)
  records.append(dict(master=t,instance=cell,content_label=value))
assert len(records)==7,len(records)
Path('/work/physical_content_labels.json').write_text(json.dumps(records,indent=2))
print('Verified seven actual content identities before physical serialization')
