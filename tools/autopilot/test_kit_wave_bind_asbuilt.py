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
