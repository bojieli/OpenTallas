"""RNE-PAIR-COPY patch (HEAD-EAST-REPLAN 11-24, merged by HEAD-ALLFIX 11-25): every anchor once -> rewritten; missing anchor fails closed."""
import importlib.util
from pathlib import Path

import pytest

_P = Path(__file__).resolve().parent / "head_lep_rne_pair_copy.py"
_S = importlib.util.spec_from_file_location("head_lep_rne_pair_copy", _P)
M = importlib.util.module_from_spec(_S)
_S.loader.exec_module(M)

SRC = (
    "        if(SAFE_CONTROL) begin:g_nonempty_regions\n"
    "          assign rne_addr[t]=addr_nz;assign rne_meta[t]=meta_nz;assign rne_return[t]=return_nz;\n"
    "        end else begin\n"
    "          assign rne_addr[t]=rne[t];assign rne_meta[t]=rne[t];assign rne_return[t]=rne[t];\n"
    "        end\n"
    "  u_a .advance_a(rne_addr[2*(t/2)]),.advance_b((t==0)?1'b1:rne_addr[2*(t/2)+1]));\n"
    "  u_b .advance_b(rne_addr[2*(t/2)+1]));\n"
    "                wire mb=(t==0)?1'b1:rne_meta[2*(t/2)+1];\n"
    "                wire mb=rne_meta[2*(t/2)+1];\n"
    "  u_c .advance_a(rne_meta[2*(t/2)]),.advance_b(mb),\n"
)


def test_apply_rewrites_every_anchor():
    out = M.apply(SRC)
    assert "(* keep=1 *) reg addr_pz;" in out and "(* keep=1 *) reg meta_pz;" in out
    assert "wire adv_pair, adv_meta_pair;" in out
    assert "rne_addr[2*(t/2)]" not in out and "rne_meta[2*(t/2)]" not in out
    assert "rne_addr[2*(t/2)+1]" not in out and "rne_meta[2*(t/2)+1]" not in out
    assert out.count("adv_pair") >= 5


def test_missing_anchor_fails_closed():
    with pytest.raises(SystemExit):
        M.apply(SRC.replace("wire mb=rne_meta[2*(t/2)+1];\n", ""))


def test_not_reapplicable():
    with pytest.raises(SystemExit):
        M.apply(M.apply(SRC))
