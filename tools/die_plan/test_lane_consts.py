"""pytest: LANE-CONSTS (LANEAGE-SWEEP 11-24) derive / compare / lane-ages on a QC C1g-shaped fixture (tt_ctlm 19/19/17/17 vs 14/10/10/13)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lane_consts as LC  # noqa: E402

LANES = [dict(lane="tt_ctlm__cmd_cmd_wi", src="tt_ctlm", bus_out="cmd", dst="sl_W5_fw", bus_in="cmd_wi", delivered=14),
         dict(lane="tt_ctlm__hr_hr_wi", src="tt_ctlm", bus_out="hr", dst="sl_W5_fw", bus_in="hr_wi", delivered=10),
         dict(lane="sl_W5_fw__ss_wo_ss5", src="sl_W5_fw", bus_out="ss_wo", dst="tt_ctlm", bus_in="ss5", delivered=10),
         dict(lane="sl_W5_fw__ag_wo_ag5", src="sl_W5_fw", bus_out="ag_wo", dst="tt_ctlm", bus_in="ag5", delivered=13),
         dict(lane="a__x_y", src="a", bus_out="x", dst="b", bus_in="y", delivered=5),
         dict(lane="a__x_z", src="a", bus_out="x", dst="c", bus_in="z", delivered=6)]
REG = dict(consts=[dict(die="qwen_compute", name="R_CMD", lane="tt_ctlm__cmd_cmd_wi"),
                   dict(die="qwen_compute", name="R_HR", match=dict(src="tt_ctlm", bus_in="hr_wi")),
                   dict(die="qwen_compute", name="R_SS", lane="sl_W5_fw__ss_wo_ss5"),
                   dict(die="qwen_compute", name="R_AG", lane_re=r"sl_W5_fw__ag_wo_ag5"),
                   dict(die="qwen_compute", name="XPF_TRANSPORT_EDGES", expr="1 + R_HR"),
                   dict(die="qwen_compute", name="SPLITX", lane_re=r"a__x_.*"),
                   dict(die="qwen_compute", name="GONE", lane="nope"),
                   dict(die="qwen_compute", name="DEP", expr="max(GONE, 3)"),
                   dict(die="qwen_compute", name="OFS", lane="a__x_y", offset=2)],
           consumers=[dict(die="qc", consumer="prog", const="R_HR", reader=dict(kind="json", glob="results/**/*meta.json", key="relay.R_HR")),
                      dict(die="qc", consumer="prog", const="R_CMD", reader=dict(kind="json", glob="results/**/*meta.json", key="relay.R_CMD")),
                      dict(die="qc", consumer="contract", const="XPF_TRANSPORT_EDGES",
                           reader=dict(kind="json", glob="results/C.json", key="compiled_XPF_TRANSPORT_EDGES", each="master")),
                      dict(die="qc", consumer="sv", const="XPF_TRANSPORT_EDGES", reader=dict(kind="sv_param", glob="rtl/*.sv", param="XPF_TRANSPORT_EDGES")),
                      dict(die="qc", consumer="inst", const="XPF_TRANSPORT_EDGES",
                           reader=dict(kind="inst_param", module_re=r"qfd_tt_ctlm\w*", param="XPF_TRANSPORT_EDGES")),
                      dict(die="qc", consumer="py", const="R_SS", reader=dict(kind="regex", glob="tools/g.py", regex=r"^R_SS = (\d+)")),
                      dict(die="qc", consumer="gone", const="GONE", reader=dict(kind="regex", glob="tools/g.py", regex=r"^R_SS = (\d+)")),
                      dict(die="qc", consumer="missing", const="R_AG", reader=dict(kind="json", glob="nothing/*.json", key="a")),
                      dict(die="s81", consumer="other die", const="R_HR", reader=dict(kind="json", glob="x", key="a"))])


def _tree(tmp_path):
    t = tmp_path / "tree"
    (t / "results" / "a").mkdir(parents=True)
    (t / "results" / "a" / "p_meta.json").write_text(json.dumps(dict(relay=dict(R_CMD=19, R_HR=10))))
    (t / "results" / "C.json").write_text(json.dumps([dict(master="m1", compiled_XPF_TRANSPORT_EDGES=21), dict(master="m2", other=1)]))
    (t / "rtl").mkdir()
    (t / "rtl" / "c.sv").write_text("module c #(parameter integer XPF_TRANSPORT_EDGES = 11 // was 21\n) ();\nendmodule\n")
    (t / "tools").mkdir()
    (t / "tools" / "g.py").write_text("R_SS = 17\n")
    b = tmp_path / "bind_rtl"
    b.mkdir()
    b.joinpath("top.sv").write_text("module top; qfd_tt_ctlm_dv_x #(.A(1), .XPF_TRANSPORT_EDGES(21)) u_c (.ck(ck));\n"
                                    "other #(.XPF_TRANSPORT_EDGES(3)) u_o ();\nendmodule\n")
    return t, b


def test_derive_laws():
    d = LC.derive("qc", LANES, REG)["consts"]
    assert (d["R_CMD"]["value"], d["R_HR"]["value"], d["R_SS"]["value"], d["R_AG"]["value"]) == (14, 10, 10, 13)
    assert d["XPF_TRANSPORT_EDGES"]["value"] == 11 and d["OFS"]["value"] == 7
    assert d["SPLITX"]["status"] == "SPLIT" and d["SPLITX"]["value"] is None
    assert d["GONE"]["status"] == "UNMEASURED" and d["DEP"]["status"] == "UNMEASURED"


def test_compare_verdicts(tmp_path):
    t, b = _tree(tmp_path)
    rows = LC.compare("qwen_compute", LC.derive("qwen_compute", LANES, REG), REG, t, b)
    v = {(r["consumer"], r["const"], r["baked"]): r["verdict"] for r in rows}
    assert v[("prog", "R_HR", 10)] == "MATCH" and v[("prog", "R_CMD", 19)] == "MISMATCH"
    assert v[("contract", "XPF_TRANSPORT_EDGES", 21)] == "MISMATCH"
    assert not any(r["consumer"] == "contract" and r["baked"] is None for r in rows)     # m2 has no key: skipped
    assert v[("sv", "XPF_TRANSPORT_EDGES", 11)] == "MATCH"                                # comment stripped
    assert v[("inst", "XPF_TRANSPORT_EDGES", 21)] == "MISMATCH" and ("inst", "XPF_TRANSPORT_EDGES", 3) not in v
    assert v[("py", "R_SS", 17)] == "MISMATCH" and v[("gone", "GONE", 17)] == "UNMEASURED"
    assert v[("missing", "R_AG", None)] == "NOT-FOUND"
    assert not any(r["consumer"] == "other die" for r in rows)
    assert LC.summary(rows)["MISMATCH"] == 4


def test_cli_report_only_and_strict(tmp_path, capsys):
    t, b = _tree(tmp_path)
    lc = tmp_path / "latcheck.json"
    lc.write_text(json.dumps(dict(summary={}, lanes=LANES)))
    rg = tmp_path / "reg.json"
    rg.write_text(json.dumps(REG))
    base = ["compare", "--die", "qwen_compute", "--latcheck", str(lc), "--registry", str(rg), "--tree", str(t), "--bind-rtl", str(b),
            "--tsv", str(tmp_path / "o.tsv"), "--json", str(tmp_path / "o.json")]
    assert LC.main(base) == 0                                  # r703: report only
    assert LC.main(base + ["--strict"]) == 4
    assert (tmp_path / "o.tsv").read_text().splitlines()[0].startswith("consumer\tdie\tconst\tbaked\tmeasured\tverdict")
    assert json.loads((tmp_path / "o.json").read_text())["summary"]["MISMATCH"] == 4


def test_lane_ages_is_ctlm_image_input(tmp_path):
    lc = tmp_path / "latcheck.json"
    lc.write_text(json.dumps(dict(summary={}, lanes=LANES)))
    rg = tmp_path / "reg.json"
    rg.write_text(json.dumps(REG))
    out = tmp_path / "la.json"
    assert LC.main(["lane-ages", "--die", "qc", "--latcheck", str(lc), "--registry", str(rg), "--out", str(out)]) == 0
    d = json.loads(out.read_text())
    assert d["schema"] == "opentallas.qwen.ctlm-lane-ages.v1"
    assert {k: d[k] for k in ("R_CMD", "R_HR", "R_SS", "R_AG", "XPF_TRANSPORT_EDGES")} == dict(R_CMD=14, R_HR=10, R_SS=10, R_AG=13,
                                                                                                    XPF_TRANSPORT_EDGES=11)
    assert len(d["source_sha256"]) == 64


def test_shipped_registry_parses_and_derives_on_c1g_shape():
    reg = LC.load_registry()
    names = {c["name"] for c in reg["consts"] if LC.die_name(c["die"]) == "qwen_compute"}
    assert {"R_CMD", "R_HR", "R_SS", "R_AG", "XPF_TRANSPORT_EDGES"} <= names
    d = LC.derive("qwen_compute", LANES, reg)["consts"]
    assert d["XPF_TRANSPORT_EDGES"]["value"] == 11
    for c in reg["consumers"]:
        assert c["const"] in {x["name"] for x in reg["consts"] if LC.die_name(x["die"]) == LC.die_name(c["die"])}, c


def test_json_list_path_with_dotted_ids(tmp_path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps(dict(buses=[dict(id="tt_ctlm.hr -> dvs_W5.hr_wi", stages=26), dict(id="x", stages=1)],
                                 constants={"RL (a, b)": [80, 12, "f"]})))
    assert LC._dig(json.loads(f.read_text()), ["buses", {"id": "tt_ctlm.hr -> dvs_W5.hr_wi"}, "stages"]) == 26
    assert LC._dig(json.loads(f.read_text()), ["constants", "RL (a, b)", 1]) == 12
    assert LC._dig(json.loads(f.read_text()), ["buses", {"id": "nope"}, "stages"]) is None


def test_param_regen_const(tmp_path):
    b = tmp_path / "bind"
    b.mkdir()
    b.joinpath("param_regen.json").write_text(json.dumps(dict(changed=[dict(inst="ectl_EN_0", param="RESPONSE_LAT", asbuilt="80", bound=26),
                                                                       dict(inst="ectl_EN_1", param="RESPONSE_LAT", asbuilt="80", bound=26),
                                                                       dict(inst="ectl_EN_0", param="QK", bound=37),
                                                                       dict(inst="ectl_EN_1", param="QK", bound=38)])))
    reg = dict(consts=[dict(die="kv", name="RL", param_regen=dict(param="RESPONSE_LAT")), dict(die="kv", name="QK", param_regen=dict(param="QK")),
                       dict(die="kv", name="QK0", param_regen=dict(param="QK", inst_re=r"ectl_EN_0")), dict(die="kv", name="RL2", expr="RL + 7")])
    d = LC.derive("kv", [], reg, bind_dir=b)["consts"]
    assert d["RL"]["value"] == 26 and d["RL2"]["value"] == 33
    assert d["QK"]["status"] == "SPLIT" and d["QK0"]["value"] == 37
    assert LC.derive("kv", [], reg)["consts"]["RL"]["status"] == "UNMEASURED"           # no bind dir: never a guessed value


def test_fixed_census_classes():
    plan = dict(lanes=[dict(id="a", fixed_cycles=2), dict(id="b", fixed_cycles=3), dict(id="c", fixed_cycles=1), dict(id="d", fixed_cycles=1),
                       dict(id="e", fixed_cycles=0), dict(id="f", fixed_cycles=4)])
    lanes = [dict(lane="a", bus_out="o", bus_in="i", source=dict(face=1, pads=1), receiver=dict(face=1, lpad=1)),
             dict(lane="b", bus_out="o", bus_in="i", source=dict(face=1, kit_ist=2, bound_lob=1), receiver=dict(face=1)),
             dict(lane="c", bus_out="o", bus_in="i", source=dict(face=1), receiver=dict(face=1), fixed_in_core=1),
             dict(lane="d", bus_out="o", bus_in="i", source=dict(face=1), receiver=dict(face=1)),
             dict(lane="e", bus_out="o", bus_in="i", source=dict(face=1), receiver=dict(face=1))]
    r = {x["lane"]: x for x in LC.fixed_census(plan, lanes)}
    assert set(r) == {"a", "b", "c", "d", "f"}
    assert r["a"]["cls"] == "BACKED" and "u_lpad_i" in r["a"]["register"] and "u_bout_o_pad*" in r["a"]["register"]
    assert r["b"]["cls"] == "BACKED+KIT-PREDICTED" and "u_lob_o" in r["b"]["register"]
    assert r["c"]["cls"] == "FIXED-IN-CORE" and r["d"]["cls"] == "NONE" and r["d"]["register"] == "NONE"
    assert r["f"]["cls"] == "NOT-IN-LATCHECK"
