"""Review-only reset-bank identity: emits CONDITIONAL, never rewires a netlist.
Canonical literal-D helper remains unchanged. A cold arbitrary bank is NOT
interchangeable until a real asynchronous assertion has been witnessed.
"""
from itertools import product

class Refused(ValueError): pass

def signature(cells, output, maturity=False):
    if not maturity:
        raise Refused("cold state: actual asynchronous reset assertion not witnessed")
    drivers={}
    for name,c in cells.items():
        for q in c.get("connections",{}).get("Q",[]):
            if q in drivers: raise Refused("multiple Q drivers")
            drivers[q]=name
    seen=set(); stages=[]; bit=output
    for age in range(3):
        if bit in seen:raise Refused("cyclic reset chain")
        seen.add(bit)
        if bit not in drivers:raise Refused("missing chain register")
        c=cells[drivers[bit]];p=c.get("connections",{})
        if c.get("type")!="$_DFF_PN0_" or set(p)!={"C","R","D","Q"}:
            raise Refused("only positive-edge async-active-low reset-zero one-bit flops")
        if any(len(p[x])!=1 for x in p):raise Refused("non-scalar register")
        if c.get("parameters") or c.get("init") not in (None,"0"):
            raise Refused("unaccounted parameters or initial state")
        stages.append((tuple(p["C"]),tuple(p["R"])))
        bit=p["D"][0]
    if bit!="1":raise Refused("requires exactly two sync stages plus one relay, rooted at one")
    if len(set(stages))!=1:raise Refused("clock/reset differs along chain")
    return ("conditional_after_async_assert",tuple(stages))

def equivalence(cells,a,b,maturity=False):
    return signature(cells,a,maturity)==signature(cells,b,maturity)

def exhaustive_maturity():
    # Enumerate arbitrary power-up states for two 3-register banks. Cold
    # mismatch is allowed and MUST NOT establish a rewrite certificate.
    cold=0;checks=0
    for a,b in product(range(8),repeat=2):
        if (a>>2)!=(b>>2):cold+=1
        mature=False
        for event in ("tick","assert","release","tick","tick","tick","tick"):
            if event=="assert":a=b=0;mature=True
            elif event=="tick":a=((a<<1)|1)&7;b=((b<<1)|1)&7
            if mature:
                assert a==b;checks+=1
    assert cold==32
    return {"cold_output_mismatches":cold,"post_assert_state_checks":checks,
            "verdict":"CONDITIONAL_AFTER_ACTUAL_ASYNC_ASSERT; no canonical rewrite"}
