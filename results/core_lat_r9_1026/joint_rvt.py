"""Bounded optional escape from a near-tied late-path coordinate-descent plateau.

The caller evaluates the entire real composed tree for every proposal. This
module invents no delays and changes at most one master on each of 2..3
independent late paths; root/topology/stages/geometry are outside its interface.
"""
import itertools
import math

GAIN = 0.05  # same strict improvement used by canonical single-driver descent


def objective(tt, ff):
    return max(max(tt.values())-min(tt.values()), max(ff.values())-min(ff.values()))


def finite(values):
    return bool(values) and all(math.isfinite(float(v)) for v in values.values())


def propose(tt, ff, parents, cells, envelope, evaluate, slew_limit=80.0):
    """evaluate(assignments, need_slew)->(full_tt,full_ff,corner_in_out_slews).

    At a single-step plateau, target the dominant corner's at most three leaves
    within the unchanged 0.05ps acceptance quantum of its latest leaf. For each
    disjoint path retain at most two best full-tree-evaluated master changes.
    Re-evaluate all <=8 combined proposals from the unchanged current tree;
    accept only a strict global improvement with both corners' IN/OUT slew<=80.
    """
    if not math.isfinite(slew_limit) or slew_limit <= 0:
        raise ValueError("joint RVT slew limit must be positive and finite")
    slew_limit=min(slew_limit,80.0)
    if not finite(tt) or not finite(ff):
        return None
    old=objective(tt,ff)
    corner,late_values=('TT',tt) if max(tt.values())-min(tt.values()) >= max(ff.values())-min(ff.values()) else ('FF',ff)
    late=max(late_values.values());near=sorted(n for n,v in late_values.items() if late-v <= GAIN+1e-9)
    if not 2<=len(near)<=3:
        return None
    def path(n):
        result=[]
        while parents.get(n) is not None:
            result.append(n);n=parents[n]
        return set(result)
    paths={n:path(n) for n in near}
    # A coupled late-path proposal cannot insert intentional delay in an early
    # path. Exclude both corners' current earliest paths and all shared drivers.
    early=path(min(tt,key=tt.get))|path(min(ff,key=ff.get))
    options=[];trials=0
    for leaf in near:
        other=set().union(*(paths[n] for n in near if n!=leaf))
        unique=paths[leaf]-other-early
        candidates=[]
        for node in sorted(unique):
            for master in envelope:
                if master==cells[node]:continue
                t,f,_=evaluate({node:master},False);trials+=1
                if not finite(t)or not finite(f):continue
                values=t if corner=='TT'else f
                if values[leaf]>=late_values[leaf]-GAIN:continue
                candidates.append((values[leaf],objective(t,f),node,master))
        choices=sorted(candidates)[:2]
        if not choices:return None
        options.append(choices)
    best=None
    for batch in itertools.product(*options):
        assignment={p[2]:p[3]for p in batch}
        assert len(assignment)==len(near)<=3
        t,f,slews=evaluate(assignment,True);trials+=1
        if not finite(t)or not finite(f)or not finite(slews)or set(slews)!={'TT_in','TT_out','FF_in','FF_out'}:continue
        score=objective(t,f)
        if score>=old-GAIN or max(slews.values())>slew_limit:continue
        key=(score,(max(t.values())-min(t.values()))+(max(f.values())-min(f.values())),tuple(sorted(assignment.items())))
        if best is None or key<best['key']:
            best=dict(key=key,assignments=assignment,tt=t,ff=f,slews=slews,corner=corner,near_leaves=near)
    if best is not None:best['full_tree_trials']=trials
    return best
