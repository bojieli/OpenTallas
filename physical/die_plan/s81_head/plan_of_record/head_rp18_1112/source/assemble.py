# HEAD-PLAN-1 l48hp1 completed die top (run from the repo root):
#   python3 -I tools/die_plan/gen.py rtl P/source_plan.json --clock-landing P/source_sidecar.json --rtl-root . --out GEN
#   python3 -I P/source/assemble.py P GEN/s81_head_top.sv OUT.sv
# START stages = l48uo_hsplit source/start_stages (l48uo == l48vd == l48ve stages byte-identical; HSPLIT is the only
# START change; LEP keeps its 7 rst_start_raw port names). Same procedure on l48uo_hsplit reproduces its published top.
import gzip, json, sys
sys.path.insert(0, "tools/s81_head"); sys.path.insert(0, "tools/die_plan")
import head_start_sources as H
P, top, out = sys.argv[1:4]
plan = json.load(gzip.open(P + "/source_plan.json.gz")); stages = json.load(gzip.open(P + "/source/start_stages.json.gz"))
t, sp = H.complete_top(open(top).read(), plan, stages)
open(out, "w").write(t); print("TOP lines", t.count(chr(10)), "unused", len(sp))
