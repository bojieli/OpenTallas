"""DIE-HEAD-38 R1/R2 (opt-in plan fields, absent = byte-identical):
R2 clock.landing_status_input_stages: registered 1-input status relays on one ring's ready/fault before the
N-input status collect (+n status cycles on that input, 0 data cycles), with FIRM sites; landing_status_anchors pin
existing agg/loc stages.  R1 clock.landing_local_resets: same-depth local reset copies per consumer group."""
import copy
import pytest
import landing_place as LP
import schema as S
from clock_landings import Landings, LandingError
from test_clock_landings import dataflow_vehicle

RELAYS = (" wire rr_far, rr_low;\n"
          " ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_n), .q(rr_parent));  // raw tap tap 0 depth 4 @ (9, 1)\n"
          " ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_n), .q(rr_far));  // raw tap tap 1 depth 4 @ (1, 9)\n"
          " ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_n), .q(rr_low));  // raw tap tap 1 depth 3 @ (1, 8)\n")


def with_relays(body):
    return body.replace(" assign ", RELAYS + " assign ", 1)


def ck(p, tn):
    return p["partition_types"][tn].setdefault("clock", {})


# ---------------- R2
def test_status_input_stages_default_is_byte_identical_and_agg_stages_ride_one_ring():
    p, t, a, b = dataflow_vehicle()
    base = Landings(p, t).type_rtl("B", b)
    ck(p, "B")["landing_status_input_stages"] = {"agg": {"y": [{"xy_um": [8, 2]}, {"xy_um": [6, 2]}]}}
    c = Landings(p, t); bb = c.type_rtl("B", b)
    assert bb != base
    assert "ot_dp_landing_collect #(.N(1)) u_cland_sin_agg_y_0 (" in bb
    assert ".ready_i({cland_ok_y}),\n        .fault_i({cland_bad_y}), .ready_o(cland_sin_r_agg_y_0)" in bb
    assert ".ready_i({cland_sin_r_agg_y_0}),\n        .fault_i({cland_sin_f_agg_y_0}), .ready_o(cland_sin_r_agg_y_1)" in bb
    # the N-input aggregate now takes the relayed status; nothing else of the chain changes
    assert ".ready_i({cland_sin_r_agg_y_1}),\n        .fault_i({cland_sin_f_agg_y_1}), .ready_o(cland_agg_r1)" in bb
    assert ".ready_i({cland_agg_r2}),\n        .fault_i({cland_agg_f2}), .ready_o(cland_up_ready_z)" in bb
    m = c.reset_placements["B"]["monitor"]
    assert m["status_input_stages"] == {"agg": {"y": dict(stages=2, status_cycles_added=2, data_cycles_added=0)}}
    assert m["data_cycles_added"] == 0 and m["flops"] == 2 * len(m["stages"])
    # data ring untouched
    for line in base.splitlines():
        if "u_cland_y (" in line or "cland_ring_y" in line:
            assert line in bb


def test_status_input_stages_on_a_local_output():
    p, t, a, b = dataflow_vehicle()
    t["collector"]["types"]["A"]["local_status_depth"] = {"x": 2}
    base = Landings(p, t).type_rtl("A", a)
    ck(p, "A")["landing_status_input_stages"] = {"x": {"w": [{"xy_um": [4, 4]}]}}
    c = Landings(p, t); aa = c.type_rtl("A", a)
    assert ".ready_i({landing_ready_w}),\n        .fault_i({landing_fault_w}), .ready_o(cland_sin_r_x_w_0)" in aa
    assert ".ready_i({cland_sin_r_x_w_0}),\n        .fault_i({cland_sin_f_x_w_0}), .ready_o(cland_loc_r_x_1)" in aa
    # the observer aggregate still reads the ring directly
    assert ".ready_i({cland_ok_w}),\n        .fault_i({cland_bad_w}), .ready_o(cland_up_ready), .fault_o(cland_up_fault)" in aa
    assert c.reset_placements["A"]["monitor"]["status_input_stages"]["x"]["w"]["status_cycles_added"] == 1
    assert base != aa


@pytest.mark.parametrize("cfg,why", [
    ({"q": {"y": [{"xy_um": [1, 1]}]}}, "not 'agg' or a local status output"),
    ({"z": {"y": [{"xy_um": [1, 1]}]}}, "not 'agg' or a local status output"),   # tree bus: use 'agg'
    ({"agg": {"nope": [{"xy_um": [1, 1]}]}}, "not a landed input ring"),
    ({"agg": {"y": []}}, "needs >= 1 stage"),
    ({"agg": {"y": [{"xy_um": [float("nan"), 1]}]}}, "finite xy_um"),
    ({"agg": {}}, "must name landed input rings"),
    ({}, "non-empty"),
])
def test_status_input_stages_fail_closed(cfg, why):
    p, t, a, b = dataflow_vehicle()
    ck(p, "B")["landing_status_input_stages"] = cfg
    with pytest.raises(LandingError, match=why):
        Landings(p, t).type_rtl("B", b)


def test_status_anchors_must_name_emitted_stages():
    p, t, a, b = dataflow_vehicle()
    ck(p, "B")["landing_status_anchors"] = {"u_cland_agg_2": [5, 1]}
    base = Landings(dataflow_vehicle()[0], t).type_rtl("B", b)
    assert Landings(p, t).type_rtl("B", b) == base      # anchors are placement only
    ck(p, "B")["landing_status_anchors"] = {"u_cland_agg_7": [5, 1]}
    with pytest.raises(LandingError, match="not an emitted agg/loc status stage"):
        Landings(p, t).type_rtl("B", b)


