"""Generate only the opt-in QKH safe32 head; leave the pinned generator unchanged."""
import argparse
import sys
import head_st_rtl as H

OUT = H.D / 'ot_qkh_head_native_r4_s_lk_nc32c.sv'


def generate():
    txt = H.generate_lk()
    for old, new, count in (
            ('ot_qkh_lane8 u_l8', 'ot_qkh_lane8_nc32c u_l8', 2),
            ('ot_qkh_ktree_lk u_kt', 'ot_qkh_ktree_lk_nc32c u_kt', 2),
            ('module ot_qkh_head_native_r4_s_lk #(', 'module ot_qkh_head_native_r4_s_lk_nc32c #(', 1),
            ('module ot_qkh_head_native_r4_ft_s_lk #(', 'module ot_qkh_head_native_r4_ft_s_lk_nc32c #(', 1)):
        if txt.count(old) != count:
            raise ValueError(f'safe32 head source changed: {old}')
        txt = txt.replace(old, new)
    return txt


if __name__ == '__main__':
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    txt = generate()
    if a.check:
        sys.exit(0 if OUT.exists() and OUT.read_text() == txt else 1)
    OUT.write_text(txt)
    print(OUT)
