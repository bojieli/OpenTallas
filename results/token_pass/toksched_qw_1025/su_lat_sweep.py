#!/usr/bin/env python3
"""TOK-SCHED 2026-10-25: re-run the QC decode-stage static plan (tools/qwen_layerbench/ctlm_image.py, every RTL seal
fail-closed) with the priced slice SU pipeline SU_LAT = 24 (MIF=0) .. 27, and list per programme op how its issue / done
edges move.  MIF=1 on su_c (btab / prog / vmr + crh rp1) = PROG issue word +1 (slice su_go delay D 2 -> 3) and SU
operand reads +1 => SU_LAT 26.

usage: python3 su_lat_sweep.py OUTDIR   (from a checkout with tools/, results/arch, results/rtl/qwen_layer_tput_1018,
       results/rtl/qwen_q_export_1014/xpf, rtl/physical, rtl/qwen_dv)
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
out_dir = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('ci', ROOT / 'tools/qwen_layerbench/ctlm_image.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)
res = {}
for lat in (24, 25, 26, 27):
    ci.PROG_CONSTANTS['SU_LAT'] = lat
    out = out_dir / f'ctlm_lat{lat}'
    sys.argv = ['ctlm_image.py', '--out', str(out)]
    ci.main()                                   # raises CompileError if any seal fails
    d = json.loads((out / 'ctlm_image.json').read_text())
    ends = [x for x in d['plan'] if x['kind'] == 'END']
    res[lat] = dict(me_stop_cycle=d['me_stop_cycle'], last_end=ends[-1]['at'], digest=d['digest'],
                    plan=[dict(pc=x['pc'], kind=x['kind'], window=x['window'], at=x['at'], done=x['done'])
                          for x in d['plan']])
base = res[24]['plan']
for lat in res:
    res[lat]['shift_vs_24'] = [dict(pc=a['pc'], kind=a['kind'], window=a['window'], d_at=b['at'] - a['at'],
                                    d_done=b['done'] - a['done']) for a, b in zip(base, res[lat]['plan'])]
(out_dir / 'su_lat_sweep.json').write_text(json.dumps(res, indent=1))
for lat in res:
    print(lat, res[lat]['me_stop_cycle'], res[lat]['last_end'])
