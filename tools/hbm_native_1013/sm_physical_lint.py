#!/usr/bin/env python3
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; out=ROOT/'results/arch/hbm_native_1013/sm'
for suffix in ['front_n','front_s','be_eg','be_wg']:
 spec=json.load(open(out/'physical_specs'/f'smn_{suffix}_ref.json')); cmd=['verilator','--lint-only','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-TIMESCALEMOD','-Wno-MULTIDRIVEN','-Wno-MODMISSING','-DSYNTHESIS',*['-D'+d for d in spec['defines']],'--top-module',spec['top'],*spec['sources']]
 proc=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True); (out/f'physical_lint_{suffix}.log').write_text(proc.stdout); report={'top':spec['top'],'params':'unoverridden production defaults including RMAX4096','rtl_snapshot_source':'49b00f711ce5613322f3c0d011f109c78894d1de','command':cmd,'returncode':proc.returncode,'pass':proc.returncode==0}; (out/f'physical_lint_{suffix}.json').write_text(json.dumps(report,indent=2)+'\n'); print(suffix,proc.returncode)
 if proc.returncode: raise SystemExit(proc.returncode)