def test_status_and_reset_sites_enter_firm_placement_and_default_adds_none():
    p, t, a, b = dataflow_vehicle()
    tb = p["partition_types"]["B"]
    assert LP._status_reset_groups(tb) == [] and LP._status_reset_groups({}) == []
    c = dict(monitor="dataflow", bands={"y": dict(rect_um=[0, 0, 4, 4])}, pins=[])
    base = LP._dataflow_tcl("B", c, tb)
    ck(p, "B").update(landing_status_input_stages={"agg": {"y": [{"xy_um": [8, 2]}]}},
                      landing_status_anchors={"u_cland_agg_2": [5, 1]},
                      landing_local_resets=[dict(name="up", raw="rr_far", xy_um=[3, 3], consumers=["u_cland_up_z"])])
    g = LP._status_reset_groups(tb)
    assert [x[0] for x in g] == ["u_cland_sin_agg_y_0", "u_cland_agg_2", "u_cland_lrst_up"]
    assert g[0][1] == pytest.approx([5.84, -0.16, 10.16, 4.16])
    tcl = LP._dataflow_tcl("B", c, tb)
    assert "{u_cland_sin_agg_y_0 {5.84000 -0.16000 10.16000 4.16000} status-stage:agg}" in tcl
    assert tcl != base


# ---------------- R1
def test_local_reset_copy_same_depth_replaces_only_listed_consumers():
    p, t, a, b = dataflow_vehicle(); b = with_relays(b)
    base = Landings(p, t).type_rtl("B", b)
    ck(p, "B")["landing_local_resets"] = [dict(name="up", raw="rr_far", xy_um=[3, 3], consumers=["u_cland_up_z"])]
    c = Landings(p, t); bb = c.type_rtl("B", b)
    assert '(* keep = "true" *) ot_dp_rrelay u_cland_lrst_up (.clk(clk), .d(rr_far), .q(cland_lrst_up));' in bb
    up = bb[bb.index("u_cland_up_z ("):].split(";")[0]
    assert ".rst_n(cland_lrst_up)" in up
    agg = bb[bb.index("u_cland_agg_1 ("):].split(";")[0]
    assert ".rst_n(cland_reset_y)" in agg                     # unlisted consumers keep the shared reset
    r = c.reset_placements["B"]["local_resets"][0]
    assert r["depth"] == 5 and r["added_cycles"] == 0 and r["replaced"] == {"u_cland_up_z": "cland_reset_y"}
    # with the copy removed again the text is the original
    assert bb.replace(".rst_n(cland_lrst_up)", ".rst_n(cland_reset_y)").replace(
        '    wire cland_lrst_up;\n', '').replace(
        '    (* keep = "true" *) ot_dp_rrelay u_cland_lrst_up (.clk(clk), .d(rr_far), .q(cland_lrst_up));  '
        '// local same-cycle reset copy (depth 5)\n', '') == base


@pytest.mark.parametrize("edit,why", [
    (dict(raw="rr_low"), "release edge would move"),
    (dict(raw="invented"), "no registered wavefront driver"),
    (dict(consumers=["u_cland_nope"]), "not one emitted landing instance"),
    (dict(xy_um=[1, float("inf")]), "finite xy_um"),
])
def test_local_reset_copy_fails_closed(edit, why):
    p, t, a, b = dataflow_vehicle(); b = with_relays(b)
    r = dict(name="up", raw="rr_far", xy_um=[3, 3], consumers=["u_cland_up_z"]); r.update(edit)
    ck(p, "B")["landing_local_resets"] = [r]
    with pytest.raises(LandingError, match=why):
        Landings(p, t).type_rtl("B", b)


def test_local_reset_consumer_listed_twice_fails_closed():
    p, t, a, b = dataflow_vehicle(); b = with_relays(b)
    ck(p, "B")["landing_local_resets"] = [dict(name="a1", raw="rr_far", xy_um=[3, 3], consumers=["u_cland_up_z"]),
                                         dict(name="a2", raw="rr_parent", xy_um=[3, 3], consumers=["u_cland_up_z"])]
    with pytest.raises(LandingError, match="listed twice"):
        Landings(p, t).type_rtl("B", b)


# ---------------- schema
def test_schema_accepts_and_rejects_the_new_fields():
    sch = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    for k in ("landing_status_input_stages", "landing_status_anchors", "landing_local_resets"):
        assert k in sch
    v = S._validate_node if hasattr(S, "_validate_node") else None
    import json, pathlib
    js = json.loads(pathlib.Path(S.__file__).with_name("die_plan.schema.json").read_text())
    assert js["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"][
        "landing_local_resets"] == json.loads(json.dumps(sch["landing_local_resets"]))
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")
    ok = [({"landing_status_input_stages": {"agg": {"u_i": [{"xy_um": [1, 2]}]}}}),
          ({"landing_status_anchors": {"u_cland_loc_d_o_1": [1, 2], "u_cland_agg_3": [3, 4]}}),
          ({"landing_local_resets": [dict(name="o", raw="rst_rl_15", xy_um=[1, 2], consumers=["u_cland_origin"])]})]
    bad = [({"landing_status_input_stages": {"agg": {"u_i": [{"xy": [1, 2]}]}}}),
           ({"landing_status_anchors": {"u_cland_up_u_o": [1, 2]}}),
           ({"landing_local_resets": [dict(name="o", raw="rst_rl_15", xy_um=[1, 2], consumers=[])]}),
           ({"landing_local_resets": [dict(name="o", raw="rst_rl_15", xy_um=[1, 2], consumers=["x_origin"])]})]
    for k in ok:
        jsonschema.validate(k, {"type": "object", "properties": sch, "additionalProperties": True})
    for k in bad:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(k, {"type": "object", "properties": sch, "additionalProperties": True})
