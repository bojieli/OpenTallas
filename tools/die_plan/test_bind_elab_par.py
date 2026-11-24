"""BIND-ELAB-PAR 11-23: the per-type define-variant elabs of `bind.py elab` (type_define_effect.elab_pass) run in a
bounded pool alongside the base elab; the emitted elab directory must be byte-identical to the serial run, and the
opt-in content-hash cache (OT_BIND_ELAB_CACHE) must hit on an unchanged rerun and give identical files."""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import type_define_effect as TDE  # noqa: E402

EX = HERE / "examples" / "bind_tiny"
HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))
needs_yosys = pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")
# Yosys run logs carry timings; provenance carries a time stamp: neither is an elab result
VOLATILE = {"asbuilt.yosys.log", "provenance_elab.json"}


def _tree(tmp_path):
    src = tmp_path / "src"
    shutil.copytree(EX, src)
    par = (src / "par.sv").read_text()
    old = "    lf_a #(.ID(K)) u_a (.clk(ck), .rst_n(rst_n), .i(x), .o(a_o));\n    lf_b u_b"
    new = ("`ifdef OT_TDX\n    localparam integer DX = 8;\n`else\n    localparam integer DX = 0;\n`endif\n"
           "`ifdef OT_TDY\n    localparam integer DY = 16;\n`else\n    localparam integer DY = 0;\n`endif\n"
           "    lf_a #(.ID(K + DX + DY)) u_a (.clk(ck), .rst_n(rst_n), .i(x), .o(a_o));\n    lf_b u_b")
    assert par.count(old) == 1
    (src / "par.sv").write_text(par.replace(old, new, 1))
    p = json.loads((src / "die_plan.json").read_text())
    p["asbuilt"]["base"] = str(src)
    p["partition_types"]["ta"]["verilog_defines"] = ["OT_TDX", "OT_TDY"]
    f = src / "die_plan_td.json"
    f.write_text(json.dumps(p))
    return f


def _digest(d):
    return {str(f.relative_to(d)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(Path(d).rglob("*")) if f.is_file() and f.name not in VOLATILE}


def _elab(plan, out):
    import bind
    return bind.main(["elab", str(plan), "--out", str(out), "--mem", "4"])


def test_variant_specs_follow_the_serial_order(tmp_path):
    req = {"B": {"t1"}, "A": {"t2"}}
    specs = TDE.variant_specs(req, tmp_path / "v")
    assert specs == [(["A", "B"], tmp_path / "v"), (["A"], tmp_path / "v" / "without_B"),
                     (["B"], tmp_path / "v" / "without_A")]
    assert TDE.variant_specs({"A": {"t"}}, tmp_path / "v") == [(["A"], tmp_path / "v")]


def test_jobs_knob(monkeypatch):
    monkeypatch.setenv("OT_BIND_ELAB_JOBS", "3")
    assert TDE.elab_jobs(5, 96) == 3 and TDE.elab_jobs(2, 96) == 2
    monkeypatch.setenv("OT_BIND_ELAB_JOBS", "0")
    assert TDE.elab_jobs(5, 96) == 1
    monkeypatch.delenv("OT_BIND_ELAB_JOBS")
    assert 1 <= TDE.elab_jobs(5, 4) <= 5


def test_unit_cap_bounds_the_jobs(tmp_path, monkeypatch):
    cg = tmp_path / "cg"
    (cg / "a.slice" / "u.scope").mkdir(parents=True)
    (cg / "a.slice" / "memory.max").write_text("max\n")
    (cg / "a.slice" / "u.scope" / "memory.max").write_text(f"{128 << 30}\n")
    pc = tmp_path / "proc_cgroup"
    pc.write_text("0::/a.slice/u.scope\n")
    assert TDE.unit_mem_gb(str(pc), str(cg)) == 128
    (cg / "a.slice" / "u.scope" / "memory.max").write_text("max\n")
    assert TDE.unit_mem_gb(str(pc), str(cg)) is None
    monkeypatch.delenv("OT_BIND_ELAB_JOBS", raising=False)
    monkeypatch.delenv("OT_BIND_ELAB_JOB_GB", raising=False)
    monkeypatch.setattr(TDE.os, "cpu_count", lambda: 512)
    monkeypatch.setattr(TDE.os, "getloadavg", lambda: (0.0, 0.0, 0.0))
    monkeypatch.setattr(TDE, "unit_mem_gb", lambda: 64.0)
    assert TDE.elab_jobs(5, 96) == 1


@needs_yosys
def test_parallel_variants_and_cache_are_byte_identical(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("OT_BIND_TYPE_DEFINES", "on")
    monkeypatch.delenv("OT_BIND_ELAB_CACHE", raising=False)
    plan = _tree(tmp_path)
    out = tmp_path / "o"
    monkeypatch.setenv("OT_BIND_ELAB_JOBS", "1")
    assert _elab(plan, out) == 0
    serial = _digest(out)
    rec = json.loads((out / "type_defines.json").read_text())
    assert rec["verdict"] == "REALIZED" and rec["added"] == ["OT_TDX", "OT_TDY"]
    assert (out / TDE.VARIANT_DIR / "without_OT_TDX" / "asbuilt.json").is_file()
    shutil.move(out, tmp_path / "o_serial")
    monkeypatch.setenv("OT_BIND_ELAB_JOBS", "4")
    capsys.readouterr()
    assert _elab(plan, out) == 0
    assert "3 define-variant elab(s) started alongside" in capsys.readouterr().out
    assert _digest(out) == serial
    shutil.move(out, tmp_path / "o_par")
    monkeypatch.setenv("OT_BIND_ELAB_CACHE", str(tmp_path / "cache"))
    assert _elab(plan, out) == 0                       # fills the cache
    assert _digest(out) == serial
    assert len(list((tmp_path / "cache").rglob("meta.json"))) == 4
    shutil.move(out, tmp_path / "o_fill")
    marks = {m: m.stat().st_mtime_ns for m in (tmp_path / "cache").rglob("meta.json")}
    assert _elab(plan, out) == 0                       # every Yosys run is a hit
    assert _digest(out) == serial
    assert {m: m.stat().st_mtime_ns for m in (tmp_path / "cache").rglob("meta.json")} == marks
    # an RTL edit misses
    lf = plan.parent / "par.sv"
    shutil.move(out, tmp_path / "o_hit")
    lf.write_text(lf.read_text() + "\n// edit\n")
    assert _elab(plan, out) == 0
    assert len(list((tmp_path / "cache").rglob("meta.json"))) == 8
