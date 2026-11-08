# S81-TYPES-8-COLH: plan_wg_e = wave plan + COL-WALLGAP-1108c only on the 13 class-C/A col_h rows (running/other col_h types stay byte-identical)
import json, sys
base, cplan, out = sys.argv[1:4]
ROWS = ["col_h9_r0_p2__t1__cl9f71e63d","col_h9_r0_p4__t1__cl8ef405e8","col_h9_r0_p6__t1","col_h9_r1__t1__cl49d7a23e",
 "col_h9_r1__t1__clf32cde8d","col_h9_r2__t1__clce45cab5","col_h10_r2__t1__cl1f5d6c2a","col_h10_r2__t1__cl8b686b3e",
 "col_h10_r2__t1__clac068e56","col_h10_r0_p1__t1__cl574cc59d","col_h10_r2__t1__cl99efd374","col_h9_r0_p3__t1__cl0cd90c0e",
 "col_h9_r0_p4__t1__clcb2fbfe8"]
B = json.load(open(base)); Cp = json.load(open(cplan))
assert {k: v for k, v in B.items() if k != "partition_types"} == {k: v for k, v in Cp.items() if k != "partition_types"}
n = 0
for t in ROWS:
    if B["partition_types"][t] != Cp["partition_types"][t]:
        B["partition_types"][t] = Cp["partition_types"][t]; n += 1
print("changed types", n)
json.dump(B, open(out, "w"), separators=(",", ":"))
