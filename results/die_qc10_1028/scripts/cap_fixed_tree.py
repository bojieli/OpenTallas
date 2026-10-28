"""ESTIMATE wrapper: count_align_plan with the start tree FIXED to the planned clock-forwarding tree (START-TREE-1 form:
one fork start port per forwarding edge) instead of its min-ambiguity search.  usage: cap_fixed_tree.py TP.txt <count_align_plan args>"""
import sys
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/die-qc9-1028/tools/die_plan')
import count_align_plan as C
tp=open(sys.argv[1]).read().split()
want={}
for a in tp:
    if a!='--tree-parent': x,p=a.split('=',1); want[x]=p
def fixed(rows, regions):
    byp={r['port']:r for r in rows}
    par={}
    for x,p in want.items(): par[x]=(byp[p]['src'],byp[p])
    roots=[r for r in regions if r not in par]
    assert len(roots)==1, roots
    par[roots[0]]=None
    return roots[0], par
C.directed_tree=fixed
sys.exit(C.main(sys.argv[2:]))
