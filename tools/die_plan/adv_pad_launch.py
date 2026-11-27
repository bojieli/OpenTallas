"""adv_pad_launch.py -- PRECHECK ADV-PAD-LAUNCH (COORD 11-23 21:0x, static estimator, advisory, never a gate).

FABLE-RC-QC found on QC sle_ctl (hub 79a52775, census in lanes/posts/QC-SLECTL-RESYN.md RESULT 2/3): internal_stations
x_su_c_p1_o / x_su_c_p2_o price the station chain as launched from the control core leaf (launch u_ctl, from_um = leaf_um),
but the real launching register is a pad-stage register (r8b_strap_r8pad_u_rp_chd_q_1) about 400 um away from the first
station: 320 endpoints, worst -93 ps TT.  The plan priced hop 0 as leaf -> regs_um[0]; silicon sees pad -> decode -> regs_um[0].

Check, per partition type and internal_stations row (regs_um present):
  priced hop0  = dist(from_um, regs_um[0])
  real   hop0  = dist(real launch, regs_um[0])
  HIT when real hop0 > hop (default 300 um, the kit station knee) and real hop0 - priced hop0 > hop/4.
Real launch candidates, strongest first:
  MEASURED  kw measured={type: {conn: [x, y]}} (a placed-DB census; the RC lanes' evidence)
  R8PAD     PROXY (stations launched from a core leaf, i.e. launch is not a face register): nearest strap_r8pad_* count-strap site of the same type, only when it lies within die.rep_um of the priced
            launch (a pad stage that plausibly feeds this core pin group); the plan has no per-lane pad site, so this is
            an estimate and is labelled PROXY.
Fix owner: seat the last pad stage next to the first station (relay_sites) or add a stage-0 station at the decode output.
findings(raw, plan_path, tree=None, **kw) -> WARN lines; hits(raw, ...) -> structured rows.
"""
import math
import re
from collections import defaultdict
from pathlib import Path

CHECK = "ADV-PAD-LAUNCH"
MAX_LINES = 20
HOP_UM = 300.0


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def _d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _r8_sites(t):
    out = []
    for c in t.get("count_straps") or []:
        if "r8pad" in str(c.get("name", "")):
            out += [s for s in c.get("sites_um") or [] if isinstance(s, (list, tuple)) and len(s) == 2]
    return out


def hits(raw, hop=None, measured=None, rep=None):
    hop = float(hop or HOP_UM)
    rep = float(rep or (raw.get("die") or {}).get("rep_um") or 450.0)
    measured = measured or {}
    rows = []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        r8 = _r8_sites(t)
        for s in t.get("internal_stations") or []:
            regs, src = s.get("regs_um") or [], s.get("from_um")
            if not regs or not src or len(regs[0]) != 2:
                continue
            conn = s.get("conn")
            r0 = regs[0]
            priced = _d(src, r0)
            real = None
            m = (measured.get(tn) or {}).get(conn)
            if m:
                real = ("MEASURED", m, _d(m, r0))
            elif r8 and not str(s.get("launch", "")).startswith("face"):
                near = [q for q in r8 if _d(q, s.get("leaf_um") or src) <= rep]
                if near:
                    site = min(near, key=lambda q: _d(q, r0))
                    real = ("R8PAD-PROXY", site, _d(site, r0))
            if real and real[2] > hop and real[2] - priced > hop / 4:
                rows.append(dict(type=tn, conn=conn, launch=s.get("launch"), basis=real[0], priced_from=list(src),
                                 real_from=list(real[1]), priced_hop=round(priced), real_hop=round(real[2]),
                                 gap=round(_d(src, real[1])), stations=len(regs)))
    rows.sort(key=lambda r: -(r["real_hop"] - r["priced_hop"]))
    return rows


_LPAD_STAGE = re.compile(r"u_lpad_(\w+)\.r\[(\d+)\]\[(\d+)\]")


def _relay_key(name):
    return name.replace("/", ".").removeprefix("u_bound.")


def _per_bit_overrides(t):
    # rs_place_all matches a native full name and then its local or slash
    # equivalent. Without bound cell names, conflicting aliases are unknown.
    points = defaultdict(set)
    for key, xy in (t.get("relay_sites") or {}).items():
        name = _relay_key(key)
        if name.startswith(("u_lpad_", "u_bin_")) and isinstance(xy, (list, tuple)) and len(xy) == 2:
            points[name].add(tuple(xy))
    return points


