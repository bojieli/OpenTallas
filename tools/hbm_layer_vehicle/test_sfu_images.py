#!/usr/bin/env python3
"""python checks of sfu_images.py (the RTL check is tb_sfu_collar.sv)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hbm_layer_vehicle import sfu_images as S  # noqa: E402


def test():
    w = S.pack_io(dict(arithmetic_start=1, prefetch_v=0x81, drain_round_bf16=2))
    assert w >> 470 == 1 and w & 0xff == 0x81 and (w >> 468) & 3 == 2
    ip = S.io_planes([w, 0])
    assert len(ip) == 3 and (ip[2][0] >> 26) & 1 == 1 and (ip[0][1] >> 223) & 0x7ff == 1
    assert all(r >> 240 == 0xc7a1 for p in ip for r in p)
    ctl = S.encode(S.compile_vector(words=64, bases=(0, 64, 128, 192, 256)))
    cp = S.ctl_planes(ctl)
    assert len(cp) == 8 and all(len(p) == len(ctl) for p in cp)
    fr, need = S.collar_install(cp, ip)
    assert need == [7 * 2048 + len(ctl), 2 * 2048 + 2]
    assert len(fr) == need[0] + need[1] + 8 + 3 + 1          # rows + selects + need
    sel = [d for a, d in fr if a == 0xE00]
    assert sel[:2] == [0, 1 << 8] and sel[8] == 1
    frc, _ = S.collar_install(cp, ip, compact=True)
    assert len(frc) == 8 * len(ctl) + 3 * 2 + 11 + 1
    p = S.prm_row(10, 5, 3, 2, 1, 1)
    assert p & 0x7ff == 10 and (p >> 11) & 0xfff == 15 and (p >> 23) & 0xffff == 1
    assert (p >> 39) & 0x7ff == 3 and (p >> 50) & 0xfff == 5 and (p >> 62) & 0xffff == 1
    print("test_sfu_images PASS")


if __name__ == "__main__":
    test()
