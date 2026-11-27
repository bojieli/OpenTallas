from hashlib import sha256
import json
from pathlib import Path
import subprocess

import pytest

import kit_resume
import kit_wave as wave
import plan_visual_review as review
import publish_gate as gate
import published_place_ready as ready
from test_kit_wave import cfg

MANIFEST = "a" * 64
PLAN = "b" * 64


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(value).encode()
    path.write_bytes(blob)
    return sha256(blob).hexdigest()


def producer_fixture(tmp_path):
    work = tmp_path / "future_event/items/part__t1/prepared_01"
    item = "part__t1"
    kit = work / "gen" / item
    (kit / "rtl").mkdir(parents=True)
    (kit / "rtl/exact.v").write_text("module exact; endmodule\n")
    (kit / "config.mk").write_text("export VERILOG_FILES = /work/rtl/exact.v\n")
    (work / "gen/run_kit.sh").write_text("#!/bin/bash\n")
    kit_resume.write_inputs(str(kit))
    preflight = work / "preflight.100.json"
    put(preflight, {"kit":str(kit), "verdict":"PASS"})
    spec = {"die":"s81","kind":"type","item":item,"event":"future_event","hub":"localhost","gen_host":"epyc7",
            "work":str(work),"root":str(work.parent),"src":"/sealed/tree","src_manifest_hash":MANIFEST,
            "plan":"/sealed/tree/plan.json","tools_sha":"e" * 40,"tools_rt":"/immutable/rt/e",
            "kit_rtl":{"mode":"bind","bind_out":"/sealed/native-bind"},"gen_env":{"OT_EXACT":"1"},
            "future_lec":{"proof_source":"recipe"},"dry_gen":True, "private":{"of":"s81/" + item},
            "goal":"place", "publish_place_prepare":{"plan_sha256":PLAN}}
    form = review.request(spec, plan_sha=PLAN)["form_sha256"]
    result = {"evidence":f"epyc7:{kit}","stage":"preflight","verdict":"DRY-PASS","src_manifest":
              {"manifest_hash":MANIFEST,"tree":spec["src"],"tree_read_only":True,"host":"epyc7"}}
    payload = {"spec":spec,"result":result,"stages":dict.fromkeys(ready.REQUIRED,0),"form":form,"plan":PLAN,
               "preflight":str(preflight)}
    return kit, spec, result, payload


def test_exact_publisher_and_private_consumer_share_one_native_work_path(tmp_path):
    kit,spec,result,capture = producer_fixture(tmp_path)
    actual = subprocess.run(["bash", "-c", ready.producer_command("capture", capture)], text=True, capture_output=True, check=True)
    assert actual.stdout.startswith(ready.PREFIX)
    ref = json.loads(actual.stdout.removeprefix(ready.PREFIX))
    origin = tmp_path / "publication/dry"
    original = origin / "spec.json"
    spec_sha = put(original,spec)
    result_sha = put(origin/"result.json",dict(result,published_place_ready=ref))
    cfg = {"src":spec["src"],"plan":spec["plan"],"event":spec["event"],"src_manifest_hash":MANIFEST,
           "plan_sha256":PLAN,"gen_hosts":["epyc7"]}
    coord = tmp_path/"coord"
    record = coord/"autopilot/publish_gate/s81"/(MANIFEST+".json")
    put(record,{"schema":"opentallas.publish_gate.v1","verdict":"PASS","die":"s81","item":spec["item"],
                "tree":spec["src"],"plan":spec["plan"],"manifest_hash":MANIFEST,"plan_sha256":PLAN,
                "checks":{**dict.fromkeys(("schema","pre_g0","hashes","contained"),{"verdict":"PASS"}),
                          "dry_gen":{"verdict":"PASS","proof_kind":"published-gen","dir":str(origin),
                                     "spec_sha256":spec_sha,"result_sha256":result_sha,"gen_host":"epyc7",
                                     "published_place_ready":ref}}})
    raw, proof = ready.read_publication(coord, original, record, cfg)
    assert raw == original.read_bytes()
    with pytest.raises(ValueError,match="committed adopted"):
        ready.read_publication(coord, original, record, dict(cfg,event="old"))
    claim = dict(proof,spec=spec,review={"verdict":"GOOD","form":capture["form"]},attempt="one-controller")
    with pytest.raises(ValueError,match="review"):
        ready.producer("claim",dict(claim,review=dict(claim["review"],verdict="BAD")))
    assert ready.producer("claim",claim)["kit"] == str(kit)
    assert ready.producer("claim",claim)["kit"] == str(kit)
    with pytest.raises(ValueError,match="already claimed"):
        ready.producer("claim",dict(claim,attempt="duplicate"))
    with pytest.raises(ValueError,match="recipe"):
        ready.producer("claim",dict(claim,spec=dict(spec,future_lec={"proof_source":"new"})))
    (kit/"rtl/exact.v").write_text("module exact; endmodule\n")
    with pytest.raises(ValueError,match="prepared input changed"):
        ready.producer("claim",claim)


