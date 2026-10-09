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
import subprocess
from pathlib import Path

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--synth-json', action='store_true', help='Reuse the actual completed pre-mapping synthesis snapshot')
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
    synth_input = None
    if a.synth_json:
        synth_input = net.parent/'mem.json'
        actual = json.loads(synth_input.read_text())
        assert int(actual['modules'][top]['parameter_default_values']['PROMPT_EXTRA'],2) == 2
        macro_sources = [src/s for s in sources if s.endswith('_bb.v')]
        ys = ''.join('read_verilog -lib -sv '+str(s)+'; ' for s in macro_sources)
        # Physical hierarchy retention is metadata, not a boundary. Flatten those
        # actual RTL modules for analysis; retain the real SRAM black boxes.
        ys += 'read_json '+str(synth_input)+'; hierarchy -top '+top+'; setattr -mod -unset keep_hierarchy; setattr -unset keep_hierarchy; flatten; memory_map; opt_clean; techmap; opt_clean; write_json '+str(a.out/'generic.json')
        q = subprocess.run([rb.YOSYS,'-p',ys],text=True,capture_output=True)
        (a.out/'yosys.log').write_text(q.stdout+q.stderr)
        if q.returncode:
            result = dict(verdict='SKIP',message='actual snapshot generic techmap failed',exit=q.returncode)
        else:
            generic = json.loads((a.out/'generic.json').read_text())
            unknown = sorted({c['type'] for c in generic['modules'][top]['cells'].values() if not c['type'].startswith('$_') and c['type'] not in ('ot_sram_1r1w_512x128_m4_r2c2','$scopeinfo')})
            if unknown:
                result = dict(verdict='SKIP',message='Unknown primitives fail closed',unknown=unknown)
            else:
                result = rb._verdict(rb.analyse(generic,top),{'top':top},rb.LEVELS,True)
    else:
        result = rb.check(spec, lambda commit,path: (src/path).read_text() if (src/path).is_file() else None)
    receipt = dict(observer_only=True, checker_sha256=sha(checker), pid=os.getpid(),pgid=os.getpgrp(),
        config_sha256=sha(a.run/'cal/config.mk'),source_commit=archive['commit'],
        top=top,params=params,sources_sha256={s:sha(src/s) for s in sources},
        actual_synth_netlist=dict(path=str(net),sha256=sha(net),bytes=net.stat().st_size,
            macro_type_occurrences=net.read_text().count('ot_sram_1r1w_512x128_m4_r2c2')),
        synth_snapshot=dict(path=str(synth_input),sha256=sha(synth_input)) if synth_input else None,
        boundary=result, scope='Generic elaboration from actual full-shape sources/params; mapped netlist is inventory only')
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(result))
    if result['verdict'] == 'REFUSE':raise SystemExit(3)
if __name__ == '__main__': main()
