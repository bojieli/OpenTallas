"""QC-PLAN-R3 11-18 (LAND-INTRA-STATIONS): pipeline stations on named intra-partition core-to-core nets, at given sites.

The QC st_a fault ring (x_st_b_i_q -> u_r2 -> u_r0 -> u_r1 -> u_r3 -> u_bout_x_st_b_o, flt_bank[3:0] + flt_vld[3:0])
is a plain wire between hard cores inside one partition type; u_r2.flt_bank_o -> u_r0.flt_bank_i is ~920 um and the
worst CTS path of the type after the tail fix (-581 ps).  Plan internal_stations core-to-core rows only map S81
CORE_CLASSES (kit_istations reports others as core_unmapped), so the binder inserts the stations itself.  The ring
protocol tolerates the cycles (ot_pl_land_phys_chunk D=4 landed bank, registered reader; OWNER pre-approved cycles).

Opt-in asbuilt key (absent = byte-identical bind output):

    "land_intra_stations": {
        "types": ["(sle|slw)_st_a.*"],
        "nets": [{"src": "u_r2.flt_bank_o", "dst": "u_r0.flt_bank_i",
                  "with": [["u_r2.flt_vld_o", "u_r0.flt_vld_i"]], "stages": 2}, ...],
        "sites": "<json, absolute or relative to the asbuilt base tree>"  (or the same object inline)
    }

Instance names are plan hard_core / leaf names (u_r0 = the bound leaf u_u_r0; the bound name is accepted too).
Sites file: {type: [{"src": "u_r2.flt_bank_o+flt_vld_o", "dst": "u_r0.flt_bank_i+flt_vld_i", "regs_um": [[x, y], ..]},
..]} (extra keys ignored; a row matches a net when its instances agree and its '+' port lists hold the net's ports).
regs_um[k] is the site of stage k counted from the source.

Per bit of the net and of every "with" companion: one ot_dp_dly_keep #(.W(1), .D(stages)) u_lis<D>_<dst leaf>__<port>_<bit>
between the driver wire and the load pin, so every bit of the group is `stages` cycles later.  (* keep *) stage regs
(same as the tail split) keep yosys from folding anything.  The added cycles are DECLARED per sink bit in
bind_core_input_pipe.json (the core_link_pipe record: bind_verify adds them to the as-built depth; compiler / TOK read
it).  LATCHECK (lane_asbuilt_latency) prices crossing lanes only; an intra-partition net is outside its scope.

Fail closed: a net that is not a direct driver -> load net (every load bit driven by that driver port, no as-built
stages, no strap bank) in a matched type, a port that already carries core_input_lockup / core_link_pipe, a stage count
that differs from len(regs_um), a matched type without a sites row, a key that matches no bound type.

OUT-BUS nets (FABLE-FIX-QC-N N4.1 11-18): a net whose dst is "bus:<out bus>" stations a leaf output on its way to the
partition's out-boundary register u_bout_<bus> (QC st_a: u_r3.nb_od -> u_bout_x_fe_o is ~1,280 um, -190 ps at CTS):

    {"src": "u_r0.nb_od", "dst": "bus:x_fe_o", "with": [["u_r0.nb_oc", "bus:x_fe_o"]], "stages": 1}

Per bus bit fed by the named leaf output: `stages` chained ot_dp_dly_keep #(.W(1), .D(1)) u_lob_<bus>__<leaf>__<port>_<bit>_<k>
(stage k at regs_um[k], counted from the leaf).  One bus = one latency: EVERY d bit of the bus must be covered by the
nets naming it, all with the same stage count (fail closed).  The cycles are LANE cycles, not core-input cycles: the
binder adds them to the lane's source stations (internal_source_cycles, like native internal stations), so the receiver
pad does not land them a second time, bind_verify expects them, and LATCHECK counts the u_lob_ chain at the source.
The plan must price them (lane fixed_cycles and latency row + stages); an unpriced lane is a LAND_INTRA_LATENCY error.

Receipt bind_intra_stations.json: types.<t> = {nets: [{src, dst, width, stages, cells}], stages: {src->dst: D},
cells, flops, sites: {<inst>.r[k] / <inst>.q: [x, y]}} -- sites in type_relay_sites key form (plan
partition_types[t].relay_sites, kit_istations rs_place_all: FIRM pre-GPL), like bind_pad_tail_split.json.
"""
import json
import re
from pathlib import Path

