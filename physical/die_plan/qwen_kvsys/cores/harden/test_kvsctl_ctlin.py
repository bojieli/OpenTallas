"""DIE-KV-60 ctlin: shared-capture recut, boot capture form, and the opt-in synth keepdc hook."""
import copy
import random
import sys
import unittest
from pathlib import Path

import hr_face_ports as H
import kvsctl_boot_capture as BC

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tools/die_plan"))
import synth_keepdc as SK  # noqa: E402


def two_reset_captures(second="adff"):
    """pin d (bit 2) captured by two flops on clock 3 that differ only in their async reset (bits 5 / 7, active low)"""
    def adff(q, r):
        return dict(type="$adff", parameters=dict(WIDTH="1", CLK_POLARITY="1", ARST_POLARITY="0", ARST_VALUE="0"),
                    attributes={}, port_directions=dict(D="input", Q="output", CLK="input", ARST="input"),
                    connections=dict(D=[2], Q=[q], CLK=[3], ARST=[r]))
    cells = dict(a=adff(4, 5))
    cells["b"] = adff(6, 7) if second == "adff" else dict(
        type="$dff", parameters=dict(WIDTH="1", CLK_POLARITY="1"), attributes={},
        port_directions=dict(D="input", Q="output", CLK="input"), connections=dict(D=[2], Q=[6], CLK=[3]))
    ports = dict(d=dict(direction="input", bits=[2]), ck=dict(direction="input", bits=[3]),
                 ra=dict(direction="input", bits=[5]), rb=dict(direction="input", bits=[7]),
                 qa=dict(direction="output", bits=[4]), qb=dict(direction="output", bits=[6]))
    return dict(modules=dict(top=dict(ports=ports, netnames={k: dict(bits=list(v["bits"]), attributes={})
                                                             for k, v in ports.items()}, cells=cells)))


def simulate(mod, seq):
    """cycle model of $dff/$adff/$and/$pos: per step the inputs settle, async resets act, then one rising edge"""
    cells = mod["cells"]
    st = {n: 0 for n, c in cells.items() if c["type"] in ("$dff", "$adff")}
    out = []

    def val(b, env):
        if b in ("0", "1"):
            return int(b)
        if b in env:
            return env[b]
        for n, c in cells.items():
            if c["connections"].get("Q") == [b] and n in st:
                c_ = cells[n]
                if c_["type"] == "$adff" and val(c_["connections"]["ARST"][0], env) == int(c_["parameters"]["ARST_POLARITY"]):
                    return 0
                return st[n]
            if c["connections"].get("Y") == [b]:
                if c["type"] == "$and":
                    return val(c["connections"]["A"][0], env) & val(c["connections"]["B"][0], env)
                if c["type"] == "$pos":
                    return val(c["connections"]["A"][0], env)
        return 0
    pb = {k: v["bits"][0] for k, v in mod["ports"].items()}
    for d, ra, rb in seq:
        env = {pb["d"]: d, pb["ra"]: ra, pb["rb"]: rb}
        out.append((val(pb["qa"], env), val(pb["qb"], env)))
        nxt = {}
        for n in st:
            c = cells[n]
            if c["type"] == "$adff" and val(c["connections"]["ARST"][0], env) == int(c["parameters"]["ARST_POLARITY"]):
                nxt[n] = 0
            else:
                nxt[n] = val(c["connections"]["D"][0], env)
        st.update(nxt)
        out.append((val(pb["qa"], env), val(pb["qb"], env)))
    return out


class SharedCapture(unittest.TestCase):
    def test_one_face_load_and_exact_behaviour(self):
        for second in ("adff", "dff"):
            gold = two_reset_captures(second)
            gate, r = H.transform(copy.deepcopy(gold), "top", shared_capture_in=["d[0]"])
            m = gate["modules"]["top"]
            loads = [(n, p) for n, c in m["cells"].items() for p, bits in c["connections"].items()
                     if c["port_directions"].get(p) == "input" and 2 in bits]
            self.assertEqual(len(loads), 1)
            self.assertEqual(m["cells"][loads[0][0]]["type"], "$dff")
            self.assertEqual(r["shared_capture_in"][0]["cycles"], 0)
            self.assertEqual(r["added_ff_bits"], 1 if second == "adff" else 0)
            rnd = random.Random(7)
            seq = [(rnd.randint(0, 1), int(rnd.random() > 0.2), int(rnd.random() > 0.3)) for _ in range(400)]
            self.assertEqual(simulate(gold["modules"]["top"], seq), simulate(m, seq))

    def test_wrong_shape_is_loud(self):
        j = two_reset_captures()
        j["modules"]["top"]["cells"]["a"]["parameters"]["ARST_VALUE"] = "1"
        with self.assertRaises(SystemExit):
            H.transform(j, "top", shared_capture_in=["d[0]"])
        with self.assertRaises(SystemExit):
            H.transform(two_reset_captures(), "top", shared_capture_in=["qa[0]"])


LEAF = ("    qkd_static_kv_boot_dispatch_mu_nc32 #(.MUT(0)) u_boot (.ck(ck), .rst_n(rst_n), .boot_pr(boot__boot_pr), "
        ".boot_image_target(boot__boot_image_target), .boot_image_ready(boot__boot_image_ready), "
        ".boot_image_fault(boot__boot_image_fault), .boot_image_epoch(boot__boot_image_epoch), "
        ".boot_image_digest(boot__boot_image_digest), .execution_active(d2d__svc[23:23]), .sink_applied(w_x));")


class BootCapture(unittest.TestCase):
    def test_every_external_boot_input_captured_once(self):
        t, led = BC.apply("module m;\n" + LEAF + "\nendmodule\n")
        self.assertEqual(led["captured_bits"], 75 + 1 + 4 + 1 + 1 + 16 + 64 + 1)
        inst = [l for l in t.split("\n") if "u_boot (" in l][0]
        for _, actual, reg, _ in BC.CONN:
            self.assertNotIn(f"({actual})", inst)
            self.assertIn(f"({reg})", inst)
        self.assertIn("always @(posedge ck) begin", t)
        self.assertNotIn("rst_n) begin", t.split("u_boot (")[0])          # plain capture, no reset: a pure delay
        with self.assertRaises(ValueError):
            BC.apply(t)                                                    # not twice
        with self.assertRaises(ValueError):
            BC.apply(LEAF.replace(".boot_image_ready(boot__boot_image_ready)", ".boot_image_ready(x)"))


SYNTH = """set synth_full_args [concat $synth_full_args \\
    "-extra-map $::env(FLOW_HOME)/platforms/common/lcu_kogge_stone.v"]
  synth -flatten -run :fine {*}$synth_full_args
  synth -top $::env(DESIGN_NAME) -run fine: -noabc {*}$synth_full_args
opt -purge
  opt -fast -purge
"""


class SynthKeepdc(unittest.TestCase):
    def test_patch_and_idempotent(self):
        s, n = SK.patch_text(SYNTH)
        self.assertEqual(n, 2)
        self.assertNotIn("synth -flatten", s)
        self.assertNotIn("run fine:", s)
        self.assertIn("opt_dff {*}$nd -keepdc", s)
        self.assertIn("wreduce -keepdc", s)
        self.assertNotIn("opt_merge -keepdc", s)
        self.assertIsNone(__import__("re").search(r"(?m)^\s*opt( |$)", s))
        self.assertEqual(SK.patch_text(s), (s, 0))

    def test_unknown_synth_tcl_fails_closed(self):
        with self.assertRaises(ValueError):
            SK.patch_text(SYNTH.replace("-noabc", ""))


if __name__ == "__main__":
    unittest.main()
