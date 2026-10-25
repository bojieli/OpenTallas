#!/usr/bin/env python3
"""TOKj-KV 10-23: ordered leaf dirs of a bind out dir = union of the binder's per-partition lint -I lists (hub_C, hub_Wi,
sys_c first), minus the lint stub dir and the PHY model dirs (bench models replace them).   lint_incdirs.py BIND_DIR > list"""
import glob, os, sys
B = sys.argv[1].rstrip('/'); seen = []
first = [f'{B}/lint/{t}/verilator_lint.f' for t in ('kv3_hub_C_part', 'kv3_hub_Wi_part', 'kv3_sys_c_part')]
for f in first + sorted(glob.glob(f'{B}/lint/*/verilator_lint.f')):
    if not os.path.exists(f): continue
    for l in open(f):
        l = l.strip()
        if l.startswith('-I'):
            d = l[2:]
            if d.endswith('/lint') or 'bind/models' in d or 'ot_qkvd_ucie_x64_phy' in d or d in seen: continue
            seen.append(d)
print('\n'.join(seen))
