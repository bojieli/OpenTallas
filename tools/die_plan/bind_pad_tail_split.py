"""KV-PAD-TAIL-SPLIT (FABLE-FIX-KV-HG-CHAIN 11-18): per-consumer-core tail copies of a landing pad.

A landing pad (bind.py emit_type, "landing pad: as-built relative timing") is ONE ot_dp_dly #(.W(1), .D(pad)) per
(in-bus bit, pad) and every consumer pin reads its q.  When the consumers are pins of several hard cores far apart, the
last pad flop drives all of them in one hop and no site reaches every core (measured on kv3_pv_v12: 768 pad chains x 8
kv3_pv_pair pins 644..1,761 um apart, register-to-core -1,197 ps at placement; chain re-spacing made it worse).

Opt-in asbuilt key (absent = byte-identical bind output):

    "land_pad_tail_split": {"types": ["kv3_pv.*"], "min_spread_um": 400, "hop_um": 380}

For a (bus bit, pad) of a selected partition type whose consumer pins sit on two or more plan hard cores with a
pin-to-pin Manhattan spread S over min_spread_um, the pad becomes a shared trunk ot_dp_dly D = pad - K (omitted when 0)
and one ot_dp_dly D = K per consumer hard core; every consumer pin reads the copy of its own core.

    K = min(pad, max(1, ceil((S / 2) / hop_um)))

S / 2 is the longest branch when the trunk ends at the L1 centre of the consumer pins (plan pin xy = core origin +
track_offset + orient(pin)), hop_um the register reach.  The depth per sink stays `pad`: only the emitted instances
change, the sink descriptors (R8 table, bind_latency / lane as-built records, LATCHECK input) are untouched.

Not covered (left as emitted today, counted in bind_pad_tail_split.json): R8 strap-count banks (ot_dp_dly_cnt),
PAD_TREE types, position-bank members, registered-pin hard partitions; consumers that are not plan hard cores (or have
no plan pin xy) keep reading the shared full-depth pad.
"""
import math
import re

KEY = "land_pad_tail_split"


def config(ab):
    """the checked option, or None when the key is absent"""
    c = (ab or {}).get(KEY)
    if c is None:
        return None
    if not isinstance(c, dict) or not isinstance(c.get("types"), list) or not c["types"] or \
            set(c) - {"types", "min_spread_um", "hop_um"}:
        raise ValueError(f"asbuilt.{KEY}: expected {{types: [regex..], min_spread_um, hop_um}}")
    out = dict(types=[re.compile(x) for x in c["types"]], min_spread_um=float(c.get("min_spread_um", 400.0)),
               hop_um=float(c.get("hop_um", 380.0)))
    if out["hop_um"] <= 0 or out["min_spread_um"] < 0:
        raise ValueError(f"asbuilt.{KEY}: hop_um must be > 0 and min_spread_um >= 0")
    return out


def selected(cfg, tn):
    return any(x.fullmatch(tn) for x in cfg["types"])


def pin_table(hard_cores, plan_dir):
    """{core inst: {port: {bit ('' = scalar): (x, y)}}} in the partition-type frame"""
    import check as CK
    tab = {}
    for hc in hard_cores or []:
        if not (hc.get("pins") or hc.get("pins_file")):
            continue
        try:
            raw = CK.core_pins(hc, plan_dir)
        except (OSError, ValueError, KeyError):
            continue
        w, h = hc["outline_um"]
        o = hc.get("orient", "R0")
        dx, dy = hc.get("track_offset_um", [0.0, 0.0])
        t = tab.setdefault(hc["inst"], {})
        for nm, _layer, x, y in raw:
            pn, _, bit = nm.partition("[")
            tx, ty = CK._orient_pt(o, w, h, x, y)
            t.setdefault(pn, {})[bit.rstrip("]")] = (hc["origin_um"][0] + dx + tx, hc["origin_um"][1] + dy + ty)
    return tab


def pin_xy(tab, rel, pn, i, width):
    """(core inst, (x, y)) of leaf `rel` pin pn[i], or (None, None) when the leaf is no plan hard core / has no pin xy"""
    for inst in (rel, rel[2:] if rel.startswith("u_") else rel):
        t = tab.get(inst)
        if t is None:
            continue
        bits = t.get(pn)
        if bits is None:
            return None, None
        xy = bits.get(str(i))
        if xy is None and width == 1:
            xy = bits.get("")
        return (inst, xy) if xy is not None else (None, None)
    return None, None


def spread(pts):
    """largest pin-to-pin Manhattan distance of the points"""
    a = [x + y for x, y in pts]
    b = [x - y for x, y in pts]
    return max(max(a) - min(a), max(b) - min(b))


def tail_depth(pad, by_core, cfg):
    """(K, S) for a pad whose consumer pins are {core inst: [(x, y)..]}, or None when it is not split"""
    if pad < 1 or len(by_core) < 2:
        return None
    s = spread([xy for v in by_core.values() for xy in v])
    if s <= cfg["min_spread_um"]:
        return None
    return min(pad, max(1, math.ceil((s / 2.0) / cfg["hop_um"]))), s
