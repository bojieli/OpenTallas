#!/usr/bin/env python3
"""DIE-KV-58 10-31 (GEOM-96 kv3_io_cor, same form as geom93b_1031; GEOM-93 14:25 FAIL PLAN, r2r part; METHODOLOGY 12.20 one-block fix per type, OWNER 12.28b):
kv3_io_ft / kv3_io_ft_v1 / kv3_hroot keep their strap-form count origin u_cland_origin at the S-edge START pin
(cland_tstart_in), but its START fans out across the whole block in ONE cycle:
  - origin -> FSTART face flops of the far output rings (kit r2r 1981 um io_ft ft3_o, 2336 um hroot ft13_o), and
  - origin -> every input landing ring (ring reset, u_fault_port; io_ft 204 captures up to 1544 um, hroot 900+ up to
    2313 um).
Fix with the EXISTING opt-in START transport (no new knob, no RTL source change):
  clock.landing_writer_start  (DIE-HEAD-38 W1): W registered relays before the FSTART face flop of each far output
                              ring; every receiving crossing binds K+W (strap_ties), boot cycles +W, data cycles 0.
  clock.landing_reader_start  (reader-only START): R registered relays from the origin to every input ring's reset;
                              that ring binds K-R, boot cycles +R, data cycles 0; origin_rect_um pins u_cland_origin
                              next to its START pin.
Stage sites lie on the Manhattan L path origin -> target (along the S edge, then up the target face column), evenly
split so every hop <= STEP_UM; each stage's raw reset = the nearest equal-depth reset tap relay rst_n_t<i> of the type
(reset_tree.consumer_taps order), so the stage's raw-reset hop is local too.
col_v (GEOM-93 (c)): the E landing-bank band holding the col_v hot spot gets ring_place "ff" + fill_axis "x".
Unchanged (asserted): every other type and plan section; within the 3 types only clock.landing_writer_start /
landing_reader_start and that one band's ring_place/fill_axis are added.
usage (repo root): delta_geom93b_start.py PLAN_IN PLAN_OUT REPORT.json"""
import copy, json, math, re, sys
from pathlib import Path
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import schema as S  # noqa: E402
import reset_tree as RT  # noqa: E402

TYPES = ("kv3_io_cor",)
# GEOM-93 col_v hot spot (AUTO-GEOM est) -> the E landing-bank band that contains it gets the existing DIE-HEAD-13/32
# opt-in band form ring_place "ff" (ring flops FIRM bit-major) + fill_axis "x" (fill along rows, inward from the E-face
# pin of each bit), so the bank stops stacking its ring in vertical columns (col_v io_ft 4.98 @ (1230,202.5),
# hroot 10.94 @ (1850,517.5)).
COLV_AT = {"kv3_io_cor": (600.0, 152.5)}   # GEOM-96 io_cor a4 col_v 4.258 @ (600, 152.5)
STEP_UM = 340.0          # target hop (r2r gate 405 um; margin for GPL of the face flop / ring cells)
NEED_UM = 380.0          # a writer branch whose direct origin -> FSTART pin distance exceeds this gets stages
EDGE_Y = 12.0            # S-edge stage row (inside core rows, clear of the M7 strap/pin sites at y 2-5)
INSET = 14.0             # target-face column inset


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def path_points(o, t, n, w, h):
    """n points splitting the L path o -> (t.x, o.y) -> t into n+1 equal hops"""
    tx = min(max(t[0], INSET), w - INSET)
    corner = (tx, o[1])
    L1, L2 = abs(tx - o[0]), abs(t[1] - o[1])
    tot = L1 + L2
    pts = []
    for k in range(1, n + 1):
        d = tot * k / (n + 1)
        if d <= L1:
            x, y = o[0] + math.copysign(d, tx - o[0]), o[1]
        else:
            x, y = tx, o[1] + math.copysign(d - L1, t[1] - o[1])
        pts.append([round(x, 3), round(y, 3)])
    return pts


def nearest_raw(taps, xy):
    i = min(range(len(taps)), key=lambda j: man(xy, taps[j][1:]))
    return f"rst_n_t{i}", round(man(xy, taps[i][1:]), 1)


