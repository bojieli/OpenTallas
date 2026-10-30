import json,sys,collections
sys.path.insert(0,"/srv/opentallas-scratch2/claude/die-qc41/src_pc/tools/die_plan")
import die_clock_128 as C128
d=sys.argv[1]; wires=json.load(open(d+"/fixed_wires.json")); pg=json.load(open(d+"/pg_rects.json"))
nd=dict(width=.08,space=.32,rf=.5,cf=1.15)
drawn=[tuple(seg)+(ext,) for w in wires for seg,mode,ext in zip(w["segs"],w.get("shield_modes") or [C128.DRAWN]*len(w["segs"]),w.get("shield_ext") or [None]*len(w["segs"])) if mode==C128.DRAWN]
ties=C128.shield_ties(C128.shield_stripes(drawn,nd),pg,nd["width"])
print({k:(len(v) if hasattr(v,"__len__") else v) for k,v in ties.items()})
for k in ("untied","shorts"):
  v=ties[k]; print(k, list(v)[:5])
