#!/usr/bin/env python3
"""Explicit common833ps PC master profile. Never infer the profile from SDC."""
import hashlib
import json
import re
from pathlib import Path

CHAIN = {
    'qkd_static_kv_pc_path_fan_nc.sv': 'static_embedding_20261014',
    'qkd_static_kv_pc_path_fan_nc_b.sv': 'static_embedding_20261014',
    **{n + '.sv': 'static_kv_20261014' for n in (
        'ot_qkd_static_ctrl_pc_emb', 'ot_qkd_static_kv_timing',
        'qkd_controller_hbm_calendar', 'qkd_ctrl_pc_host_static',
        'qkd_ctrl_pc_host_static_core', 'qkd_ctrl_pc_nc', 'qkd_kv_landing_cal',
        'qkd_kvpc_sram_clones_1019', 'qkd_static_kv_pc_path_nc',
        'qkd_static_kv_phase_launch', 'qkd_static_kv_return_calendar')},
}


def source(repo, original):
    """Use the current reviewed RTL chain, preserving generated interface leaves."""
    original = Path(original)
    return Path(repo) / 'rtl/qwen_sys' / CHAIN[original.name] / original.name if original.name in CHAIN else original


def apply_kit(kit):
    kit = Path(kit)
    records = []
    for p in sorted((kit / 'rtl').glob('*.sv')):
        text = p.read_text()
        if re.search(r'\bmodule\s+qkd_static_kv_pc_path_fan_nc_b_head_p\b', text):
            # A current source assembly may already carry the common-clock parameter.
            decl = re.search(r'(module\s+qkd_static_kv_pc_path_fan_nc_b_head_p\s*#\s*\()(?P<params>[^;]*?)\)\s*\(', text, re.S)
            if not decl: raise ValueError('head-p module parameter census')
            if not re.search(r'\bCORE_CLOCK\s*=', decl['params']):
                text = text[:decl.end(1)] + 'parameter integer CORE_CLOCK = 0,\n' + text[decl.end(1):]
            child = re.search(r'(qkd_static_kv_pc_path_emb_nc_b\s*#\s*\()(?P<params>[^;]*?)\)(?P<tail>\s+u_pce\s*\()', text, re.S)
            if not child: raise ValueError('head-p u_pce parameter census')
            clocks = re.findall(r'\.CORE_CLOCK\s*\(\s*([^)]*)\)', child['params'])
            if clocks and clocks != ['CORE_CLOCK']: raise ValueError('head-p u_pce clock forwarding differs')
            if not clocks:
                text = text[:child.end(1)] + '.CORE_CLOCK(CORE_CLOCK),' + text[child.end(1):]
        # Select the actual u_pc independent of named-parameter order; never duplicate an existing selection.
        selected = [0]
        def select(match):
            params = match['params']
            clocks = re.findall(r'\.CORE_CLOCK\s*\(\s*([^)]*)\)', params)
            if clocks and clocks != ['1']: raise ValueError('actual PC u_pc clock selection differs')
            selected[0] += 1
            return match.group(0) if clocks else match.group(1) + '.CORE_CLOCK(1),' + params + ')' + match['tail']
        text = re.sub(r'(qkd_static_kv_pc_path_fan_nc_b(?:_head_p)?\s*#\s*\()(?P<params>[^;]*?)\)(?P<tail>\s+u_pc\s*\()', select, text, flags=re.S)
        if selected[0]: records.append(dict(file=p.name, selected_u_pc_instances=selected[0]))
        p.write_text(text)
    if not records: raise ValueError('no actual PC u_pc instance selected for CORE_CLOCK=1')
    # Require the full RTL timing path rather than inserting an unsupported param.
    for n in ('qkd_static_kv_pc_path_nc.sv', 'qkd_ctrl_pc_nc.sv', 'ot_qkd_static_ctrl_pc_emb.sv', 'ot_qkd_static_kv_timing.sv'):
        if 'CORE_CLOCK' not in (kit/'rtl'/n).read_text(): raise ValueError('missing common833 chain: '+n)
    r = dict(schema='opentallas.kvspc.core_clock.v1', controller_ps=833,
             optin='CORE_CLOCK=1 at actual u_pc; default RTL CORE_CLOCK=0 retained',
             records=records, physical_minimum_cycles=dict(tFAW=19,tRAS=35,tRCD=24,tRP=20,tWRR=35,tWTR=18),
             refresh_deadlines=dict(tREFIPB=144,tREFI=4680),
             rtl_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((kit/'rtl').glob('*.sv'))})
    (kit/'kvspc_core_clock.json').write_text(json.dumps(r,indent=1)+'\n')
    return r