KEY = "land_intra_stations"
NET_KEYS = {"src", "dst", "with", "stages"}
BUS = "bus:"


def is_bus(d):
    """a parsed dst that names an out bus: ("bus:", name)"""
    return d[0] == BUS


def dst_pin(s, what):
    """'u_r0.flt_bank_i' -> ('u_r0', 'flt_bank_i'); 'bus:x_fe_o' -> ('bus:', 'x_fe_o')"""
    if isinstance(s, str) and s.startswith(BUS):
        if not re.fullmatch(r"[A-Za-z_]\w*", s[len(BUS):]):
            raise ValueError(f"asbuilt.{KEY}: {what} {s!r} is not 'bus:<out bus>'")
        return BUS, s[len(BUS):]
    return pin(s, what)


def pin(s, what):
    """'u_r2.flt_bank_o' -> ('u_r2', 'flt_bank_o')"""
    if not isinstance(s, str) or "." not in s:
        raise ValueError(f"asbuilt.{KEY}: {what} {s!r} is not '<inst>.<port>'")
    inst, _, port = s.rpartition(".")
    if not inst or not port or not re.fullmatch(r"[A-Za-z_]\w*", port):
        raise ValueError(f"asbuilt.{KEY}: {what} {s!r} is not '<inst>.<port>'")
    return inst, port


def row_pin(s):
    """sites row 'u_r2.flt_bank_o+flt_vld_o' -> ('u_r2', {'flt_bank_o', 'flt_vld_o'})"""
    inst, _, ports = str(s).rpartition(".")
    return inst, set(ports.split("+"))


def load_sites(v, base):
    if isinstance(v, dict):
        return v
    if not isinstance(v, str) or not v:
        raise ValueError(f"asbuilt.{KEY}.sites: expected a json path or an object")
    f = Path(v)
    if not f.is_absolute():
        f = Path(base or ".") / f
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError) as exc:
        raise ValueError(f"asbuilt.{KEY}.sites: cannot read {f}: {exc}") from exc
    if not isinstance(d, dict):
        raise ValueError(f"asbuilt.{KEY}.sites: {f} is not {{type: [rows]}}")
    return d


