"""tests for tools/die_plan/param_class_split.py (DIE-QC-97 11-09): python3 -I -m unittest test_param_class_split

Unit part (no Yosys): a QC-shaped plan + bind-of-record stub (bind_report types + bound top) where sle_st_b_v1 binds
three slices with the coll_regen HI_PAD pads 30/29/30 -> two clones; ID-only differences stay one type; plan and
sidecar references follow the clones.  End-to-end part (Yosys via $OT_BIND_YOSYS or docker): the bind_tiny die, whose
type ta binds A0/A1 with P_u_a_ID 1/2 (kit-rtl stops without --instance), split -> rebind -> kit-rtl kits each clone
generically, and each kit's bound module carries its own value baked in."""
import copy
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import param_class_split as PCS  # noqa: E402
import bind  # noqa: E402

PAD = "#(.P_u_r4_HI_PAD({v}), .P_u_r5_HI_PAD({v}))"


def qc_plan():
    lc = dict(base_type="sle_st_b_v1", collector_tree=dict(type="sle_st_b_v1", nodes=[]))
    return {
        "schema": "x", "die": {"name": "qwen_compute"},
        "partition_types": {
            "sle_st_b_v1": {"module": "qfd_qc_sle_st_b", "buses": [], "clock": {"landing_contract": lc}},
            "cbf_q11": {"module": "qfd_qc_cb_f_q11", "buses": []},
            "glue": {"module": "glue", "buses": []}},
        "partitions": [{"name": n, "type": "sle_st_b_v1"} for n in ("sl_E0_st_b", "sl_E2_st_b", "sl_E4_st_b")] +
                      [{"name": "c_a", "type": "cbf_q11"}, {"name": "c_b", "type": "cbf_q11"},
                       {"name": "g", "type": "glue"}],
        "clock": {"ring_hold": {"write_edge": "fall", "write_fall_types": ["cbf_q11", "sle_st_b_v1"]},
                  "tap_window": {"per_type_ps": {"sle_st_b_v1": 60}}},
        "reset": {"in_sites": {"sle_st_b_v1": [8.16, 8.608]}},
    }


def qc_bind(d):
    out = Path(d) / "bind"
    (out / "rtl").mkdir(parents=True)
    (out / "bind_report.json").write_text(json.dumps({"types": {
        "sle_st_b_v1": {"module": "qfd_qc_sle_st_b"}, "cbf_q11": {"module": "qfd_qc_cb_f_q11"},
        "glue": {"module": "glue"}}}))
    top = ["module qwen_compute_bound_top ();"]
    for n, v in (("sl_E0_st_b", 30), ("sl_E2_st_b", 29), ("sl_E4_st_b", 30)):
        top.append(f"    qfd_qc_sle_st_b {PAD.format(v=v)} {n} (")
        top.append("        .clk(clk));")
    for n, i in (("c_a", 0), ("c_b", 48)):
        top.append(f"    qfd_qc_cb_f_q11 #(.S_u_fab_sidx(3'b101), .S_u_t_tile_id(16'd{i})) {n} (")
        top.append("        .clk(clk));")
    top += ["    glue g (", "        .clk(clk));", "endmodule"]
    (out / "rtl" / "qwen_compute_bound_top.sv").write_text("\n".join(top) + "\n")
    return out


def qc_sidecar():
    return {"collector": {
        "parts": {n: dict(type="sle_st_b_v1", active=True) for n in ("sl_E0_st_b", "sl_E2_st_b", "sl_E4_st_b")},
        "types": {"sle_st_b_v1": dict(base_type="sle_st_b_v1", tree=dict(type="sle_st_b_v1"))},
        "base_type_by_part": {n: "sle_st_b_v1" for n in ("sl_E0_st_b", "sl_E2_st_b", "sl_E4_st_b")}}}


