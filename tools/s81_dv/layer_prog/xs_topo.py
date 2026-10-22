"""S81-RATE3 (10-20): per-slice PHYSICAL frame counts for the field row dealing (opt-in OT_XS_TOPO=1).

The p4l(-MU) die has 122 physical frames: 12 slices with 8 frames, cl2S / cl5S with 7, cl3S / cl4S with 6
(results/arch/s81_fullstage_admission_1020/summary.json).  xs_place.op_groups / xs_bf._bf_groups dealt every slice's rows
over NFRAME = 8 owners, so on the 7/6-frame slices the rows of the phantom owners 6/7 were never compiled (wq_b 384
rank rows, merged gu 54 and down 60 rank rows per expert).  With OT_XS_TOPO=1 every slice deals its rows over its real
frames; the die-wide phase list (one phase sequence for every frame) then takes the slowest slice's phase count.
Default off: earlier evidence stays reproducible byte-for-byte.  Set from the bind9 die by dv_layer_compile.Die.
"""
import xs_flags as XO

ENABLED = XO.on('OT_XS_TOPO')     # S81-ROMOPT-A: release default on
# OT_XS_PROP=1 (needs OT_XS_TOPO=1): ops whose slice ownership is free (row-sharded outputs that the CAP descriptors
# address by per-slice rbase / rcnt: attn.wo_b, ffn.down) deal their rows over the slices IN PROPORTION to the physical
# frames, so a 6-frame slice no longer sets the die-wide phase count.  Heads (wq_b, idx.q) stay on their slice.
PROP = ENABLED and XO.on('OT_XS_PROP')
NFRAME_DEFAULT = 8
TOPO = None          # TOPO[g] = physical frames of slice index g (None = legacy 8 everywhere)
SOURCE = None


def set_from_die(die):
    """record the die's frames per slice index (slice_index = the sid strap, else the sorted slice order)"""
    global TOPO, SOURCE
    if not ENABLED:
        return
    s = die.slices()
    t = {}
    for sl in s:
        g = s[sl]['sid'] if s[sl].get('sid') is not None else sorted(s).index(sl)
        t[int(g)] = len(die.frames_of(sl))
    n = max(t) + 1
    assert sorted(t) == list(range(n)), ('slice indices not contiguous', sorted(t))
    assert all(1 <= v <= NFRAME_DEFAULT for v in t.values()), t
    TOPO = [t[g] for g in range(n)]
    SOURCE = getattr(die, 'die_sha', None)


def nfr(g):
    return NFRAME_DEFAULT if TOPO is None else TOPO[g]


def describe():
    return dict(enabled=ENABLED, frames_per_slice=TOPO, die_sha=SOURCE)


def chunk(grp, sel_all, c, R):
    """rows of die-wide chunk c of one frame (sel_all = the frame's rows of the group).  Legacy: consecutive blocks of R
    (a frame with fewer rows gets empty tail chunks).  OT_XS_TOPO=1: the die-wide chunk count is set by the slowest
    (fewest-frame) slice, so every frame spreads its rows evenly over all chunks (+-1 row, <= R each): no empty FP
    phase on the 8-frame slices, and the per-phase row count never exceeds the measured shape's R."""
    if TOPO is None:
        return sel_all[c * R:(c + 1) * R]
    most = max(len(fr) for sl in grp['groups'] for fr in sl)
    nch = -(-most // R)
    b, e = divmod(len(sel_all), nch)
    lo = c * b + min(c, e)
    out = sel_all[lo:lo + b + (1 if c < e else 0)]
    assert len(out) <= R, (len(out), R)
    return out


def slice_deal(n, nslice):
    """n rows over nslice slices as contiguous ranges: equal (+-1) by default; with OT_XS_PROP=1 in proportion to the
    slices' physical frames (largest remainder, ties to the lower slice index)"""
    if not PROP or TOPO is None:
        b, e = divmod(n, nslice)
        cnt = [b + (1 if i < e else 0) for i in range(nslice)]
    else:
        tot = sum(TOPO[:nslice])
        q = [n * TOPO[i] / tot for i in range(nslice)]
        cnt = [int(x) for x in q]
        for i in sorted(range(nslice), key=lambda i: (-(q[i] - cnt[i]), i))[:n - sum(cnt)]:
            cnt[i] += 1
    out, s = [], 0
    for k in cnt:
        out.append(list(range(s, s + k)))
        s += k
    assert s == n
    return out