@pytest.mark.parametrize("macro_geometry", ["PASS", "FINDINGS"])
def test_private_place_uses_the_existing_prepared_receipt(tmp_path, macro_geometry):
    kit, spec, result, payload = producer_fixture(tmp_path)
    spec.update(src_manifest="require", launch_plan_review_required=True, place_spill=False,
                roam_hosts=["epyc7"], place_spill_hosts=["epyc7"], hosts=["epyc7"],
                reviewed_station_prepare={"path": "/exact/recipe", "sha256": "c" * 64})
    payload["form"] = review.request(spec, plan_sha=PLAN)["form_sha256"]
    put(Path(payload["preflight"]), {"kit": str(kit), "verdict": "PASS",
                                    "macro_geometry": {"verdict": macro_geometry}})
    ref = ready.producer("capture", payload)
    original = tmp_path / "dry" / "spec.json"
    put(original, spec)
    source = {"host": "epyc7", "manifest_hash": MANIFEST, "from": "verify", "mode": "require"}
    dry_result = dict(result, src_manifest=source, published_place_ready=ref)
    result_path = original.parent / "result.json"
    put(result_path, dict(dry_result, src_manifest=dict(source, **{"from": "peek"})))
    with pytest.raises(ValueError, match="private dry preparation"):
        ready.read_private_prepared(original)
    put(result_path, dry_result)
    raw, verified = ready.read_private_prepared(original)
    assert raw == original.read_bytes()
    assert verified == {"ref": ref, "private_prepared": {"manifest": MANIFEST, "plan": PLAN}}
    claim = dict(spec=spec, ref=ref, review={"verdict": "GOOD", "form": payload["form"]}, attempt="one-controller")
    with pytest.raises(ValueError, match="review"):
        ready.producer("claim-private", dict(claim, review=dict(claim["review"], verdict="BAD")))
    with pytest.raises(ValueError, match="private place producer"):
        ready.producer("claim-private", dict(claim, spec=dict(spec, goal="grt")))
    if macro_geometry == "FINDINGS":
        with pytest.raises(ValueError, match="macro geometry"):
            ready.producer("claim-private", claim)
        return
    assert ready.producer("claim-private", claim)["kit"] == str(kit)
    assert ready.producer("claim-private", claim)["kit"] == str(kit)
    with pytest.raises(ValueError, match="already claimed"):
        ready.producer("claim-private", dict(claim, attempt="duplicate"))
    with pytest.raises(ValueError, match="recipe"):
        ready.producer("claim-private", dict(claim, spec=dict(spec, gen_env={"OT_CHANGED": "1"})))


