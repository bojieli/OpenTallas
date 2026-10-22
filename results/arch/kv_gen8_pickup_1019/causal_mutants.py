#!/usr/bin/env python3
"""Correct selected-leaf MUT controls; preserve original MUT=1 audits."""
import json, pathlib, subprocess
R=pathlib.Path('/srv/opentallas-scratch/claude/kv-params-1019')
# Each value is the literal RTL predicate affecting this exact selected module.
CAUSAL={'ot_qkh_head_score4_native':3,'ot_qkh_head_stin_native':4,
        'ot_qkh_head_stk_native':5,'qkh_head_gather_stage':41,
        'qkd_seq_fan_s':9,'qkd_seq_xs_s':8}
for mod,mut in CAUSAL.items():
    f=R/'runs'/f'{mod}.audit.json'
    # Live positive seq_xs has not emitted an audit yet; its existing MUT=1 request is exact except MUT.
    if not f.exists():
        if mod=='qkd_seq_xs_s':
            d={'rtl':'rtl/qwen_sys/static_kv_20261014/qkd_seq_static_s.sv','view':'physical/ref_tile/qkd_seq_xs_s/views/qkd_seq_xs_s','parameters':{'MUT':0},'archive_run':str(R/'arch/qkd_seq_xs_s/qkd_seq_xs_s-x1-9c9c3d7b5')}
        else: raise RuntimeError(f'missing {f}')
    else: d=json.loads(f.read_text())
    n=f'{mod}.causal_mut{mut}'
    if (R/'runs'/f'{n}.audit.json').exists(): continue
    cmd=['python3','tools/qwen_kv_die/kv_param_native_audit.py','audit','--root','.', '--module',mod,'--rtl',d['rtl'],'--view',d['view'],'--params',json.dumps(dict(d['parameters'],MUT=mut)), '--archive-run',d['archive_run'],'--work',str(R/'runs'/n),'--out',str(R/'runs'/f'{n}.audit.json'),'--expect','fail']
    rl=pathlib.Path(d['archive_run'])/'reset_landing.json'
    if rl.exists(): cmd+=['--reset-landing',str(rl)]
    print(n,flush=True)
    subprocess.run(cmd,cwd=R/'src',check=True)
