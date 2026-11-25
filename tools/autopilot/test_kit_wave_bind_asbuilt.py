"""FLOW-STRIPBODY-R2 11-22: a private --bind-out carries the as-built manifest that bind read (kit_wave.bind_asbuilt)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def test_bind_asbuilt_reads_the_bind_provenance_manifest(tmp_path):
    src, bo = tmp_path / "tree", tmp_path / "bind"
    (src / "p").mkdir(parents=True)
    bo.mkdir()
    (src / "p" / "asbuilt_vN.json").write_text("{}")
    (bo / "provenance_bind.json").write_text(json.dumps(dict(provenance=dict(manifest="p/asbuilt_vN.json"))))
    assert KW.bind_asbuilt(bo, src) == str(src / "p" / "asbuilt_vN.json")
    assert KW.bind_asbuilt(bo, None) is None                     # relative manifest, no tree: unknown
    assert KW.bind_asbuilt(tmp_path / "none", src) is None       # no provenance: keep the spec's asbuilt
    (bo / "provenance_bind.json").write_text(json.dumps(dict(provenance=dict(manifest="p/missing.json"))))
    assert KW.bind_asbuilt(bo, src) is None


def test_private_spec_does_not_shadow_the_ab_list():
    # efe70f16d3 named the manifest `ab` inside private_spec and the --ab loop then iterated its characters ("--ab '/'")
    import inspect
    src = inspect.getsource(KW.private_spec)
    assert "\n            ab = " not in src and "\n        ab = " not in src


def test_asbuilt_clock_landing_names_the_split_sidecar(tmp_path):
    src = tmp_path / "tree"
    (src / "p").mkdir(parents=True)
    (src / "p" / "eW_sidecar.json").write_text("{}")
    ab = src / "p" / "asbuilt_vN.json"
    ab.write_text(json.dumps(dict(clock_landing_table="p/eW_sidecar.json")))
    assert KW.asbuilt_clock_landing(ab, src) == str(src / "p" / "eW_sidecar.json")
    ab.write_text(json.dumps(dict()))
    assert KW.asbuilt_clock_landing(ab, src) is None
    assert KW.asbuilt_clock_landing(tmp_path / "none.json", src) is None


def test_bind_asbuilt_resolves_by_sha_when_a_stale_tree_sits_at_the_recorded_path(tmp_path):
    """FLOW-0930 F-05: the bind records the as-built at an absolute path; on another host an old tree sits there with other content"""
    import hashlib
    stale = tmp_path / "C1L" / "tree" / "physical" / "ab.json"
    stale.parent.mkdir(parents=True)
    stale.write_text('{"old": 1}')
    src = tmp_path / "launch" / "physical"
    src.mkdir(parents=True)
    good = src / "sub" / "ab.json"
    good.parent.mkdir()
    good.write_text('{"new": 1}')
    bo = tmp_path / "bind"
    bo.mkdir()
    (bo / "provenance_bind.json").write_text(json.dumps(dict(provenance=dict(manifest=str(stale)))))
    (bo / "native_topology.json").write_text(json.dumps(dict(asbuilt_sha256=hashlib.sha256(good.read_bytes()).hexdigest())))
    assert KW.bind_asbuilt(bo, tmp_path / "launch") == str(good)          # not the stale file at the recorded path
    (bo / "native_topology.json").write_text(json.dumps(dict(asbuilt_sha256="0" * 64)))
    assert KW.bind_asbuilt(bo, tmp_path / "launch") is None               # nothing matches the bind sha
    (bo / "native_topology.json").write_text(json.dumps(dict(asbuilt_sha256=hashlib.sha256(stale.read_bytes()).hexdigest())))
    assert KW.bind_asbuilt(bo, tmp_path / "launch") == str(stale)         # the file at the path IS the bind's: kept
