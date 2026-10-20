"""Proof-only monitors bound to frozen actual mapped regional reset graph."""
import gzip,json,hashlib
from pathlib import Path
base=Path(__file__).resolve().parent
g=json.loads(gzip.decompress((base/'reset_graph_profile.json.gz').read_bytes()))
cs={x['instance']:x for x in g['conditioners']}
def one(x,p):
 a=x['inputs'][p];assert len(a)==1;return a[0]
def root(z):return (z['root_net'],z['inverted'])
def wire(z):return ('~' if z['inverted'] else '')+'dut.'+z['root_net']
def prev(x):
 d=one(x,'D');assert d['inverted'] and d['driver_pin']=='QN';return cs[d['driver']]
def q(x):
 a=x['outputs']['QN'];assert len(a)==1 and not a[0]['inverted'];return 'dut.'+a[0]['root_net']
rows=[];groups={}
for f in cs.values():
 if f['stage']!='regional_final':continue
 s2=prev(f);assert s2['stage']=='regional_S2'
 s1=prev(s2);assert s1['stage']=='regional_S1'
 assert one(s1,'D')['driver_type']=='TIEHIx1_ASAP7_75t_R' and not one(s1,'D')['inverted']
 rs=[one(x,'RESETN') for x in (s1,s2,f)]
 for x in (s1,s2,f):
  assert x['type']=='DFFASRHQNx1_ASAP7_75t_R'
  assert one(x,'SETN')['driver_type']=='TIEHIx1_ASAP7_75t_R' and not one(x,'SETN')['inverted']
  assert one(x,'CLK')['top_input']=='ck_core' and not one(x,'CLK')['inverted']
 k=tuple(root(z) for z in rs);groups.setdefault(k,[]).append((s1,s2,f))
 rows.append({'final':f['instance'],'s2':s2['instance'],'s1':s1['instance'],'reset_roots':[list(v) for v in k],'final_QN':q(f),'original':f['original']})
assert len(rows)==323
sv=['// Proof-only. No relation is assumed before an actual regional asynchronous assertion.']
for n,(k,chains) in enumerate(groups.items()):
 roots=[wire({'root_net':v[0],'inverted':v[1]}) for v in k]
 for i,rst in enumerate(roots):sv.append(f'wire ro_reset_{n}_{i} = {rst};')
 sv += [f'wire ro_alllow_{n} = !(ro_reset_{n}_0 | ro_reset_{n}_1 | ro_reset_{n}_2);',f'reg [2:0] ro_age_{n}; reg ro_witness_{n}=0; integer ro_checks_{n}=0;',f'always @(posedge ro_alllow_{n}) ro_witness_{n}=1;',f'always @(posedge ck_core or posedge ro_alllow_{n}) if(ro_alllow_{n}) ro_age_{n}<=0; else ro_age_{n} <= {{ro_age_{n}[1:0],1\'b1}};',f'always @(negedge ck_core or posedge ro_alllow_{n}) begin #0.1; if(ro_witness_{n}) begin ro_checks_{n}=ro_checks_{n}+1;', f'if(ro_reset_{n}_0 !== ro_reset_{n}_1 || ro_reset_{n}_1 !== ro_reset_{n}_2) $fatal(1,"RESET_ROOT_ALIGNMENT_FAIL group={n}");']
 for chain in chains:
  for i,f in enumerate(chain):sv.append(f'if ((~{q(f)}) !== ro_age_{n}[{i}]) $fatal(1,"RESET_AGE_FAIL group={n} stage={i} final={f["instance"]}");')
 sv += ['end end',f'final begin if(!ro_witness_{n} || ro_checks_{n}<100) $fatal(1,"RESET_AGE_NO_COVER group={n}"); $display("RESET_AGE_PASS group={n} finals={len(chains)} checks=%0d",ro_checks_{n}); end']
(base/'reset_observers.svh').write_text('\n'.join(sv)+'\n')
manifest={'schema':'peer.actual_regional_reset_observers.v1','mapped_sha256':g['mapped_sha256'],'generated_source_sha256':json.loads((base/'review_input_capture.json').read_text())['source_sha256'],'finals':len(rows),'reset_roots':len(groups),'chains':rows,'scope':'Exact extracted topology: positive core clock, three explicitly named actual asynchronous roots across the ASR stages; no literal-root equality assumed, tie-high SETN and S1 D, inverted QN stage propagation. Runtime root alignment and three-stage relation checked only after simultaneous actual assertion of all three roots witnessed; no pre-reset equivalence assumption. Does not prove downstream first-valid/admission dominance.'}
(base/'reset_observers_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS exact topology',len(rows),'finals',len(groups),'roots')
