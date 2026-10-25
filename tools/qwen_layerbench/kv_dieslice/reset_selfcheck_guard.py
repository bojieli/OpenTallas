#!/usr/bin/env python3
"""Guard the generated E-face copy simulation check until delivered reset is valid.

Owner decision13 permits unrelated power-on values. This assertion must compare
copies only after reset; synthesis removes the whole check. Apply to a staged
COPY only, since the original generated source may live outside the repository.
"""
import argparse
from pathlib import Path

OLD = 'always @(negedge ck) if (h_e !== h) $fatal(1, "qkd_kv_es_fan_root2_b_nc32: E-face copy differs from its original");'
NEW = OLD.replace('if (h_e !== h)', 'if (rst_n && rs_q && h_e !== h)')


def apply(root):
    changed = 0
    for path in Path(root).rglob('qkd_kv_ctl_nc32_face.sv'):
        text = path.read_text()
        if NEW in text:
            continue
        if text.count(OLD) != 1 or '`ifndef SYNTHESIS' not in text[:text.index(OLD) if OLD in text else 0]:
            raise ValueError(f'{path}: expected one known simulation-only E-face copy check')
        path.write_text(text.replace(OLD, NEW))
        print(f'RESET_SELFCHECK_GUARD {path}')
        changed += 1
    return changed


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('staged_src', type=Path)
    args = ap.parse_args()
    apply(args.staged_src)
