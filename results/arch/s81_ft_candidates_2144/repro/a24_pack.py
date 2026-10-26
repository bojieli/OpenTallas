import json,sys,re,copy,inspect,math
from pathlib import Path
from multiprocessing import get_context
S=Path(sys.argv[1]);out=Path(sys.argv[2]);sys.path[:0]=[str(S/'tools/die_plan'),str(S/'physical/die_plan/s81'),str(S)]
import ft_corridor as F,compact_plan
raw=json.loads((S/'physical/die_plan/s81/die_plan.json').read_text())
targets={"ot_s81sl_leaf__t68":{"ft2":None,"ft4":None}}
# Preserve every other slot's exact existing coordinates and reserve those cells.
code=inspect.getsource(F.place).replace('def place(', 'def place_selected(')
code=code.replace('for slot in sorted(ty["ft_slots"], key=lambda s: -s["width"]):',
'''for frozen in ty["ft_slots"]:
            if f"{tn}/{frozen['name']}" not in jogs:
                for stage in frozen.get('bit_sites_um', []):
                    for x,y in stage: alloc.reserve_rectangle((x,y,x+CELL[0],y+CELL[1]))
        for slot in sorted(ty["ft_slots"], key=lambda s: -s["width"]):
            if f"{tn}/{slot['name']}" not in jogs: continue''')
exec(compile(code,'<preserve-unselected-ft-slots>','exec'),F.__dict__)
def work(tn):
 t=raw['partition_types'][tn]
 original=copy.deepcopy(t)
 jogs={tn+'/'+sn:v for sn,v in targets[tn].items()}
 split={}
 bands={}
 for slot in t["ft_slots"]:
  if slot["name"] not in targets[tn]:continue
  delta=abs(sum(slot["in_window_um"])-sum(slot["out_window_um"]))/2
  if delta>600:
   jogs[tn+"/"+slot["name"]]=1150.2 if slot["in_face"]=="S" else 19.5
   split[tn+"/"+slot["name"]]=128
   continue
  c=(sum(slot["in_window_um"])+sum(slot["out_window_um"]))/4
  bw=360. if slot["width"]>500 else 220.
  lo=min(max(6.144,c-bw/2),t["outline_um"][0]-6.144-bw)
  bands[tn+"/"+slot["name"]]=(lo,lo+bw)
 try:
  ledger=F.place_selected(raw,[tn],jogs=jogs,split_bits=split,bands=bands)
  for a,b in zip(original['ft_slots'],t['ft_slots']):
   assert a['stations']==b['stations']
   if a['name'] not in targets[tn]:assert a==b
  assert original['hard_cores']==t['hard_cores']
  return tn,t,ledger,None
 except Exception as e:return tn,original,[],repr(e)
report={'base':'A18 d8d3dd75ef418806','targets':targets,'pass':[],'fail':{},'added_cycles':0,'ledger':[]}
with get_context('fork').Pool(min(8,len(targets))) as pool:
 for tn,t,led,err in pool.imap_unordered(work,targets):
  if err:report['fail'][tn]=err;print('FAIL',tn,err,flush=True)
  else:raw['partition_types'][tn]=t;report['pass'].append(tn);report['ledger']+=led;print('PASS',tn,targets[tn],flush=True)
out.write_text(compact_plan.dumps(raw));Path(str(out)+'.report.json').write_text(json.dumps(report,indent=2));print('A24',len(report['pass']),'PASS',len(report['fail']),'FAIL',flush=True)