class Unit(unittest.TestCase):
    def test_parse_params(self):
        self.assertEqual(PCS.parse_params("#(.A(1), .B({x, y}), .C(32'h0f))"), {"A": "1", "B": "{x, y}", "C": "32'h0f"})
        self.assertEqual(PCS.parse_params(""), {})

    def test_groups_logic_vs_id(self):
        diff, logic, g = PCS.logic_groups({"a": PAD.format(v=30), "b": PAD.format(v=29), "c": PAD.format(v=30)})
        self.assertEqual(logic, ["P_u_r4_HI_PAD", "P_u_r5_HI_PAD"])
        self.assertEqual(sorted(x["insts"] for x in g.values()), [["a", "c"], ["b"]])
        diff, logic, g = PCS.logic_groups({"a": "#(.S_t_tile_id(1))", "b": "#(.S_t_tile_id(2))"})
        self.assertEqual((diff, logic, len(g)), (["S_t_tile_id"], [], 1))      # parent_id_straps case, no split

    def test_split_plan_and_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            P = qc_plan()
            pf = Path(d) / "plan.json"
            pf.write_text(json.dumps(P, separators=(", ", ": ")) + "\n")
            sf = Path(d) / "sidecar.json"
            sf.write_text(json.dumps(qc_sidecar(), indent=1) + "\n")
            out = qc_bind(d)
            self.assertEqual(PCS.main([str(pf), "--bind-out", str(out), "--check"]), 3)
            po, so, rp = Path(d) / "p2.json", Path(d) / "s2.json", Path(d) / "r.json"
            self.assertEqual(PCS.main([str(pf), "--bind-out", str(out), "--out", str(po), "--sidecar", str(sf),
                                       "--sidecar-out", str(so), "--report", str(rp)]), 0)
            Q, S2, R = json.loads(po.read_text()), json.loads(so.read_text()), json.loads(rp.read_text())
            self.assertEqual(po.read_text(), json.dumps(Q, separators=(", ", ": ")) + "\n")   # plan text style kept
            (s,) = R["splits"]
            self.assertEqual(s["type"], "sle_st_b_v1")
            c30, c29 = s["clones"]
            self.assertEqual((c30["partitions"], c29["partitions"]), (["sl_E0_st_b", "sl_E4_st_b"], ["sl_E2_st_b"]))
            self.assertEqual(c30["values"]["P_u_r4_HI_PAD"], "30")
            self.assertTrue(re.fullmatch(r"sle_st_b_v1__pv[0-9a-f]{8}", c30["name"]))
            self.assertNotIn("sle_st_b_v1", Q["partition_types"])
            ptype = {p["name"]: p["type"] for p in Q["partitions"]}
            self.assertEqual(ptype["sl_E2_st_b"], c29["name"])
            self.assertEqual(ptype["sl_E0_st_b"], ptype["sl_E4_st_b"])
            self.assertEqual(ptype["c_a"], "cbf_q11")                               # ID-only: unchanged
            for c in (c30, c29):
                t = Q["partition_types"][c["name"]]
                self.assertEqual((t["module"], t["param_base_type"]), (c["name"], "sle_st_b_v1"))
                self.assertEqual(t["clock"]["landing_contract"]["base_type"], "sle_st_b_v1")
                self.assertEqual(t["clock"]["landing_contract"]["collector_tree"]["type"], c["name"])
                self.assertEqual(Q["reset"]["in_sites"][c["name"]], [8.16, 8.608])
                self.assertEqual(Q["clock"]["tap_window"]["per_type_ps"][c["name"]], 60)
                self.assertIn(c["name"], Q["clock"]["ring_hold"]["write_fall_types"])
                self.assertEqual(S2["collector"]["types"][c["name"]]["tree"]["type"], c["name"])
                self.assertEqual(S2["collector"]["types"][c["name"]]["base_type"], "sle_st_b_v1")
            self.assertEqual(S2["collector"]["parts"]["sl_E2_st_b"]["type"], c29["name"])
            self.assertEqual(S2["collector"]["parts"]["sl_E4_st_b"]["type"], c30["name"])
            self.assertEqual(S2["collector"]["base_type_by_part"]["sl_E2_st_b"], "sle_st_b_v1")
            # everything else in the plan is untouched
            for k in ("cbf_q11", "glue"):
                self.assertEqual(Q["partition_types"][k], P["partition_types"][k])

    def test_unknown_reference_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            P = qc_plan()
            P["budgets"] = {"owner": "sle_st_b_v1"}
            pf = Path(d) / "plan.json"
            pf.write_text(json.dumps(P))
            out = qc_bind(d)
            self.assertEqual(PCS.main([str(pf), "--bind-out", str(out), "--out", str(Path(d) / "o.json")]), 2)
            self.assertFalse((Path(d) / "o.json").exists())

    def test_idempotent_after_split(self):
        with tempfile.TemporaryDirectory() as d:
            out = qc_bind(d)
            top = (out / "rtl" / "qwen_compute_bound_top.sv").read_text().replace(PAD.format(v=29), PAD.format(v=30))
            (out / "rtl" / "qwen_compute_bound_top.sv").write_text(top)
            pf = Path(d) / "plan.json"
            pf.write_text(json.dumps(qc_plan()))
            self.assertEqual(PCS.main([str(pf), "--bind-out", str(out), "--check"]), 0)


HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))
EX = HERE / "examples" / "bind_tiny"


@unittest.skipUnless(HAVE_YOSYS and (EX / "die_plan_lanes.json").is_file(), "no Yosys (OT_BIND_YOSYS) and no docker")
class EndToEnd(unittest.TestCase):
    def test_tiny_split_rebind_kit_rtl(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            p = json.loads((EX / "die_plan_lanes.json").read_text())
            p["asbuilt"]["base"] = str(EX)
            pf = d / "plan.json"
            pf.write_text(json.dumps(p))
            out = d / "o"
            for c in ("elab", "bind"):
                self.assertEqual(bind.main([c, str(pf), "--out", str(out), "--mem", "4"]), 0)
            self.assertNotEqual(bind.main(["kit-rtl", str(pf), "--out", str(out), "--type", "ta",
                                           "--kit", str(d / "k0")]), 0)    # A0/A1 carry P_u_a_ID 1 / 2
            p2 = d / "plan2.json"
            self.assertEqual(PCS.main([str(pf), "--bind-out", str(out), "--out", str(p2), "--report",
                                       str(d / "r.json")]), 0)
            (s,) = json.loads((d / "r.json").read_text())["splits"]
            self.assertEqual(s["type"], "ta")
            out2 = d / "o2"
            for c in ("elab", "bind"):
                self.assertEqual(bind.main([c, str(p2), "--out", str(out2), "--mem", "4"]), 0)
            self.assertEqual(json.loads((out2 / "bind_report.json").read_text())["n_errors"], 0)
            self.assertEqual(PCS.main([str(p2), "--bind-out", str(out2), "--check"]), 0)     # idempotent
            for c in s["clones"]:
                kd = d / ("k_" + c["name"])
                self.assertEqual(bind.main(["kit-rtl", str(p2), "--out", str(out2), "--type", c["name"],
                                            "--kit", str(kd)]), 0)
                man = json.loads((kd / "kit_rtl.json").read_text())
                self.assertEqual(man["instances"], c["partitions"])
                val = c["values"]["P_u_a_ID"]
                body = Path(next(f for f in man["files"] if Path(f).stem == man["bound_module"])).read_text()
                # one value set per type: the bind bakes it into the clone's module (no per-instance parameter;
                # declared straps such as S_u_b_id stay strap parameters, as on every bound type)
                self.assertNotIn("P_u_a_ID", man["params"])
                self.assertRegex(body, rf"lf_a #\(\.ID\({val}\)\)")


if __name__ == "__main__":
    unittest.main()
