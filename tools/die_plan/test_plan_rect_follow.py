import copy
import plan_rect_follow as F


def clock():
    return {"band_fixed_um": {"attn_i0": {"rect_um": [51.84, 2877.12, 384.056, 2954.88],
                                          "rects_um": [[51.84, 2877.12, 384.056, 2954.88], [60.992, 2954.88, 384.056, 2963.52]],
                                          "tap_windows_um": [[51.84, 384.056], [2877.12, 2954.88]]}},
            "band_tap_windows_um": [[[10, 20], [100, 110]], [[10, 20], [2954.88, 2963.52]]]}


def test_n_shrink_moves_shapes_as_one():
    c = clock()
    bad = []
    n = F.walk_shapes(c, F.n_edge_moves(2980.8, 2800.0, 34.56, 2.2), bad.append)
    assert not bad
    b = c["band_fixed_um"]["attn_i0"]
    assert b["rect_um"] == [51.84, 2842.56, 384.056, 2920.32]
    assert b["rects_um"][1] == [60.992, 2920.32, 384.056, 2928.96]
    assert b["tap_windows_um"] == [[51.84, 384.056], [2842.56, 2920.32]]
    assert c["band_tap_windows_um"][0] == [[10, 20], [100, 110]]      # below the cores: unchanged
    assert c["band_tap_windows_um"][1] == [[10, 20], [2920.32, 2928.96]]
    assert n == 5
    for r in [b["rect_um"]] + b["rects_um"]:                          # all inside the new outline (H - 34.56)
        assert r[3] <= 2980.8 - 34.56


def test_band_keeps_top_on_n_face_and_bottom_on_cores():
    c = {"rect_um": [879.456, 2833.92, 1130.472, 2963.52]}
    bad = []
    F.walk_shapes(c, F.n_edge_moves(2980.8, 2800.0, 34.56, 2.2), bad.append)
    assert c["rect_um"] == [879.456, 2833.92, 1130.472, 2928.96] and not bad     # top follows the N face, bottom stays on the cores


def test_collapsed_shape_is_refused():
    c = {"rect_um": [0, 2840.0, 10, 2845.0]}                                       # entirely in the cut zone: both ends move, fine
    bad = []
    F.walk_shapes(c, F.n_edge_moves(2980.8, 2800.0, 34.56, 2.2), bad.append)
    assert c["rect_um"] == [0, 2805.44, 10, 2810.44] and not bad
    d = {"rect_um": [0, 2830.0, 10, 2840.0]}                                       # y0 stays (below top+g), y1 stays: unchanged
    F.walk_shapes(d, F.n_edge_moves(2980.8, 2800.0, 34.56, 2.2), bad.append)
    assert d["rect_um"] == [0, 2830.0, 10, 2840.0]


def test_s_grow_keeps_s_anchored_and_moves_rest():
    c = {"rects_um": [[0, 0.5, 5, 1.5], [0, 100.0, 5, 110.0]], "tap_windows_um": [[0, 5], [0, 1.0]]}
    bad = []
    F.walk_shapes(c, F.s_grow_moves(34.56, 2.2), bad.append)
    assert c["rects_um"] == [[0, 0.5, 5, 1.5], [0, 134.56, 5, 144.56]]
    assert c["tap_windows_um"] == [[0, 5], [0, 1.0]] and not bad


def test_buses_subtree_untouched():
    c = {"buses": [{"rect_um": [0, 3000, 1, 3001]}]}
    d = copy.deepcopy(c)
    F.walk_shapes(c, F.n_edge_moves(2980.8, 2800.0, 34.56, 2.2), lambda m: None)
    assert c == d


def test_tap_windows_and_tap_reserved_are_rect_lists():
    c = {"band_fixed_um": {"attn_i0": {"tap_windows_um": [[51.84, 2877.12, 60.0, 2880.0], [52.352, 2954.88, 60.992, 2963.52]]}},
         "tap_reserved_um": [[104.192, 2959.168, 112.832, 2967.808], [1.0, 100.0, 2.0, 110.0]]}
    bad = []
    n = F.walk_shapes(c, F.n_edge_moves(2980.8, 2800.0, 34.56, 2.2), bad.append)
    assert c["band_fixed_um"]["attn_i0"]["tap_windows_um"][1] == [52.352, 2920.32, 60.992, 2928.96]
    assert c["tap_reserved_um"] == [[104.192, 2924.608, 112.832, 2933.248], [1.0, 100.0, 2.0, 110.0]]
    assert n == 3 and not bad
