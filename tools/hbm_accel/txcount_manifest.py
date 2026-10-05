"""Default-off manifest lowering for HA1; caller must use frozen actual owners.
Returns descriptors, never synthesizes ACKs, fences, timers or owner retirement.
"""
def lower(*, enabled=False, rank, job, generation, owners):
    if not enabled:
        return None
    if not (0 <= rank < 128 and 0 <= job < 2**32 and 0 <= generation < 16):
        raise ValueError('rank/job/generation bounds')
    owners = tuple(owners)
    if not 1 <= len(owners) <= 32 or len(set(owners)) != len(owners):
        raise ValueError('manifest requires 1..32 unique owner55 identities')
    for owner in owners:
        if type(owner) is not int or not 0 <= owner < 2**55:
            raise ValueError('owner55 bounds')
        if (owner >> 48, (owner >> 13) & 0xffffffff, (owner >> 9) & 15) != (rank, job, generation):
            raise ValueError('owner55 must match frozen rank/tag(job)/generation')
        if ((owner >> 45) & 7) >= 6:
            raise ValueError('owner55 SM bound')
    return dict(rank=rank, job=job, generation=generation, count=len(owners),
                transactions=[dict(index=i, owner55=o) for i, o in enumerate(owners)],
                completion='scheduler visibility only; canonical consumer and drain retain leases')
