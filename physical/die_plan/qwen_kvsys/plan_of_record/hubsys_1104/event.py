#!/usr/bin/env python3
"""DIE-KV-70 11-04: kv3_hub_Ei + kv3_sys_c one-block plan event, the GEOM-96 form of kv3_io_cor (32d3e2665d) and
kv3_io_cor_v1.  hub_Ei row failed post-CTS FF -458.64 on 30550 endpoints with AUTO-GEOM clock_tap_sinks 9455 and r2r 2755;
sys_c has edge taps only and no routed read yet (same class by plan, inferred).  GEOM-96 tools unchanged except:
- taps: delta_geom96_taps.py asserts tap_edge_y_um == [21.6]; hub_Ei has two edge rows, so this step applies the same
  change (tap_mode grid+explicit, added_taps, grid unchanged, grid_explicit_taps validates) without that assert.
- start: no col_v band change.  hub_Ei reads col_v 1.495 (io_cor 4.26) and sys_c has no read, so ring_place stays.
  Sites that land in clock.keepouts_um are moved out sideways (sys_c hard core).
- cover: added_taps.json is cover_taps.py output.  On sys_c its search raises at an intermediate tap set, so the search
  ran with grid_explicit_taps stubbed; the final set is validated here unstubbed.
usage (repo root): event.py taps|start|raw PLAN_IN PLAN_OUT REPORT.json|RAWBR.json; event.py rawgen PLAN BIND_RTL_DIR RAWBR.json"""
import copy, json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(HERE.parent / "geom96_1031"))
TYPES = ("kv3_hub_Ei", "kv3_sys_c")


def splice(text, raw, types):
    for tn in types:
        m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, m.end())
        text = text[:m.end()] + json.dumps(raw["partition_types"][tn], indent=1).replace("\n", "\n  ") + text[j:]
    assert json.loads(text) == raw
    return text


def same_except(raw, orig):
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn in raw["partition_types"]:
        if tn not in TYPES:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn


def taps(a, b, c):
    import schema as S, taps as TP, plan_geom as PG
    text = open(a).read()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    added = json.load(open(HERE / "added_taps.json"))
    P0 = S.Plan(copy.deepcopy(raw), Path(a).resolve())
    rep = {}
    for tn in TYPES:
        ck = raw["partition_types"][tn]["clock"]
        assert ck.get("tap_mode") is None and ck.get("tap_edge_y_um"), tn
        ck["tap_mode"] = "grid+explicit"
        ck["added_taps"] = copy.deepcopy(added[tn])
    P = S.Plan(copy.deepcopy(raw), Path(a).resolve())
    for tn in TYPES:
        assert S._grid_taps(P, tn) == S._grid_taps(P0, tn), tn
        fin = TP.grid_explicit_taps(P, tn)
        m = PG.type_metrics(P, tn)
        rep[tn] = dict(added=len(added[tn]), taps=len(fin), clock_reach=m["clock_reach_max"], tap_sinks=m.get("grid_tap_sinks_max"),
                       max_radius=round(max(x[4] for x in fin), 1), max_load=round(max(x[3] for x in fin), 1))
    same_except(raw, orig)
    open(b, "w").write(splice(text, raw, TYPES))
    json.dump(rep, open(c, "w"), indent=1)
    print(rep)


def out_of(xy, boxes, w):
    x, y = xy
    for x0, y0, x1, y1 in boxes:
        if x0 - 3 <= x <= x1 + 3 and y0 - 3 <= y <= y1 + 3:
            x = x0 - 8 if x - x0 < x1 - x else x1 + 8
    return [round(min(max(x, 14.0), w - 14.0), 3), xy[1]]


def start(a, b, c):
    import schema as S, delta_geom96_start as M
    text = open(a).read()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    P = S.Plan(copy.deepcopy(raw), Path(a).resolve())
    rep = {}
    for tn in TYPES:
        t = raw["partition_types"][tn]
        ck = t["clock"]
        assert "landing_writer_start" not in ck and "landing_reader_start" not in ck, tn
        x0, y0, x1, y1 = next(iter(ck["landing_contract"]["bands"].values()))["rect_um"]
        M.COLV_AT = {tn: ((x0 + x1) / 2, (y0 + y1) / 2)}    # design() needs a site; its band choice is dropped below
        cw, cr, r = M.design(P, tn)
        r.pop("colv_band")
        boxes = ck.get("keepouts_um", [])
        moved = 0
        for cfg in (cw, cr):
            for br in (cfg or {}).get("branches", {}).values():
                for st in br["stages"]:
                    new = out_of(st["xy_um"], boxes, t["outline_um"][0])
                    moved += new != st["xy_um"]
                    st["xy_um"] = new
        r["moved_out_of_keepouts"] = moved
        if cw:
            ck["landing_writer_start"] = cw
        ck["landing_reader_start"] = cr
        rep[tn] = r
        print(tn, "W", r["W"], "R", r["R"], "moved", moved,
              "writer hop", max([v["max_hop_um"] for v in r["writer"].values()] or [0]),
              "reader hop", max(v["max_hop_um"] for v in r["reader"].values()))
    same_except(raw, orig)
    open(b, "w").write(splice(text, raw, TYPES))
    json.dump(rep, open(c, "w"), indent=1)


def rawgen(a, b, c):
    import raw_branches_gen as M
    M.TYPES = TYPES
    sys.argv = ["x", a, b, c]
    M.main()


def rawadd(a, b, c):
    text = open(a).read()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    br = json.load(open(c))
    for tn in TYPES:
        t = raw["partition_types"][tn]
        ck = t["clock"]
        assert "landing_raw_branches" not in ck, tn
        for x in br[tn]["branches"]:
            for st in x["stages"]:
                st["xy_um"] = out_of(st["xy_um"], ck.get("keepouts_um", []), t["outline_um"][0])
        ck["landing_raw_branches"] = br[tn]["branches"]
        print(tn, "raw branches", len(br[tn]["branches"]), "copies", sum(len(x["stages"]) for x in br[tn]["branches"]))
    same_except(raw, orig)
    open(b, "w").write(splice(text, raw, TYPES))


step, a, b, c = sys.argv[1:5]
dict(taps=taps, start=start, rawgen=rawgen, raw=rawadd)[step](a, b, c)
