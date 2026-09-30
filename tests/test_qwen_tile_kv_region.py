"""The Qwen O4 tile's local KV slice keeps K below V at every window (rtl/hdc/ot_qwen_rom_tile.sv KV_KL).

K local words of a group are (position tile // PRK) * NH + head, for 2^(KV_HB-7) position tiles a head; V starts
at KV_KL.  KV_KL was a literal 512 position tiles (the 8K window): at 32K the V region then overlaps K.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GT, KV_SK, NH = 6144, 7, 2           # TP-4 product: 2 KV heads a die


def k_top(kv_hb):
    prk = GT >> KV_SK
    return (((1 << (kv_hb - 7)) - 1) // prk) * NH + NH - 1


def kl(pt):
    prk = GT >> KV_SK
    return -(-pt // prk) * NH


def test_literal_512_overlaps_at_32k():
    assert k_top(16) < kl(512)                   # 8K: fine
    assert k_top(18) >= kl(512)                  # 32K: the old literal puts V inside K


def test_window_scaled_region_is_disjoint():
    for kv_hb in (16, 18, 20, 21):               # 8K, 32K, 128K, 256K
        assert k_top(kv_hb) < kl(1 << (kv_hb - 7))


def test_rtl_and_tool_scale_the_region():
    rtl = (ROOT / "rtl/hdc/ot_qwen_rom_tile.sv").read_text()
    m = re.search(r"localparam integer KV_KL = (.*);", rtl)
    assert m and "KV_PT" in m.group(1) and "512" not in m.group(1)
    assert "KV_PT = 1 << (KV_HB - 7)" in rtl
    tool = (ROOT / "tools/qwen_o4_kv_slice_map.py").read_text()
    assert "(1 << (KV_HB - 7))" in tool and "-(-512 //" not in tool
