#!/usr/bin/env python3
"""Exact root wrapper contract check; arithmetic and F20 protocol abstracted.

Run through fleet admission. The separate actual native component gate must
qualify arithmetic; this script never claims it.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]
RTL='rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_root_static.sv'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--baseline-ref',default='51f4c117ca5')
    a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    baseline=subprocess.check_output(['git','show',f'{a.baseline_ref}:{RTL}'],cwd=ROOT,text=True)
    def parameters(text):
        return [(n,r.split('//')[0].strip().rstrip(',').strip()) for n,r in
                re.findall(r'parameter\s+(?:integer|\[[^]]+\])\s+(\w+)\s*=\s*([^\n]+)',text.split(')(\n',1)[0])]
    old_params=parameters(baseline);new_params=parameters((ROOT/RTL).read_text())
    if len(old_params)!=12 or new_params[:12]!=old_params:
        raise RuntimeError('legacy12 positional parameter/default ABI changed')
    (out/'root_original.sv').write_text(baseline.replace('module ot_hbm_hc_root_static #(',
                                                        'module ot_hbm_hc_root_orig #('))
    files=[RTL,'rtl/lib/ot_rst_relay.sv','tools/hbm_layer_vehicle/owned_root_stubs.sv',
           'tools/hbm_layer_vehicle/tb_owned_root_wrapper.sv','tools/hbm_layer_vehicle/tb_owned_root_positional.sv']
    sources={}
    for f in files:
        shutil.copy2(ROOT/f,out/Path(f).name)
        sources[f]=hashlib.sha256((ROOT/f).read_bytes()).hexdigest()
    results=[]
    for mut,bad,expected in ((0,False,'OWNED_ROOT_WRAPPER PASS'),(8,False,'owned global-row mismatch'),(9,False,'owned weight-base mismatch'),(0,True,'OWNED_ROOT_BAD_ROW_CAUGHT')):
        label='badrow' if bad else str(mut)
        extra=['-DBAD_ROW'] if bad else []
        with (out/f'build{label}.log').open('w') as log:
            subprocess.run(['iverilog','-g2012',f'-DMUT={mut}',*extra,'-s','tb_owned_root_wrapper','-o',f'sim{label}',
                            'tb_owned_root_wrapper.sv','owned_root_stubs.sv','root_original.sv',
                            'ot_hbm_hc_root_static.sv','ot_rst_relay.sv'],cwd=out,
                           stdout=log,stderr=subprocess.STDOUT,check=True)
        with (out/f'run{label}.log').open('w') as log:
            p=subprocess.run(['vvp',f'sim{label}'],cwd=out,stdout=log,stderr=subprocess.STDOUT)
        text=(out/f'run{label}.log').read_text()
        if (p.returncode==0)!=(mut==0) or expected not in text:
            raise RuntimeError(f'wrapper case{mut} failed expected result')
        results.append(dict(mutant=mut,bad_row=bad,rc=p.returncode,result='PASS' if mut==0 else 'CAUGHT'))
    with (out/'buildpositional.log').open('w') as log:
        subprocess.run(['iverilog','-g2012','-s','tb_owned_root_positional','-o','simpositional',
                        'tb_owned_root_positional.sv','owned_root_stubs.sv','ot_hbm_hc_root_static.sv',
                        'ot_rst_relay.sv'],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
    with (out/'runpositional.log').open('w') as log:
        subprocess.run(['vvp','simpositional'],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
    if 'OWNED_ROOT_LEGACY_POSITIONAL_ABI_PASS' not in (out/'runpositional.log').read_text():
        raise RuntimeError('compiled legacy positional ABI check failed')
    summary=dict(schema='opentallas.hc_owned_root_wrapper.v1',baseline_ref=a.baseline_ref,
        baseline_sha256=hashlib.sha256(baseline.encode()).hexdigest(),source_sha256=sources,
        results=results,legacy_parameter_prefix=old_params,legacy_positional_abi_preserved=True,legacy_positional_compiled=True,cycles=1200,clock_period_fs=833000,
        scope='default wrapper comparison plus owned command/base/global-row/store checks',
        arithmetic_abstracted=True,f20_protocol_abstracted=True,qualifies_owned_arithmetic=False,
        qualifies_current_die=False,qualifies_native_layer=False,qualifies_native_chain=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))


if __name__=='__main__':main()
