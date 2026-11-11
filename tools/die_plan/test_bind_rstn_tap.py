"""RSTN-TAP (DIE-QC-97 11-11): every u_bin_* / u_bout_* boundary epoch flop takes its reset from the nearest
same-depth, same-role reset-tree consumer tap when the leaf tap is out of reach; in-reach flops keep `rst_n` (bytes).
    python3 -m pytest -q tools/die_plan/test_bind_rstn_tap.py"""
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402
from test_bind_wavefront import emitter, plan  # noqa: E402

INST = re.compile(r"ot_dp_st #\(\.W\(\d+\)\) (u_b(?:in|out)_\w+) \(\.clk\(clk\), \.rst_n\((\w+)\), .*?\.ea\(([\w\[\]]+)\)")


def _buses(b, part, names_in, names_out):
    """synthetic in buses of `part` and out buses forwarding them bit for bit (no leaves needed)"""
    ins = []
    for n in names_in:
        L = dict(iname=n, width=8, src="pa", dst=part, items=[("leaf", None, "x", k) for k in range(8)])
        b.in_bus[part].append(L)
        ins.append(L)
    for n, L in zip(names_out, ins):
        b.out_bus[part].append(dict(oname=n, width=8, src=part, dst="pb", items=[("fwd", L, k) for k in range(8)]))


def _emit(tmp_path, raw, sites, opt_in=True):
    raw = copy.deepcopy(raw)
    raw["partition_types"]["mid"]["relay_sites"] = sites
    if opt_in:
        raw["partition_types"]["mid"].setdefault("reset", {})["boundary_tap"] = "nearest"
        assert schema.validate(raw) == []
    b = emitter(raw)
    _buses(b, "pm1", ["fx_i", "cfg_i"], ["fx_o", "cfg_o"])
    b.emit(tmp_path)
    text = (tmp_path / "rtl" / f"{raw['partition_types']['mid']['module']}.sv").read_text()
    regs = {m.group(1): (m.group(2), m.group(3)) for m in INST.finditer(text)}
    meta = tmp_path / "bind_reset_taps.json"
    return b, text, regs, (json.loads(meta.read_text()) if meta.exists() else None)


def test_far_corner_bus_regs_get_distinct_same_depth_taps_in_reach(tmp_path):
    raw = plan()
    P = schema.Plan(raw)
    T = RT.for_type(P, "mid")
    leaf = RT.leaf_tap(P, "mid")
    taps = RT.same_depth_taps(T, leaf)
    w, h = P.types["mid"]["outline_um"]
    # the four epoch flops at the four far corners of the 864 x 864 outline (>= 576 um from the centre leaf tap)
    sites = {"u_bin_fx_i/eq_reg": [20.0, 20.0], "u_bin_cfg_i/eq_reg": [20.0, h - 20.0],
             "u_bout_fx_o/eq_reg": [w - 20.0, 20.0], "u_bout_cfg_o/eq_reg": [w - 20.0, h - 20.0]}
    b, text, regs, meta = _emit(tmp_path, raw, sites)
    assert set(regs) == {"u_bin_fx_i", "u_bin_cfg_i", "u_bout_fx_o", "u_bout_cfg_o"}
    depth = {r["q"]: r["depth"] for r in T["relays"]}
    lx, ly = taps[leaf]
    chosen = set()
    for inst, (rst, ea) in regs.items():
        x, y = sites[inst + "/eq_reg"]
        assert abs(lx - x) + abs(ly - y) > RT.relay_um(P)            # the leaf tap is out of reach
        m = re.fullmatch(r"rst_n_t(\d+)", rst)
        assert m, (inst, rst)
        i = int(m.group(1))
        assert i != leaf and depth[rst] == depth[f"rst_n_t{leaf}"]   # same release cycle as the leaf tap
        assert abs(taps[i][0] - x) + abs(taps[i][1] - y) <= RT.relay_um(P)
        assert (ea == rst) if inst.startswith("u_bout_") else ea.endswith("]")   # bout epoch = its reset level
        chosen.add(i)
        assert f"// RSTN-TAP {inst}: " in text
    assert len(chosen) == 4                                           # four corners, four taps
    assert "    wire rst_n = rst_n_t%d;" % leaf in text                  # leaves keep the leaf tap
    rows = {r["inst"]: r for r in meta["types"]["mid"]}
    assert set(rows) == set(regs) and all(r["dist_um"] <= r["reach_um"] < r["leaf_dist_um"] for r in rows.values())


