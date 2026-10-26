"""Proposed charge-conservation model only; not an OpenROAD patch."""
import itertools,json
out=[]
for order in itertools.permutations(['A','B']):
    ledger={'A':5,'B':300};balance=15+sum(ledger.values());trace=[]
    for net in order:
        delta=-ledger.pop(net);balance+=delta
        trace.append({'net':net,'removed_stored_charge':-delta,'balance':balance})
        assert balance==15+sum(ledger.values()) and balance>=15
    assert balance==15
    out.append({'removal_order':order,'trace':trace,'final_balance':balance})
print(json.dumps({'scope':'hypothetical per-net charge ledger, not router fix; capacity-layer restoration not implemented','controls':out},indent=2))
