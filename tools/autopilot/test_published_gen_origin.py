import copy, hashlib, inspect, json, tempfile, types, unittest
from pathlib import Path
import published_gen_origin as P


def run_item_fixture(spec_path):
    return "actual generation recipe"


def changed_recipe(spec_path):
    return "changed generation recipe"


class PublishedProof(unittest.TestCase):
    def case(self, advisory=False, legacy=False):
        root = Path(tempfile.mkdtemp())
        code = root / "tools/autopilot/kit_wave.py"
        code.parent.mkdir(parents=True); code.write_text(inspect.getsource(run_item_fixture))
        (code.parent / "kit_store.py").write_text("original external helper")
        dep = root / "tools/die_plan/gen.py"; dep.parent.mkdir(parents=True); dep.write_text("fixture generator")
        modules = {}
        for alias in ("BI", "KR", "TS", "WJ", "ROAM", "FG", "RS"):
            file = root / ("dep_" + alias + ".py"); file.write_text(alias)
            modules[alias] = types.SimpleNamespace(__file__=str(file))
        modules["FG"].ENTRY_FILES = ("tools/die_plan/gen.py",)
        modules["FG"].closure_files = lambda read: ["tools/die_plan/gen.py"]
        plan = root / "plan.json"; plan.write_text('{"plan":"one"}')
        ab = root / "asbuilt.json"; ab.write_text('{"bind":"one"}')
        bind = root / "bind"; bind.mkdir(); (bind / "native_topology.json").write_text('{"native":"one"}')
        kw = types.SimpleNamespace(__file__=str(code), run_item=run_item_fixture, **modules)
        kw.file_sha = lambda cfg, die, path, ttl=0: hashlib.sha1(Path(path).read_bytes()).hexdigest()
        sp = dict(die="kv", item="hg_v1", kind="type", src="/published/tree", src_manifest_hash="a"*64,
                  plan=str(plan), kit_rtl=dict(mode="bind", asbuilt=str(ab), bind_out=str(bind)),
                  gen_args=["--production"], gen_env={"OT_FORM": "A"}, dry_gen=True, event="pg123",
                  root="/run/dry", work="/run/dry/item", gen_host="epyc7", hosts=["epyc7"])
        cfg = {"dies": {"kv": dict(src=sp["src"], src_manifest_hash=sp["src_manifest_hash"],
                                   plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest())}}
        jd = root / "dry"; jd.mkdir(); (jd/"spec.json").write_text(json.dumps(sp))
        observed = P.capture(cfg, "kv", sp, jd, kw)
        if legacy:
            path = jd/"published_gen_origin.json"
            original = json.loads(path.read_text())
            for key in ("recipe_file", "recipe_file_sha256", "external_helpers"):
                original.pop(key, None)
            path.write_text(json.dumps(original))
            observed["origin_sha256"] = P.sha(path.read_bytes())
        result = dict(verdict="DRY-PASS", stage="preflight", die="kv", item="hg_v1")
        if advisory: result["preflight_fail_advisory"] = ["real preflight failure"]
        (jd/"result.json").write_text(json.dumps(result))
        (jd/"unit.log").write_text("\n".join("KW_STAGE_RC " + stage + " 0" for stage in P.REQUIRED_STAGES))
        sealed = P.seal(jd, 0)
        checks = {name: {"verdict":"PASS"} for name in ("schema","pre_g0","hashes","contained")}
        checks["dry_gen"] = dict(verdict="PASS", item=sp["item"], kind="type", dir=str(jd),
                                rc=0, stage="preflight", result="DRY-PASS") | observed | sealed
        rec = dict(schema="opentallas.publish_gate.v1", die="kv", tree=sp["src"], manifest_hash=sp["src_manifest_hash"],
                   plan_sha256=cfg["dies"]["kv"]["plan_sha256"], item=sp["item"], verdict="PASS", checks=checks)
        record = root / "publish.json"; record.write_text(json.dumps(rec))
        ref = dict(kind="published-gen", record=str(record), record_sha256=P.sha(record.read_bytes()))
        live = dict(sp, event="LIVE", root="/run/live", work="/run/live/a2", gen_host="epyc8", hosts=["epyc8"])
        live.pop("dry_gen")
        kw.spec_for = lambda cfg, die, item, hub, kind="type": live
        return root, jd, cfg, sp, live, kw, ref, record

    def test_exact_completed_dry_generation_reuses_only_source_proof(self):
        root, jd, cfg, sp, live, kw, ref, record = self.case()
        proved, why = P.validate_reference(ref, cfg, "kv", "hg_v1", kw, live)
        self.assertEqual(proved, "a"*64, why)
        self.assertTrue(json.loads((jd/"spec.json").read_text())["dry_gen"])
        self.assertEqual(json.loads((jd/"result.json").read_text())["verdict"], "DRY-PASS")

    def test_arguments_environment_and_unknown_semantic_change_refuse(self):
        _, _, cfg, sp, live, kw, ref, _ = self.case()
        for changes in ({"gen_args":["--other"]}, {"gen_env":{"OT_FORM":"B"}}, {"new_semantic_input":"x"}):
            altered = dict(live, **changes)
            self.assertEqual(P.validate_reference(ref,cfg,"kv","hg_v1",kw,altered)[0], "")

    def test_current_applied_identity_is_required(self):
        _, _, cfg, sp, live, kw, ref, _ = self.case()
        for key,value in (("src","/other"), ("src_manifest_hash","b"*64), ("plan_sha256","c"*64)):
            changed=copy.deepcopy(cfg); changed["dies"]["kv"][key]=value
            self.assertEqual(P.validate_reference(ref,changed,"kv","hg_v1",kw,live)[0], "")
        self.assertEqual(P.validate_reference(ref,cfg,"kv","other_item",kw,live)[0], "")

    def test_fresh_plan_bind_tool_and_recipe_content_are_required(self):
        for target in ("plan", "native", "tool", "recipe"):
            _, _, cfg, sp, live, kw, ref, _ = self.case()
            if target=="plan": Path(sp["plan"]).write_text("changed")
            if target=="native": (Path(sp["kit_rtl"]["bind_out"])/"native_topology.json").write_text("changed")
            if target=="tool": (Path(kw.__file__).parents[2]/"tools/die_plan/gen.py").write_text("changed")
            if target=="recipe": kw.run_item=changed_recipe
            self.assertEqual(P.validate_reference(ref,cfg,"kv","hg_v1",kw,live)[0], "",target)

    def test_original_spec_result_log_and_publish_record_are_immutable(self):
        for name in ("spec.json","result.json","unit.log","publish"):
            _, jd, cfg, sp, live, kw, ref, record = self.case()
            path = record if name=="publish" else jd/name
            path.write_bytes(path.read_bytes()+b" ")
            self.assertEqual(P.validate_reference(ref,cfg,"kv","hg_v1",kw,live)[0], "",name)

    def test_advisory_or_failed_incomplete_stage_never_imports(self):
        _, _, cfg, sp, live, kw, ref, _ = self.case(advisory=True)
        self.assertEqual(P.validate_reference(ref,cfg,"kv","hg_v1",kw,live)[0], "")
        for text in ("KW_STAGE_RC gen 0\n", "KW_STAGE_RC gen 0\nKW_STAGE_RC gen_kit 0\nKW_STAGE_RC gen_lint 0\nKW_STAGE_RC preflight 2\n"):
            _, jd, cfg, sp, live, kw, ref, record = self.case()
            (jd/"unit.log").write_text(text)
            self.assertIn("published_gen_import_declined", P.seal(jd,0))

    def test_relocated_bind_paths_require_same_actual_bytes(self):
        root, _, cfg, sp, live, kw, ref, _ = self.case()
        moved=root/"moved"; moved.mkdir()
        old=Path(sp["kit_rtl"]["bind_out"])/"native_topology.json"
        (moved/"native_topology.json").write_bytes(old.read_bytes())
        ab=root/"moved_ab.json"; ab.write_bytes(Path(sp["kit_rtl"]["asbuilt"]).read_bytes())
        live["kit_rtl"]=dict(live["kit_rtl"], bind_out=str(moved), asbuilt=str(ab))
        self.assertEqual(P.validate_reference(ref,cfg,"kv","hg_v1",kw,live)[0],"a"*64)

    def test_legacy_capture_requires_explicit_existing_archive_binding(self):
        from unittest.mock import patch
        root,jd,cfg,sp,live,kw,ref,_ = self.case(legacy=True)
        self.assertEqual(P.validate_reference(ref,cfg,"kv","hg_v1",kw,live)[0],"")
        module = root/"tools/autopilot/kit_wave.py"
        digest = P.sha(module.read_bytes())
        ref["recipe_archive"] = dict(commit=P.ARCHIVE_COMMIT,root=str(root),module_sha256=digest,
                                    external_helpers=P.external_helpers(module.parent))
        with patch.object(P,"REVIEWED_RECIPE_FILES",{digest}):
            self.assertEqual(P.validate_reference(ref,cfg,"kv","hg_v1",kw,live)[0],"a"*64)
            (module.parent/"kit_store.py").write_text("changed helper")
            self.assertEqual(P.validate_reference(ref,cfg,"kv","hg_v1",kw,live)[0],"")

    def test_missing_recipe_capture_declines_and_keeps_normal_gen(self):
        _, jd, cfg, sp, live, kw, ref, _ = self.case()
        (jd/"published_gen_origin.json").unlink()
        self.assertEqual(P.validate_reference(ref,cfg,"kv","hg_v1",kw,live)[0], "")
