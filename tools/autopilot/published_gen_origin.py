"""Read-only origin capture for an actual prepublication GEN; never grants credit."""
import hashlib, inspect, json, os, re
from pathlib import Path

def sha(data):
    return hashlib.sha256(data).hexdigest()

ARCHIVE_COMMIT = "00b48fe8d83bc70b1660bec8582f1ca91bf13b2b"
# Exact whole-file compatibility is filled from the reviewed imported-proof
# change; unknown scheduler versions always keep normal GEN as fallback.
REVIEWED_RECIPE_FILES = {'9cea75b21b9bbbbaed17207330350c7388e5fb6bff2e648f4aaa032be08f942d', '251744c0682fdfcd3f069c50ed72d119917fab31322211f7a02bf2a6824a7f8e', 'c9335d32f3663f45bc474cd26035b6ba589941c3eeb8e0b64e79e36481dc71cf'}
EXTERNAL_HELPERS = ("kit_store.py", "src_manifest.py", "prov_view.py", "kit_rtl_closure.py", "future_kit_lec.py")


def external_helpers(directory):
    directory = Path(directory)
    return {name: sha((directory / name).read_bytes()) for name in EXTERNAL_HELPERS
            if (directory / name).is_file()}


def recipe_file_equivalent(old, current):
    return bool(old) and (old == current or old in REVIEWED_RECIPE_FILES and current in REVIEWED_RECIPE_FILES)


def archive_identity(binding):
    """Explicit coordinator binding to the existing pre-launch frozen archive."""
    assert binding.get("commit") == ARCHIVE_COMMIT, "unapproved recipe archive"
    root = Path(binding["root"])
    module = root / "tools/autopilot/kit_wave.py"
    assert sha(module.read_bytes()) == binding["module_sha256"], "recipe archive module changed"
    assert binding["module_sha256"] in REVIEWED_RECIPE_FILES, "unknown archived scheduler file"
    helpers = external_helpers(module.parent)
    assert helpers and helpers == binding["external_helpers"], "recipe archive helpers changed"
    return binding["module_sha256"], helpers


def execution_inputs(cfg, die, sp, KW):
    root = Path(KW.__file__).resolve().parents[2]
    def read(rel):
        try: return (root / rel).read_text()
        except OSError: return None
    closure = KW.FG.closure_files(read)
    assert closure and set(KW.FG.ENTRY_FILES) <= set(closure), "generation tool closure incomplete"
    tools = {rel: sha((root / rel).read_bytes()) for rel in closure}
    for name in ("plan_block_identity", "kit_resume", "tool_skew", "wave_jobs",
                 "kit_wave_roam", "flow_guard", "repeat_stop"):
        module = getattr(KW, {"plan_block_identity":"BI", "kit_resume":"KR", "tool_skew":"TS",
                             "wave_jobs":"WJ", "kit_wave_roam":"ROAM", "flow_guard":"FG", "repeat_stop":"RS"}[name])
        tools["autopilot:" + name] = sha(Path(module.__file__).read_bytes())
    kr = sp.get("kit_rtl") or {}
    files = {"plan": KW.file_sha(cfg, die, sp["plan"], ttl=0)}
    if kr.get("mode") == "bind":
        files["asbuilt"] = KW.file_sha(cfg, die, kr["asbuilt"], ttl=0)
        files["native_topology"] = KW.file_sha(cfg, die, str(Path(kr["bind_out"]) / "native_topology.json"), ttl=0)
    assert all(files.values()), "generation input hash unavailable"
    files["declared_plan_sha256"] = cfg["dies"][die].get("plan_sha256")
    assert files["declared_plan_sha256"], "declared plan hash unavailable"
    recipe = inspect.getsource(KW.run_item)
    return files, tools, recipe


