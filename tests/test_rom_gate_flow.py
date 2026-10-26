"""D-ROM-1 (OWNER 2026-10-25): the pre-route gate runs tools/mem_compiler/rom_infer_gate.py on the kit synthesis mem.json
and FAILs an undeclared ROM synthesised as logic; declared math tables (D-ROM-2 (a)) pass as INFO."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "ref_tile"))
sys.path.insert(0, str(ROOT / "tools" / "mem_compiler"))

import pre_route_gate as PRG  # noqa: E402
import rom_infer_gate as RG  # noqa: E402


def _gate(out):
    g = PRG.Gate()
    PRG.check_rom_gate(g, out)
    return [(i["severity"], i["check"]) for i in g.items], g


def _remote_line(tmp_path, design):
    """run the exact shell lines REMOTE_SH ships, on a mem.json, and return the GATE_ROMGATE output"""
    sh = PRG.REMOTE_SH
    i = sh.index("# ROM-INFER GATE")
    block = sh[i:sh.index("fi\n", i) + 3]
    b = tmp_path / "base"
    b.mkdir()
    (b / "mem.json").write_text(json.dumps(design))
    p = subprocess.run(["bash", "-c", block.replace("{{", "{").replace("}}", "}")], cwd=ROOT, capture_output=True,
                       text=True, env={"B": str(b), "R": str(tmp_path), "PATH": "/usr/bin:/bin"})
    return p.stdout


def _rom(words, width, init):
    return {"type": "$mem_v2", "attributes": {}, "parameters": {
        "SIZE": format(words, "032b"), "WIDTH": format(width, "032b"), "RD_PORTS": format(1, "032b"),
        "WR_PORTS": format(0, "032b"), "MEMID": "$auto$proc_rom", "INIT": init}}


def test_remote_block_formats_and_gate_verdicts(tmp_path):
    assert "GATE_ROMGATE" in PRG.REMOTE_SH and "check_rom_gate(g, out)" in Path(PRG.__file__).read_text()
    bad = {"modules": {"top": {"cells": {"t": _rom(256, 8, "01" * 1024)}}}}
    (tmp_path / "a").mkdir()
    out = _remote_line(tmp_path / "a", bad)
    assert re.search(r'^GATE_ROMGATE .*"verdict": "FAIL"', out, re.M), out
    sev, g = _gate(out)
    assert sev == [("FAIL", "rom_gate")] and g.verdict == "FAIL"
    (tmp_path / "b").mkdir()
    sev, _ = _gate(_remote_line(tmp_path / "b", {"modules": {"top": {"cells": {"t": _rom(16, 8, "01" * 64)}}}}))
    assert sev == [("INFO", "rom_gate")]
    assert _gate("GATE_ROMGATE_MISSING\n")[0] == [("INFO", "rom_gate")]
    assert _gate("")[0] == []


def test_declared_table_passes_in_flow(tmp_path):
    e = RG.load_allowlist()[0]
    # a table whose INIT hashes to a declared entry cannot be forged here; check the DECL path through check_design
    import hashlib
    init = "1" * (e["words"] * e["width"])
    allow = [dict(e, sha256=hashlib.sha256(init.encode()).hexdigest(), src="")]
    r = RG.check_design({"modules": {"top": {"cells": {"t": _rom(e["words"], e["width"], init)}}}}, allowlist=allow)
    assert r["verdict"] == "PASS" and r["declared"] == [e["id"]]
