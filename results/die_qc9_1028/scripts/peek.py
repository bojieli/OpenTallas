import json,collections,sys
from pathlib import Path
Q=Path("/srv/opentallas-scratch2/claude/die-qc9-1028");R=Path("/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028")
sys.path.insert(0,str(R/"source_tree/tools/die_plan"));import schema as S
P=S.Plan(json.load(open(R/"build_inputs/event/qc_k2b_phase12.json")))
T=json.load(open(Q/"trial7/clock/tree.json"));reg=json.load(open(R/"build_inputs/part_region.json"))["part_region"]
contracts={(p,n):tp for p,pp in P.parts.items() for n,_,_,tp in S.core_taps(P,pp["type"])}
tl={l.split()[1]:float(l.split()[2]) for l in open(Q/"c7_TT/arr_TT.txt") if l[0]=="T"}
g=sys.argv[1]
for t in T["taps"]:
  if reg[t["part"]]!=g: continue
  tp=contracts.get((t["part"],t["tap"]));lat=S.core_tap_insertion_ps(tp,"TT") if tp else 250
  print(f'{t["port"]:40s} {P.parts[t["part"]]["type"]:14s} arr {tl[t["port"]]:8.1f} lat {lat:6.1f} b {tl[t["port"]]+lat:8.1f} xy {t["xy"]}')
