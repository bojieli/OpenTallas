"""PIN-DOC-1124: --hosts is a placement preference (a disk-ETA ETA-STAGE may move it); OT_RUN_NO_SPILL=1 / --no-spill make it hard."""
import importlib.machinery, importlib.util, pathlib
l = importlib.machinery.SourceFileLoader("ot_run_pin_doc", str(pathlib.Path(__file__).with_name("ot-run")))
m = importlib.util.module_from_spec(importlib.util.spec_from_loader(l.name, l)); l.exec_module(m)


def test_eta_stage_gate(monkeypatch):
    monkeypatch.setattr(m, "ETA_STAGE_AFTER_S", 600)
    assert m.eta_stage_allowed(False, {})
    assert not m.eta_stage_allowed(False, {"OT_RUN_NO_SPILL": "1"})
    assert not m.eta_stage_allowed(True, {})
    monkeypatch.setattr(m, "ETA_STAGE_AFTER_S", -1)
    assert not m.eta_stage_allowed(False, {})


def test_doc_says_preference_and_how_to_make_it_hard():
    src = pathlib.Path(m.__file__).read_text()
    assert "--hosts IS A PLACEMENT PREFERENCE, NOT A HARD PIN" in src and "sets OT_RUN_NO_SPILL=1" in src
