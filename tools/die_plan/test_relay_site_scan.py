"""relay_site_scan: a relay in the 8.7 um channel between two hard cores is found and moved to a legal site."""
import relay_site_scan as SC
import reset_tree as RT


def test_scan_finds_the_channel_relay():
    c = RT.CLEAR_UM
    ha, hb = (86, 993.6, 328, 1088.6), (86, 1097.3, 328, 1200.0)
    boxes = [(a - c, b - c, e + c, d + c) for a, b, e, d in (ha, hb)]
    box_out = (0.0, 0.0, 600.0, 2000.0)
    T = dict(root=(500.0, 1092.96), relays=[
        dict(name="u_rrl_136", d="rst_rl_135", q="rst_rl_136", xy=[373.7, 980.1], depth=1, kind="relay", tap=None),
        dict(name="u_rrl_137", d="rst_rl_136", q="rst_rl_137", xy=[219.58, 1092.96], depth=2, kind="relay", tap=None),
        dict(name="u_rrl_135", d="rst_root_n", q="rst_rl_135", xy=[500.0, 1092.96], depth=1, kind="relay", tap=None)])
    rows = SC.scan_tree(T, boxes, box_out, reach=300.0)
    assert [r["relay"] for r in rows] == ["u_rrl_137"]
    r = rows[0]
    assert RT._free(tuple(r["legal_xy"]), boxes, box_out) and r["moved_um"] > 0
    assert not RT._free((219.58, 1092.96), boxes, box_out)
