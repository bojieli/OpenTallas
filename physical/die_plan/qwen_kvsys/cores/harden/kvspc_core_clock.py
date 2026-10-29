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
            # This generated PC-identity variant remains the same module/ports.
            # Add the optin parameter and forward it to its actual u_pce child.
            header = re.search(r'module\s+qkd_static_kv_pc_path_fan_nc_b_head_p\s*#\s*\((.*?)\)\s*\(', text, re.S)
            if header is None:
                raise ValueError('head-p module parameter census')
            declared = len(re.findall(r'\bparameter\s+(?:integer\s+)?CORE_CLOCK\b', header.group(1)))
            if declared > 1:
                raise ValueError('head-p duplicate CORE_CLOCK parameter')
            if not declared:
                pos = header.start(1)
                text = text[:pos] + 'parameter integer CORE_CLOCK = 0,\n' + text[pos:]
            child = re.search(r'qkd_static_kv_pc_path_emb_nc_b\s*#\s*\((.*?)\)\s+u_pce\s*\(', text, re.S)
            if child is None:
                raise ValueError('head-p u_pce parameter census')
            forwarded = len(re.findall(r'\.CORE_CLOCK\s*\(', child.group(1)))
            if forwarded > 1:
                raise ValueError('head-p duplicate u_pce CORE_CLOCK assignment')
            if not forwarded:
                pos = child.start(1)
                text = text[:pos] + '.CORE_CLOCK(CORE_CLOCK),' + text[pos:]
        # Actual physical PC/PC-head leaf, including private-port renamed copies.
        pattern = r'(qkd_static_kv_pc_path_fan_nc_b(?:_head_p)?\s*#\s*\()(\s*\.[^;]*?)(\)\s+u_pc\s*\()'
        count = 0
        def select_u_pc(match):
            nonlocal count
            args = match.group(2)
            if not re.search(r'\.MU\s*\(\s*1\s*\)', args):
                return match.group(0)
            values = list(re.finditer(r'\.CORE_CLOCK\s*\(\s*([^()]*)\s*\)', args))
            if len(values) > 1:
                raise ValueError('physical u_pc duplicate CORE_CLOCK assignment')
            if values:
                value = values[0].group(1).strip()
                if value not in ('0', '1'):
                    raise ValueError('physical u_pc CORE_CLOCK must be literal 0 or 1')
                args = args[:values[0].start()] + '.CORE_CLOCK(1)' + args[values[0].end():]
            else:
                args = '.CORE_CLOCK(1),' + args
            count += 1
            return match.group(1) + args + match.group(3)
        text = re.sub(pattern, select_u_pc, text, flags=re.S)
        if count: records.append(dict(file=p.name, selected_u_pc_instances=count))
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
