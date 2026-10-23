"""Explicit clock followers of real owner ports, after legacy instance following.

This selects an existing regional clock. It creates no clock, register or edge.
A source owner must supply the exact port law; presence of a clock port alone
is not a source-domain proof.
"""
import os


def apply(model, per, record):
    mapping = model.get('ck_follow_port') or {}
    if not mapping:
        return 0
    if os.environ.get('OT_SPLIT_CK_FOLLOW_PORT', '0') != '1':
        raise ValueError('explicit per-port clock following is disabled by default')
    locations = {}
    for region, endpoints in per.items():
        for endpoint in endpoints:
            locations.setdefault(endpoint, []).append(region)
    legacy = model.get('ck_follow') or {}
    moves = []
    for follower, owner in sorted(mapping.items()):
        for endpoint in (follower, owner):
            if not isinstance(endpoint, tuple) or len(endpoint) != 2 or not all(isinstance(x,str) and x for x in endpoint):
                raise ValueError('clock follower and owner must be exact instance/port tuples')
            if len(locations.get(endpoint, [])) != 1:
                raise ValueError('clock endpoint must have one actual region: '+str(endpoint))
        if legacy.get(follower) != owner[0]:
            raise ValueError('explicit clock port disagrees with actual legacy instance owner')
        if owner in legacy or owner in mapping or follower == owner:
            raise ValueError('owner must be a real terminal clock input, not another follower')
        moves.append((follower,owner,locations[follower][0],locations[owner][0]))
    # Validate every endpoint before mutating any regional clock list.
    for follower,owner,source,destination in moves:
        if source != destination:
            per[source].remove(follower)
            per[destination].append(follower)
    for region in [region for region, endpoints in per.items() if not endpoints]:
        del per[region]
    record['follow_port'] = [dict(follower=list(f),owner=list(o),source_region=s,destination_region=d)
                             for f,o,s,d in moves]
    return sum(s != d for f,o,s,d in moves)