def config(ab, base=None):
    """the checked option, or None when the key is absent"""
    c = (ab or {}).get(KEY)
    if c is None:
        return None
    if not isinstance(c, dict) or set(c) - {"types", "nets", "sites"} or not isinstance(c.get("types"), list) \
            or not c["types"] or not isinstance(c.get("nets"), list) or not c["nets"] or "sites" not in c:
        raise ValueError(f"asbuilt.{KEY}: expected {{types: [regex..], nets: [{{src, dst, with, stages}}..], sites}}")
    nets = []
    for n in c["nets"]:
        if not isinstance(n, dict) or set(n) - NET_KEYS or not {"src", "dst", "stages"} <= set(n):
            raise ValueError(f"asbuilt.{KEY}: net {n!r}: expected {{src, dst, with, stages}}")
        st = n["stages"]
        if not isinstance(st, int) or isinstance(st, bool) or st < 1:
            raise ValueError(f"asbuilt.{KEY}: net {n['src']} -> {n['dst']}: stages must be an int >= 1")
        w = n.get("with") or []
        if not isinstance(w, list) or not all(isinstance(x, (list, tuple)) and len(x) == 2 for x in w):
            raise ValueError(f"asbuilt.{KEY}: net {n['src']} -> {n['dst']}: with must be [[src, dst], ..]")
        main = (pin(n["src"], "src"), dst_pin(n["dst"], "dst"))
        members = [main] + [(pin(s, "with src"), dst_pin(d, "with dst")) for s, d in w]
        if len({is_bus(m[1]) for m in members}) != 1 or len({m[1] for m in members if is_bus(m[1])}) > 1:
            raise ValueError(f"asbuilt.{KEY}: net {n['src']} -> {n['dst']}: a bus net and its companions name ONE out bus")
        nets.append(dict(src=main[0], dst=main[1], members=members, stages=st, label=f"{n['src']}->{n['dst']}",
                         bus=main[1][1] if is_bus(main[1]) else None))
    sinks = [m[1] if not is_bus(m[1]) else (m[1], m[0]) for n in nets for m in n["members"]]
    if len(set(sinks)) != len(sinks):
        raise ValueError(f"asbuilt.{KEY}: a load pin is named twice")
    depth = {}
    for n in nets:
        if n["bus"] is not None and depth.setdefault(n["bus"], n["stages"]) != n["stages"]:
            raise ValueError(f"asbuilt.{KEY}: out bus {n['bus']}: nets with different stage counts (one bus = one latency)")
    return dict(types=[re.compile(x) for x in c["types"]], nets=nets, sites=load_sites(c["sites"], base), bus_depth=depth)


def selected(cfg, tn):
    return any(x.fullmatch(tn) for x in cfg["types"])


def type_sites(cfg, tn):
    """[(net, regs_um)] of type tn, from the sites file; ValueError when a row is missing or disagrees"""
    rows = cfg["sites"].get(tn)
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{KEY} {tn}: the sites file has no rows for this type")
    out = []
    for n in cfg["nets"]:
        hit = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            si, sp = row_pin(r.get("src", ""))
            if n["bus"] is not None:
                if si == n["src"][0] and n["src"][1] in sp and r.get("dst") == BUS + n["bus"]:
                    hit.append(r)
                continue
            di, dp = row_pin(r.get("dst", ""))
            if si == n["src"][0] and di == n["dst"][0] and n["src"][1] in sp and n["dst"][1] in dp:
                hit.append(r)
        if len(hit) != 1:
            raise ValueError(f"{KEY} {tn}: net {n['label']}: {len(hit)} sites rows (need exactly 1)")
        regs = hit[0].get("regs_um")
        if not isinstance(regs, list) or not all(isinstance(xy, (list, tuple)) and len(xy) == 2 and
                                                 all(isinstance(a, (int, float)) for a in xy) for xy in regs):
            raise ValueError(f"{KEY} {tn}: net {n['label']}: regs_um must be [[x, y], ..]")
        if len(regs) != n["stages"]:
            raise ValueError(f"{KEY} {tn}: net {n['label']}: stages {n['stages']} != len(regs_um) {len(regs)}")
        out.append((n, [[round(float(x), 3), round(float(y), 3)] for x, y in regs]))
    return out


def site_rows(inst, regs):
    """type_relay_sites key form for the D-stage ot_dp_dly_keep `inst`: stage k at regs[k] (yosys names the last
    stage after the output port: <inst>.q, the others <inst>.r[k])"""
    rows = {f"{inst}.r[{k}]": list(regs[k]) for k in range(len(regs) - 1)}
    rows[f"{inst}.q"] = list(regs[-1])
    return rows


def leaf_match(name, rel, bound):
    """plan / bound leaf name `name` names the bound leaf of partition-relative name `rel` (instance `bound`)"""
    return name in (rel, bound)


def bus_stage_rows(inst, xy):
    """type_relay_sites key form for one D=1 out-bus station stage `inst` (its flop is <inst>.q)"""
    return {f"{inst}.q": [round(float(xy[0]), 3), round(float(xy[1]), 3)]}
