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


def _tree(tmp_path, defines=("OT_TDX", "OT_TDY")):
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
    p["partition_types"]["ta"]["verilog_defines"] = list(defines)
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
    assert TDE.elab_jobs(5, 96) == 2 and TDE.elab_jobs(2, 96) == 2 and TDE.elab_jobs(1, 96) == 1
    for serial in ("1", "0"):
        monkeypatch.setenv("OT_BIND_ELAB_JOBS", serial)
        assert TDE.elab_jobs(5, 96) == 0
    monkeypatch.delenv("OT_BIND_ELAB_JOBS")
    assert 0 <= TDE.elab_jobs(5, 4) <= 5


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
    assert TDE.elab_jobs(5, 96) == 0            # no room for a second Yosys: serial
    monkeypatch.setattr(TDE, "unit_mem_gb", lambda: 128.0)
    monkeypatch.setattr(TDE.os, "cpu_count", lambda: 96)
    monkeypatch.setattr(TDE.os, "getloadavg", lambda: (112.0, 0.0, 0.0))
    real = Path.read_text
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: "MemAvailable: 524288000 kB\n"
                        if str(self) == "/proc/meminfo" else real(self, *a, **k))
    assert TDE.elab_jobs(6, 96) == 3            # loaded host: base + 3 variants inside the 128 GB unit
    assert TDE.elab_jobs(1, 96) == 1            # S81 c8: the one variant still runs beside the base


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
    monkeypatch.setenv("OT_BIND_ELAB_JOBS", "5")
    capsys.readouterr()
    assert _elab(plan, out) == 0
    assert "3 define-variant elab(s) started alongside" in capsys.readouterr().out
    assert _digest(out) == serial
    shutil.move(out, tmp_path / "o_par")
    monkeypatch.setenv("OT_BIND_ELAB_CACHE", str(tmp_path / "cache"))
    import bind_elab as E
    monkeypatch.setattr(E.ElabCache, "MIN_FREE_GB", 0)
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


def _entry(tmp_path, out, body="module m; endmodule\n", src=None):
    """a hand-made elab step: OUT/a.ys reading one staged and one tree source; no Yosys needed"""
    import bind_elab as E
    src = src or tmp_path / "rtl" / "m.sv"
    src.parent.mkdir(exist_ok=True)
    src.write_text(body)
    out.mkdir(parents=True, exist_ok=True)
    (out / "s.sv").write_text("module s; endmodule\n")
    (out / "a.ys").write_text(f"read_slang -I{src.parent} {out}/s.sv {src}\nwrite_json {out}/asbuilt.json\n")
    return E.ElabCache.open(out / "a.ys")


@pytest.fixture
def cache_env(tmp_path, monkeypatch):
    import bind_elab as E
    exe = tmp_path / "yosys"
    exe.write_text("v1")
    monkeypatch.setenv("OT_BIND_YOSYS", str(exe))
    monkeypatch.setenv("OT_BIND_ELAB_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(E.ElabCache, "MIN_FREE_GB", 0)
    return tmp_path


def _fill(c, out, content):
    (out / "asbuilt.json").write_text(content)
    (out / "y.log").write_text("log")
    c.store(out / "y.log")


def test_cache_hits_in_a_sibling_out_dir_only_when_relocatable(cache_env):
    t = cache_env
    a, b, deep = t / "c8_out", t / "compose9_out", t / "x" / "c9_out"
    _fill(_entry(t, a), a, "relative only")
    c = _entry(t, b)
    assert c.fetch(b / "y.log") and (b / "asbuilt.json").read_text() == "relative only"
    assert not _entry(t, deep).fetch(deep / "y.log")            # other depth: slang relative src text differs
    n = t / "d_out"
    body = "module m; wire w; endmodule\n"
    _fill(_entry(t, n, body), n, f"names {n}/s.sv")
    e = t / "e_out"
    assert not _entry(t, e, body).fetch(e / "y.log")             # output names its out dir
    assert _entry(t, n, body).fetch(n / "y.log")


def test_cache_misses_or_stays_off_when_unsafe(cache_env):
    t = cache_env
    a = t / "a_out"
    _fill(_entry(t, a), a, "x")
    assert not _entry(t, a, "module m; wire q; endmodule\n").fetch(a / "y.log")        # source edit
    for body in ('`include "gone.svh"\n', "`include `HDR\n", "`include <gone.svh>\n",
                 'module m; initial $readmemh("a.hex", r); endmodule\n'):
        assert _entry(t, a, body) is None
    inc = t / "rtl" / "h.svh"
    inc.write_text("// 1\n")
    k1 = _entry(t, a, '`include "h.svh"\n').key
    inc.write_text("// 2\n")
    assert _entry(t, a, '`include "h.svh"\n').key != k1                                # include edit
    (t / "yosys").write_text("v2")
    assert not _entry(t, a).fetch(a / "y.log")                                         # another Yosys
    c = _entry(t, a, "module m; wire r; endmodule\n")
    (t / "rtl" / "m.sv").write_text("module m; wire changed; endmodule\n")
    _fill(c, a, "y")                                                                   # edited while Yosys ran
    assert not c.dir.exists()
    c = _entry(t, a, "module m; wire z; endmodule\n")
    _fill(c, a, "good")
    (c.dir / "out.json").write_text("bad!")                                            # corrupt entry
    assert not c.fetch(a / "y.log") and (a / "asbuilt.json").read_text() == "good"


@needs_yosys
def test_single_variant_runs_beside_the_base(tmp_path, monkeypatch, capsys):
    """S81 c8 (only ATTCUT left): one variant elab must still start beside the base, not after it"""
    monkeypatch.setenv("OT_BIND_TYPE_DEFINES", "on")
    monkeypatch.delenv("OT_BIND_ELAB_CACHE", raising=False)
    plan = _tree(tmp_path, ("OT_TDX",))
    out = tmp_path / "o"
    monkeypatch.setenv("OT_BIND_ELAB_JOBS", "1")
    assert _elab(plan, out) == 0
    assert "run after the base elab" in capsys.readouterr().out
    serial = _digest(out)
    shutil.move(out, tmp_path / "o_serial")
    monkeypatch.delenv("OT_BIND_ELAB_JOBS")
    import type_define_effect as T
    monkeypatch.setattr(T, "unit_mem_gb", lambda: None)
    assert _elab(plan, out) == 0
    assert "1 define-variant elab(s) started alongside" in capsys.readouterr().out
    assert _digest(out) == serial
