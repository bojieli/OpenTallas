import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Generator uses Python 3.12 f-string syntax elsewhere; exercise this isolated
# packaging helper on the coordinator's Python 3.10 too.
import types
import re
G = types.SimpleNamespace(TOOL=HERE.parents[2] / "tools/die_plan")
sys.path.insert(0, str(G.TOOL))
import lec
body = (HERE / "gen_core_kit_hbm.py").read_text().split("def stamp_generation_inputs(",1)[1].split("\ndef main(",1)[0]
ns = dict(Path=Path, REPO=HERE.parents[2], TOOL=G.TOOL, sys=sys, re=re, json=json)
exec("def stamp_generation_inputs(" + body, ns)
G.stamp_generation_inputs = ns["stamp_generation_inputs"]


def kit(tmp_path, profile=None):
    (tmp_path / "rtl").mkdir()
    for name, text in {"config.mk":"config", "lec.py":"tool", "rtl/a.sv":"module a; endmodule"}.items():
        (tmp_path / name).write_text(text)
    freeze = {"kit_hash":"abc"}
    if profile: freeze["source_profile"] = profile
    (tmp_path / "freeze.json").write_text(json.dumps(freeze))
    return tmp_path


def test_new_clean_generation_stamps_exact_inputs_and_detects_mutation(tmp_path, monkeypatch):
    sha = "a"*40
    monkeypatch.setattr(lec, "_repo_provenance", lambda repo: {"commit":sha,"dirty":False,"source":"git"})
    kd = kit(tmp_path, {"source_commit":sha,"source_hash":"b"*64})
    assert G.stamp_generation_inputs(kd)
    rec = json.loads((kd / "PROVENANCE.json").read_text())
    assert rec["provenance"]["commit"] == sha
    assert rec["files"] == lec._kit_input_identity(kd)
    (kd / "rtl/a.sv").write_text("changed")
    assert rec["files"] != lec._kit_input_identity(kd)


def test_dirty_or_different_profile_never_gets_current_attribution(tmp_path, monkeypatch):
    kd = kit(tmp_path, {"source_commit":"b"*40})
    for dirty in (False,True):
        monkeypatch.setattr(lec, "_repo_provenance", lambda repo: {"commit":"a"*40,"dirty":dirty})
        assert not G.stamp_generation_inputs(kd)
        assert not (kd / "PROVENANCE.json").exists()
        assert "source_commit" not in json.loads((kd / "freeze.json").read_text())
