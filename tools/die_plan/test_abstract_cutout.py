#!/usr/bin/env python3
"""DIE-ROUTE-ABS-1: python3 -m pytest tools/die_plan/test_abstract_cutout.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abstract_cutout as A  # noqa: E402

LEF = """MACRO m
  CLASS BLOCK ;
  SIZE 20.0000 BY 10.0000 ;
  PIN sig
    USE SIGNAL ;
    PORT
      LAYER M7 ;
        RECT 4.0000 0.0000 4.3000 10.0000 ;
    END
  END sig
  PIN VDD
    USE POWER ;
    PORT
      LAYER M7 ;
        RECT 8.0000 0.0000 8.3000 10.0000 ;
      LAYER M8 ;
        RECT 9.0000 0.0000 9.3000 10.0000 ;
    END
  END VDD
  OBS
    LAYER M1 ;
      RECT 0.0000 0.0000 20.0000 10.0000 ;
    LAYER M8 ;
      RECT 0.0000 0.0000 20.0000 10.0000 ;
  END
END m
"""


def _area(rs):
    return sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs)


def test_rect_sub_area_and_disjoint():
    r = (0.0, 0.0, 10.0, 8.0)
    holes = [(2.0, 2.0, 4.0, 3.0), (3.0, 2.5, 6.0, 5.0), (-1.0, 7.0, 1.0, 9.0)]
    out = A.rect_sub(r, holes)
    union = 2 * 1 + 3 * 2.5 - 1 * 0.5 + 1 * 1
    assert abs(_area(out) - (80.0 - union)) < 1e-9
    assert A.rect_sub(r, []) == [r]
    assert A.rect_sub(r, [(-1, -1, 11, 9)]) == []


def test_cut_lef_cuts_obs_m1_and_pg_m7_only():
    txt, st = A.cut_lef_text(LEF, [(7.5, 3.0, 8.8, 5.0)])
    assert st["obs_rects_in"] == 1 and st["obs_rects_out"] == 4
    assert st["pg_rects_in"] == 1 and st["pg_rects_out"] == 2
    assert "RECT 4.0000 0.0000 4.3000 10.0000" in txt          # signal pin untouched
    assert "LAYER M8 ;\n      RECT 0.0000 0.0000 20.0000 10.0000" in txt   # M8 OBS untouched
    assert "RECT 9.0000 0.0000 9.3000 10.0000" in txt          # M8 PG pin untouched
    assert "RECT 8.0000 0.0000 8.3000 3.0000" in txt and "RECT 8.0000 5.0000 8.3000 10.0000" in txt
    # the cut OBS never covers the window
    obs = [tuple(float(v) for v in l.split()[1:5]) for l in txt.split("OBS")[1].split("LAYER M8")[0].splitlines()
           if l.strip().startswith("RECT")]
    assert abs(_area(obs) - (200.0 - 1.3 * 2.0)) < 1e-6


def test_no_windows_is_identity():
    assert A.cut_lef_text(LEF, [])[0] == LEF


def test_tree_sites(tmp_path):
    p = tmp_path / "tree.json"
    p.write_text(json.dumps({"sites": {"b0": [1.0, 2.0], "r1_0": [3.0, 4.0]}}))
    assert sorted(x[0] for x in A.tree_sites(p)) == [(1.0, 2.0), (3.0, 4.0)]


def test_kit_flag_is_wired_and_opt_in():
    import inspect
    import subprocess
    import die_trial as D
    assert inspect.signature(D.write_kit).parameters["cut_abstracts"].default is None      # off unless asked
    out = subprocess.run([sys.executable, "-I", str(Path(D.__file__)), "kit", "--help"], capture_output=True, text=True).stdout
    assert "--cut-abstracts-under-clock" in out


def test_run_cuts_kit_lefs(tmp_path, monkeypatch):
    import die_trial as D
    import schema as S
    class P:
        types = {"T": dict(outline_um=[20.0, 10.0], module="t")}
        parts = {"a": dict(type="T")}
        def rect(self, n): return (0.0, 0.0, 20.0, 10.0)
        def to_type(self, n, xy): return xy
    monkeypatch.setattr(S, "load", lambda p: {})
    monkeypatch.setattr(S, "Plan", lambda raw, path: P())
    monkeypatch.setattr(D, "standin_module_names", lambda p: {"T": "t"})
    monkeypatch.setattr(D, "core_obs", lambda t: [])
    (tmp_path / "abstracts").mkdir(); (tmp_path / "clock").mkdir()
    (tmp_path / "abstracts" / "t.lef").write_text(LEF)
    (tmp_path / "clock" / "tree.json").write_text(json.dumps({"sites": {"b0": [5.0, 5.0]}}))
    rep = A.run(tmp_path / "plan.json", tmp_path, 0.25)
    assert rep["windows"] == 1 and rep["sites_under_partition"] == 1
    assert (tmp_path / "abstracts" / "t.lef.precut").read_text() == LEF
    new = (tmp_path / "abstracts" / "t.lef").read_text()
    assert new != LEF and "RECT 0.0000 0.0000 20.0000 10.0000" not in new.split("OBS")[1].split("LAYER M8")[0]
    A.run(tmp_path / "plan.json", tmp_path, 0.25)                                            # idempotent
    assert (tmp_path / "abstracts" / "t.lef").read_text() == new


def test_coarsen_rows_clusters_and_budget():
    w = [(0, 0, 1, 1), (2, 0, 3, 1.5), (500, 0, 501, 1), (0, 100, 1, 101), (1000, 100, 1001, 101)]
    b = A.coarsen_windows(w, gap_y=4.0, gap_x=80.0)
    assert (0, 0, 3, 1.5) in b and (500, 0, 501, 1) in b and len(b) == 4
    for r in w:
        assert any(x[0] <= r[0] and x[1] <= r[1] and x[2] >= r[2] and x[3] >= r[3] for x in b)
    b2 = A.coarsen_windows(w, max_boxes=2)
    assert len(b2) == 2 and all(any(x[0] <= r[0] and x[1] <= r[1] and x[2] >= r[2] and x[3] >= r[3] for x in b2) for r in w)


def test_coarsen_merges_overlaps():
    assert A.coarsen_windows([(0, 0, 10, 10), (5, 5, 15, 15)], gap_y=0.0, gap_x=0.0) == [(0, 0, 15, 15)]


def test_closed_view_size_mismatch_is_refused(tmp_path):
    """COORD r206: a closed view whose LEF SIZE differs from the plan outline falls back to the plan abstract (all dies)"""
    import die_trial as D

    class P:
        types = {"same": dict(outline_um=[20.0, 10.0], module="m_same"), "narrow": dict(outline_um=[20.0, 10.0], module="m_nar"),
                 "wide": dict(outline_um=[20.0, 10.0], module="m_wide"), "none": dict(outline_um=[5.0, 5.0], module="m_none")}
    for tn, mod, size in (("same", "m_same", "20.0000 BY 10.0000"), ("narrow", "m_nar", "19.5 BY 10"), ("wide", "m_wide", "20 BY 10.2")):
        (tmp_path / tn).mkdir()
        (tmp_path / tn / f"{mod}.lef").write_text(LEF.replace("20.0000 BY 10.0000", size))
    ok, refused = D.closed_view_candidates(P, tmp_path)
    assert set(ok) == {"same"} and set(refused) == {"narrow", "wide"}
    assert refused["narrow"]["view_size_um"] == [19.5, 10.0] and refused["narrow"]["outline_um"] == [20.0, 10.0]
    assert D.closed_view_candidates(P, None) == ({}, {})
