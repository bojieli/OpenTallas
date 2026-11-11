"""STRUCT-CTL-1 pin cycles: lane fixed_cycles += added source out-station + added destination in-station count
(native_istations / ts_relay_event convention) for every lane through the edited type; lane_latency diff vs base."""
import sys,json,copy,hashlib
sys.path.insert(0,sys.argv[1]+'/tools/die_plan')
import schema as S
base_f,cand_f,T,out_f,rep_f=sys.argv[2:7]
rb=open(cand_f,'rb').read(); raw=json.loads(rb); base=json.load(open(base_f))
def style(b,P):
    for f in (lambda p: json.dumps(p,separators=(",",":"))+"\n",lambda p: json.dumps(p)+"\n",lambda p: json.dumps(p,indent=1)+"\n",lambda p: json.dumps(p,indent=2)+"\n",lambda p: json.dumps(p,separators=(",",":")),lambda p: json.dumps(p)):
        if f(P).encode()==b: return f
    raise SystemExit('style unknown')
dump=style(rb,raw)
PT=raw['partition_types']
BT=base['partition_types']
def cnt(tn,bus,pt=None):
    return sum(len(e['regs_um']) for e in (PT if pt is None else pt).get(tn,{}).get('internal_stations',[]) if e.get('conn')=='bus:'+bus)
P=S.Plan(copy.deepcopy(raw))
lanes={l['id']:l for l in raw['lanes']} if isinstance(raw['lanes'],list) else raw['lanes']
changed={}
for lid,ln in lanes.items():
    a=P.ports[ln['ports'][0]]; b=P.ports[ln['ports'][-1]]
    if T not in (P.parts.get(a['src']['part'],{}).get('type'),P.parts.get(b['dst']['part'],{}).get('type')): continue
    # TLOAD-ROMSTAGE 11-11: incremental -- fixed_cycles += (candidate - base) station count on the lane's source /
    # destination bus, so a lane that already carries cycles from an earlier event (landing pads, base stations) keeps
    # them (the old form refused any lane whose base fixed_cycles was not 0).
    add=0
    for end,side in ((a,'src'),(b,'dst')):
        if end[side]['part'] in P.parts:
            tn=P.parts[end[side]['part']]['type']
            add+=cnt(tn,end[side]['bus'])-cnt(tn,end[side]['bus'],BT)
    old=int(ln.get('fixed_cycles',0))
    if add:
        if old+add<0: raise SystemExit(f'{lid}: fixed_cycles {old} + {add} < 0, refusing')
        ln['fixed_cycles']=old+add; changed[lid]=[old,old+add]
def lat(r):
    Q=S.Plan(copy.deepcopy(r)); o={}
    for l in Q.lanes:
        try:o[l]=Q.lane_latency(l)['cycles']
        except Exception:pass
    return o
L0,L1=lat(base),lat(raw)
d={l:[L0.get(l),L1.get(l)] for l in set(L0)|set(L1) if L0.get(l)!=L1.get(l)}
errs=S.validate(raw) if hasattr(S,'validate') else []
open(out_f,'w').write(dump(raw))
sha=hashlib.sha256(open(out_f,'rb').read()).hexdigest()
json.dump(dict(fixed_cycles_set=changed,lane_latency_delta=d,n_lanes_changed=len(d),validate_errors=len(errs) if errs else 0,sha256=sha),open(rep_f,'w'),indent=1,sort_keys=True)
print('fixed set',len(changed),'latency lanes changed',len(d),'extra(not set)',sorted(set(d)-set(changed))[:10],'validate',len(errs) if errs else 0,'sha',sha[:12])
