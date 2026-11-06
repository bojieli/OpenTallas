#!/usr/bin/env python3
"""DIE-HEAD-70 (COORD 11-05 12:12, OWNER 11-03 'pin cycles are the lever'): one-block HEAD plan delta for hd_tile only.

Sets the u_core (ot_s81hd_tile_native) long-hop options in partition_types.hd_tile.contents and republishes the hd_tile
wrapper (published/ot_s81hd_tile_p.sv) with the tools root's gen.py, exactly as head_cland_stage_delta.py --republish.
No outline, pin, bus, macro, strap, clock or reset key changes; every other type's wrapper is copied byte-equal.

  ROW_IN_REG 1  row_in = row0 + 32q registered per A core (row0 = ID strap: 0 data cycles)
  TEN_HOP    1  kept ten hop register by the control / compare logic (ten = static strap: 0 data cycles)
  FLT_XHOP   1  third sticky fault hop (0 result cycles)
  BST        3  x / go broadcast depth 2 -> 3: +1 cycle on the tile's own result, +1 once per lm-head position

  l48ug (11-05 tile4 CTS estimate on l48uf): TEN_HOP 2 (ten_q on the pin face, users ~620 um up: one hop -187 ps)
  and KEY_HOP 1 (order key before the operand hop: kl_gt -279 ps): 0 data cycles

  l48uh (DIE-HEAD-71, COORD 11-05 14:01: u_x skew-line line[899] -126.5 / line[769] -103.3 at tile5 4_cts TT): --xrelay.
  Root cause: the plan relay_sites pin the 32 direct xa lanes (b = 256..271, 384..399: skew lane j % 8 == 0, D = 0, so
  x_d feeds the A inputs u_ad1 directly) of u_x at the A-core cross (y 337.76) under the keys line[512 + b], i.e. the
  LAST stage of the BST 2 line.  BST 3 made line[512 + b] the MIDDLE stage: it stayed FIRM at the cross, the new last
  stage line[1024 + b] floated next to it (0-um hop) and stage 0 (top face) -> stage 1 (cross) became one ~685-um hop.
  --xrelay re-keys the cross sites to the last stage line[512 * (BST - 1) + b] and puts the BST - 2 stages before it on
  the L route x_q[b - 256] site -> (x of the cross site, y XBAND) -> cross: the last-but-one stage in the band between
  the A2/A3 row and elemB (y 714 / 718, clear of every hard core + 8.64-um halo), the earlier ones evenly along the
  x_q -> band leg.  Existing RTL flops only (0 cycles), no BST / param / wrapper change; BST 2 = no-op.

usage: head_tile_hop_delta.py SRC_PREPARED_DIR OUT_DIR --republish TOOLS_ROOT [--event l48ug --set TEN_HOP=2 ...]
                              [--xrelay]
  without --set: the l48uf parameter set (the params must not be set yet); with --set: those keys only (may overwrite);
  --xrelay alone: relay_sites only (no param change)
"""
import argparse, json, shutil, sys
from pathlib import Path

PARAMS = {"ROW_IN_REG": "1", "TEN_HOP": "1", "FLT_XHOP": "1", "BST": "3"}
TYPE = "hd_tile"
XKEY = "u_b.u_x.genblk1.g_line.line[{}]"
XQKEY = "x_q[{}]"
XDIRECT = tuple(range(256, 272)) + tuple(range(384, 400))   # xa lanes with skew depth 0 (j % 8 == 0)
XBAND = {256: 714.0, 384: 718.0}                            # y of the last-but-one stage per lane group
HALO = 8.64


def core_rects(T):
    out = []
    for h in T["hard_cores"]:
        (x, y), (w, hh) = h["origin_um"], h["outline_um"]
        if h.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        out.append((x - HALO, y - HALO, x + w + HALO, y + hh + HALO))
    return out


