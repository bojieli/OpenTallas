"""FLOW-FLEET-R1 11-22 (OWNER via COORD: make private family-plan kits count directly).  A private-spec kit on an ot-tree-fork tree is sealed at gen
(src_manifest.py seal: parent main sha + changed files as overlay, never written into the tree); after its sign-off + routed LEC the run-item chain
(or `kit_wave.py private-provenance` for a kit signed by hand) writes <work>/gen/PROVENANCE.json kind private, which release_tree_plan counts as a
versioned sign-off naming the private plan sha; auto_export names the unit by its wave item."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "fleet"))
import src_manifest as SM        # noqa: E402
import kit_wave as KW            # noqa: E402
import auto_export as AE         # noqa: E402


def _git(repo, *a):
    return subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t"] + list(a), check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """a published manifest tree (main sha + no overlay) and a writable fork of it (as ot-tree-fork leaves it: files + the parent manifest)"""
    monkeypatch.setattr(SM, "CACHE_DIR", str(tmp_path / "cache"))
    repo = tmp_path / "repo"
    (repo / "rtl").mkdir(parents=True)
    (repo / "physical").mkdir()
    _git(str(repo), "init", "-q")
    (repo / "rtl" / "a.sv").write_text("module a; endmodule\n")
    (repo / "rtl" / "b.sv").write_text("module b; endmodule\n")
    (repo / "physical" / "plan.json").write_text('{"p": 1}\n')
    _git(str(repo), "add", "rtl", "physical")
    _git(str(repo), "commit", "-qm", "m")
    sha = _git(str(repo), "rev-parse", "HEAD")
    pub = tmp_path / "pub"
    m = SM.build(str(repo), sha, None, ["rtl", "physical"], str(pub), main_ref="")
    fork = tmp_path / "fork"
    shutil.copytree(pub, fork)
    for dp, dn, fn in os.walk(fork):
        os.chmod(dp, 0o755)
        for f in fn:
            os.chmod(os.path.join(dp, f), 0o644)
    yield {"repo": repo, "sha": sha, "pub": pub, "fork": fork, "m": m}
    for dp, dn, fn in os.walk(tmp_path):
        os.chmod(dp, 0o755)


def test_seal_unchanged_fork_is_its_parent(tree):
    rec, why = SM.seal(str(tree["fork"]))
    assert not why and rec["unchanged"] and rec["manifest_hash"] == tree["m"]["manifest_hash"] and rec["main_sha"] == tree["sha"]


def test_seal_edited_fork_names_every_change_and_never_writes_the_tree(tree, tmp_path):
    f = tree["fork"]
    (f / "rtl" / "a.sv").write_text("module a; wire x; endmodule\n")
    (f / "physical" / "plan_fam.json").write_text('{"p": 2}\n')
    os.unlink(f / "rtl" / "b.sv")
    before = sorted(os.listdir(f))
    man0 = (f / SM.MANIFEST).read_bytes()
    out = tmp_path / "w" / "logs" / KW.SEAL_NAME
    rec, why = SM.seal(str(f), str(out))
    assert not why and not rec["unchanged"]
    assert sorted(os.listdir(f)) == before and (f / SM.MANIFEST).read_bytes() == man0      # the tree is never written
    assert set(rec["overlay"]) == {"rtl/a.sv", "physical/plan_fam.json"} and rec["deleted_vs_parent"] == ["rtl/b.sv"]
    assert rec["main_sha"] == tree["sha"] and rec["parent_manifest_hash"] == tree["m"]["manifest_hash"]
    import gzip
    full = json.loads(gzip.open(out).read())
    assert SM.manifest_hash(full) == rec["manifest_hash"] == full["manifest_hash"] != tree["m"]["manifest_hash"]
    assert full["files"]["rtl/a.sv"] == SM.sha256_file(str(f / "rtl" / "a.sv")) and "rtl/b.sv" not in full["files"]
    rec2, _ = SM.seal(str(f))                            # stat cache: same answer
    assert rec2["manifest_hash"] == rec["manifest_hash"]


def test_seal_refuses_a_tree_without_parent_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(SM, "CACHE_DIR", str(tmp_path / "cache"))
    (tmp_path / "t").mkdir()
    (tmp_path / "t" / "x").write_text("x")
    rec, why = SM.seal(str(tmp_path / "t"))
    assert rec is None and "SEAL-REFUSED" in why and "ot-tree-fork" in why


def test_seal_cli_line_is_what_run_item_reads(tree):
    p = subprocess.run([sys.executable, "-I", str(HERE / "src_manifest.py"), "seal", str(tree["fork"])], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    r = KW.seal_record(p.stdout)
    assert r["manifest_hash"] == tree["m"]["manifest_hash"] and r["main_sha"] == tree["sha"]
    assert KW.seal_record("SRC_MANIFEST OK " + "a" * 64 + " main 0123456789ab files 3")["main_sha"] == "0123456789ab"


def test_seal_mode_cmd_and_verdict():
    sp = {"src": "/srv/x/fork", "src_manifest": "seal", "work": "/srv/w/private/L/it_1122000000"}
    cmd = KW.src_manifest_cmd(sp)
    assert " seal /srv/x/fork --out /srv/w/private/L/it_1122000000/logs/" + KW.SEAL_NAME in cmd and not cmd.endswith("--ro")
    why, note = KW.src_manifest_verdict(sp, 1, "SRC_MANIFEST SEAL-REFUSED /srv/x/fork: no parent")
    assert why == "" and "SIGNED-UNVERSIONED" in note                       # the kit still builds; it just cannot count
    assert KW.src_manifest_verdict(sp, 0, 'SRC_MANIFEST_SEAL {"manifest_hash": "h", "main_sha": "s"}') == ("", "")


def test_private_spec_seals_a_private_tree_by_default(tmp_path, monkeypatch):
    from test_private_spec_env_provenance import wave_cfg, D, I
    monkeypatch.setattr(KW, "plan_names", lambda AP, st, d: {"flags": {}, "deps": {}})
    c = wave_cfg()
    sp = KW.private_spec(c, D, I, "intel2", tree=str(tmp_path / "tree"), lane="FAM-X")
    assert sp["src_manifest"] == "seal" and sp["src_manifest_hash"] == ""
    assert KW.private_spec(c, D, I, "intel2", tree=str(tmp_path / "tree"), src_manifest="off")["src_manifest"] == "off"
    assert KW.private_spec(c, D, I, "intel2", src_manifest="on")["src_manifest"] == "require"
    assert KW.private_spec(c, D, I, "intel2")["src_manifest"] != "seal"      # no private tree: the wave's own check


def _kit(tmp_path, lec_verdict="EQUIVALENT", lec_newer=True):
    W = tmp_path / "kw" / "runs" / "s81" / "kit-wave" / "s81" / "ev1" / "private" / "FAM-X" / "slice_t36_1122010203"
    K = W / "gen" / "slice_t36"
    base = K / "run" / "results" / "asap7" / "dp_slice_t36" / "base"
    base.mkdir(parents=True)
    (K / "config.mk").write_text("export DESIGN_NAME = dp_slice_t36\n")
    (base / "6_final.v").write_text("module dp; endmodule\n")
    (K / "signoff").mkdir()
    (K / "signoff" / "signoff.json").write_text(json.dumps({"verdict": "SIGNED", "profile": "minimal", "name": "dp_slice_t36", "inputs": {"base": str(base)}}))
    (K / "PROVENANCE.json").write_text(json.dumps({"schema": "opentallas.kit_provenance.v1", "kit": str(K)}))   # the kit's own build record
    lec = K / "lec_routed_autopilot_1" / "lec.json"
    lec.parent.mkdir()
    lec.write_text(json.dumps({"verdict": lec_verdict, "superset_vec": {"all_shown": True}}))
    if not lec_newer:
        os.utime(lec, (time.time() - 3600, time.time() - 3600))
    plan = tmp_path / "fork" / "physical" / "plan_fam.json"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text('{"fam": 1}\n')
    sp = {"die": "s81", "item": "slice_t36", "hub": "hubx", "gen_host": "hubx", "work": str(W), "src": str(tmp_path / "fork"), "plan": str(plan),
          "private": {"lane": "FAM-X", "of": "s81/slice_t36", "wave_plan": "/srv/wave/plan.json", "tree_fork": {"src": "/srv/kw45/snap", "dst": str(tmp_path / "fork")}}}
    return sp, K


SEAL = {"manifest_hash": "c" * 64, "main_sha": "d" * 40, "parent_manifest_hash": "e" * 64, "overlay_n": 1, "overlay": {"physical/plan_fam.json": "f" * 64}}
TAG = (lambda die, sha: {"src_commit": sha, "flow_tag": "flow-20261121-a-s81"})


def _counter_prov(signoff):
    import release_tree_plan as RTP
    return RTP._PROV_NS["prov"](str(signoff), json.loads(Path(signoff).read_text()), lambda f: json.load(open(f)))


def test_private_signoff_counts_end_to_end(tmp_path):
    sp, K = _kit(tmp_path)
    r = KW.private_provenance(sp, "hubx", str(K), str(K / "signoff" / "signoff.json"), SEAL, chain={}, resolve=TAG)
    assert r["verdict"] == "SIGNED" and r["flow_tag"] == "flow-20261121-a-s81" and r["src_commit"] == "d" * 40
    doc = json.loads((Path(sp["work"]) / "gen" / "PROVENANCE.json").read_text())
    import hashlib
    assert doc["kind"] == "private" and doc["private"]["plan_sha256"] == hashlib.sha256(Path(sp["plan"]).read_bytes()).hexdigest()
    assert doc["private"]["src_manifest_hash"] == "c" * 64 and doc["lec"]["ok"]
    got = _counter_prov(K / "signoff" / "signoff.json")    # the counter skips the kit's kit_provenance.v1 record and finds the private one
    assert got["src_commit"] == "d" * 40 and got["flow_tag"] == "flow-20261121-a-s81" and got["private_plan_sha"] == doc["private"]["plan_sha256"]


@pytest.mark.parametrize("seal,lec,tag,why", [
    ({}, "EQUIVALENT", TAG, "no src manifest seal"),
    (SEAL, "NOT_EQUIVALENT", TAG, "no routed LEC"),
    (SEAL, "EQUIVALENT", (lambda d, s: {"src_commit": s, "flow_tag": "", "error": "no flow release tag carries this commit's flow"}), "flow tag"),
])
def test_private_signoff_without_provenance_never_counts(tmp_path, seal, lec, tag, why):
    sp, K = _kit(tmp_path, lec_verdict=lec)
    r = KW.private_provenance(sp, "hubx", str(K), str(K / "signoff" / "signoff.json"), seal, chain={}, resolve=tag)
    assert r["verdict"] == "SIGNED-UNVERSIONED" and why in r["why"] and r["src_commit"] == ""
    assert _counter_prov(K / "signoff" / "signoff.json") == {}


def test_stale_lec_is_not_the_routed_proof(tmp_path):
    sp, K = _kit(tmp_path, lec_newer=False)
    r = KW.private_provenance(sp, "hubx", str(K), str(K / "signoff" / "signoff.json"), SEAL, chain={}, resolve=TAG)
    assert r["verdict"] == "SIGNED-UNVERSIONED" and "routed LEC" in r["why"]


def test_provisional_marker_is_kept(tmp_path):
    sp, K = _kit(tmp_path)
    p = Path(sp["work"]) / "gen" / "PROVENANCE.json"
    p.write_text(json.dumps({"verdict": "PROVISIONAL"}))
    r = KW.private_provenance(sp, "hubx", str(K), str(K / "signoff" / "signoff.json"), SEAL, chain={}, resolve=TAG)
    assert r["verdict"].startswith("KEPT") and json.loads(p.read_text())["verdict"] == "PROVISIONAL"


def test_export_names_a_private_kit_by_its_wave_item():
    u = {"signoff": "/srv/s/claude/kw43/runs/s81/kit-wave/s81/dc92652f0d5/private/FAM-S81-SLICE-R4/slice_station__t36_1121074053/gen/slice_station__t36/signoff/signoff.json",
         "top": "s81p_slice_station__t36", "name": "dp_slice_station__t36"}
    die, el, kind, how = AE.infer(u, [])
    assert (die, el, how) == ("s81", "slice_station__t36", "wave path")
