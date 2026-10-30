from pathlib import Path
import re,gzip,json
P=Path(__file__).parent/'cdc_lvt_model';cells=['BUFx16f','BUFx10'];rows=[]
def blk(t,kind):
 for m in re.finditer(r'\b'+kind+r'\s*\(\s*([^)]*)\s*\)\s*\{',t):
  i=m.end();dep=1;j=i
  while dep:dep+=(t[j]=='{')-(t[j]=='}');j+=1
  yield m.group(1).strip(),t[i:j-1]
def num(t,key):
 m=re.search(r'\b'+key+r'\s*:\s*([-+.0-9eE]+)',t);return float(m[1])if m else None
lefs={}
for vt in ['R','L']:
 t=(P/f'asap7sc7p5t_28_{vt}_1x_220121a.lef').read_text();lefs[vt]={m.group(1):m.group(0)for m in re.finditer(r'(?ms)^MACRO\s+(\S+)\s*\n.*?^END\s+\1\s*$',t)}
for short in cells:
 r=lefs['R'][short+'_ASAP7_75t_R'];l=lefs['L'][short+'_ASAP7_75t_L'];same=r==l.replace('_ASAP7_75t_L','_ASAP7_75t_R').replace('LVTN','RVTN').replace('LVTP','RVTP');row={'cell':short,'full_LEF_except_intended_VT_master_and_implant_layer_names_identical':same,'corners':{}}
 for cor in ['TT','FF']:
  cc={}
  for vt in ['RVT','LVT']:
   t=gzip.open(P/f'asap7sc7p5t_INVBUF_{vt}_{cor}_nldm_220122.lib.gz','rt').read();b=dict(blk(t,'cell'))[short+'_ASAP7_75t_'+vt[0]];pins=dict(blk(b,'pin'));fields={key:num(b,key)for key in ['area','cell_leakage_power']}
   unconditional=[num(q,'value')for _,q in blk(b,'leakage_power')if 'when'not in q and re.search(r'related_pg_pin\s*:\s*VDD',q)]
   fields['unconditional_VDD_leak_pW']=unconditional[0]if len(unconditional)==1 else None
   for key in ['capacitance','rise_capacitance','fall_capacitance']:fields['A_'+key+'_fF']=num(pins['A'],key)
   fields['Y_function']=re.search(r'function\s*:\s*([^;]+)',pins['Y'])[1];cc[vt]=fields
   if vt=='RVT':
    row['units']={}
    for k in ['capacitive_load_unit','leakage_power_unit']:
     m=re.search(k+r'\s*[:(]\s*([^;]+)',t);row['units'][k]=m[1]if m else'not explicit'
  row['corners'][cor]=cc
 rows.append(row)
r={'status':'READONLY_PRICE_NOT_ADOPTED','allowlist':{'wire4506':'BUFx16f','place3260':'BUFx10','place3259':'BUFx10'},'selected_cells':3,'current_cells_including_clock_TAP':62599,'fraction_percent':3/62599*100,'global_LVT_resizer_exposure':False,'cell_characterization':rows};(P/'physical_electrical_identity.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