def x_relay(T, bst):
    """re-key the u_x direct-lane cross sites to the last stage; place the earlier stages (see module doc)"""
    rs = T["relay_sites"]
    W, H = T["outline_um"]
    rects = core_rects(T)
    moved = {}
    if bst < 3:
        return moved
    for b in XDIRECT:
        have = [s for s in range(bst) if XKEY.format(512 * s + b) in rs]
        assert len(have) == 1, ("expected one cross site per direct lane", b, have)
        cx, cy = rs.pop(XKEY.format(512 * have[0] + b))
        x0, y0 = rs[XQKEY.format(b - 256)]
        yb = XBAND[256 if b < 384 else 384]
        assert y0 > yb and cx > x0, ("x_q site not above-left of the band site", b, (x0, y0), (cx, yb))
        legs = (y0 - yb) + (cx - x0)
        n = bst - 2                                          # stages 0 .. n-1 on the x_q -> band L route
        sites = {}
        for i in range(n):
            d = legs * (i + 1) / (n + 1)
            sites[i] = [x0, round(y0 - d, 3)] if d <= y0 - yb else [round(x0 + d - (y0 - yb), 3), yb]
        sites[bst - 2] = [cx, yb]
        sites[bst - 1] = [cx, cy]
        for s, (x, y) in sites.items():
            assert 0 < x < W and 0 < y < H, ("site outside the outline", b, s, x, y)
            assert not any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in rects), ("site on a hard core", b, s, x, y)
            rs[XKEY.format(512 * s + b)] = [x, y]
            moved[XKEY.format(512 * s + b)] = [x, y]
    return moved


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", type=Path); ap.add_argument("out", type=Path)
    ap.add_argument("--republish", type=Path, required=True, help="tools root whose gen.py regenerates published/")
    ap.add_argument("--event", default="l48uf-tilehop")
    ap.add_argument("--set", action="append", default=[], metavar="K=V", help="u_core param to set (repeatable)")
    ap.add_argument("--xrelay", action="store_true", help="u_x direct-lane relay sites follow BST (l48uh)")
    a = ap.parse_args(argv)
    root = a.republish.resolve()
    sys.path[:0] = [str(root / "tools/s81_head")]
    import head_cland_stage_delta as D
    plan = json.loads((a.src / "source_plan.json").read_text())
    T = plan["partition_types"][TYPE]
    core = [c for c in T["contents"] if c.get("inst") == "u_core"]
    assert len(core) == 1 and core[0]["module"] == "ot_s81hd_tile_native", core
    old = dict(core[0]["params"])
    if a.set:
        params = dict(kv.split("=", 1) for kv in a.set)
        assert any(old.get(k) != v for k, v in params.items()), ("no change", old, params)
    elif a.xrelay:
        params = {}
    else:
        params = PARAMS
        assert not set(PARAMS) & set(old), ("already set", old)
    core[0]["params"].update(params)
    xmoved = x_relay(T, int(core[0]["params"].get("BST", "2"))) if a.xrelay else {}
    assert not a.xrelay or xmoved, "--xrelay: BST < 3, nothing to move"
    if a.out.exists():
        D.writable(a.out)
        shutil.rmtree(a.out)
    shutil.copytree(a.src, a.out, symlinks=True)
    D.writable(a.out)
    (a.out / "source_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    D.republish(a.out, root, [TYPE], a.out / "source_sidecar.json")
    report = dict(event=a.event, tool="tools/s81_head/head_tile_hop_delta.py", type=TYPE,
                  params_before=old, params_after=core[0]["params"], sidecar_changed=False,
                  data_cycles_added={"ROW_IN_REG": 0, "TEN_HOP": 0, "FLT_XHOP": 0, "KEY_HOP": 0,
                                     "BST": "+1 on the tile own result, +1 once per lm-head position"})
    if a.xrelay:
        report.update(xrelay_sites=xmoved, xrelay_data_cycles_added=0)
    (a.out / "tilehop_report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