def packed_override_hits(raw, plan_path):
    """Report over-reach legs involving at least one effective packed point override."""
    used = {p["type"] for p in raw.get("partitions") or []}
    rows = []
    plan = None
    for tn, t in (raw.get("partition_types") or {}).items():
        if tn not in used or not t.get("internal_stations") or not t.get("relay_sites"):
            continue
        points = _per_bit_overrides(t)
        stages = defaultdict(set)
        for key in points:
            m = _LPAD_STAGE.fullmatch(key)
            if m:
                bus, stage, bit = m.groups()
                stages[bus].add((int(stage), int(bit)))
        if not stages:
            continue
        from die_hop_scan import input_site, md, pin_table
        from gen_rtl import sv_id
        from kit_istations import bus_entries, chain_floats
        from schema import Plan, SIGNAL_REACH_UM

        reach = min(float(raw["die"]["reach_um"]), SIGNAL_REACH_UM)
        rank_lines = {_relay_key(key) for key in t.get("relay_rank_sites") or {}}
        bands = ((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}
        buses = {b["name"]: b for b in t.get("buses") or [] if b.get("dir") == "in"}
        pins = None
        for e in bus_entries(t):
            bus = e["conn"][4:]
            key = sv_id(bus)
            if bus not in buses or key not in stages or e.get("core") or chain_floats(t, e["conn"]):
                continue
            regs = e.get("regs_um") or []
            if not regs:
                continue
            # A full, explicit per-bit bank may supply the other endpoint of
            # a leg. Nominal regs_um centers cannot stand in for packed bits.
            banks = e.get("bit_sites_um")
            if banks and (len(banks) != len(regs) or e.get("bit_route") or e.get("face_bit_sites_um")):
                banks = None
            width = int(buses[bus]["width"])

            def site(rank, bit):
                name = f"u_lpad_{key}.r[{rank}]"
                if name in rank_lines:
                    return None
                candidates = points.get(f"{name}[{bit}]")
                if candidates is not None:
                    return next(iter(candidates)) if len(candidates) == 1 else None
                # The last bank can map to a physical q bit for a fixed delay.
                qrank = f"u_lpad_{key}.q"
                if rank == len(regs) - 1 and (qrank in rank_lines or f"{qrank}[{bit}]" in points):
                    return None
                if banks and bit < len(banks[rank]):
                    return banks[rank][bit]
                return None

            legs = {}
            # A bound LPAD .q may be a counted-delay mux output or a
            # different actual depth. Check only explicit consecutive r
            # ranks that can be identified before the bound RTL is available.
            for stage, bit in stages[key]:
                if stage >= len(regs) or bit > width:
                    continue
                point = site(stage, bit)
                if point is None:
                    continue
                if stage == 0 and bus not in bands and str(e.get("launch", "")).startswith("face"):
                    binkey = f"u_bin_{key}"
                    rank = binkey + (".eq" if bit == width else ".q")
                    alias = rank if bit == width else f"{rank}[{bit}]"
                    if rank not in rank_lines:
                        override = points.get(alias)
                        if override is not None:
                            face = next(iter(override)) if len(override) == 1 else None
                        else:
                            if pins is None:
                                if plan is None:
                                    plan = Plan(raw, Path(plan_path))
                                pins = pin_table(plan, tn)
                            pin = pins.get(bus, {}).get(bit)
                            face = input_site(pin) if pin else None
                        legs[bit, 0] = face, point
                if stage > 0:
                    legs[bit, stage] = site(stage - 1, bit), point
                if stage + 1 < len(regs):
                    legs[bit, stage + 1] = point, site(stage + 1, bit)

            for (bit, stage), (a, b) in legs.items():
                if a is None or b is None:
                    continue
                distance = md(a, b)
                if distance > reach + 1e-6:
                    rows.append(dict(type=tn, conn=e["conn"], bit=bit, stage=stage,
                                     distance=distance, reach=reach))
    return sorted(rows, key=lambda r: (-r["distance"], r["type"], r["conn"], r["stage"], r["bit"]))


def findings(raw, plan_path, tree=None, **kw):
    try:
        rows = hits(raw, kw.get("hop"), kw.get("measured"))
        overrides = packed_override_hits(raw, plan_path)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]

    grouped = defaultdict(list)
    for r in overrides:
        grouped[(r["type"], r["conn"])].append(r)
    out = []
    for (tn, conn), bits in grouped.items():
        worst = bits[0]
        first = sum(r["stage"] == 0 for r in bits)
        target = f"r[{worst['stage']}]"
        launch = f"r[{worst['stage']-1}]" if worst["stage"] else "face launch"
        out.append(_w(f"{tn} {conn}: packed point overrides exceed {worst['reach']:g} um reach, "
                      f"{first} first leg(s) and {len(bits)-first} consecutive rank leg(s); "
                      f"worst bit {worst['bit']} {launch} -> {target} {worst['distance']:.2f} um; "
                      "re-seat the per-bit overrides before placement"))
    out += [_w(f"{r['type']} {r['conn']}:", f"priced launch {r['launch']} {r['priced_from']} hop0 {r['priced_hop']} um, "
              f"real launch {r['basis']} {r['real_from']} hop0 {r['real_hop']} um (gap {r['gap']} um) > station reach; "
              "fix: seat the pad stage at the first station or add a stage-0 station") for r in rows[:MAX_LINES]]
    out = out[:MAX_LINES]
    out.append(_w("summary", f"{len(rows)} station chain(s) priced from a launch point that differs from the real launching register"
                  + (f"; {len(overrides)} over-reach packed legs in {len(grouped)} chain(s)" if overrides else "")))
    return out


if __name__ == "__main__":
    import json
    import sys
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1]):
        print(ln)
