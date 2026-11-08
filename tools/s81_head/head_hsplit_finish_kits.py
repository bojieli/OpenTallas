#!/usr/bin/env python3
"""DIE-HEAD-84 HSPLIT: (1) prepare: head_start_raw_private.prepare_plan on the two halves -> PLAN_OUT;
(2) alias KIT OUT: alias-patched wrappers (relay table input of head_cland_stage_delta); (3) patch KIT: the HEAD wave export's wrapper patches (alias_patch, then private patch_rtl) into every copy of the
generated wrapper of the two kits (head_wave_kit_rtl.py export does exactly these two steps)."""
import json, sys, glob
sys.path[:0] = ['tools/die_plan', 'tools/s81_head']
from head_start_raw_private import prepare_plan, patch_rtl as private_patch
from head_start_reset_aliases import patch_rtl as alias_patch
mode = sys.argv[1]
if mode == 'prepare':
    p = json.load(open(sys.argv[2])); q, rep = prepare_plan(p, ['hd_host_w', 'hd_host_e'])
    json.dump(q, open(sys.argv[3], 'w'), indent=1); print(json.dumps(rep))
elif mode == 'alias':
    p = json.load(open(sys.argv[2])); kits, out = sys.argv[3], sys.argv[4]
    for tn in ('hd_host_w', 'hd_host_e'):
        t = p['partition_types'][tn]; m = t['module']
        txt = alias_patch(open(f'{kits}/_rtl/{m}.sv').read(), t.get('reset_start_raw_exports', []))
        open(f'{out}/{m}.sv', 'w').write(txt); print(tn, m, len(t.get('reset_start_raw_exports', [])), 'exports')
else:
    p = json.load(open(sys.argv[2])); kits = sys.argv[3]
    for tn in ('hd_host_w', 'hd_host_e'):
        t = p['partition_types'][tn]; m = t['module']
        files = sorted(set(glob.glob(f'{kits}/_rtl/{m}.sv') + glob.glob(f'{kits}/{tn}/rtl/{m}.sv')))
        for f in files:
            txt = alias_patch(open(f).read(), t.get('reset_start_raw_exports', []))
            txt, r = private_patch(txt, t)
            open(f, 'w').write(txt); print(tn, f, r)
