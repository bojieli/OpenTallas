#!/usr/bin/env python3
"""Snapshot selected PV profiles for review. Never manufactures native qualification.

The mutable kit spec supplies *candidate intent*, not proof of routed parameters.
Exact selected artifacts, spec, all listed source hashes and old gate receipt are
recorded. Strict expansion refuses these candidates until a matching immutable
native_parameter_profile.v1 receipt is independently reviewed and attached.
"""
import argparse
import json
from pathlib import Path
import kv_expand_parameters as P

KITS = dict(ot_qwen_tp8_pv_slice_t='qkd_pv_slice_rstpin_r5',
            ot_qwen_tp8_pv_join_t='qkd_pv_join_sfe_r6',
            ot_qwen_tp8_pv_wide_ctl_tb='qkd_pv_ctl_tb1')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a=ap.parse_args(); profiles={}; audit={}
    for module,kit in KITS.items():
        kd=Path('physical/ref_tile')/kit
        specpath=kd/'spec.json'; spec=json.loads((a.root/specpath).read_text())
        if spec['top'] != module: raise ValueError(f'{kit}: wrong top')
        rtl=Path('rtl/hdc/nearhbm')/('ot_qwen_tp8_pv_wide_ctl_tb.sv' if module.endswith('_tb') else 'ot_qwen_tp8_pv_wide_pair.sv')
        defaults=P.integer_defaults((a.root/rtl).read_text(),module)
        params=dict(defaults)
        for key,value in spec['params'].items():
            if key not in defaults or type(value) is not int or not -(1<<31)<=value<(1<<31):
                raise ValueError(f'{kit}: unsupported kit parameter {key}={value!r}')
            params[key]=value
        view=kd/'views'/module
        identity=P.artifact_identity(a.root,str(view),str(rtl))
        profiles[module]=dict(parameters=params,identity=identity)
        gp=kd/'gate_result.json'
        audit[module]=dict(native_qualified=False,status='MISSING_FROZEN_MATCHING_NATIVE_PROFILE',
                           kit_spec=dict(path=str(specpath),sha256=P.sha(a.root/specpath)),
                           candidate_parameter_intent=spec['params'],
                           source_sha256={p:P.sha(a.root/p) for p in spec['sources']},
                           old_gate_receipt=dict(path=str(gp),sha256=P.sha(a.root/gp)),
                           reason='Mutable spec and historical gate receipt do not establish exact frozen routed parameter identity')
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'candidate_profiles.json').write_text(json.dumps(profiles,indent=2)+'\n')
    (a.out/'candidate_audit.json').write_text(json.dumps(audit,indent=2)+'\n')

if __name__=='__main__': main()