def band_target(band):
    x0, y0, x1, y1 = band["rect_um"]
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def design(P, tn):
    t = P.types[tn]
    w, h = t["outline_um"]
    lc = t["clock"]["landing_contract"]
    pins = {p["name"]: p for p in lc["pins"]}
    sp = pins["cland_tstart_in"]["xy_um"]
    o = (sp[0], EDGE_Y)
    taps = RT.consumer_taps(P, tn)
    outs = sorted(n[len("cland_fstart_out_"):] for n in pins if n.startswith("cland_fstart_out_"))
    ins = sorted(n[len("cland_fstart_in_"):] for n in pins if n.startswith("cland_fstart_in_"))
    far_out = {b: man(o, pins["cland_fstart_out_" + b]["xy_um"]) for b in outs}
    far_out = {b: d for b, d in far_out.items() if d > NEED_UM}
    W = max([math.ceil(d / STEP_UM) - 1 for d in far_out.values()] or [0])
    # reader target = the ring's farthest corner from the origin (its fault port / ring flops sit inside the band)
    rin = {}
    for b in ins:
        band = lc["bands"][b]
        x0, y0, x1, y1 = band["rect_um"]
        rin[b] = max(([x0, y0], [x1, y0], [x0, y1], [x1, y1]), key=lambda c: man(o, c))
    R = max(math.ceil(man(o, c) / STEP_UM) - 1 for c in rin.values())
    rep = dict(origin_site=list(o), W=W, R=R, writer={}, reader={})
    ws = {}
    for b, d in sorted(far_out.items()):
        tgt = pins["cland_fstart_out_" + b]["xy_um"]
        pts = path_points(o, tgt, W, w, h)
        st = []
        for xy in pts:
            raw, rd = nearest_raw(taps, xy)
            st.append(dict(xy_um=xy, raw_reset=raw))
        hops = [man(a, b_) for a, b_ in zip([list(o)] + pts, pts + [tgt])]
        rep["writer"][b] = dict(direct_um=round(d, 1), max_hop_um=round(max(hops), 1), raw_hop_max_um=max(
            nearest_raw(taps, xy)[1] for xy in pts))
        ws[b] = dict(stages=st)
    rs = {}
    for b in ins:
        tgt = rin[b]
        R_b = R
        pts = path_points(o, band_target(lc["bands"][b]), R_b, w, h)
        st = [dict(xy_um=xy, raw_reset=nearest_raw(taps, xy)[0]) for xy in pts]
        hops = [man(a, b_) for a, b_ in zip([list(o)] + pts, pts + [tgt])]
        rep["reader"][b] = dict(direct_um=round(man(o, tgt), 1), max_hop_um=round(max(hops), 1), raw_hop_max_um=max(
            nearest_raw(taps, xy)[1] for xy in pts))
        rs[b] = dict(stages=st)
    cx, cy = COLV_AT[tn]
    hot = [b for b, band in lc["bands"].items()
           if band["rect_um"][0] - 1 <= cx <= band["rect_um"][2] + 1 and band["rect_um"][1] - 1 <= cy <= band["rect_um"][3] + 1]
    assert len(hot) == 1, (tn, hot)
    rep["colv_band"] = dict(band=hot[0], rect_um=lc["bands"][hot[0]]["rect_um"], col_v_at=[cx, cy])
    cfg_w = dict(depth=W, branches=ws) if W else None
    cfg_r = dict(depth=R, origin_rect_um=[round(o[0] - 8.64, 3), 6.48, round(o[0] + 8.64, 3), 19.44], branches=rs)
    return cfg_w, cfg_r, rep


def _fmt(x):
    return json.dumps(x, indent=1).replace("\n", "\n  ")


def main():
    src, dst, rp = sys.argv[1:4]
    text = open(src).read()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    P = S.Plan(copy.deepcopy(raw), Path(src).resolve())
    rep = dict(lane="DIE-KV-58", rule="GEOM-93 FAIL PLAN r2r, 12.20 one-block START transport", step_um=STEP_UM,
               types={})
    for tn in TYPES:
        ck = raw["partition_types"][tn]["clock"]
        assert "landing_writer_start" not in ck and "landing_reader_start" not in ck, tn
        cw, cr, r = design(P, tn)
        band = raw["partition_types"][tn]["clock"]["landing_contract"]["bands"][r["colv_band"]["band"]]
        assert "ring_place" not in band and "fill_axis" not in band, tn
        band["ring_place"] = "ff"
        band["fill_axis"] = "x"
        if cw:
            ck["landing_writer_start"] = cw
        ck["landing_reader_start"] = cr
        rep["types"][tn] = r
    for tn in raw["partition_types"]:
        x, y = copy.deepcopy(raw["partition_types"][tn]), orig["partition_types"][tn]
        if tn in TYPES:
            for k in ("landing_writer_start", "landing_reader_start"):
                x["clock"].pop(k, None)
            for k in ("ring_place", "fill_axis"):
                x["clock"]["landing_contract"]["bands"][rep["types"][tn]["colv_band"]["band"]].pop(k)
        assert x == y, tn
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn in TYPES:
        m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, m.end())
        text = text[:m.end()] + _fmt(raw["partition_types"][tn]) + text[j:]
    assert json.loads(text) == raw
    open(dst, "w").write(text)
    json.dump(rep, open(rp, "w"), indent=1)
    for tn, r in rep["types"].items():
        print(tn, "colv band", r["colv_band"]["band"], "W", r["W"], "R", r["R"],
              "writer max hop", max([v["max_hop_um"] for v in r["writer"].values()] or [0]),
              "reader max hop", max(v["max_hop_um"] for v in r["reader"].values()),
              "raw hop max", max([v["raw_hop_max_um"] for v in list(r["writer"].values()) + list(r["reader"].values())]))


if __name__ == "__main__":
    main()
