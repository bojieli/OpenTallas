"""CLOCK-128-R8 opt-in (--stack-r8): wide-merge shield rule, downward-via junction splits, leaf port on the trunk"""
import clock_routed as CR
import die_clock_128 as C


def test_merged_width_counts_touching_same_net_pg():
    ix = C.MetalIndex(0.08)
    ix.add(("M8", "VSS", "pg", 19733.52, 19734.00, 0.0, 1000.0))     # die VSS stripe 0.48
    ix.add(("M8", "VDD", "pg", 19735.00, 19735.48, 0.0, 1000.0))
    sh = ("M8", "VSS", "shield", 19733.96, 19734.12, 10.0, 20.0)     # R7 shield overlapping it
    assert abs(C.merged_width(ix, sh, "VSS") - 0.60) < 1e-6
    assert C.merged_width(ix, sh, "VSS") >= C.WIDE_MERGE_UM
    clear = ("M8", "VSS", "shield", 19734.20, 19734.36, 10.0, 20.0)
    assert abs(C.merged_width(ix, clear, "VSS") - 0.16) < 1e-6


def test_router_default_has_no_wide_merge():
    r = C.TrackRouter(dict(width=0.16, space=0.08), "VSS", {"M8": dict(pitch_um=0.08, offset_um=0.04)})
    assert r.wide_merge_um is None


def test_split_down_only_when_opted_in():
    pts = [("M7", 1.0, 2.0), ("M6", 1.0, 2.0), ("M5", 1.0, 2.0)]
    a, b = [], []
    CR._emit_steps(a, pts)
    CR._emit_steps(b, pts, split_down=True)
    assert a == ["$e addTechVia [V VIA67]", "$e addTechVia [V VIA56]"]
    assert len(b) == 4 and b[0].startswith("set jd") and b[1].startswith("$e newPath $jd") and "RL" not in b[1]
    up = [("M5", 1.0, 2.0), ("M6", 1.0, 2.0)]
    c = []
    CR._emit_steps(c, up, split_down=True)
    assert c == ["$e addTechVia [V VIA56]"]
    d = []
    CR._emit_steps(d, [("M9", 0.0, 0.0), ("M8", 0.0, 0.0), ("M8", 3.0, 0.0)], split_down=True)
    assert d[1].endswith("[RL M8]") and d[2] == "$e addPoint 3000 0"


def test_downward_pad_follows_split_path():
    L = []
    CR._emit_stack(L, [("M7", 1.0, 2.0), ("M6", 1.0, 2.0), ("M5", 1.0, 2.0)], {(1.0, 2.0): {"M6", "M5"}},
                   split_down=True)
    i = next(k for k, s in enumerate(L) if "VIA67" in s)
    assert L[i + 1].startswith("$e newPath $jd") and L[i + 2].startswith("$e addRect")
