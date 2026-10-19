#!/usr/bin/env python3
"""MTP-AREA sizing synthesis (no placement): the d4g SM leaf matrix columns at P activation/accumulator lanes.

Same tool / liberty / dont_use / ABC target as tools/run_abi3_physical.run_synthesis (Yosys 0.68 flatten, ASAP7 RVT TT),
then OpenSTA on the mapped netlist at 0.833 ns (no wire load, IO 20% of the period, 60 ps setup uncertainty): a
synthesis-timing plausibility check, NOT sign-off.
  --unit bdc|tcc  --p N   (P-lane variant ot_hbm_sm_{bdc,tcc}_p)   or   --baseline (the production single-lane column).
"""
import argparse, hashlib, json, pathlib, re, sys
ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--unit', choices=['bdc', 'tcc'], required=True)
ap.add_argument('--p', type=int, default=1); ap.add_argument('--baseline', action='store_true'); a = ap.parse_args()
r = pathlib.Path(__file__).resolve().parents[4]; sys.path.insert(0, str(r / 'tools')); import run_abi3_physical as D
out = pathlib.Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
s = json.loads((r / 'physical/ref_tile/smh_bdc_ref_p50/spec.json').read_text())
files = s['sources'] + ['rtl/hbm_accel/sm/mtp_lanes/ot_hbm_sm_bdc_p.sv']
text = '\n'.join('`define ' + d for d in s['defines']) + '\n' + '\n'.join((r / f).read_text() for f in files)
canon = out / 'canonical.sv'; canon.write_text(text)
if a.baseline:
    top = 'ot_hbm_accel_smh_bdc' if a.unit == 'bdc' else 'ot_hbm_accel_smh_tcc'; params = {}
else:
    top = f'ot_hbm_sm_{a.unit}_p'; params = {'P': a.p}
block = {'top': top, 'sources': [str(canon)], 'parameters': params, 'clock_port': 'clk',
         'false_path_from_ports': ['rst_a'], 'clock_uncertainty_ns': 0.06}
v = D.VIEWS['asap7']; c = v['corners']['TT']; period = 0.833333
cells = D.scan_liberty([pathlib.Path(f) for f in c['liberty']])
z = D.run_synthesis(v, c, block, out, period, D.expand_dont_use(v['dont_use'], cells))
sta = D.run_sta(v, c, block, out, z['netlist'], period)
log = (out / 'yosys.log').read_text(errors='replace')
mem_inferred = len(re.findall(r'\$mem(_v2)?\b', (out / 'stat.txt').read_text(errors='replace')))
rpt = (out / 'setup_path.rpt').read_text(errors='replace') if (out / 'setup_path.rpt').is_file() else ''
sp = re.search(r'Startpoint: (\S+)', rpt); ep = re.search(r'Endpoint: (\S+)', rpt)
res = {'schema': 'opentallas.hbm_mtp_area.lane_synth.v1',
       'scope': 'mapped std-cell area + synthesis STA only; no placement, no wires, no x-store / VM / gather change',
       'unit': a.unit, 'P': 1 if a.baseline else a.p, 'baseline_production_module': a.baseline, 'top': top,
       'parameters': params, 'defines': s['defines'], 'clock_period_ns': period,
       'source_sha256': {f: hashlib.sha256((r / f).read_bytes()).hexdigest() for f in files},
       'canonical_sha256': hashlib.sha256(canon.read_bytes()).hexdigest(), 'yosys': str(D.YOSYS), 'sta': str(D.STA),
       'liberty_sha256': {pathlib.Path(f).name: hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest() for f in c['liberty']},
       'synthesis': z['record'], 'sta_tt': sta,
       'setup_critical': {'start': sp.group(1) if sp else None, 'end': ep.group(1) if ep else None},
       'checks': {'mem_cells_in_stat': mem_inferred}}
(out / 'area.json').write_text(json.dumps(res, indent=2, default=str) + '\n'); print(json.dumps(res, indent=1, default=str)[:3000])
