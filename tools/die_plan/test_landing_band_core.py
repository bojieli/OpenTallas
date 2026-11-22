"""FLOW-FLEET-R1 11-22 (lever 7): G0 landing band x core overlap is an ERROR (S81 kv_leaf t5: vp cores regridded onto ft0_i / ft1_i / monitor_0)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_band_core as LB  # noqa: E402
import check as CK  # noqa: E402

T5 = {"clock": {"landing_contract": {
    "bands": {"ft0_i": {"rect_um": [65.28, 1168.56, 125.348, 1209.6], "width": 8},
              "ft1_i": {"rect_um": [126.528, 1168.56, 186.596, 1209.6], "width": 8},
              "monitor_0": {"rect_um": [180.36, 1140.48, 189, 1168.56]},
              "clear_i": {"rect_um": [400, 10, 420, 20]},
              "split_i": {"rects_um": [[0, 0, 10, 10], [500, 500, 510, 510]]}},
    "native_stage_groups": {"groups": [{"tag": "stage:a", "rect_um": [300, 300, 320, 320]}]},
    "group_rects_um": {"g1": [700, 700, 710, 710]}}}}
BOXES = {"u_lf.u_vp.g_ln[4].u_l": (43.308, 1105.96, 157.788, 1220.44), "u_lf.u_vp.g_ln[0].u_l": (181.548, 1105.96, 296.028, 1220.44),
         "edge": (420, 10, 440, 20), "stage_core": (310, 310, 400, 400), "grp": (705, 0, 800, 705.0), "far": (505, 505, 900, 900)}


def test_band_rects_kinds():
    k = {(kind, n) for kind, n, _ in LB.band_rects(T5)}
    assert ("band", "ft0_i") in k and ("band", "split_i#1") in k and ("stage_band", "stage:a") in k and ("group_band", "g1") in k


def test_t5_overlaps_and_shares():
    f = LB.findings_type("t5", T5, BOXES)
    got = {(x["band"], x["core"]): x["share"] for x in f}
    assert got[("ft0_i", "u_lf.u_vp.g_ln[4].u_l")] == 1.0
    assert abs(got[("ft1_i", "u_lf.u_vp.g_ln[4].u_l")] - 0.52) < 0.01
    assert abs(got[("monitor_0", "u_lf.u_vp.g_ln[0].u_l")] - 0.86) < 0.01
    assert ("clear_i", "edge") not in got                          # touching edges are legal
    assert ("stage:a", "stage_core") in got and ("split_i#1", "far") in got
    assert got[("g1", "grp")] == 0.25


def test_check_py_runs_it():
    src = (Path(__file__).resolve().parent / "check.py").read_text()
    assert 'summ["landing_band_core"] = LBC.check(P, R, base=band_base)' in src and '"--band-base"' in src


class _P:
    def __init__(self, types, parts):
        self.types, self.parts = types, parts


def _bx(t):
    return BOXES if t is T5 or t.get("is_t5") else {"c": (5, 0, 9, 5)}


def _run(types, base):
    R = CK.Report()
    s = LB.check(_P(types, {f"p{i}": {"type": n} for i, n in enumerate(types)}), R, boxes_fn=_bx, base=base)
    return R, s


def test_no_base_is_warn_only():
    R, s = _run({"t5": T5}, None)
    assert not R.errors() and s["nobase"] == s["findings"] > 0
    assert all(i["level"] == "WARN" and "[no base plan" in i["msg"] for i in R.items)


def test_inherited_is_warn_and_listed_new_is_error():
    t5r = dict(T5, is_t5=True)                                     # same type under an event re-hash name
    base = {"partition_types": {"t5__cl1234abcd": t5r}, "partitions": [{"type": "t5__cl1234abcd"}]}
    R, s = _run({"t5__cl9999eeee": t5r}, base)
    assert not R.errors() and s["inherited"] == s["findings"] > 0 and s["errors"] == 0
    assert all(i["level"] == "WARN" and i["msg"].startswith("[inherited") for i in R.items)
    assert any("ft0_i" in m for m in s["inherited_list"])          # the G0 summary lists them for the owners
    clean = {"clock": {"landing_contract": {"bands": {}}}}         # base without the overlaps: every one is new
    R, s = _run({"t5": T5}, {"partition_types": {"t5": clean}, "partitions": [{"type": "t5"}]})
    assert s["new"] == s["findings"] > 0 and len(R.errors()) == s["new"] and all(e["msg"].startswith("[new]") for e in R.errors())


def test_larger_overlap_is_error():
    small = {"u_lf.u_vp.g_ln[4].u_l": (43.308, 1105.96, 80.0, 1220.44)}   # base: core covered less of ft0_i
    idx = LB.base_index({"partition_types": {"t5": T5}, "partitions": [{"type": "t5"}]}, boxes_fn=lambda t: small)
    R = CK.Report()
    s = LB.check(_P({"t5": T5}, {"p": {"type": "t5"}}), R, boxes_fn=_bx, base=idx)
    larger = [e for e in R.errors() if e["msg"].startswith("[larger")]
    assert larger and all("ft0_i" in e["msg"] or "ft1_i" in e["msg"] for e in larger)
    assert s["larger"] == len(larger) and s["new"] > 0                   # the g_ln[0] overlaps are not in that base at all


def test_publish_gate_passes_band_base(tmp_path, monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "autopilot"))
    import publish_gate as PG
    seen = []

    class _R:
        returncode, stdout, stderr = 0, 'PG_STATIC {"schema": {"verdict": "PASS"}}', ""
    PG.static_remote("h1", "/w", "/t", "/t/p.json", None, "s", runner=lambda argv, **k: seen.append(argv) or _R(), band_base="/live/plan_c.json")
    assert "--band-base /live/plan_c.json" in seen[0][-1]
    tree = tmp_path / "tree"; (tree / "tools/die_plan").mkdir(parents=True)
    (tree / "tools/die_plan/check.py").write_text("# knows --band-base\n")
    plan = tree / "p.json"; plan.write_text("{}")
    base = tmp_path / "base.json"; base.write_text("{}")
    cmds = []
    monkeypatch.setattr(PG, "_sub", lambda argv, cwd: cmds.append(argv) or (0, ""))
    try:
        PG.run_static(str(tree), str(plan), work=str(tmp_path / "w"), band_base=str(base))
    except Exception:
        pass
    g0 = [c for c in cmds if any(str(x).endswith("check.py") for x in c)]
    assert g0 and g0[0][-2:] == ["--band-base", str(base)]


def test_own_landing_core_is_not_an_overlap():
    """COORD 11-22 (KV HGI false positives): cl_<band> core = the band footprint (+0.012 track offset) -> no finding; moved away -> own-offset"""
    t = {"clock": {"landing_contract": {"bands": {"ft2_i": {"rect_um": [77.76, 587.52, 242.784, 644.544]},
                                                  "i_slg_Q_N_krsp": {"rect_um": [8.64, 371.52, 51.84, 590.544]}},
                                        "native_stage_groups": {"groups": [{"tag": "stage:a", "rect_um": [300, 300, 320, 320]}]}}}}
    boxes = {"cl_ft2_i": (77.772, 587.532, 242.796, 644.556), "cl_i_slg_Q_N_krsp": (8.652, 371.532, 51.852, 590.556),
             "cl_stage_a": (300.012, 300.012, 320.012, 320.012)}
    assert LB.findings_type("kv3_hg", t, boxes) == []
    moved = dict(boxes, cl_ft2_i=(150.0, 587.532, 315.036, 644.556))     # R6d: the core moved, the band stayed
    f = LB.findings_type("kv3_hg", t, moved)
    assert [(x["band"], x["own"]) for x in f] == [("ft2_i", True)] and "own landing core" in LB.message(f[0])
    other = dict(boxes, u_x=(200.0, 600.0, 260.0, 700.0))                 # a foreign core on the band is still an overlap
    f = LB.findings_type("kv3_hg", t, other)
    assert [(x["band"], x["core"], x["own"]) for x in f] == [("ft2_i", "u_x", False)]
