"""Small RTL gate for Qwen's opt-in 18-bit token and row-offset encoding."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa as I  # noqa: E402
import hdc_qwen_fullshape_isa as F  # noqa: E402
import hdc_program as P  # noqa: E402
import rtl_hdc_decode_campaign as C  # noqa: E402


def test_fullshape_high_token_and_instruction_row0(tmp_path):
    fields = dict(
        unit=I.UNIT_SU, su_nout=1, su_nin=128,
        a_src=I.SRC_ALT, a_base=0, a_d=I.DYN_EMBED, a_si=1,
        dst=I.DST_VM, d_base=0, d_si=1, me_row0=0x2345, me_amc=1,
    )
    # The upper row bits start AFTER me_amc at bit 897.
    instruction = I.encode(**fields) | (1 << 898)
    (tmp_path / "program.hex").write_text(P.hexwords((instruction, I.encode(unit=I.UNIT_END)),
                                                         I.INSTR_BITS))
    binary = tmp_path / "sim.vvp"
    sources = [*C.HDC, *C.PIPES,
               ROOT / "rtl/hdc/ot_hdc_dyn_ttiles.sv",
               ROOT / "rtl/hdc/ot_hdc_qwen_int8_arith.sv",
               ROOT / "rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv",
               ROOT / "rtl/hdc/ot_hdc_core_vector_weight.sv",
               ROOT / "rtl/test/tb_hdc_qwen_fullshape_decode.sv"]
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_fullshape_decode",
                    "-Irtl/hdc", "-o", str(binary), *map(str, sources)],
                   cwd=ROOT, check=True, capture_output=True, text=True)
    result = subprocess.run(["vvp", str(binary), f"+DIR={tmp_path}"],
                            cwd=ROOT, check=True, capture_output=True, text=True)
    assert "code_addr=303870 scale_addr=151935 row0=12345" in result.stdout


def test_fullshape_tp_descriptor_high_row0(tmp_path):
    binary = tmp_path / "seq.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_rom_tp_fullshape_desc",
                    "-o", str(binary),
                    str(ROOT / "rtl/rom/ot_rom_tp_seq.sv"),
                    str(ROOT / "rtl/test/tb_rom_tp_fullshape_desc.sv")],
                   cwd=ROOT, check=True, capture_output=True, text=True)
    result = subprocess.run(["vvp", str(binary)], cwd=ROOT, check=True,
                            capture_output=True, text=True)
    assert "row0=75968 next_token=75978" in result.stdout