def capture(cfg, die, sp, jobdir, KW):
    jd = Path(jobdir)
    raw = (jd / "spec.json").read_bytes()
    assert json.loads(raw) == sp, "spec changed before origin capture"
    assert sp.get("dry_gen") is True and sp.get("die") == die
    files, tools, recipe = execution_inputs(cfg, die, sp, KW)
    rec = dict(schema="opentallas.published_gen_origin.v1", spec_sha256=sha(raw), die=die,
               item=sp["item"], src_manifest_hash=sp["src_manifest_hash"], source=sp["src"],
               input_hashes=files, tool_hashes=tools, recipe_sha256=sha(recipe.encode()),
               run_item_source=recipe, recipe_file=str(Path(KW.__file__).resolve()),
               recipe_file_sha256=sha(Path(KW.__file__).read_bytes()),
               external_helpers=external_helpers(Path(KW.__file__).resolve().parent))
    target = jd / "published_gen_origin.json"
    temp = jd / (target.name + ".%s.tmp" % os.getpid())
    temp.write_text(json.dumps(rec, sort_keys=True) + "\n")
    try:
        os.link(temp, target)
    except FileExistsError:
        assert json.loads(target.read_text()) == rec, "different origin already recorded; use a new jobdir"
    finally:
        temp.unlink(missing_ok=True)
    return {"origin": str(target), "origin_sha256": sha(target.read_bytes()),
            "spec_sha256": rec["spec_sha256"]}

REQUIRED_STAGES = ("gen", "gen_kit", "gen_lint", "preflight")


def _completed(raw_result, raw_log, rc):
    result = json.loads(raw_result)
    assert rc == 0 and result.get("verdict") == "DRY-PASS" and result.get("stage") == "preflight", "dry GEN did not finish"
    assert not result.get("preflight_fail_advisory"), "preflight error was downgraded to advisory"
    log = raw_log.decode()
    stages = {}
    for name, value in re.findall(r"^KW_STAGE_RC ([A-Za-z0-9_]+) (-?[0-9]+)\b", log, re.M):
        stages.setdefault(name, []).append(int(value))
    assert all(stages.get(name) and all(v == 0 for v in stages[name]) for name in REQUIRED_STAGES), "GEN/lint/preflight stage incomplete or failed"
    assert all(v == 0 for v in stages.get("kit_topology", [])), "topology stage failed"
    return result


def seal(jobdir, rc):
    """Pin the genuine terminal dry evidence; no live attempt/state is created."""
    jd = Path(jobdir)
    try:
        origin = json.loads((jd / "published_gen_origin.json").read_bytes())
        assert origin["spec_sha256"] == sha((jd / "spec.json").read_bytes()), "original spec changed"
        result, log = (jd / "result.json").read_bytes(), (jd / "unit.log").read_bytes()
        _completed(result, log, rc)
        return dict(origin=str(jd / "published_gen_origin.json"),
                    origin_sha256=sha((jd / "published_gen_origin.json").read_bytes()),
                    spec_sha256=origin["spec_sha256"], result_sha256=sha(result),
                    unit_log_sha256=sha(log), proof_kind="published-gen")
    except (AssertionError, OSError, KeyError, TypeError, ValueError) as e:
        return {"published_gen_import_declined": str(e)}

# Explicitly operational fields: they schedule/name a run, not its generated kit.
# src_overlay is the older partial tree digest; the required full immutable
# source manifest and actual tool/input hashes bind that same source here.
OPERATIONAL = {"dry_gen", "event", "root", "work", "hub", "gen_host", "hosts", "roam_hosts",
               "ot_run", "start_delay_s", "crit", "place_prefer", "place_spill", "place_threads",
               "place_mem_gb", "gen_mem_gb", "bind_mem_gb", "lint_mem_gb", "geom_mem_gb", "src_overlay"}


def semantic_spec(sp):
    out = {k: v for k, v in sp.items() if k not in OPERATIONAL}
    if isinstance(out.get("kit_rtl"), dict):
        kr = {k: v for k, v in out["kit_rtl"].items() if not k.startswith("note")}
        if kr.get("mode") == "bind":          # these two inputs are compared by their fresh content hashes
            kr.pop("asbuilt", None)
            kr.pop("bind_out", None)
        out["kit_rtl"] = kr
    return out