def test_in_reach_bus_regs_keep_todays_bytes(tmp_path):
    raw = plan()
    near = {"u_bin_fx_i/eq_reg": [400.0, 420.0], "u_bin_cfg_i/eq_reg": [440.0, 300.0],
            "u_bout_fx_o/eq_reg": [500.0, 500.0], "u_bout_cfg_o/eq_reg": [432.0, 432.0]}
    _, text, regs, meta = _emit(tmp_path / "a", raw, near)
    assert all(v[0] == "rst_n" for v in regs.values()) and meta is None and "RSTN-TAP" not in text
    assert all(v[1] == "rst_n" for k, v in regs.items() if k.startswith("u_bout_"))
    # and the same RTL as a bind that never looks at sites (selector disabled = the pre-RSTN-TAP emitter)
    orig = bind.boundary_reset_selector
    try:
        bind.boundary_reset_selector = lambda *a: (lambda body, kind, n, W: "rst_n")
        _, text0, _, _ = _emit(tmp_path / "b", raw, near)
    finally:
        bind.boundary_reset_selector = orig
    assert text == text0


def test_tap_choice_never_changes_depth_or_role():
    T = dict(n_clock_taps=4, relays=[
        dict(q="rst_n_t0", depth=3, xy=(432.0, 432.0)),       # leaf
        dict(q="rst_n_t1", depth=2, xy=(30.0, 30.0)),         # nearest, but one cycle earlier
        dict(q="rst_n_t2", depth=3, xy=(40.0, 40.0)),         # nearest same depth, other START role
        dict(q="rst_n_t3", depth=3, xy=(200.0, 200.0)),       # same depth + role
        dict(q="rst_n_t4", depth=3, xy=(20.0, 20.0)),         # a registered out (>= consumer count)
        dict(q="rr_x", depth=3, xy=(10.0, 10.0))],             # not a tap net
        tap_roles={0: "gated", 1: "gated", 2: "boot", 3: "gated"})
    assert sorted(RT.same_depth_taps(T, 0)) == [0, 3]
    assert RT.boundary_reset_tap(T, 0, (20.0, 20.0), 405.0) == (3, 360.0, 824.0)
    assert RT.boundary_reset_tap(T, 0, (300.0, 300.0), 405.0) == (0, 264.0, 264.0)   # in reach: leaf
    assert RT.boundary_reset_tap(T, 0, None, 405.0) == (0, None, None)
    assert RT.boundary_reset_tap(dict(T, relays=T["relays"][1:]), 0, (20.0, 20.0), 405.0) == (0, None, None)


