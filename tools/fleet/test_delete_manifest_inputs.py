"""FLOW-OPS-1000: the small generated inputs of a deleted tree are packed beside its manifest (FABLE-FLOW-1000 h, ring_declared.json)"""
import gzip
import json
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delete_manifest as DM  # noqa: E402


def test_inputs_packed_outputs_not(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_DELETE_MANIFEST_DIR", str(tmp_path / "m"))
    t = tmp_path / "fable-pd-head-clk"; (t / "ca2").mkdir(parents=True)
    (t / "ca2" / "ring_declared.json").write_text('{"ring": 1}')
    (t / "run.sh").write_text("echo")
    (t / "6_final.odb").write_bytes(b"x" * 100)
    (t / "5_2_route.log").write_text("log")
    m = DM.write(str(t), "ot-auto-retire")
    end = [json.loads(ln) for ln in gzip.open(m, "rt")][-1]
    assert end["inputs_n"] == 2 and end["inputs_tar"].endswith(".inputs.tar.gz")
    names = set(tarfile.open(end["inputs_tar"]).getnames())
    assert names == {"ca2/ring_declared.json", "run.sh"}