def validate_reference(ref, cfg, die, pilot, KW, live_spec=None):
    """Return the proved full manifest, or a refusal; never edits config/state."""
    try:
        assert ref.get("kind") == "published-gen", "wrong imported proof kind"
        record_path = Path(ref["record"])
        raw_record = record_path.read_bytes()
        assert sha(raw_record) == ref["record_sha256"], "publish record changed"
        rec = json.loads(raw_record)
        d = cfg["dies"][die]
        for key, value in (("schema", "opentallas.publish_gate.v1"), ("die", die),
                           ("tree", d["src"]), ("manifest_hash", d["src_manifest_hash"]),
                           ("plan_sha256", d["plan_sha256"]), ("item", pilot)):
            assert rec.get(key) == value, "applied " + key + " differs"
        checks = rec.get("checks") or {}
        assert rec.get("verdict") == "PASS" and all((checks.get(k) or {}).get("verdict") == "PASS"
               for k in ("schema", "pre_g0", "hashes", "contained", "dry_gen")), "publish checks incomplete"
        check = checks["dry_gen"]
        assert check.get("proof_kind") == "published-gen" and check.get("rc") == 0, "dry evidence not sealed"
        assert not check.get("preflight_fail_advisory"), "dry preflight was downgraded"
        jd = Path(check["dir"])
        raw_origin = (jd / "published_gen_origin.json").read_bytes()
        assert str(jd / "published_gen_origin.json") == check["origin"], "origin path differs"
        assert sha(raw_origin) == check["origin_sha256"], "origin changed"
        origin = json.loads(raw_origin)
        raw_spec = (jd / "spec.json").read_bytes()
        assert sha(raw_spec) == check["spec_sha256"] == origin["spec_sha256"], "original spec changed"
        old = json.loads(raw_spec)
        result, log = (jd / "result.json").read_bytes(), (jd / "unit.log").read_bytes()
        assert sha(result) == check["result_sha256"] and sha(log) == check["unit_log_sha256"], "terminal evidence changed"
        terminal = _completed(result, log, check["rc"])
        assert terminal.get("die") == die and terminal.get("item") == pilot, "terminal item differs"
        assert old.get("dry_gen") is True and old.get("die") == die and old.get("item") == pilot, "original dry item differs"
        assert old.get("src") == d["src"] and old.get("src_manifest_hash") == d["src_manifest_hash"], "original source differs"
        assert origin.get("schema") == "opentallas.published_gen_origin.v1", "wrong origin schema"
        assert origin.get("die") == die and origin.get("item") == pilot and origin.get("source") == d["src"], "origin identity differs"
        assert origin.get("src_manifest_hash") == d["src_manifest_hash"], "origin manifest differs"
        assert re.fullmatch(r"[0-9a-f]{64}", d["src_manifest_hash"]), "invalid manifest"
        if live_spec is None:
            import copy
            prospective = copy.deepcopy(cfg)
            prospective["_otrun_status"] = {}
            live_spec = KW.spec_for(prospective, die, pilot, cfg.get("_hub") or "localhost", kind=check.get("kind") or "type")
        assert semantic_spec(old) == semantic_spec(live_spec), "generation arguments/environment or semantic spec differs"
        files, tools, recipe = execution_inputs(cfg, die, live_spec, KW)
        assert files == origin["input_hashes"], "plan/asbuilt/bind content differs"
        assert tools == origin["tool_hashes"], "generation tool closure differs"
        assert sha(recipe.encode()) == origin["recipe_sha256"], "run-item recipe differs"
        if origin.get("recipe_file_sha256"):
            old_file = origin["recipe_file_sha256"]
            old_helpers = origin.get("external_helpers")
        else:
            old_file, old_helpers = archive_identity(ref.get("recipe_archive") or {})
        assert recipe_file_equivalent(old_file, sha(Path(KW.__file__).read_bytes())), "whole scheduler recipe differs"
        assert old_helpers and old_helpers == external_helpers(Path(KW.__file__).resolve().parent), "external generation helper differs"
        return d["src_manifest_hash"], ""
    except (AssertionError, OSError, KeyError, TypeError, ValueError, AttributeError) as e:
        return "", str(e)


def reference_for_apply(coord, cfg, die, pilot, KW, recipe_archive=None):
    """Use only the actual matching publish record; mismatch keeps normal GEN."""
    try:
        d = cfg["dies"][die]
        path = Path(coord) / "autopilot/publish_gate" / die / (d["src_manifest_hash"] + ".json")
        ref = dict(kind="published-gen", record=str(path), record_sha256=sha(path.read_bytes()))
        if recipe_archive is not None:
            ref["recipe_archive"] = recipe_archive
        proved, why = validate_reference(ref, cfg, die, pilot, KW)
        return (ref if proved else None), why
    except (OSError, KeyError, TypeError, ValueError) as e:
        return None, str(e)
