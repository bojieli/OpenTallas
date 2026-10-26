import copy,json,re,subprocess,sys,functools
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/wt/codex-shared-core-0733/tools/die_plan')
import core_infra as CI
base=Path(__file__).parent;root=Path('/home/ubuntu/wt/codex-qc-su-0733');template=json.load(open('/srv/opentallas-scratch/claude/shared-core-0733/posthook64_2w_design/input.json'))
seq={c:Path(f'/home/ubuntu/.cache/opentallas/asap7_nldm/asap7sc7p5t_SEQ_RVT_{c}_nldm_220123.lib').read_text() for c in ['TT','FF']}
def blk(txt,tag):
 p=txt.index(tag);a=txt.index('{',p);n=1;j=a+1
 while n:n+=(txt[j]=='{')-(txt[j]=='}');j+=1
 return txt[a+1:j-1]
@functools.cache
def cap(txt,master,pin):
 b=blk(blk(txt,'cell ('+master+')'),'pin ('+pin+')');assert re.search(r'clock\s*:\s*true',b)
 return float(re.search(r'\bcapacitance\s*:\s*([\d.]+)',b).group(1))
for typ in ['btab','prog','vmr']:
 out=base/typ;out.mkdir(exist_ok=True);geo=root/f'results/qc_su_lat/r4/geo/{"vmr_aligned" if typ=="vmr" else typ+"_posthook"}.txt';old=root/f'results/qc_su_lat/r3/specs/planH_{typ}.json'
 subprocess.run([sys.executable,str(base/'plan.py'),str(geo),str(old),str(out/'named.tcl')],check=True)
 report=json.load(open(out/'named.tcl.json'));sl=copy.deepcopy(template['slice']);sl.pop('cell_placements',None);sl.pop('placement_basis',None);sl['type']=report['type'];sl['module']=report['type'];sl['instances']=[];sl['master_plan_sha256']='MODEL-ONLY-COHORT-NOT-FROZEN';sl['latency']['tol_ps']=20
 lines=[l.split() for l in geo.read_text().splitlines()];die=next(x for x in lines if x[0]=='DIE');sl['outline_um']=list(map(float,die[3:5]));entry=report['entry'];rect=[entry[0]-4.32,entry[1]-4.32,entry[0]+4.32,entry[1]+4.32]
 sl['islands']=[dict(name='clock_entry',rect_um=rect,centre_um=entry,clock_pin=dict(layer='M5',xy_um=entry))]
 isl=sl['pushdown']['islands'][0];isl['centre_um']=entry;isl['rect_um']=rect
 for p in isl['ft_ports']:
  p['xy_um']=[entry[0]+(-2.16 if p['dir']=='in' else 2.16),entry[1]+(2.16 if '_ck_' in p['name'] else -2.16)]
 points={};caps={};macpins={};inventory={};pairs={}
 for f in lines:
  if f[0]=='SINK':
   key=f[4]+'/'+f[5];points[key]=list(map(float,f[1:3]));cv=[cap(seq[c],f[3],f[5]) for c in ['TT','FF']];caps[key]=dict(zip(['TT','FF'],cv));inventory[f[3]]=dict(nominal_cap_ff_by_corner=dict(zip(['TT','FF'],cv)),selected_cap_ff=max(cv));
   name=f[4].replace(chr(92),'');m=re.match(r'^g_(?:wr|mw)\[([01])\]\.(?:g_r\.)?u_d/q\[([0-9]+)\]\$_DFF_P_$',name)
   if m:pairs.setdefault(m.groups(),[]).append(key)
  if f[0]=='MACRO':
   master=f[2];macpins[f[1]]='clk';key=f[1]+'/clk';points[key]=list(map(float,f[8:10]));cv=[]
   for c in ['tt','ff']:
    file=base/'macros'/f'{master}_{c}.lib'
    if not file.exists():file=Path('/srv/opentallas-scratch/claude/shared-core-0733/rp1_actual')/f'{master}_{c}.lib'
    cv.append(cap(file.read_text(),master,'clk'))
   caps[key]=dict(zip(['TT','FF'],cv));inventory[master]=dict(nominal_cap_ff_by_corner=dict(zip(['TT','FF'],cv)),selected_cap_ff=max(cv))
 sl['core_tree']=CI.named_tree_report(report,'ck',macpins,load_balance='joint_nldm_plan')
 leafby={q:l['node'] for l in sl['core_tree']['leaves'] for q in l['sinks']}
 assert all(len(v)==2 and leafby[v[0]]==leafby[v[1]] for v in pairs.values()),'atomic MIF pairs must be complete and same-leaf'
 sl['core_tree']['same_leaf_pairs']=list(pairs.values());data={k:copy.deepcopy(v) for k,v in template.items() if k!='slice'};data.update(slice=sl,points=points,caps=caps,profiles=[[2,1.1],[4,1.3]],slew_limits=[78.],input_slew_ps=0.,source_geometry=str(geo),cap_inventory=inventory,atomic_pairs=len(pairs),qualification='MODEL ONLY; ideal0ps prototype input, parent-die driver slew undeclared; actual per-corner nominal pin caps; rise-only buffer NLDM; NDR C scaling assumed; geometry hook confirmation required')
 (out/'input.json').write_text(json.dumps(data,indent=1));print(typ,'pairs',len(pairs),'caps',inventory)
