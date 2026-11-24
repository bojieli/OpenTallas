"""TAG-CANCEL-1124 (KV-PV-CAP 09:0x: `ot-run --cancel oth-ubuntu-3730999-1795505348` on E11 killed the batch script and left 2 yosys containers of
its xargs -P fan-out running until ot-heavy-stop --tag): stopping a unit also stops every container carrying the unit's ot-run tag."""
import importlib.machinery, importlib.util, pathlib, unittest

P = str(pathlib.Path(__file__).with_name("ot-heavy-stop"))
loader = importlib.machinery.SourceFileLoader("ot_heavy_stop_tag", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_heavy_stop_tag", loader))
loader.exec_module(M)

U = "oth-ubuntu-3730999-1795505348"
TAG = "otrun-tolerant-swine-1101357-530117394"


class TagCancel(unittest.TestCase):
    def test_tags_come_from_unit_labels_and_scope_env(self):
        rows = [f"otc-1-1|{U}|{TAG}", "otc-2-2|oth-ubuntu-9-9|otrun-other-1-2", f"otc-3-3|oth-child-1|{TAG}", "magical_fermi||"]
        self.assertEqual(M.unit_tags(U, [], rows), [TAG])
        self.assertEqual(M.unit_tags(U, [11, 12], [], envtag=lambda p: {11: "otrun-x-5-6"}.get(p, "")), ["otrun-x-5-6"])
        self.assertEqual(M.unit_tags("oth-none", [], rows), [])

    def test_stopping_a_unit_stops_its_fan_out_containers(self):
        """two yosys containers of a nested call: child unit label, the parent's tag; the --unit stop finds them by the tag after the scope is gone"""
        docker = {"ps": [f"otc-100-1|{U}|{TAG}", f"otc-200-7|oth-child-1|{TAG}", f"otc-201-8|oth-child-2|{TAG}", "otc-300-9|oth-ubuntu-9-9|otrun-other-1-2"]}
        stopped, scopes = [], []

        def run(cmd, capture_output=True, **k):
            if cmd[:2] == ["docker", "stop"] or cmd[:2] == ["docker", "kill"]:
                stopped.append(cmd[-1])
                docker["ps"] = [r for r in docker["ps"] if r.split("|")[0] != cmd[-1]]
            elif cmd[:2] == ["systemctl", "--user"]:
                scopes.append(cmd[-1])
            return type("R", (), {"returncode": 0, "stdout": ""})()

        def sh(*a, timeout=120):
            if a[:2] == ("docker", "ps"):
                fmt = a[-1]
                return "\n".join(r if fmt == M.LABEL_FMT else r.split("|")[0] for r in docker["ps"]) + "\n"
            return ""
        orig = (M.subprocess.run, M.sh, M.scope_pids, M.env_tag)
        M.subprocess.run, M.sh, M.scope_pids, M.env_tag = run, sh, (lambda u: [100] if u == U else []), (lambda p: "")
        try:
            rc = M.main(["--unit", U])
        finally:
            M.subprocess.run, M.sh, M.scope_pids, M.env_tag = orig
        self.assertEqual(rc, 0)
        self.assertEqual(sorted(stopped), ["otc-100-1", "otc-200-7", "otc-201-8"])          # never another job's container
        self.assertEqual(scopes, [U + ".scope"])


if __name__ == "__main__":
    unittest.main()
