import sys,json,re,hashlib
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan');import die_clock_128 as D
base=Path('/home/ubuntu/OpenTallas/physical/qwen_missing_phy/nface_tall_1017/ot_qfd_serdes_112g_x12_phy_s597')
r=.0118796; stockc=.187426
out={'scope':'Actual declared native PHY published abstract tables, NOT fabricated stronger driver; no routed/extracted claim. N/S output launch only; inputs need actual sourceFF tables separately.','layer_M6':{'R_kohm_um':r,'stock_C_ff_um':stockc,'stock_source':'openroad/orfs:asap7lock /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl','extra_coupling_guards':[1,1.7]},'corners':{}}
for corner in ['TT','FF']:
 path=base/f'ot_qfd_serdes_112g_x12_phy_s597_{corner.lower()}.lib';txt=path.read_text();i=txt.index('pin (tx_up)');j=txt.index('pin (tx_v)',i);b=txt[i:j];maxcap=float(re.search(r'max_capacitance\s*:\s*([\d.]+)',b)[1]);bufcap={'TT':2.34978,'FF':2.60735}[corner]
 rows=[]
 for guard in [1,1.7]:
  for length in [100,120,160,208,250]:
   c=length*stockc*guard;el=r*length*(c/2+bufcap);load=c+bufcap
   trans=max(D._bilin(D._table(b,k),80,load) for k in ['rise_transition','fall_transition']);cq=max(D._bilin(D._table(b,k),80,load) for k in ['cell_rise','cell_fall']);slew=(trans**2+(2.2*el)**2)**.5
   rows.append({'wire_um':length,'coupling_guard':guard,'total_load_ff':load,'published_maxcap_ff':maxcap,'cap_pass':load<=maxcap,'source_transition_ps':trans,'wire_elmore_ps':el,'receiver_transition_ps':slew,'CQ_plus_wire_ps':cq+el,'slew80_pass':slew<=80,'table_domain_pass':load<=D._table(b,'cell_rise')[1][-1]})
 out['corners'][corner]={'source':str(path.relative_to(Path('/home/ubuntu/OpenTallas'))),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'output_pin':'tx_up (same declared registered output driver family must compare allbits before adoption)','rows':rows}
Path('/tmp/qcclock0336/native_launch_prep.json').write_text(json.dumps(out,indent=2)+'\n')
for co,v in out['corners'].items():
 print(co,[z for z in v['rows'] if z['wire_um']==208])
for co,v in out['corners'].items():
 txt=(Path('/home/ubuntu/OpenTallas')/v['source']).read_text();tables={}
 for name,tag in [('tx_up','pin'),('rx_v','pin'),('rx_flit','bus')]:
  i=txt.index(tag+' ('+name+')');end=txt.find('\n    '+('bus' if name=='rx_v' else 'pin')+' (',i+10);b=txt[i:end if end!=-1 else len(txt)]
  data={k:D._table(b,k) for k in ['cell_rise','cell_fall','rise_transition','fall_transition']}
  tables[name]={'tables_sha256':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),'bits':597 if name=='rx_flit' else 1}
 v['all_output_family_table_identity']=tables;v['all599outputs_same_tables']=len(set(z['tables_sha256'] for z in tables.values()))==1
Path('/tmp/qcclock0336/native_launch_prep.json').write_text(json.dumps(out,indent=2)+'\n')
print({co:v['all599outputs_same_tables'] for co,v in out['corners'].items()})
