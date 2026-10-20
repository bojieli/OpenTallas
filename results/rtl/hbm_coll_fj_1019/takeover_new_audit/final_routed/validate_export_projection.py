import pathlib,json,re,hashlib,subprocess
W=pathlib.Path(__file__).resolve().parents[5];O=pathlib.Path(__file__).resolve().parent
# Complete actual BTerms, immutable exported Liberty groups, and final routed clock receipts.
def groups(s,kind):
 out={}
 for m in re.finditer(r"\b"+kind+r'\("?([^"()]+)"?\)\s*\{',s):
  i=m.end();j=i;depth=1
  while depth:
   if s[j]=='{':depth+=1
   elif s[j]=='}':depth-=1
   j+=1
  out[m[1]]=s[i:j-1]
 return out
out={}
constants=json.loads((O/'output_constant_classes.json').read_text())
for q,top,ref in [(3,'ot_hgi_coll_fj_n2s1_r128','40d164681'),(2,'ot_hgi_coll_fj_q2_r128','265378acd')]:
 P=W/f'physical/ref_tile/hcoll_fj{q}_r128u3/views/{top}';ports={l.split('\t')[1]:l.split('\t')[0].lower() for l in (O/f'fj{q}_final_ports.tsv').read_text().splitlines()};ins=json.loads((P/'insertion.json').read_text());d={'top':top,'status':'PASS','source_record':ref,'ports':len(ports),'corners':{},'native_clock_pin':'u_ot_pr_core.u.u_program.u_flow/clk','forwarded_clock_outputs':[]};errs=[]
 for corner in ['tt','ff','ss']:
  f=P/f'{top}_{corner}.lib';s=f.read_text();pins=groups(s,'pin');checks={};clocks=[]
  for name,direction in ports.items():
   b=pins.get(name,'');types=re.findall(r'timing_type\s*:\s*(\w+)',b)
   if not re.search(r'direction\s*:\s*'+direction+r'\b',b):errs.append(corner+' missing/direction '+name)
   if re.search(r'clock\s*:\s*true',b):clocks.append(name);continue
   if direction=='input' and not {'setup_rising','hold_rising'}<=set(types):errs.append(corner+' inputarc '+name)
   if direction=='output' and not types:
    cls=constants[str(q)].get(name,[])
    if not cls or not all(x[0].startswith('TIELO') for x in cls):errs.append(corner+' untimedoutput '+name)
   checks[name]={'direction':direction,'types':types,'constant_driver':constants[str(q)].get(name)}
  if clocks!=['clk']:errs.append(corner+' clockcoverage '+str(clocks))
  cb=pins['clk'];timing=[]
  for m in re.finditer(r'timing_type\s*:\s*(min_clock_tree_path|max_clock_tree_path)\s*;',cb):
   end=cb.find('timing()',m.end());part=cb[m.end():end if end>=0 else len(cb)];vals=[float(v) for v in re.findall(r'values\("([0-9.eE+-]+)"\)',part)];timing.append({'type':m[1],'rise_fall_ps':vals})
  mn=min(timing[0]['rise_fall_ps']);mx=max(timing[1]['rise_fall_ps']);actual=ins[corner];macro=actual['macros'];allc=actual['all'];spread=allc['max']-allc['min'];envspread=mx-mn
  if not mn<=allc['min']<=allc['max']<=mx:errs.append(corner+' exportedclocknotenvelope')
  if corner in ['tt','ff'] and (spread>80 or envspread>80):errs.append(corner+' spread')
  if macro['n']!=1 or len(macro['pins'])!=1 or macro['pins'][0]['pin']!=d['native_clock_pin'] or actual['clock_family']!={'core_clk':allc['n']}:errs.append(corner+' nativeclockcoverage')
  d['corners'][corner]={'lib_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'input_count':sum(v=='input' for v in ports.values()),'output_count':sum(v=='output' for v in ports.values()),'timing_by_port':checks,'export_clock_tree':timing,'export_full_rise_fall_spread_ps':envspread,'actual_all_sinks_spread_ps':round(spread,3),'actual_clock':actual,'actual_native_macro_clock_count':macro['n']}
 d['errors']=errs;d['status']='FAIL' if errs else 'PASS';out[q]=d
(O/'export_complete_clock_io_audit.json').write_text(json.dumps(out,indent=2)+'\n')
for q,d in out.items():print(q,d['status'],d['errors'],[(c,r['actual_all_sinks_spread_ps'],r['export_full_rise_fall_spread_ps']) for c,r in d['corners'].items()])
assert all(d['status']=='PASS' for d in out.values())
