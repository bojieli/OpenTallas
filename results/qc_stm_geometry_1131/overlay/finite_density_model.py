import pathlib,json,gzip,math,re,shutil
B=pathlib.Path(__file__).resolve().parent;J=json.load(gzip.open(B/'shared_allFF_membership.json.gz'));M=json.load(gzip.open(B/'native_all_FF_masters.json.gz'));old=json.load(open(B/'native_sink_estimate.json'));allpos={};fails=[]
def nat(n):return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)',n)]
master={'DFFHQNx1_ASAP7_75t_R':[1.08,.27],'DFFLQNx1_ASAP7_75t_R':[1.08,.27],'DFFASRHQNx1_ASAP7_75t_R':[1.404,.27]}
for z in J['regions']:
 ns=sorted(z['native_named_FFs'],key=nat);r=z['window_um'];mw=max(master[M[n]['master']][0] for n in ns);cols=math.floor((r[2]-r[0]+1e-8)/mw);ny=math.ceil(len(ns)/cols);first=math.ceil((r[1]-1e-8)/.27)*.27;last=math.floor((r[3]-.27+1e-8)/.27)*.27;available=round((last-first)/.27)+1
 if available<ny:fails.append({'region':z['name'],'rows_needed':ny,'planned_rows_available':available});continue
 rowids=[round(j*(available-1)/(ny-1)) if ny>1 else(available-1)//2 for j in range(ny)]
 for i,n in enumerate(ns):
  col=i%cols;row=i//cols;w,h=master[M[n]['master']];x=r[0]+mw/2+(r[2]-r[0]-mw)*(col/(cols-1) if cols>1 else.5);y=first+.27*rowids[row]+h/2;assert r[0]-1e-7<=x-w/2 and x+w/2<=r[2]+1e-7 and r[1]-1e-7<=y-h/2 and y+h/2<=r[3]+1e-7;allpos[n]={'xy_um':[x,y],'region':z['name'],'native_clock_roots':M[n]['clock_roots'],'actual_master':M[n]['master']}
if fails:print('ROW_MODEL_FAIL',fails);raise SystemExit(1)
assert len(allpos)==68857
local={n:z for n,z in allpos.items() if z['native_clock_roots']==['clk']};assert len(local)==52609
shutil.copyfile(B/'native_sink_estimate.json',B/'native_sink_estimate_pubonly_FAIL.json')
model={'n':52609,'bin_um':.27,'bins':[[*z['xy_um'],1] for z in local.values()],'qualified':False,'source':'ACTUAL52609UNIQUE_NATIVE_NAMES; DETERMINISTIC_ROW_SPREAD_WITHIN_REVIEWED_NEW_FINITE_INTENT_WINDOWS; PLANNING_ONLY','note':'Original76endpoint homes and native roots unchanged.16248forwarded FFs priced/stored separately, NEVER inserted into local bins.10691.5869um2 nonFF unreserved; projected tiny84.22% overlap remains. No jitter or per-tap forcing. Planned row origin0/.27 from core/site lattice, actual placed ROW orientation unmeasured.'};(B/'native_sink_estimate.json').write_text(json.dumps(model,separators=(',',':'))+'\n')
with gzip.open(B/'finite_density_per_native_name.json.gz','wt') as f:json.dump({'source':'d90b109213c6949da87b330ef143d96bbe937934','actual_native_FF_total':68857,'local_bins':52609,'forwarded_excluded_from_local_bins':16248,'model':'natural native-name order per finite window; full-width legalmastercolumns/whole-cell planned .27um rows; NOT actual placement or tap identity','names':allpos},f,separators=(',',':'))
print('MODEL',len(local),'local',len(allpos),'allFF','rowFAIL',len(fails))
