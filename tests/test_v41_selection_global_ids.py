"""tools/v41_selection_global_ids.py is the checked id -> die/stack/local/port contract: the RTL that places selected
compressed-KV rows (selected-CKV DMA of every die, the ID table's read ports, the wide fetch's port choice) is
simulated on ~440 ids against it, and a deliberately wrong expectation must be caught."""
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from v41_selection_global_ids import bits_form, owner, port  # noqa: E402

VL = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")) / \
    "verilator-5.050/bin/verilator"
SRC = ["rtl/test/tb_v41_selection_global_ids.sv", "rtl/chip/ot_chip_v41x_ckv_fp4_decode.sv",
       "rtl/chip/ot_chip_v41x_ckv_selected_dma.sv", "rtl/chip/ot_chip_v41x_ckv_sel_ids.sv",
       "rtl/chip/ot_chip_v41x_ckv_pc_fetch.sv"]


def test_tool_matches_bit_form():
    r = random.Random(3)
    for g in list(range(2048)) + [r.randrange(1 << 21) for _ in range(20000)]:
        assert owner(g) == bits_form(g)


def _ids():
    r = random.Random(7)
    return sorted(set(list(range(40)) + [r.randrange(262144) for _ in range(400)] + [262143, 1 << 19, (1 << 20) - 1]))


def _exp(ids, corrupt=False):
    out = []
    for i, g in enumerate(ids):
        d, s, l = owner(g)
        if corrupt and i == 17:
            d ^= 1
        out.append(f"{(d << 27) | (s << 25) | (l << 4) | (port(g, 4) % 4):08x}\n")
    return "".join(out)


@pytest.mark.skipif(not VL.is_file(), reason="Verilator 5.050 not installed")
def test_rtl_agrees_with_contract(tmp_path):
    obj = tmp_path / "obj"
    subprocess.run([str(VL), "--binary", "--timing", "-j", "4", "-Wno-fatal", "-Wno-WIDTH", "-Wno-TIMESCALEMOD",
                    "-Mdir", str(obj), "--top-module", "tb_v41_selection_global_ids",
                    *[str(ROOT / s) for s in SRC]], check=True, capture_output=True)
    exe = obj / "Vtb_v41_selection_global_ids"
    ids = _ids()
    (tmp_path / "ids.hex").write_text("".join(f"{g:08x}\n" for g in ids))
    for corrupt in (False, True):
        (tmp_path / "exp.hex").write_text(_exp(ids, corrupt))
        out = subprocess.run([str(exe), f"+n={len(ids)}"], cwd=tmp_path, check=True, capture_output=True,
                             text=True).stdout
        line = [x for x in out.splitlines() if x.startswith("GLOBAL_IDS")][-1]
        errors = int(line.split("errors=")[1])
        assert int(line.split("checked=")[1].split()[0]) == 6 * len(ids)
        assert (errors > 0) if corrupt else (errors == 0), line
