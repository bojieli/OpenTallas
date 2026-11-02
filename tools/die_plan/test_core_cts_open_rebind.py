import copy
import unittest

import core_cts_open_rebind as R


def fixture():
    parents = {"qb_entry_0": "port:clk[0]"}
    parents.update({f"qb_entry_{i}": f"qb_entry_{i-1}" for i in range(1, 6)})
    parents.update(qb_root="qb_entry_5", qb_S="qb_root", qb_N="qb_root",
                   qb_SW="qb_S", qb_SE="qb_S", qb_NW="qb_N", qb_NE="qb_N")
    nodes, instances = [], {}
    nets = {"clk[0]": dict(sig="CLOCK", protected=True, wire=False, special=[]),
            "data": dict(sig="SIGNAL", protected=False, wire=False, special=[]),
            "VDD": dict(sig="POWER", protected=False, wire=False, special=[["M5", 0, 0, 120, 2000, False]])}
    for i, (name, parent) in enumerate(parents.items()):
        master = ("BUFx2_ASAP7_75t_R" if name.startswith("qb_entry") else
                  "BUFx16f_ASAP7_75t_R" if name == "qb_root" else "BUFx12_ASAP7_75t_R")
        net = name + "_out"; source = "clk[0]" if parent.startswith("port:") else parent + "_out"
        xy = {"qb_SW": (0, 0), "qb_SE": (20000, 0), "qb_NW": (0, 20000), "qb_NE": (20000, 20000)}.get(name, (i*400, 10000))
        bbox = [xy[0], xy[1], xy[0]+270, xy[1]+270]
        n = dict(name=name, master=master, parent=parent, net_y=net, bbox=bbox,
                 orient="R0", status="FIRM", protected=True)
        nodes.append(n)
        instances[name] = {k: copy.deepcopy(n[k]) for k in ("master", "bbox", "orient", "status", "protected")}
        instances[name].update(origin=bbox[:2], pins={
            "A": dict(net=source, io="INPUT", sig="SIGNAL"), "Y": dict(net=net, io="OUTPUT", sig="SIGNAL")})
        nets[net] = dict(sig="CLOCK", protected=name not in R.LEAVES, wire=False, special=[])
    leaves = [dict(node=n, sinks=[]) for n in ("qb_SW", "qb_SE", "qb_NW", "qb_NE")]
    for i in range(1972):
        physical = i // 493; leaf = leaves[(physical+1) % 4]; name = "ff" + str(i)
        master = "DFFHQNx1_ASAP7_75t_R"; x = (physical % 2)*20000; y = (physical//2)*20000
        bbox = [x+(i%17)*54, y+(i%19)*270, x+(i%17)*54+540, y+(i%19)*270+270]
        instances[name] = dict(master=master, bbox=bbox, origin=bbox[:2], orient="R0", status="PLACED", protected=False,
            pins={"CLK": dict(net=leaf["node"]+"_out", io="INPUT", sig="CLOCK"),
                  "D": dict(net="data", io="INPUT", sig="SIGNAL"),
                  "VDD": dict(net="VDD", io="INOUT", sig="POWER")})
        leaf["sinks"].append(dict(instance=name, master=master, pin="CLK"))
    state = dict(module="dsfd_node_LLfd", dbu=1000, instances=instances, nets=nets,
                 ports={"clk[0]": dict(net="clk[0]", io="INPUT", sig="CLOCK", boxes=[])})
    manifest = dict(schema="opentallas.qbs_cts_open_rebind.v1", stage="pre_cts", module="dsfd_node_LLfd",
                    period_ps=833, reviewed_source_event="explicit test event", clock_port="clk[0]",
                    nodes=nodes, leaves=leaves)
    return state, manifest


class Guards(unittest.TestCase):
    def setUp(self):
        self.s, self.m = fixture()

    def rejects(self, reason):
        with self.assertRaisesRegex(R.RebindError, reason):
            R.validate(self.s, self.m)

    def test_positive_exact_count_and_preservation(self):
        targets = R.validate(self.s, self.m)
        new, moves, stats = R.proposal(self.s, self.m)
        self.assertTrue(stats["converged"]); self.assertGreater(len(moves), 0)
        self.assertEqual([len(l["sinks"]) for l in new["leaves"]], [493]*4)
        after = copy.deepcopy(self.s)
        for move in moves:
            after["instances"][move["instance"]]["pins"]["CLK"]["net"] = move["target"]+"_out"
        R.validate(after, new)
        self.assertEqual(R.digest(R.preserved_state(self.s, targets)), R.digest(R.preserved_state(after, targets)))
        self.assertFalse(any(after["nets"][l["node"]+"_out"]["protected"] for l in new["leaves"]))

    def test_default_off(self):
        with self.assertRaisesRegex(R.RebindError, "DEFAULT_OFF"):
            R.run_native("missing", "missing", "missing", "missing")

    def test_unknown_stage(self):
        self.m["stage"] = "cts"; self.rejects("PRE_CTS_STAGE")

    def test_nonregister_endpoint(self):
        s = self.m["leaves"][0]["sinks"][0]; s["master"] = "BUFx2_ASAP7_75t_R"
        self.s["instances"][s["instance"]]["master"] = s["master"]
        self.rejects("DIRECT_REGISTER_CLK")

    def test_closed_cts_net(self):
        self.s["nets"]["qb_SW_out"]["protected"] = True; self.rejects("CTS_OPEN_NET")

    def test_routed_clock_net(self):
        self.s["nets"]["qb_SW_out"]["wire"] = True; self.rejects("ALREADY_ROUTED")

    def test_foreign_driver(self):
        self.s["instances"]["foreign"] = dict(pins={"Y": dict(net="qb_SW_out", io="OUTPUT")})
        self.rejects("FOREIGN_DRIVER")

    def test_missing_member(self):
        name = self.m["leaves"][0]["sinks"][0]["instance"]
        self.s["instances"][name]["pins"]["CLK"]["net"] = None
        self.rejects("SOURCE_MEMBERSHIP")

    def test_wrong_root(self):
        self.s["instances"]["qb_entry_0"]["pins"]["A"]["net"] = "data"
        self.rejects("PLANNED_TRUNK_TOPOLOGY")

    def test_changed_stage_depth(self):
        node = next(n for n in self.m["nodes"] if n["name"] == "qb_SW")
        node["parent"] = "qb_root"; self.s["instances"]["qb_SW"]["pins"]["A"]["net"] = "qb_root_out"
        self.rejects("STAGE_DEPTH")

    def test_changed_planned_pose(self):
        self.s["instances"]["qb_root"]["bbox"][0] += 1; self.rejects("POSE_OR_MASTER")

    def test_non_target_data_pg_or_protection_is_detected(self):
        targets = R.validate(self.s, self.m); baseline = R.digest(R.preserved_state(self.s, targets))
        for kind in ("data", "pg", "protection", "pose"):
            changed = copy.deepcopy(self.s)
            if kind == "data": changed["instances"]["ff0"]["pins"]["D"]["net"] = "other"
            if kind == "pg": changed["nets"]["VDD"]["special"][0][1] = 1
            if kind == "protection": changed["nets"]["qb_SW_out"]["protected"] = True
            if kind == "pose": changed["instances"]["ff0"]["origin"][0] += 1
            self.assertNotEqual(baseline, R.digest(R.preserved_state(changed, targets)), kind)


if __name__ == "__main__":
    unittest.main()
