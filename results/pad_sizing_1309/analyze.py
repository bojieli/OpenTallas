import gzip,json,re,sys,pathlib,hashlib,statistics
r=pathlib.Path(sys.argv[1])
sys.path.insert(0,str(pathlib.Path(sys.argv[2])/'tools'))
import qwen_embedding_pad_nldm as n
records={};libs={};bufs={}
for corner in ('TT','FF'):
 text=(r/f'probe_{corner}.log').read_text(); rec=[]
 for match in re.finditer(r'^PAD (\S+) (\S+) NET (\S+)\n(.*?)^ENDPAD \1$',text,re.M|re.S):
  name,cell,net,body=match.groups()
  c=re.search(r'Total capacitance: ([\d.]+)-([\d.]+)',body)
  loads=re.search(r'Number of loads: (\d+)',body)
  p={'name':name,'cell':cell,'net':net,'loads':int(loads[1]),'total_cap_min_ff':float(c[1]),'total_cap_max_ff':float(c[2]),'polarities':{}}
  for a in re.finditer(r'\nA ([\^v]) -> Y ([\^v])\n(.*?)(?=\nA [\^v] -> Y|\Z)',body,re.S):
   f=a[3];sl=re.search(r'input_net_transition = ([\d.]+)',f);cap=re.search(r'total_output_net_capacitance = ([\d.]+)',f);delay=re.search(r'Delay = ([\d.]+)',f)
   if a[1]!=a[2]:raise ValueError('inverting BUF arc')
   p['polarities']['rise' if a[1]=='^' else 'fall']={'input_slew_ps':float(sl[1]),'effective_cap_ff':float(cap[1]),'observed_cell_delay_ps':float(delay[1])}
  assert len(p['polarities'])==2,(corner,name,p)
  rec.append(p)
 assert len(rec)==35,(corner,len(rec))
 records[corner]=rec
 path=r/'libs'/f'asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz'
 lib=gzip.open(path,'rt').read();libs[corner]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 bufs[corner]={}
 for cell in re.findall(r'cell\s*\(\s*(BUF[^)]*)\)',lib):
  b=n.block(lib,'cell',cell);assert re.search(r'function\s*:\s*"A"',b)
  tables={pol:n.table(b,'cell_'+pol) for pol in ('rise','fall')};samples=[]
  for p in rec:
   q={'pad':p['name'],'loads':p['loads'],'polarities':{}}
   for pol,a in p['polarities'].items():
    # Measured total physical net cap is conservative relative to the current
    # BUFx2 Ceff; no wire/route guess is introduced for other cell strengths.
    val,extra=n.interpolate(tables[pol],a['input_slew_ps'],p['total_cap_max_ff'])
    eff,_=n.interpolate(tables[pol],a['input_slew_ps'],a['effective_cap_ff'])
    q['polarities'][pol]={'total_cap_lookup_ps':val,'current_ceff_lookup_ps':eff,'outside_table':extra}
   samples.append(q)
  vals=[a['total_cap_lookup_ps'] for q in samples for a in q['polarities'].values()]
  valid=[a['total_cap_lookup_ps'] for q in samples for a in q['polarities'].values() if not a['outside_table']]
  bufs[corner][cell]={'input_cap_ff':n.caps(lib,cell,'A'),'min_delay_ps':min(vals),'max_delay_ps':max(vals),'in_table_samples':len(valid),'total_samples':len(vals),'all_70_edges_le15_in_table':len(valid)==len(vals) and max(vals)<=15,'samples':samples}
result={'basis':'actual routed hd_turn_a candidate35 pinreg pad groups; fixed measured input slew and measured total output net cap; cell-only NLDM sensitivity, NOT proof of new-clock insertion','libraries':libs,'records':records,'buffers':bufs,'limitations':['Changing buffer input capacitance changes upstream loading/slew; full net insertion is not equal to the cell propagation number.','Existing routed wire geometry is held fixed for sensitivity. No new graph was placed, routed, or adopted.','Any out-of-table evaluation is explicitly flagged, is extrapolation, and cannot qualify a conservative cell choice.','A COMPLETED reference canary is not silicon physical closure; this study supplies clock-design sizing only.']}
(r/'analysis.json').write_text(json.dumps(result,indent=1)+'\n')
for c in ('TT','FF'):
 rec=records[c];print(c,'groups',len(rec),'loads',[min(x['loads'] for x in rec),statistics.median(x['loads'] for x in rec),max(x['loads'] for x in rec)],'capff',[min(x['total_cap_max_ff'] for x in rec),statistics.median(x['total_cap_max_ff'] for x in rec),max(x['total_cap_max_ff'] for x in rec)],'slewps',[min(a['input_slew_ps'] for x in rec for a in x['polarities'].values()),max(a['input_slew_ps'] for x in rec for a in x['polarities'].values())])
 for cell,v in bufs[c].items():print(cell,round(v['min_delay_ps'],3),round(v['max_delay_ps'],3),'in-table',v['in_table_samples'],'/',v['total_samples'])
