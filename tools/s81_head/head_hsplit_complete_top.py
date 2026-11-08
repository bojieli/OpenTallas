import json, sys
sys.path.insert(0, "tools/s81_head"); sys.path.insert(0, "tools/die_plan")
import head_start_sources as H
plan = json.load(open(sys.argv[1])); stages = json.load(open(sys.argv[2])); top = open(sys.argv[3]).read()
t, sp = H.complete_top(top, plan, stages)
open(sys.argv[4], "w").write(t); print('unused uniform exports', len(sp), [x for x in sp if 'host' in x['part']])
