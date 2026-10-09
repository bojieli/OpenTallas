"""LINT-AT-SUBMIT 2026-10-09: pin density / utilisation estimated at intake (submit_lint.py) and its loop wiring."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
import closure_loop as cl  # noqa: E402
import submit_lint as S  # noqa: E402

RTL = """
// a comment with module fake (
module ot_t #(
    parameter integer NS = 8,
    parameter integer W = 16,   // width
    parameter AW = $clog2(NS) + 2
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire [NS-1:0]       i_we,
    input  wire [NS*W*32-1:0]  i_data,
    input  wire [AW-1:0]       i_a, i_b,
    output reg  [W-1:0]        o_mask,
    output reg                 fault
);
endmodule
"""


class FakeGit:
    def __init__(self, files):
        self.files = files

    def show(self, commit, path):
        return self.files.get(path)

    def blob(self, commit, path):
        return "b" + str(hash(self.files.get(path, ""))) if path in self.files or path == "" else None


def cfg(pins, fw=777.6, fh=518.4, extra="", params="--param NS=8"):
    return (f"TOP=ot_t\nSRCS='rtl/t.sv'\nPARAMS=({params})\nFW={fw}\nFH={fh}\nPINS=({pins})\n{extra}\n")


def spec(cmd_env="", name="t", **kw):
    s = {"name": "j1", "block": "b", "owner": "o", "source": {"branch": "main", "commit": "abcdef1"},
         "stages": {"route": {"cmd": f"export OT_ORFS_CORNER_OVERRIDE=TC; {cmd_env}OT_MM_FF_SDC=x SRC={{SRC}} bash "
                                     f"physical/qwen_die_masters/jobs/route_master.sh {name} {{LABEL}} {{RUN}}/routes"}}}
    s.update(kw)
    return s


FLOW_NEW = {"physical/qwen_die_masters/jobs/route_master.sh": "IO_PLACER_H IO_PLACER_V PIN_MIN_TRACKS",
            "tools/run_abi3_physical.py": "OT_PIN_GROUP_MAX OT_PIN_BALANCE_H OT_PIN_BALANCE_V"}
FLOW_PRE_DDE = {"physical/qwen_die_masters/jobs/route_master.sh": "IO_PLACER_H IO_PLACER_V",  # be5b56d78..08ef6a8a8
                "tools/run_abi3_physical.py": "set_io_pin_constraint -group -order"}


def git_for(cfgtext, name="t", flow=None):
    return FakeGit({f"physical/qwen_die_masters/cfg/{name}.env": cfgtext, "rtl/t.sv": RTL,
                    **(FLOW_NEW if flow is None else flow)})


class Expr(unittest.TestCase):
    def test_eval(self):
        env = {"NS": 8, "W": 16}
        self.assertEqual(S.sv_eval("NS*W*32-1", env), 4095)
        self.assertEqual(S.sv_eval("$clog2(NS+1)+1", env), 5)
        self.assertEqual(S.sv_eval("(NS > 1) ? $clog2(NS) : 1", env), 3)
        self.assertEqual(S.sv_eval("8'd255 + 'h10 - 2**3", env), 263)
        self.assertEqual(S.sv_eval("W/3", env), 5)
        with self.assertRaises(S.ExprError):
            S.sv_eval("UNKNOWN+1", env)

    def test_ports(self):
        ports = S.top_ports(RTL, "ot_t", {"NS": "4"})
        d = {n: (w, l) for n, w, l in ports}
        self.assertEqual(d["i_data"], (4 * 16 * 32, 0))
        self.assertEqual(d["i_we"], (4, 0))
        self.assertEqual(d["i_a"], d["i_b"])           # inherited declaration
        self.assertEqual(d["i_a"][0], 4)                # AW = clog2(4) + 2
        self.assertEqual(d["clk"], (1, -1))
        self.assertIn("i_data[2047]", S.bit_names(ports))

    def test_unmodelled_port_type(self):
        with self.assertRaises(S.ExprError):
            S.top_ports("module m (input my_pkg::t_s a); endmodule", "m")


class Density(unittest.TestCase):
    def test_big_group_balanced(self):
        # 2048 even data bits as ONE ordered group: 20.5 b/um on M4 and M6 alike (more layers cannot dilute one group);
        # the first approved fix, pin_balance, spreads them uniformly over 518 um on M4+M6: ~2 b/um
        g = git_for(cfg("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left' --pin-region '^i_data\\[[0-9]*[13579]\\]$=right'"))
        r = S.check(spec(), g)
        self.assertEqual(r["verdict"], "FIX", r)
        self.assertEqual(r["est"]["W"], 20.48)
        self.assertEqual(r["fix"], "pin_balance")
        self.assertLess(r["est_fix"]["W"], 6)
        s2 = S.apply_fix(spec(), r, "now")
        cmd = s2["stages"]["route"]["cmd"]
        self.assertIn("OT_PIN_GROUP_MAX=32 OT_PIN_BALANCE_H='M4 M6' OT_PIN_BALANCE_V='M5 M7' PIN_H='M4 M6' "
                      "PIN_V='M5 M7' bash physical/qwen_die_masters/jobs/route_master.sh t", cmd)
        self.assertTrue(cmd.startswith("export OT_ORFS_CORNER_OVERRIDE=TC; "))
        self.assertEqual(s2["submit_lint"]["applied"], "pin_balance")
        self.assertEqual(s2["submit_lint"]["env"]["OT_PIN_GROUP_MAX"], "32")
        self.assertNotIn("submit_lint", spec())

    def test_fix_the_source_flow_does_not_read(self):
        # drive-0212: sys-08ef6a8a8-ls / kv624-a732a1d76-ls ran pin_balance on a source predating dde873a8e and
        # re-failed at the identical density.  A fix the source's flow does not read is never applied: REFUSE.
        g = git_for(cfg("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left'"), flow=FLOW_PRE_DDE)
        r = S.check(spec(), g)
        self.assertEqual(r["verdict"], "REFUSE", r)
        self.assertIn("pin_balance: the source abcdef1 flow does not read OT_PIN_GROUP_MAX", r["message"])
        self.assertIn("pin_tracks2_spread: the source abcdef1 flow does not read PIN_MIN_TRACKS", r["message"])
        # balance already in the command but unread by the flow: the estimate ignores it (as the flow does)
        env = "OT_PIN_GROUP_MAX=32 OT_PIN_BALANCE_H='M4 M6' OT_PIN_BALANCE_V='M5 M7' "
        self.assertEqual(S.check(spec(cmd_env=env), g)["verdict"], "REFUSE")
        self.assertEqual(S.check(spec(cmd_env=env), git_for(cfg("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left'")))
                         ["verdict"], "PASS")
        # dde873a8e balanced only lo-hi regions: a whole-face region falls through to the second fix
        strict = dict(FLOW_NEW, **{"tools/run_abi3_physical.py": FLOW_NEW["tools/run_abi3_physical.py"] +
                                   " balanced pins require ... bounded regions"})
        r3 = S.check(spec(), git_for(cfg("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left'"), flow=strict))
        self.assertEqual(r3.get("fix"), "pin_tracks2_spread", r3)
        # a cfg PIN_MIN_TRACKS=2 the flow does not read gives no slot relief
        g2 = git_for(cfg("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left'", extra="PIN_MIN_TRACKS=2"),
                     flow=FLOW_PRE_DDE)
        self.assertEqual(S.check(spec(), g2)["verdict"], "REFUSE")

    def test_balanced_disjoint_ranges_do_not_add(self):
        # drive-0212: qfd_hub_ps-dde873a8e-tc-bal32 (six disjoint right:lo-hi ranges, balanced) was estimated at
        # 26.3 b/um by summing every region of the face; measured 8.0, CLOSED.  Only overlapping ranges add.
        env = "OT_PIN_GROUP_MAX=32 OT_PIN_BALANCE_H='M4 M6' OT_PIN_BALANCE_V='M5 M7' PIN_H='M4 M6' PIN_V='M5 M7' "
        pins = ("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left:0-250' "
                "--pin-region '^i_data\\[[0-9]*[13579]\\]$=left:260-510'")
        r = S.check(spec(cmd_env=env), git_for(cfg(pins)))
        self.assertEqual(r["verdict"], "PASS", r)
        self.assertLess(r["est"]["W"], 6)                                   # 2048 pins / 250 um x 100 um / 2 layers ~ 4.1
        over = ("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left:0-150' "
                "--pin-region '^i_data\\[[0-9]*[13579]\\]$=left:0-150'")
        r2 = S.check(spec(cmd_env=env), git_for(cfg(over)))                # same range: 4096 / 150 um / 2 ~ 13.7
        self.assertEqual(r2["verdict"], "REFUSE", r2)

    def test_refused_when_no_fix_fits(self):
        # 2048 pins on a 60 um face: balanced spacing 0.029 um < pitch, two-track group needs 197 um
        g = git_for(cfg("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left'", fh=60))
        r = S.check(spec(), g)
        self.assertEqual(r["verdict"], "REFUSE", r)
        self.assertIn("pin_balance:", r["message"])
        self.assertIn("pin_tracks2_spread:", r["message"])

    def test_second_fix_and_cfg_block(self):
        g = git_for(cfg("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left'"))
        with patch.object(S, "FIXES", S.FIXES[1:]):
            r = S.check(spec(), g)
            self.assertEqual((r["verdict"], r["fix"]), ("FIX", "pin_tracks2_spread"), r)
            self.assertLessEqual(max(r["est_fix"].values()), 12)
            g2 = git_for(cfg("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left'", extra="PIN_MIN_TRACKS=1"))
            r2 = S.check(spec(), g2)
            self.assertEqual(r2["verdict"], "REFUSE")
            self.assertIn("the cfg sets PIN_MIN_TRACKS", r2["message"])

    def test_force_applies_fix_to_measured_failure(self):
        # the estimate passes as configured (a lower bound), but the flow measured a failure: force applies fix 1
        g = git_for(cfg("--pin-region '^i_we(\\[|$)=left'"))
        self.assertEqual(S.check(spec(), g)["verdict"], "PASS")
        r = S.check(spec(), g, force=True)
        self.assertEqual((r["verdict"], r["fix"]), ("FIX", "pin_balance"))
        env = "OT_PIN_GROUP_MAX=32 OT_PIN_BALANCE_H='M4 M6' OT_PIN_BALANCE_V='M5 M7' "
        r2 = S.check(spec(cmd_env=env), g, force=True)                    # balance already set: the second fix
        self.assertEqual(r2["fix"], "pin_tracks2_spread")

    def test_pass_and_tracks_and_balance(self):
        g = git_for(cfg("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left'", extra="PIN_MIN_TRACKS=2"))
        self.assertEqual(S.check(spec(), g)["verdict"], "PASS")              # 2-track slots: 10.4 b/um
        g = git_for(cfg("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left'"))
        env = "OT_PIN_GROUP_MAX=32 OT_PIN_BALANCE_H='M4 M6' OT_PIN_BALANCE_V='M5 M7' "
        r = S.check(spec(cmd_env=env), g)
        self.assertEqual(r["verdict"], "PASS", r)                            # uniform over 518 um: ~2 b/um/layer

    def test_env_settings_read(self):
        g = git_for(cfg("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left'"))
        r = S.check(spec(cmd_env="PIN_H='M4 M6' PIN_V='M5 M7' "), g)
        self.assertEqual(r["layers"]["PIN_H"], "M4 M6")
        self.assertEqual(r["est"]["W"], 15.63)                              # the group can land on M6: 1,563 slots

    def test_skips(self):
        self.assertEqual(S.check(spec(fp_lint=False), git_for(cfg("")))["verdict"], "SKIP")
        self.assertEqual(S.check(spec(submit_lint=False), git_for(cfg("")))["verdict"], "SKIP")
        s = spec()
        s["stages"]["route"]["cmd"] = "bash physical/s81_ph_views/common/route_view.sh x"
        self.assertEqual(S.check(s, git_for(cfg("")))["verdict"], "SKIP")
        self.assertEqual(S.check(spec(name="missing"), git_for(cfg("")))["verdict"], "SKIP")
        g = FakeGit({"physical/qwen_die_masters/cfg/t.env": cfg("").replace("ot_t", "ot_other"), "rtl/t.sv": RTL})
        self.assertEqual(S.check(spec(), g)["verdict"], "SKIP")

    def test_threshold_override_and_warn_only(self):
        g = git_for(cfg("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left'"))
        self.assertEqual(S.check(spec(fp_lint={"set": {"pin_density_max": 25}}), g)["verdict"], "PASS")
        g = git_for(cfg("--pin-region '^i_data\\[[0-9]*[02468]\\]$=left'", fh=60))
        r = S.check(spec(fp_lint={"warn_only": True}), g)
        self.assertEqual(r["verdict"], "PASS")                              # warn_only never refuses
        self.assertTrue(r["message"].startswith("warn_only"))

    def test_util_from_same_synthesis_input(self):
        def spec(**kw):
            return globals()["spec"](fp_lint={"set": {"pin_density_max": 1000}}, **kw)
        g = git_for(cfg("--pin-region '^(clk|rst_n|i_\\w+|o_\\w+|fault)(\\[|$)=left'", fw=300, fh=300))
        reason = "util: utilisation 70.0% > 60% (std 60000 + macro 0 um2 in 85000 um2): grow the outline to <= 55-60%"
        key, rec = S.util_record(spec(), reason, g, "old")
        r = S.check(spec(), g, {key: rec})
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("utilisation", r["message"])
        g2 = git_for(cfg("--pin-region '^(clk|rst_n|i_\\w+|o_\\w+|fault)(\\[|$)=left'", fw=400, fh=400))
        r2 = S.check(spec(), g2, {key: rec})                                 # bigger outline, same synthesis input
        self.assertEqual(r2["verdict"], "PASS")
        self.assertLess(r2["util_est"]["util"], 0.6)
        g3 = git_for(cfg("--pin-region '^(clk|rst_n|i_\\w+|o_\\w+|fault)(\\[|$)=left'", fw=300, fh=300,
                         params="--param NS=4"))
        self.assertNotIn("util_est", S.check(spec(), g3, {key: rec}))        # other parameters: no estimate


class LoopWiring(unittest.TestCase):
    def job(self):
        return {"name": "j1", "spec": spec(), "status": "QUEUED", "events": []}

    def test_spread_recorded(self):
        j = self.job()
        res = {"verdict": "FIX", "message": "m", "est": {"W": 17}, "est_fix": {"W": 8}, "fix": "pin_balance",
               "fix_env": dict(S.FIXES[0]["env"])}
        with patch.object(cl, "submit_check", return_value=res), patch.object(cl, "ledger"), patch.object(cl, "log"):
            cl.lint_at_submit(j)
        self.assertEqual(j["status"], "QUEUED")
        self.assertEqual(j["spec_submitted"], spec())
        self.assertIn("OT_PIN_BALANCE_H='M4 M6'", j["spec"]["stages"]["route"]["cmd"])
        self.assertEqual(j["spec"]["submit_lint"]["est_fix"], {"W": 8})

    def test_refused(self):
        j = self.job()
        with patch.object(cl, "submit_check", return_value={"verdict": "REFUSE", "message": "too dense"}), \
                patch.object(cl, "ledger"), patch.object(cl, "log"):
            cl.lint_at_submit(j)
        self.assertEqual(j["status"], "REFUSED")
        self.assertTrue(j["reason"].startswith("SUBMIT_LINT FLOORPLAN_MARGIN: too dense"))

    def test_error_never_blocks(self):
        j = self.job()
        with patch.object(cl, "submit_check", side_effect=RuntimeError("boom")), patch.object(cl, "log"):
            cl.lint_at_submit(j)
        self.assertEqual(j["status"], "QUEUED")
        self.assertEqual(j["spec"], spec())

    def test_validate_refuses(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(spec(), f)
        with patch.object(cl, "validate", return_value=[]), \
                patch.object(cl, "submit_check", return_value={"verdict": "REFUSE", "message": "dense"}), \
                patch("builtins.print"), self.assertRaises(SystemExit) as ex:
            cl.cmd_validate(SimpleNamespace(file=f.name))
        self.assertEqual(ex.exception.code, 1)
        Path(f.name).unlink()

    def test_release_route_key(self):
        with tempfile.TemporaryDirectory() as d, patch.object(cl, "STATE", Path(d)):
            cl.keys_path().parent.mkdir(parents=True, exist_ok=True)
            cl.keys_path().write_text(json.dumps({"b@abcdef1": ["j0", "j1", "j2"]}))
            cl.release_route_key({"name": "j1", "spec": spec()})
            self.assertEqual(cl.route_keys()["b@abcdef1"], ["j0", "j2"])

    def test_util_db_roundtrip(self):
        with tempfile.TemporaryDirectory() as d, patch.object(cl, "STATE", Path(d)):
            cl.util_db_add("k", {"area_um2": 1})
            cl.util_db_add("k2", {"area_um2": 2})
            self.assertEqual(set(cl.util_db()), {"k", "k2"})


if __name__ == "__main__":
    unittest.main()
