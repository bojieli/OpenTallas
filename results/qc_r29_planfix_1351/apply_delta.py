"""Apply the R29 FT-site proposal to the same unmodified slot contracts."""
import argparse,copy,hashlib,json
from pathlib import Path
def apply(plan,delta):
 out=copy.deepcopy(plan)
 for row in delta["types"]:
  tn=row["type"];old=out["partition_types"][tn]["ft_slots"]
  got=hashlib.sha256(json.dumps(old,sort_keys=True).encode()).hexdigest()
  if got!=row["original_slots_sha256"]:
   raise ValueError(tn+": source FT slots changed; recompose/replan instead of overwriting")
  assert [x["stations"]for x in old]==[x["stations"]for x in row["ft_slots"]]
  out["partition_types"][tn]["ft_slots"]=copy.deepcopy(row["ft_slots"])
 return out
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("plan");p.add_argument("--out",required=True)
 p.add_argument("--delta",default=str(Path(__file__).with_name("ft_delta.json")));a=p.parse_args()
 raw=apply(json.load(open(a.plan)),json.load(open(a.delta)))
 Path(a.out).write_text(json.dumps(raw,indent=1)+"\n")
if __name__=="__main__":main()
