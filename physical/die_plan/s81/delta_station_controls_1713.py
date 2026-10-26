"""Source-only ST3 clock-demand closure for non-root station RESET and START.

Apply after the station geometry/density delta. This adds only control DFF demand;
face/FT sites continue to come from taps.planned_sinks. No data cycles are added; reset/START release offsets must be regenerated.
Root sync/lock controllers need a separate weighted census and are rejected.
"""
import copy
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/die_plan"))
import schema as S
import reset_tree as RT

STATIONS=tuple(f"slice_station__t{n}" for n in (24,25,26,27,30,36,37,38,40,41,42,46,47))


def census(T):
    if T["entry"] == "sync":
        raise ValueError("root sync/lock clock census is not a station single-DFF census")
    entries=[("u_rst_in",T["root"],"reset_entry")]
    if T.get("start"):
        entries.append(("u_run_in",T["start_in"],"start_entry"))
        rel=RT.start_relays(T)
    else:
        rel=[dict(r,role="reset") for r in T["relays"]]
    entries += [(r["name"],r["xy"],r.get("role","reset")) for r in rel]
    names=[e[0] for e in entries]
    if len(set(names))!=len(names):raise ValueError("duplicate physical control DFF alias")
    cnt=Counter((round(xy[0],3),round(xy[1],3)) for _,xy,_ in entries)
    return sorted([x,y,n] for (x,y),n in cnt.items()),dict(Counter(r for _,_,r in entries))


def apply(raw,types=STATIONS,rounds=16,require_start=True,waveform=None,plan_path=None):
    # Simultaneous group rounds matter: reset contract depth can span types.
    # Work on a copy so failure never leaves a partially updated plan.
    trial=copy.deepcopy(raw);types=tuple(types)
    for tn in types:
        ck=trial["partition_types"][tn].setdefault("clock",{})
        if ck.get("sink_sites_um"):
            raise ValueError(f"{tn}: existing extra sink inventory requires explicit reconciliation")
    prev=None;seen=set();base_contract=None
    for k in range(rounds):
        P=S.Plan(trial,path=plan_path)
        trees={tn:RT.for_type(P,tn) for tn in types}
        if require_start and any(not T.get("start") for T in trees.values()):
            raise ValueError("START broadcast is absent; reset-only census cannot qualify a START-enabled successor")
        contracts={tn:dict(depth=T["depth"],release_clocks=RT.release_clocks(T)) for tn,T in trees.items()}
        if base_contract is None:base_contract=contracts
        inventories={tn:census(T) for tn,T in trees.items()}
        key=tuple((tn,tuple(tuple(v) for v in inventories[tn][0])) for tn in types)
        if key==prev:
            report={tn:dict(sites=len(sites),flops=sum(r[2] for r in sites),roles=roles,rounds=k+1,fixed_point=True,initial_contract=base_contract[tn],final_contract=contracts[tn],
                                   release_delta=contracts[tn]["release_clocks"]-base_contract[tn]["release_clocks"])
                    for tn,(sites,roles) in inventories.items()}
            if waveform is not None:
                waveform.update(RT.wf_plan(P))
            raw.clear();raw.update(trial)
            return report
        if key in seen:raise ValueError("group control/tap census oscillates")
        seen.add(key);prev=key
        for tn,(sites,_) in inventories.items():
            trial["partition_types"][tn]["clock"]["sink_sites_um"]=sites
    raise ValueError(f"group control/tap census did not converge in {rounds} rounds")
