#!/usr/bin/env python3
"""Inline package imports for Yosys while preserving original RTL byte-for-byte."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RTL=ROOT/'rtl/qwen_sys/emb_hbm_20261008'
NAMES=('ot_qfd_emb_strip','ot_qfd_emb_gw','ot_qfd_emb_pcport','ot_qwen_die_hub_emb')
def generate():
    pkg=(RTL/'ot_qfd_emb_pkg.sv').read_text()
    body=pkg.split('package ot_qfd_emb_pkg;',1)[1].rsplit('endpackage',1)[0]
    out=RTL/'synth';out.mkdir(exist_ok=True)
    manifest={'schema':'opentallas.emb_hbm_package_inline.v1','transformation':'Replace exactly one import ot_qfd_emb_pkg::*; with the identical package body (module-local localparams and functions); original sources are unchanged.','package_sha256':hashlib.sha256(pkg.encode()).hexdigest(),'sources':{}}
    for name in NAMES:
        text=(RTL/(name+'.sv')).read_text();needle='import ot_qfd_emb_pkg::*;'
        assert text.count(needle)==1,name
        expanded=text.replace(needle,body)
        target=out/(name+'.sv');target.write_text(expanded)
        manifest['sources'][name]={'original_sha256':hashlib.sha256(text.encode()).hexdigest(),'generated_sha256':hashlib.sha256(expanded.encode()).hexdigest()}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest
if __name__=='__main__':print(json.dumps(generate(),indent=2))
