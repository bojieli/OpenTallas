#!/usr/bin/env python3
"""Read the actual SOURCE calibration inventory and run the existing boundary check.

This is an observer adapter: it neither changes the frozen job nor treats mapped
standard cells as black boxes for boundary qualification.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shlex
from pathlib import Path

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    src = Path((a.run/'cl/SRC_DIR').read_text().strip())
    cfg = (a.run/'cal/config.mk').read_text()
    def var(name):
        return re.search(r'^export '+name+r' = (.*)$', cfg, re.M).group(1)
    top = var('DESIGN_NAME')
    sources = [s.removeprefix('/src/') for s in shlex.split(var('VERILOG_FILES'))]
    pts = shlex.split(var('VERILOG_TOP_PARAMS'))
    params = dict(zip(pts[::2], pts[1::2]))
    case = json.loads((a.run/'cal/case.json').read_text())
    assert int(params['PROMPT_EXTRA']) == case['params']['PROMPT_EXTRA'] == 2
    assert all(int(params[k]) == v for k,v in case['params'].items())
    archive = json.loads((a.run/'cl/source_archive.json').read_text())
    for path, expected in archive['required_sha256'].items():
        assert sha(src/path) == expected, path
    net = next((a.run/'cal').glob('results/asap7/*/base/1_2_yosys.v'))
    checker = src/'tools/closure_loop/rtl_boundary.py'
    modspec = importlib.util.spec_from_file_location('source_boundary', checker)
    rb = importlib.util.module_from_spec(modspec)
    modspec.loader.exec_module(rb)
    rb.CACHE = a.out/'private_cache.json'
    # Adapt only recipe discovery to the actual generated config. The existing
    # checker elaborates the exact RTL generically and retains its normal policy.
    cmd = 'probe --top '+shlex.quote(top)
    cmd += ''.join(' --source '+shlex.quote(s) for s in sources)
    cmd += ''.join(' --param '+shlex.quote(k+'='+v) for k,v in params.items())
    spec = dict(source={'commit':archive['commit']},registered_io=True,stages={'route':{'cmd':cmd}})
    result = rb.check(spec, lambda commit,path: (src/path).read_text() if (src/path).is_file() else None)
    receipt = dict(observer_only=True, checker_sha256=sha(checker), pid=os.getpid(),pgid=os.getpgrp(),
        config_sha256=sha(a.run/'cal/config.mk'),source_commit=archive['commit'],
        top=top,params=params,sources_sha256={s:sha(src/s) for s in sources},
        actual_synth_netlist=dict(path=str(net),sha256=sha(net),bytes=net.stat().st_size,
            macro_type_occurrences=net.read_text().count('ot_sram_1r1w_512x128_m4_r2c2')),
        boundary=result, scope='Generic elaboration from actual full-shape sources/params; mapped netlist is inventory only')
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(result))
    if result['verdict'] == 'REFUSE':raise SystemExit(3)
if __name__ == '__main__': main()