def test_opted_in_publisher_freezes_real_event_and_distinct_work(tmp_path, monkeypatch):
    die,item,host = "qwen_kvsys","kv3_pc","epyc7"
    raw = cfg()
    raw["dies"][die].update(event="future_event",plan_sha256=PLAN)
    monkeypatch.setattr(wave,"load_config",lambda _text:raw)
    monkeypatch.setattr(wave,"spec_for",lambda *a,**k:{"work":str(tmp_path/"future_event/items"/item)})
    def private_spec(cfg, die, item, hub, **kw):
        assert cfg["dies"][die]["event"] == "future_event" and kw["goal"] == "place" and kw["host"] == host
        return {"event":cfg["dies"][die]["event"],"kind":"type","die":die,"item":item,"src":"/sealed",
                "src_manifest":"True","src_manifest_hash":MANIFEST,"work":kw["work"],"goal":"place"}
    monkeypatch.setattr(wave,"private_spec",private_spec)
    args=("{}",die,item,"type",str(tmp_path/"publication"),"localhost",host)
    a=gate.dry_gen(*args,run_unit=False,want=MANIFEST,prepare_place=True)
    b=gate.dry_gen(*args,run_unit=False,want=MANIFEST,prepare_place=True)
    first, second = [json.loads((Path(x["dir"])/"spec.json").read_text()) for x in (a,b)]
    assert a["dir"] != b["dir"] and first["work"] != second["work"]
    assert first["event"] == second["event"] == "future_event"
    assert first["dry_gen"] and first["launch_plan_review_required"]
    assert first["src_manifest"] == second["src_manifest"] == "require"
    assert first["publish_place_prepare"]["plan_sha256"] == PLAN


@pytest.mark.parametrize("route_ok", [False, True])
@pytest.mark.parametrize("private_mode", [False, True])
def test_prepared_pipeline_calls_route_preflight_after_claim_without_regeneration(tmp_path, monkeypatch, route_ok, private_mode):
    raw = cfg()
    die,item = "qwen_kvsys","kv3_pc"
    spec = wave.spec_for(raw,die,item,"localhost",kind="type")
    spec.update(work=str(tmp_path/"future_event/items/kv3_pc/prepared"),
                private={"of":"qwen_kvsys/kv3_pc"},dry_gen=True,goal="place",
                launch_plan_review_required=True,gen_host="epyc7",src_manifest_hash=MANIFEST,
                start_delay_s=0,hosts=["epyc7"],roam_hosts=[],place_async=False,kit_self_contained="off")
    folder = tmp_path/"consumer"
    spec_path = folder/"spec.json"
    put(spec_path,spec)
    for name in ("bind_plan_refusal","private_lbl_refusal","private_plan_visual_policy","private_spec_stale"):
        monkeypatch.setattr(wave,name,lambda *a,**k:"")
    monkeypatch.setattr(wave,"repick_stage_hosts",lambda sp:sp)
    def early_reuse_forbidden(*args):
        raise AssertionError("an exact publication-prepared kit never re-enters the KIT_RTL boundary")
    monkeypatch.setattr(wave.KRR, "configured", early_reuse_forbidden)
    called=[]
    def check_review(*a,**k):
        called.append("visual")
        assert k["plan_shas"] == {("epyc7",spec["plan"]):PLAN}
        return ""
    monkeypatch.setattr(wave,"plan_visual_refusal",check_review)
    def claim_command(operation, payload):
        assert operation == ("claim-private" if private_mode else "claim")
        assert ("publication" in payload) is not private_mode
        return "prepared_claim_only"
    monkeypatch.setattr(ready,"producer_command",claim_command)
    monkeypatch.setattr(wave,"route_preflight_on",lambda:True)
    monkeypatch.setattr(wave,"route_preflight_cmd",lambda *a,**k:"real_route_preflight")
    monkeypatch.setattr(wave,"src_skew_check",lambda *a:"")
    monkeypatch.setattr(wave,"resume_prepare",lambda *a:"")
    class EnteredPlace(Exception):
        pass
    def fake_run(argv,**kw):
        argv = " ".join(argv)
        if "prepared_claim_only" in argv:
            called.append("claim")
            return subprocess.CompletedProcess(argv,0,stdout="")
        if "real_route_preflight" in argv:
            called.append("route_preflight")
            return subprocess.CompletedProcess(argv,0 if route_ok else 2,stdout="synthetic route preflight outcome")
        if "rsync -a --delete" in argv and "epyc7:" in argv:
            called.append("sync_hub")
            return subprocess.CompletedProcess(argv,0,stdout="")
        if "env_provenance.py" in argv:
            return subprocess.CompletedProcess(argv,0,stdout="")
        if "run_kit.sh" in argv and " place " in argv:
            called.append("ordinary_place")
            raise EnteredPlace()
        raise AssertionError(f"unexpected stage {argv[:180]}")
    monkeypatch.setattr(wave.subprocess,"run",fake_run)
    authority = {"manifest": MANIFEST, "plan": PLAN}
    if not private_mode:
        authority["verdict"] = "PASS"
    proof = {"private_prepared" if private_mode else "publication": authority, "ref": {"sha256": "c" * 64}}
    if route_ok:
        with pytest.raises(EnteredPlace):
            wave._run_item(spec_path,prepared=proof)
        assert called == ["visual","claim","route_preflight","sync_hub","ordinary_place"]
    else:
        assert wave._run_item(spec_path,prepared=proof) == 1
        assert called == ["visual","claim","route_preflight"]
        assert json.loads((folder/"result.json").read_text())["stage"] == "preflight"


