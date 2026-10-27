import sys,json,os
from pathlib import Path
root=Path.home()/"OpenTallas";sys.path[:0]=[str(root/"tools"),str(root/"tools/throughput")]
import accepted_cost as A
out={"scope":"C14toC15 core-chain sensitivity ONLY; unproved native capture graph prevents adoption", "lane_total_delta":0,"changes":"4COLLdatachains+1 and2SMresponsechains+1; coherent operations not22cycle sum", "workloads":{}}
for wl,name in A.DESIGNS["r25gq"]["workloads"].items():
 run,count=A.hbm_schedule(name);b=run();r={"reference_cycles":b,"reference_tok_s":1.2e9/b,"variants":{},"record_class_counts":{}}
 for k in ["COLL.*","SM.*|ATT.*"]:r["record_class_counts"][k]=sum(v for op,v in count.items() if A.op_match(op,k))
 for tag,ex in [("COLL_plus1",(("COLL.*",None,1.0),)),("SM_response_plus1",(("SM.*|ATT.*",None,1.0),)),("both_serial_upper",(("COLL.*",None,1.0),("SM.*|ATT.*",None,1.0)))]:
  x=run(extra=ex);r["variants"][tag]={"added_cycles":x-b,"tok_s":1.2e9/x,"reference_loss_pct":A.loss_pct(b,x)}
 out["workloads"][wl]=r
Path("conditional_core_price.json").write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out))
