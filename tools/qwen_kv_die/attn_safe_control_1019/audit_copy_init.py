import pathlib,importlib.util,json,collections
r=pathlib.Path('.');sp=importlib.util.spec_from_file_location('lint',r/'tools/textbook_lint.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
g,top=T.flatten(T.parse_verilog((r/'synth/results/asap7/opentallas_qkd_kvs_attn_fl_ba5_asap7_ref_gate/base/1_2_yosys.v').read_text()),None);A=T.build(g,None);c=json.loads((r/'candidate/correspondence.json').read_text());cnt=collections.Counter(c['origins'][len(g.cells):]);out=[]
for oi,k in cnt.items():
 if A['kind'][oi]!='ff':continue
 typ,name,pins=g.cells[oi];stack=list(pins.get('D',[]));seen=set();up=set()
 while stack:
  x=stack.pop()
  if x in seen:continue
  seen.add(x);ci,pn=A['driver'].get(x,(-1,''))
  if ci<0:continue
  if A['kind'][ci]=='ff':up.add(ci);continue
  for pn,bs in g.cells[ci][2].items():
   if A['pin_dir'][ci][pn]=='in':stack.extend(bs)
 out.append({'origin':oi,'name':name,'master':typ,'extra_copies':k,'unreset':not any(p in pins for p in ('RESETN','SETN','RN','SN')),'self_feedback':oi in up,'upstream_copied_FF':[x for x in up if x in cnt]})
(r/'candidate/copy_initialization.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