def test_epoch_pin_site_without_relay_sites(tmp_path):
    """no relay_sites: the epoch flop's site is its epoch pin [W] (face_flops.tcl FIRM at the pin, gen_phys.type_pins)"""
    raw = plan()
    P = schema.Plan(raw)
    import gen_phys
    pins = {(bn, bit): (x, y) for bn, bit, _l, x, y, _f in gen_phys.type_pins(P, "mid")}
    _, text, regs, meta = _emit(tmp_path, raw, {})
    T = RT.for_type(P, "mid")
    leaf = RT.leaf_tap(P, "mid")
    taps = RT.same_depth_taps(T, leaf)
    rows = {r["inst"]: r for r in meta["types"]["mid"]}
    for inst, (rst, _ea) in regs.items():
        bus = inst.split("_", 2)[2]
        x, y = pins[(bus, 8)]
        dl = abs(taps[leaf][0] - x) + abs(taps[leaf][1] - y)
        if dl <= RT.relay_um(P):
            assert rst == "rst_n" and inst not in rows
        else:
            i = int(rst[len("rst_n_t"):])
            assert rows[inst]["site_from"] == "epoch_pin" and rows[inst]["site_um"] == [round(x, 3), round(y, 3)]
            assert abs(taps[i][0] - x) + abs(taps[i][1] - y) <= RT.relay_um(P) < dl
    assert rows                                                       # the 864-um tiny faces sit > 405 um out


def test_kit_rsync_keeps_rstn_tap_epoch_flop_as_ste(tmp_path):
    """an RSTN-TAP bout (ea = its tap net rst_n_t<i>) becomes ot_dp_ste in the kit like an ea(rst_n) one"""
    import kit_rsync
    from test_reset_tree import PAIR, piped
    raw = piped(PAIR)
    raw["partition_types"]["fa"].setdefault("reset", {})["boundary_tap"] = "nearest"
    assert schema.validate(raw) == []
    P = schema.Plan(raw)
    (tmp_path / "plan.json").write_text(json.dumps(raw))
    kd = tmp_path / "kit"
    kd.mkdir()
    mod = P.types["fa"]["module"]
    b = kd / f"{mod}.sv"
    b.write_text(f"module {mod} (input wire clk, input wire arst_n, input wire [3:0] x, output wire [4:0] y);\n"
                 "    wire rst_n;\n"
                 "    ot_reset_sync #(.ASYNC_STAGES(2)) u_rst_sync (.clk(clk), .async_rst_n(arst_n), .sync_rst_n(rst_n));\n"
                 "    ot_dp_st #(.W(4)) u_bout_y (.clk(clk), .rst_n(rst_n_t1), .d(x), .ea(rst_n_t1), .q(y[3:0]), .eq(y[4]));\n"
                 "endmodule\n")
    c = kd / "bind_cells.sv"
    c.write_text("// cells\nmodule ot_dp_st #(parameter W = 1) (input wire clk);\nendmodule\n")
    (kd / "kit_rtl.json").write_text(json.dumps(dict(files=[str(b), str(c)], bound_module=mod)))
    assert kit_rsync.main([str(tmp_path / "plan.json"), "fa", str(kd)]) == 0
    v = b.read_text()
    assert "ot_dp_ste #(.W(4)) u_bout_y (.clk(clk), .rst_n(rst_n_t1), .d(x), .ea(rst_n_t1)" in v


def test_key_absent_far_regs_keep_todays_bytes(tmp_path):
    """OPT-IN: without reset.boundary_tap the far-corner type emits exactly the pre-RSTN-TAP RTL and no receipt"""
    raw = plan()
    w, h = schema.Plan(raw).types["mid"]["outline_um"]
    far = {"u_bin_fx_i/eq_reg": [20.0, 20.0], "u_bout_cfg_o/eq_reg": [w - 20.0, h - 20.0]}
    _, text, regs, meta = _emit(tmp_path / "a", raw, far, opt_in=False)
    assert meta is None and "RSTN-TAP" not in text and all(v[0] == "rst_n" for v in regs.values())
    orig = bind.boundary_reset_selector
    try:
        bind.boundary_reset_selector = lambda *a: (lambda body, kind, n, W: "rst_n")
        _, text0, _, _ = _emit(tmp_path / "b", raw, far, opt_in=False)
    finally:
        bind.boundary_reset_selector = orig
    assert text == text0
    for f in (tmp_path / "a").rglob("*"):
        if f.is_file():
            assert f.read_bytes() == (tmp_path / "b" / f.relative_to(tmp_path / "a")).read_bytes(), f
