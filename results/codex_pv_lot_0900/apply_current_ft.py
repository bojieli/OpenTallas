"""Apply zero-cycle PV physical-site repair to exact matching current slot arrays."""
import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);P=json.loads(p.read_text());ledger=json.load(open(pathlib.Path(__file__).with_name("current_ft_bit_site_delta.json")))
for r in ledger:
 slots=[s for s in P["partition_types"][r["type"]]["ft_slots"] if s["name"]==r["slot"]]
 assert len(slots)==1,r
 s=slots[0];j=r["stage"]-1
 assert s["bit_sites_um"][j]==r["old"],("source mismatch",r["type"],r["slot"],j)
 s["bit_sites_um"][j]=r["new"]
pathlib.Path(sys.argv[2]).write_text(json.dumps(P,indent=1)+"\n")
print("APPLIED",len(ledger),"existing stage-group translations;0 cycles")