def test_a_changed_prepared_kit_keeps_fresh_preparation_available(tmp_path):
    kit, spec, _, payload = producer_fixture(tmp_path)
    exact = ready.capture(spec, payload["result"], payload["stages"], payload["form"],
                          payload["plan"], payload["preflight"])
    (kit / "config.mk").write_text("export VERILOG_FILES = /work/rtl/changed.v\n")
    accepted = {"verdict": "PASS", "manifest": MANIFEST, "plan": PLAN}
    viewed = {"verdict": "GOOD", "form": payload["form"]}
    with pytest.raises(ValueError, match="prepared input changed"):
        ready.claim(exact, spec, accepted, viewed, "new-attempt")
    new_kit, new_spec, _, new_payload = producer_fixture(tmp_path / "fresh")
    current = ready.capture(new_spec, new_payload["result"], new_payload["stages"], new_payload["form"],
                            new_payload["plan"], new_payload["preflight"])
    assert current["work"] != exact["work"]
    assert wave.KRR.configured(spec, {"manifest_hash": MANIFEST}) is None
    assert ready.claim(current, new_spec, accepted, viewed, "fresh-attempt") == new_kit


def test_named_station_recipe_is_place_only_and_exact_in_plan_review(tmp_path, monkeypatch):
    _, spec, _, _ = producer_fixture(tmp_path)
    spec.update(src_manifest="require", launch_plan_review_required=True, place_spill=False,
                roam_hosts=["epyc7"], reviewed_station_prepare={"path": "/exact/recipe", "sha256": "c" * 64},
                gen_args=["--clock-landing", "/producer/old-landing.json"])
    spec["kit_rtl"]["asbuilt"] = "/exact/asbuilt"
    def checked(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0, "REVIEWED_STATION_PREPARE " + json.dumps(
            {"clock_landing": {"path": "/exact/physical-landing.json"}, "source_manifest_sha256": MANIFEST}))
    monkeypatch.setattr(wave.subprocess, "run", checked)
    recipe = wave.reviewed_station_prepare(spec)
    wave.set_reviewed_station_landing(spec, recipe)
    args = spec["gen_args"][:]
    wave.set_reviewed_station_landing(spec, recipe)
    assert args == spec["gen_args"]
    assert "/producer/old-landing.json" not in args and "/exact/physical-landing.json" in args
    form = review.request(spec, plan_sha=PLAN)
    changed = dict(spec, reviewed_station_prepare=dict(spec["reviewed_station_prepare"], sha256="d" * 64))
    assert review.request(changed, plan_sha=PLAN)["form_sha256"] != form["form_sha256"]
    for option in ({"goal": "route"}, {"dry_gen": False}, {"place_spill": True},
                   {"src_manifest": "off"}, {"type_overlay": "/unexpected/overlay"}):
        with pytest.raises(ValueError, match="same-host private place-only dry"):
            wave.reviewed_station_prepare(dict(spec, **option))
