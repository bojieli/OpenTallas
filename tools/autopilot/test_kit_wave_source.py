import json,tempfile,unittest
from pathlib import Path
from unittest import mock
from test_kit_wave import KW,cfg,FakeAP
class AP:
    DRY=True
    def __init__(self):self.logs=[]
    def log(self,x):self.logs.append(x)
class PinnedSource(unittest.TestCase):
    def run_case(self,pinned,retry=False):
        td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup)
        if pinned is not None:(Path(td.name)/"spec.json").write_text(json.dumps(pinned))
        c=cfg(src_sha="newsha",retry=["kv3_hg_v1@1"] if retry else [])
        r=dict(die="qwen_kvsys",item="kv3_hg_v1",attempt=1,dir=td.name,event="event28w_c",geom_dir="/g",kit="intel1:/k",cells=100,status="PASS")
        ap=AP();KW.enqueue_pass(ap,c,{},r,{})
        return r,ap
    def test_changed_config_cannot_relabel_old_result(self):
        r,a=self.run_case(dict(src_sha="oldsha"))
        self.assertIn("main@oldsha",a.logs[0]);self.assertNotIn("main@newsha",a.logs[0])
    def test_explicit_flow_retry_preserves_old_result_without_enqueue(self):
        r,a=self.run_case(dict(src_sha="oldsha"),True)
        self.assertEqual(r["class"],"FLOW");self.assertEqual(a.logs,[])
    def test_missing_identity_does_not_use_current_config(self):
        for p in (None,dict(src_sha="")):
            r,a=self.run_case(p);self.assertEqual(r["class"],"FLOW");self.assertEqual(a.logs,[])
if __name__=="__main__":unittest.main()

class RetryOutput(unittest.TestCase):
    def test_second_attempt_keeps_first_output_and_identity(self):
        with tempfile.TemporaryDirectory() as td:
            ap=FakeAP(td,"");c=cfg();st={"items":{}};r=dict(item="kv3_hg_v1",kind="type",block_sha="abc",replicas=2)
            a=KW.launch(ap,c,st,"qwen_kvsys",r,"intel2");sp1=json.loads((Path(a["dir"])/"spec.json").read_text())
            # a live producer is never replaced (LAUNCH-KEEP); attempt 2 follows a finished attempt
            self.assertIsNone(KW.launch(ap,c,st,"qwen_kvsys",r,"intel2"))
            self.assertEqual(len(st["items"]),1)
            for rec in st["items"].values():rec["status"]="FAIL"
            b=KW.launch(ap,c,st,"qwen_kvsys",r,"intel2");sp2=json.loads((Path(b["dir"])/"spec.json").read_text())
            self.assertNotEqual(sp1["work"],sp2["work"]);self.assertTrue(sp2["work"].endswith("/attempt_2"))
            self.assertEqual(json.loads((Path(a["dir"])/"spec.json").read_text()),sp1)


class ActiveSpecController(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="wave active spec ")))
        self.ap = FakeAP(self.root, "")
        self.config = cfg(future_lec=False)
        self.enterContext(mock.patch.object(KW, "tree_host_for", return_value="intel1"))
        self.enterContext(mock.patch.object(KW, "tool_skew_refuse", return_value=False))
        self.enterContext(mock.patch.object(KW, "draining_hosts", return_value=set()))
        self.pick = dict(item="kv3_hg_v1", kind="type", block_sha="abc", replicas=2)
        self.state = {"items": {}}
        self.first = self.launch()
        self.spec = Path(self.first["dir"]) / "spec.json"
        self.original = self.spec.read_bytes()
        self.service = self.first["unit"] + ".service"
        self.ap.active_unit_set = lambda: {self.service, self.first["unit"]}
        original_sh = self.ap.sh

        def fake_systemctl(cmd, **kwargs):
            if cmd[:3] == ["systemctl", "--user", "show"]:
                self.assertEqual(cmd[-1:], [self.service])
                return 0, self.properties, ""
            return original_sh(cmd, **kwargs)

        self.ap.sh = fake_systemctl
        self.set_controller(self.spec)
        (self.root / KW.LAUNCH_JOURNAL).unlink()

    def set_controller(self, spec, status="active"):
        import shlex
        self.properties = (
            f"Id={self.service}\n"
            f"ActiveState={status}\n"
            "ExecStart={ path=/bin/bash ; argv[]=/bin/bash -c "
            f"exec >> /some/unit.log 2>&1; python3 /old/rt/kit_wave.py run-item {shlex.quote(str(spec))}; "
            "echo AP_RC=$? ; ignore_errors=no ; }\n"
        )

    def launch(self):
        return KW.launch(self.ap, self.config, self.state, "qwen_kvsys", self.pick, "intel2")

    def test_live_exact_spec_survives_missing_journal_and_state(self):
        self.state = KW.load_state(self.root)
        self.assertEqual(self.state["items"], {})
        self.assertIsNone(self.launch())
        self.assertEqual(self.state["items"], {})
        self.assertEqual(len(self.ap.units), 1)
        self.assertEqual(self.spec.read_bytes(), self.original)
        self.assertFalse((self.root / KW.LAUNCH_JOURNAL).exists())

    def test_finished_exact_controller_allows_restart(self):
        self.state = KW.load_state(self.root)
        self.set_controller(self.spec, status="inactive")
        self.assertEqual(self.launch()["attempt"], 1)
        self.assertEqual(len(self.ap.units), 2)

    def test_same_unit_prefix_different_spec_does_not_block(self):
        self.state = KW.load_state(self.root)
        self.set_controller(self.spec.with_suffix(".json.other"))
        self.assertEqual(self.launch()["attempt"], 1)
        self.assertEqual(len(self.ap.units), 2)

    def test_normal_next_attempt_preserves_prior_spec(self):
        self.first["status"] = "FAIL"
        self.assertEqual(self.launch()["attempt"], 2)
        self.assertEqual(len(self.ap.units), 2)
        self.assertEqual(self.spec.read_bytes(), self.original)
