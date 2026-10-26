import json,sys
sys.path.insert(0,"/srv/opentallas-scratch2/claude/s81-plan2")
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/s81-plan2/physical/die_plan/s81")
import pdump, delta_ir_1025 as D
raw=json.load(open(sys.argv[1])); rep=D.apply(raw); print("\n".join(rep))
open(sys.argv[2],"w").write(pdump.dumps(raw))
