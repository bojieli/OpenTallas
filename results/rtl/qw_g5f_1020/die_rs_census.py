# QW-G5F 10-20: die-level reset-net census of the early-sticky capture proposal on the actual g5 die.v:
# existing die-top loads of each group's reset net + the capture node's direct rs loads (N+2 mapped, census fcap16/fcap1).
import json, sys, collections
sys.path[:0] = ['.']
import fault_inventory as F
die, prop = sys.argv[1], json.load(open(sys.argv[2]))
nets, tin, tout, insts = F.E.P.parse_die(die)
loads = collections.Counter()
for mst, name, params, cm in insts:
    for p, expr in cm.items():
        if p in ('rs', 'rst_n', 'rst', 'reset_n', 'rsi'):
            for b in (F.E.P.expr_bits(expr, nets) or []):
                loads[b[0] if nets[b[0]][0] == 1 else f'{b[0]}[{b[1]}]'] += 1
add = collections.Counter(); nodes = collections.Counter()
for n in prop['nodes']:
    add[n['reset']] += n['reset_added_direct_loads']; nodes[n['reset']] += 1
rows = sorted(((loads.get(r, 0) + a, loads.get(r, 0), a, nodes[r], r) for r, a in add.items()), reverse=True)
over = [r for r in rows if r[0] > 32]
print(json.dumps(dict(reset_nets=len(rows), over32=len(over), worst=rows[:8], die_existing_max=max(loads.values()),
                      added_total=sum(add.values()), nodes=len(prop['nodes'])), default=str))
