from pathlib import Path
import json,re,collections,math,hashlib
R=Path.cwd();D=R/'capture_gutter_v1';binding=json.load(open(D/'native_macro_binding.json'));byname={q['actual_native_name']:q for q in binding['rows']};lef=(R/'sram.lef').read_text();public=(R/'io.tcl').read_text();pinrects={}
for m in re.finditer(r'\bPIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1\s*\n',lef,re.S):pinrects[m[1]]=[list(map(float,x))for x in re.findall(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s*;',m[2])]
abi={}
for name,layer,x,y,w,h in re.findall(r'place_pin -pin_name \{([^}]+)\} -layer (\S+) -location \{([\d.-]+) ([\d.-]+)\} -pin_size \{([\d.-]+) ([\d.-]+)\}',public):
 x,y,w,h=map(float,(x,y,w,h));abi[name]=dict(layer=layer,rect=[x-w/2,y-h/2,x+w/2,y+h/2],centre=[x,y])
assert len(abi)==6040,len(abi)
gen=json.load(open(R/'pins.json'));assert {f"{p['bus']}[{p['bit']}]"for p in gen}==set(abi)
assert all(abi[f"{p['bus']}[{p['bit']}]"]['rect'][0]-1e-6<=p['x']<=abi[f"{p['bus']}[{p['bit']}]"]['rect'][2]+1e-6 and abi[f"{p['bus']}[{p['bit']}]"]['rect'][1]-1e-6<=p['y']<=abi[f"{p['bus']}[{p['bit']}]"]['rect'][3]+1e-6 for p in gen)
def distance(a,b):return max(a[0]-b[2],b[0]-a[2],0)+max(a[1]-b[3],b[1]-a[3],0)
# Source pins may access any actual rectangle. Point/rectangle lower bounds only;
# no gate placement or routed path is assumed.
macros=json.load(open(R/'macro_ownership.json'));groups={};per_source=collections.defaultdict(list);bad=[];checks=0;unmatched=set();fffrontiers=0
for q in macros:
 ox,oy=byname[q['instance']]['planned_xy_um'];assert byname[q['instance']]['planned_orient']=='R0'
 for group,g in q['pin_groups'].items():
  if g['direction']!='INPUT':continue
  k=q['instance']+'/'+group;summary=dict(instance=q['instance'],pin_group=group,source_ABI_bits=set(),source_FF=set(),perbit_ABI_checks=0,perbit_ABI_failures=0,max_GEN_pin_rectangle_lowerbound_um=0,worst=None)
  for p in g['pins']:
   target=[[ox+a,oy+b,ox+c,oy+d]for a,b,c,d in pinrects[p['pin']]]
   for kind,owner,pin in p['frontier']:
    if kind=='ff':summary['source_FF'].add(owner);continue
    if kind!='port':continue
    if owner not in abi:unmatched.add(owner);continue
    origin=abi[owner]['rect'];d=min(distance(origin,t)for t in target);checks+=1;summary['perbit_ABI_checks']+=1;summary['source_ABI_bits'].add(owner)
    item=dict(source_ABI=owner,source_GEN_rectangle_um=origin,target_macro=q['instance'],target_pin=p['pin'],target_rectangles_um=target,minimum_rectangle_distance_um=d)
    per_source[owner].append(item)
    if d>summary['max_GEN_pin_rectangle_lowerbound_um']:summary['max_GEN_pin_rectangle_lowerbound_um']=d;summary['worst']=item
    if d>405+1e-6:summary['perbit_ABI_failures']+=1;bad.append(item)
  summary['source_ABI_bits']=sorted(summary['source_ABI_bits']);summary['source_FF']=sorted(summary['source_FF']);groups[k]=summary
print('PAIRS',checks,'FAIL',len(bad),'UNMATCHED',len(unmatched),flush=True);assert not unmatched,sorted(unmatched)
# Necessary fanout-point minimax over exact source pin centres. Rectangle corner
# bounds make the certificate optimistic for all actual access rectangles.
fanouts=[]
for source,items in per_source.items():
 rects=[t for i in items for t in i['target_rectangles_um']];centres=[((a+c)/2,(b+d)/2)for a,b,c,d in rects];u=[x+y for x,y in centres];v=[x-y for x,y in centres];centre_lb=max(max(u)-min(u),max(v)-min(v))/2
 # max distance to rectangular targets: using each target rectangle's expanded
 # centre radius gives a conservative continuous source-point lower bound.
 slack=max((c-a+d-b)/2 for a,b,c,d in rects);source_rect=abi[source]['rect'];source_radius=(source_rect[2]-source_rect[0]+source_rect[3]-source_rect[1])/2;optimistic=max(0,centre_lb-slack-source_radius)
 fanouts.append(dict(source_ABI=source,reachable_macro_count=len({i['target_macro']for i in items}),actual_perbit_paths=len(items),continuous_target_centre_minimax_um=centre_lb,optimistic_target_rectangle_minimax_lowerbound_um=optimistic,GEN_point=abi[source]['centre'],source_macros=sorted({i['target_macro']for i in items})))
fanouts.sort(key=lambda q:q['optimistic_target_rectangle_minimax_lowerbound_um'],reverse=True)
res=dict(status='FAIL_CURRENT_GEN_INPUT_TO_NATIVE_SRAM_405'if bad else'NECESSARY_GEN_PIN_GEOMETRY_ONLY',source_odb_sha256=binding['source_odb_sha256'],macro_variant='capture_gutter_v1',public_IO_assignment='Original SAME979 GEN io.tcl, not qualified physical native pins',perbit_ABI_to_SRAM_checks=checks,perbit_ABI_to_SRAM_failures=len(bad),max_current_GEN_rectangle_distance_um=max((q['minimum_rectangle_distance_um']for q in bad),default=0),source_ABI_bits=len(per_source),source_bits_continuously_impossible_even_with_repositioning=sum(q['optimistic_target_rectangle_minimax_lowerbound_um']>405+1e-6 for q in fanouts),max_optimistic_target_rectangle_minimax_lowerbound_um=max((q['optimistic_target_rectangle_minimax_lowerbound_um']for q in fanouts),default=0),groups=groups,source_fanouts=fanouts,worst_failed_pairs=sorted(bad,key=lambda q:q['minimum_rectangle_distance_um'],reverse=True)[:128],scope='actual perbit native combinational frontier plus GEN public and actual native SRAM LEF rectangles; necessary geometry, not route/STA/source activation',holds=['GEN public IO is a proposal, not actual built source pin qualification','Conservative combinational cell reach can include unsensitized paths; no timing exceptions inferred','No mapped FF coordinates, pin movement, relay or cycles invented','Point-to-target rectangle minimax impossibility is only used as a lower-bound FAIL; candidate existence cannot PASS physical reach'])
(R/'write_geometry.json').write_text(json.dumps(res,indent=2)+'\n');print({k:v for k,v in res.items()if k not in ['groups','source_fanouts','worst_failed_pairs','holds']},flush=True)
