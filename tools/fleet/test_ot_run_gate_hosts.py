import importlib.machinery, importlib.util, pathlib, unittest

HERE = pathlib.Path(__file__).resolve().parent
loader = importlib.machinery.SourceFileLoader("otr_gate", str(HERE / "ot-run"))
spec = importlib.util.spec_from_loader("otr_gate", loader)
R = importlib.util.module_from_spec(spec)
loader.exec_module(R)


class GateHosts(unittest.TestCase):
    POOL = ["epyc2", "intel1", "localhost", "epyc7", "epyc8", "intel2"]

    def test_gate_commands_never_use_localhost_or_the_hub(self):
        for cmd in (["bash", "/srv/x/rt/current/tools/fleet/ot-gate-remote", "claude/b@abc", "16"], ["ot-gate-remote", "claude/b@abc"]):
            self.assertEqual(R.gate_hosts(cmd, self.POOL), ["epyc2", "intel1", "epyc7", "epyc8"])

    def test_other_commands_keep_the_whole_pool(self):
        self.assertEqual(R.gate_hosts(["python3", "-c", "1"], self.POOL), self.POOL)
        self.assertFalse(R.gate_like(["bash", "run_ot-gate-remote-notes.sh"]))        # a name that merely contains the string is not a gate

    def test_a_pin_that_names_only_forbidden_hosts_is_left_alone(self):
        self.assertEqual(R.gate_hosts(["ot-gate-remote", "x"], ["localhost"]), ["localhost"])
