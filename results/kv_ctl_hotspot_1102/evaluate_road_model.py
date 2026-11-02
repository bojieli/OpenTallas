import runpy,json,gzip,sys,os,inspect,math
from pathlib import Path
O=Path(__file__).resolve().parent
code=(O/'trace_hotspots.py').read_text().split('allnets=D.nets;boxmap=[]')[0]
exec(compile(code,str(O/'trace_hotspots.py'),'exec'))
old_rr=G.r2r_metrics(D);old_pin=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT));old_clock=G.clock_metrics(D)
r=json.loads(gzip.decompress((O/'comb_road_model.json.gz').read_bytes()));ids={c[6]:i for i,c in D.cells.items()}
for q in r['cells']:
 i=ids[q['name']];c=D.cells[i];assert c[0] in 'BL' and i not in clock_cells;assert c[1]==q['master'];x,y=q['ll_dbu'];w,h=q['size_dbu'];D.cells[i]=tuple(list(c[:2])+[x/1000,y/1000,(x+w)/1000,(y+h)/1000]+list(c[6:]))
rr=G.r2r_metrics(D);pin=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT));clock=G.clock_metrics(D);assert rr==old_rr and pin==old_pin and clock==old_clock
nominal=G.demand_metrics(D);boxes=np.array(G._net_boxes(D));cuts=[];src=inspect.getsource(G.demand_metrics).replace('def demand_metrics(','def guided_demand(').replace('cap = np.full(nb, full * step)','cap = source_phase_cap(d,float(c),nb)');ns=dict(vars(G));ns['source_phase_cap']=source_phase_cap;exec(src,ns);predict=ns['guided_demand'](D)
original_windows=[]
for win in json.load(open(O/'hotspot_summary.json'))['windows']:
 direction=win['direction'];cut=win['cut_um'];a0,a1=win['window_um'];nb=math.ceil(302.4 if direction=='H' else 233.28);cap=source_phase_cap(direction,cut,nb);cs=np.concatenate([[0.],np.cumsum(cap)]);demand=0.
 for x0,y0,x1,y1 in boxes:
  lo,hi,b0,b1=(y0,y1,x0,x1) if direction=='H' else(x0,x1,y0,y1)
  if not b0<cut<b1:continue
  i=max(0,min(nb-1,int(lo)));j=max(0,min(nb-1,int(hi)));total=cs[j+1]-cs[i];left,right=max(int(a0),i),min(int(a1),j+1)
  if total>0 and right>left:demand+=(cs[right]-cs[left])/total
 original_windows.append(dict(direction=direction,cut_um=cut,window_um=[a0,a1],before=win['proxy_ratio'],after=demand/(cs[int(a1)]-cs[int(a0)])))
res=dict(status='GUIDED_CELL_MODEL_ONLY_NOT_POST_PLACE_OR_ROUTE',FF_R2R_unchanged=rr,pins_unchanged=pin,clock_model_unchanged=clock,source_cells=len(D.cells),source_nets=len(D.nets),existing_comb_cells_guided=len(r['cells']),inserted_cells=0,original_window_ratios_after=original_windows,nominal_cut_model=nominal,native_phase_PG_prediction=predict,full_cuts=cuts,limits=r['report']['limits'])
(O/'guided_source_model.json').write_text(json.dumps(res,indent=2)+'\n');(O/'guided_cell_model.json.gz').write_bytes(gzip.compress(json.dumps(list(D.cells.values()),separators=(',',':')).encode(),mtime=0));print(json.dumps({k:v for k,v in res.items() if k not in ['full_cuts','limits','clock_model_unchanged']},indent=2))
