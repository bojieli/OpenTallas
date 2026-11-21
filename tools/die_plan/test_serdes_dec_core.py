"""FAM-S81-SERDES 11-21: serdes__t4 no-growth split -- the one-clock hard-core wrapper ot_s81_kp4_dec_lp_core and the
OT_S81_SERDES_DEC_CORE column form (rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv).  Wiring only, 0 added cycles:
the wrapper has the lp decoder's ports with ck replacing ck_syn/ck_dly/ck_chn/ck_out, and the column drives ck from pma_rck
exactly as it drives the four region clocks in the default form."""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
L = R / "rtl/dsrom_sys/s81_link"
COL = L / "col/ot_pdie_serdes_col.sv"
CORE = L / "lp/ot_s81_kp4_dec_lp_core.sv"
LP = L / "lp/ot_s81_kp4_dec_native_flat_lp.sv"
CKS = ("ck_syn", "ck_dly", "ck_chn", "ck_out")


def _ports(text, module):
    m = re.search(r"\bmodule\s+" + module + r"\b(.*?)\);", text, re.S)
    assert m, module
    hdr = re.sub(r"//[^\n]*", "", m.group(1))
    hdr = hdr.split("(", 1)[1] if "#(" not in hdr else hdr.split(")", 1)[1].split("(", 1)[1]
    names = set()
    for part in hdr.split(","):
        w = re.findall(r"[A-Za-z_]\w*", re.sub(r"\[[^\]]*\]", "", part))
        if w:
            names.add(w[-1])
    return names


def test_wrapper_ports_are_lp_ports_with_one_clock():
    lp = _ports(LP.read_text(), "ot_s81_kp4_dec_native_flat_lp")
    core = _ports(CORE.read_text(), "ot_s81_kp4_dec_lp_core")
    assert set(CKS) <= lp
    assert core == (lp - set(CKS)) | {"ck"}


def test_wrapper_drives_every_region_clock_from_ck_and_has_no_logic():
    t = re.sub(r"//[^\n]*", "", CORE.read_text())
    for c in CKS:
        assert re.search(r"\." + c + r"\(ck\)", t), c
    assert not re.search(r"\b(always|assign|reg)\b", t)
    assert len(re.findall(r"\bot_s81_kp4_dec_native_flat_lp\b", t)) == 1


def test_column_dec_core_form_selects_wrapper_on_pma_rck():
    t = COL.read_text()
    i = t.index("`ifdef OT_S81_SERDES_DEC_CORE")
    blk = t[i:t.index("u_rm", i)]
    assert "ot_s81_kp4_dec_lp_core #(.MUT((MUT >= 1 && MUT <= 4) ? MUT : 0)) u_dec (" in blk
    assert "`elsif OT_S81_RCK_REFORM" in blk
    assert re.search(r"`ifdef OT_S81_SERDES_DEC_CORE\s+\.ck\(pma_rck\)\);\s+`else\s+\.ck_syn\(pma_rck\), \.ck_dly\(pma_rck\), "
                     r"\.ck_chn\(pma_rck\), \.ck_out\(pma_rck\)\);\s+`endif", blk)


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
@pytest.mark.parametrize("defs,module,ck", [((), "ot_s81_kp4_dec_native_flat_lp", ".ck_syn(pma_rck)"),
                                            (("OT_S81_SERDES_DEC_CORE",), "ot_s81_kp4_dec_lp_core", ".ck(pma_rck)"),
                                            (("OT_S81_SERDES_DEC_CORE", "OT_S81_RCK_REFORM"), "ot_s81_kp4_dec_lp_core", ".ck(pma_rck)")])
def test_column_preprocesses_to_one_decoder_form(defs, module, ck):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "col.E"
        subprocess.run(["iverilog", "-g2012", "-E", "-I", str(L), *[f"-D{x}" for x in defs], "-o", str(out), str(COL)],
                       check=True, capture_output=True, timeout=60)
        e = out.read_text()
        dec = re.search(r"\n\s*(\w+)\s+#\(\.MUT\(\(MUT >= 1 && MUT <= 4\) \? MUT : 0\)\)\s+u_dec\s*\((.*?)\);", e, re.S)
        assert dec and dec.group(1) == module
        assert ck in dec.group(2)


ENC_CORE = L / "ot_s81_kp4_enc_core.sv"


def test_enc_core_wrapper_is_h0_seq_only_form_and_used_in_split_form():
    """FAM-S81-SERDES-R4 11-21: the split form's u_enc hard core = ot_s81_kp4_enc #(.H0_SEQ_ONLY(1)), wiring only."""
    t = re.sub(r"//[^\n]*", "", ENC_CORE.read_text())
    assert re.search(r"ot_s81_kp4_enc\s*#\(\.MUT\(MUT\),\s*\.H0_SEQ_ONLY\(1\)\)\s*u_enc", t)
    assert not re.search(r"\b(always|assign|reg)\b", t)
    c = COL.read_text()
    i = c.index("ot_s81_kp4_enc_core u_enc")
    assert "`ifdef OT_S81_SERDES_DEC_CORE" in c[i - 400:i]
    assert "ot_s81_kp4_enc u_enc (.clk(clk), .rst_n(rn_te_rst)" in c        # default form unchanged
