#!/usr/bin/env python3
"""Materialise tile's real peer insertion; shell env is not forwarded into ORFS.

A CTS-only calibration may use temporary0ps. A routed qualification requires
measured TT and FF insertion. Fixed166.6ps communication budgets, both launch
phases and60/25ps uncertainties remain unchanged.
"""
import argparse,json,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--calibrate',action='store_true');a=p.parse_args()
tt=os.environ.get('CK_TT_MEAN',os.environ.get('CK_SS_MEAN'));ff=os.environ.get('CK_FF_MEAN')
if a.calibrate:tt=ff='0'
if tt is None or ff is None:raise SystemExit('TT/FF matched-root insertion missing; calibrate before tile route')
tt,ff=float(tt),float(ff)
if not a.calibrate and (tt<=0 or ff<=0):raise SystemExit('Measured insertion must be positive')
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
base=Path('physical/hbm_accel_die_views/su/tile_registered_io.sdc').read_text();start=base.index('set ti_lat 0');end=base.index('set_clock_latency',start)
s=base[:start]+f'set ti_lat {tt}\nif {{[llength [get_libs -quiet *_FF_*]]}} {{set ti_lat {ff}}}\n'+base[end:]
(out/'io.sdc').write_text(s)
head=Path('physical/hbm_accel_die_views/su/tile_registered_signoff.sdc').read_text().split('source /src/',1)[0]
(out/'signoff.sdc').write_text(head+s)
(out/'budget.json').write_text(json.dumps(dict(grade='temporary_cts_only' if a.calibrate else 'measured',tt_peer_insertion_ps=tt,ff_peer_insertion_ps=ff,launch_max_ps=166.6,launch_min_ps=25,capture_max_ps=166.6,capture_min_ps=-25,setup_uncertainty_ps=60,hold_uncertainty_ps=25,launch_phases=['rise','fall'],source='closure_loop matched-root calibration'),indent=2)+'\n')
