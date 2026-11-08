#!/usr/bin/env python3
"""DIE-HBM-90-TSTRAP 11-07: plan event that fits each die.pg.domains rect to its own SerDes partition.

Cause (HBM d44v, measured): a PHY domain rect is its IO window / bump field grown by one diagonal bump pitch
(45 * sqrt(2) = 63.64 um).  Where the window sits on its partition edge, that halo leaves the partition and covers
core-VDD neighbours: phy_NW_io_u_lk_N0 covers 63.64 um of NW_su21 (q_su21) and 50 um of NW_b013, phy_NE_io_u_lk_N2
the mirror (q_su21__physical_v1, q_b013), phy_vsN0_u_lk_S1 29 um of NW_sm3 (q_sm3).  gen_phys.phy_pg_domains then
stops those types ("PG domain ... holds no macro"), and inside NW_io/NE_io the halo cuts the endpoint core u_ep_N*
("macro u_ep_N0 straddles PG domain").  die_io.check_pg_domains already states the rule ("the domain inside its
serdes partition (no VDDPHY straps over a core-VDD neighbour)") but applies it only with phy_macro_um/binding.

The event changes ONLY die.pg.domains[].rect_um, and only by shrinking it:
  1. clip to the partition of the domain's IO window(s) (one partition, else fail);
  2. while a placed block of that partition's type (contents / hard_cores / physical_parts with origin+outline, the
     same set gen_phys.phy_pg_domains judges) partly overlaps the rect, cut the rect at that block's edge, choosing
     the cut that keeps the most area and still covers every required box (bump rect, IO windows, bumps.exclude_um,
     esd_um); fail closed when no cut keeps them;
  3. fail closed unless at least one placed block lies fully inside (the PHY macro the domain powers).
Bumps, windows, grids, nets, every partition, type, lane and port stay byte for byte.

    fit_phy_pg_domains.py PLAN_IN PLAN_OUT LEDGER
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

EPS = 1e-6


def _inside(a, b):
    return a[0] >= b[0] - EPS and a[1] >= b[1] - EPS and a[2] <= b[2] + EPS and a[3] <= b[3] + EPS


def _overlap(a, b):
    return a[0] < b[2] - EPS and a[2] > b[0] + EPS and a[1] < b[3] - EPS and a[3] > b[1] + EPS


def _area(r):
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _r4(r):
    return [round(v, 4) + 0.0 for v in r]


def placed_blocks(P, part):
    """[(inst, die-frame box)] of the placed blocks of part's type, as gen_phys.phy_pg_domains enumerates them."""
    import gen_phys
    placed = gen_phys.pg_placed_blocks(P.ptype(part))
    out = []
    for c in placed:
        if "origin_um" not in c or "outline_um" not in c:
            continue
        x0, y0 = c["origin_um"]
        cw, ch = c["outline_um"]
        if c.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            cw, ch = ch, cw
        a, b = P.to_die(part, (x0, y0)), P.to_die(part, (x0 + cw, y0 + ch))
        out.append((c["inst"], [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]))
    return out


def fit_domain(P, d):
    """(new rect, steps) for domain d; raises ValueError when the rule cannot be met by shrinking."""
    io = {w["name"]: w for w in P.die.get("io", []) or []}
    parts = {(io.get(n) or {}).get("part") for n in d["io"]}
    if len(parts) != 1 or None in parts or next(iter(parts)) not in P.parts:
        raise ValueError(f"{d['name']}: io windows {d['io']} do not name exactly one known partition")
    part = next(iter(parts))
    need = [list(d["bumps"]["rect_um"])] + [list(io[n]["rect_um"]) for n in d["io"]]
    need += [list(e) for e in d["bumps"].get("exclude_um") or []] + [list(e) for e in d.get("esd_um") or []]
    pr = P.rect(part)
    r = [max(d["rect_um"][0], pr[0]), max(d["rect_um"][1], pr[1]), min(d["rect_um"][2], pr[2]), min(d["rect_um"][3], pr[3])]
    steps = []
    if _r4(r) != _r4(d["rect_um"]):
        steps.append(dict(cut="partition", part=part, part_rect=_r4(pr)))
    blocks = placed_blocks(P, part)
    for _ in range(len(blocks) + 1):
        strad = [(n, b) for n, b in blocks if _overlap(b, r) and not _inside(b, r)]
        if not strad:
            break
        n, b = strad[0]
        cands = [[r[0], r[1], r[2], b[1]], [r[0], b[3], r[2], r[3]], [r[0], r[1], b[0], r[3]], [b[2], r[1], r[2], r[3]]]
        cands = [c for c in cands if c[0] < c[2] and c[1] < c[3] and all(_inside(x, c) for x in need)]
        if not cands:
            raise ValueError(f"{d['name']}: block {n} {_r4(b)} straddles the domain and no cut keeps the bump field/windows")
        r = max(cands, key=_area)
        steps.append(dict(cut="block", inst=n, block=_r4(b)))
    else:
        raise ValueError(f"{d['name']}: block cuts did not converge")
    for x in need:
        if not _inside(x, r):
            raise ValueError(f"{d['name']}: fitted rect {_r4(r)} does not cover required box {x}")
    if not any(_inside(b, r) for _, b in blocks):
        raise ValueError(f"{d['name']}: fitted rect {_r4(r)} holds no placed block of {part}")
    return _r4(r), part, steps


def run(raw, plan_path=None):
    import schema as S
    P = S.Plan(raw, plan_path)
    led = dict(schema="opentallas.fit_phy_pg_domains.v1", domains=[])
    new = {}
    for i, d in enumerate(P.die.get("pg", {}).get("domains", []) or []):
        r, part, steps = fit_domain(P, d)
        lost = sorted(n for n in P.parts if n != part and _overlap(P.rect(n), d["rect_um"]))
        led["domains"].append(dict(name=d["name"], part=part, rect_before=list(d["rect_um"]), rect_after=r,
                                   changed=r != _r4(d["rect_um"]), steps=steps,
                                   neighbours_uncovered=[dict(part=n, type=P.parts[n]["type"]) for n in lost]))
        if r != _r4(d["rect_um"]):
            new[i] = r
    out = json.loads(json.dumps(raw))
    for i, r in new.items():
        out["die"]["pg"]["domains"][i]["rect_um"] = r
    led["changed"] = len(new)
    return out, led


def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    pin, pout, ledger = (Path(a) for a in argv[1:])
    raw = json.loads(pin.read_text())
    try:
        out, led = run(raw, str(pin))
    except ValueError as exc:
        print(f"fit_phy_pg_domains: FAIL {exc}", file=sys.stderr)
        return 1
    note = (f"DIE-HBM-90-TSTRAP fit_phy_pg_domains ({led['changed']} PHY PG domain rects fitted to their SerDes "
            "partition, endpoint cores cut out)")
    if led["changed"]:
        out["note"] = note + " <- " + raw["note"] if raw.get("note") else note
    pout.write_text(json.dumps(out))
    ledger.write_text(json.dumps(led, indent=1, sort_keys=True) + "\n")
    print(f"fit_phy_pg_domains: {led['changed']} of {len(led['domains'])} domains fitted")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
