# usage (repo root): python3 tools/qwen_tp8/cut_layer_plan.py ITDIR  -> top fine cuts per axis under layer plan A (die M8+ over tile_nk) and B (tile_nk <= M6, die M7+)
import sys; sys.path.insert(0,'results/arch/qwen_tp8_1012'); import cuts as C
d=sys.argv[1]
for plan in 'AB':
    C.CAP_MODE='v3'; C.CLUSTER_PLAN=plan; A=C.Net(d+'/rom_tp8b.json')
    F=A.fine(top=40)
    for ax in 'xy':
        r=[f for f in F if f['ax']==ax][:2]
        print(plan, ax, [(f['util'], f['pos'], f['win'], f['fam']) for f in r])
