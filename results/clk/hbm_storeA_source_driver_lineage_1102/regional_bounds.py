from pathlib import Path
import json,re,collections,math
R=Path.cwd();root=R.parent;script=(R/'capture_geometry.py').read_text();exec(compile(script[:script.index('out=[]\nfor i,')],str(R/'capture_geometry.py'),'exec'))
# Full FF body is an optimistic source-access rectangle, wider than real Q pins.
for model in masters.values():model['D_bbox']=[0,0,model['width'],model['height']]
source_master='DFFASRHQNx1_ASAP7_75t_R';schemes={
'memory_halves_16':lambda f,r,c:f'm{f}',
'vertical_halves_16':lambda f,r,c:f'c{c//2}',
'memory_column_quadrants_8':lambda f,r,c:f'm{f}c{c//2}',
'memory_row_quadrants_8':lambda f,r,c:f'm{f}r{r//2}',
'vertical_columns_8':lambda f,r,c:f'c{c}',
'compact_blocks_4':lambda f,r,c:f'm{f}r{r//2}c{c//2}'}
# Accumulate each actual ABI -> regional target set as extrema; preserves exact
# perbit/native pin reach without retaining millions of duplicate path records.
def update(e,rect):
 a,b,c,d=rect;vals=dict(umax=a+b,umin=c+d,vmax=a-d,vmin=c-b,xmax=a,xmin=c,ymax=b,ymin=d)
 if not e:e.update(vals)
 else:
  for k,v in vals.items():e[k]=(max if k.endswith('max')else min)(e[k],v)
macros=json.load(open(R/'macro_ownership.json'));by_scheme={s:{}for s in schemes};regionmacros={s:collections.defaultdict(set)for s in schemes}
for q in macros:
 b=rows[q['instance']];ox,oy=b['planned_xy_um'];m=re.search(r'm([01])\.g_bank\\\[(\d+)\\\]',q['instance']);family,bank=map(int,m.groups());row,col=bank//4,bank%4
 for group,g in q['pin_groups'].items():
  if g['direction']!='INPUT':continue
  for pin in g['pins']:
   rects=[[ox+a,oy+b,ox+c,oy+d]for a,b,c,d in pins[pin['pin']]];assert len(rects)==1
   for kind,owner,port in pin['frontier']:
    if kind!='port':continue
    if owner.startswith('store0_sw_mask['):continue # exact selected-source constant1; local tie proposal has no FFQ
    if owner in ['comb128_A[0]','comb144_A[0]']:continue # two non-global16bank source FF handled separately
    for scheme,keyfn in schemes.items():
     region=keyfn(family,row,col);regionmacros[scheme][region].add(q['instance']);e=by_scheme[scheme].setdefault((owner,region),{});update(e,rects[0])
del macros
result={}
for scheme,items in by_scheme.items():
 out=[]
 for (source,region),e in items.items():
  lo=continuous_min(e);c=candidate(e,source_master,405);out.append(dict(source_ABI=source,region=region,continuous_source_point_minimax_um=lo,optimistic_full_FFbody_row405_candidate=c))
 badpoint=[q for q in out if q['continuous_source_point_minimax_um']>405+1e-6];badrow=[q for q in out if q['optimistic_full_FFbody_row405_candidate']is None]
 result[scheme]=dict(regions={k:sorted(v)for k,v in regionmacros[scheme].items()},ABI_region_checks=len(out),point_bound_failures=len(badpoint),optimistic_legal_body_failures=len(badrow),max_continuous_source_point_minimax_um=max(q['continuous_source_point_minimax_um']for q in out),source_FF_state_cost_per_complete_region=2200,cost_basis='2048registered data +120address +16group +16expect/scalar FF bits;8stage_v ANDs and64constantmask outputs not independent state',rows=out)
 print(scheme,len(out),'pointfails',len(badpoint),'rowfails',len(badrow),'maxR',result[scheme]['max_continuous_source_point_minimax_um'],flush=True)
res=dict(status='PROSPECTIVE_GEOMETRIC_REGIONALIZATION_BOUNDS_ONLY',source_odb_sha256=binding['source_odb_sha256'],macro_variant='capture_gutter_v1',variable_source_ABI_bits=2192,constant_mask_bits=64,schemes=result,scope='existing source terminal FF private-copy placement necessary bounds only; no new RTL/cycles or D/clock/reset reach proof',optimism=['FF source access anywhere in full1.404x0.27 body, not actualQ/inverter pins','BothR0/MX allowed everyrow; no other stdcell occupancy or simultaneous copy capacity','SourceD upstream locations/reach and clock/reset physical domains remain unqualified','No region count is selected; point or independent-row success is not physical PASS'])
(R/'regional_bounds.json').write_text(json.dumps(res,indent=2)+'\n')
