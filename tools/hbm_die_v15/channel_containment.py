"""Exact legacy containment diagnostic with immutable channel-parent filtering."""


def channel_containment(placement, channels):
    # channels is a pure lookup of immutable view/master/slot grant metadata.
    # Keep insertion order and duplicate names for multiply-containing parents.
    parents = [(m, u) for m, u in placement.items() if channels(m)]
    return sorted(n for n, v in placement.items() for m, u in parents if m != n and
                  u['x'] <= v['x'] and v['x'] + v['w'] <= u['x'] + u['w'] and
                  u['y'] <= v['y'] and v['y'] + v['h'] <= u['y'] + u['h'])
