"""Partition placement candidates into reciprocal linear chains, preserving every branch.

The contract can fan out. A pred/succ dictionary pair contains one selected successor
per source; following pred through a fork and then a different succ loses the starting
branch. Only reciprocal links belong to the same linear placement group. Connectivity
and edge timing are untouched; the post-placement per-bus reach audit remains binding.
"""
def linear_chains(nodes, pred, succ):
    pending = set(nodes)
    for n in nodes:
        if n not in pending:
            continue
        head = n
        seen = {n}
        while pred.get(head) in pending:
            parent = pred[head]
            if succ.get(parent) != head or parent in seen:
                break
            head = parent
            seen.add(head)
        chain = [head]
        members = {head}
        while succ.get(chain[-1]) in pending:
            child = succ[chain[-1]]
            if pred.get(child) != chain[-1] or child in members:
                break
            chain.append(child)
            members.add(child)
        if n not in members:
            raise ValueError(f'linear placement group lost starting instance {n}')
        pending.difference_update(members)
        yield chain
    if pending:
        raise ValueError(f'unplaced relay group members: {sorted(pending)[:12]}')
