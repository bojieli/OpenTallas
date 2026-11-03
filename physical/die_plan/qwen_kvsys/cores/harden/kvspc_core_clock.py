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
    if 'rtl_rf1' in original.parts:   # RF-KV1 (DIE-KV-64/RF-B 11-03): a re-form source copy is kept as named in the core json
        return original
    return Path(repo) / 'rtl/qwen_sys' / CHAIN[original.name] / original.name if original.name in CHAIN else original


def stage_calendar_alias_candidate(kit):
    """A user-match proposal, never a constraint: normal LEC proves or drops it.

    ROW0=64 plus a six-bit layer sets row[6] on exactly the same valid-go
    branch as static_cmd_owner, and both reset to zero. Synthesis can merge
    these registers; rare boot traffic can hide the twin from random discovery.
    """
    kit = Path(kit)
    path = kit / 'rtl/qkd_static_kv_pc_path_nc.sv'
    if not path.is_file() or not re.search(
            r'qkd_controller_hbm_calendar\s*#\s*\([^;]*?\.ROW0\s*\(\s*64\s*\)[^;]*?\)\s*u_calendar',
            path.read_text(), re.S):
        return None
    key = 'ff:u_dut.u_leaf.u_pc.u_pce.u_path.u_calendar.active_row[6]'
    partner = 'ff:u_dut.u_leaf.u_pc.u_pce.u_path.u_calendar.static_cmd_owner'
    proposal = ['gold', key, ['eq', 'gold', partner, 0]]
    target = kit / 'lec_hints.json'
    hints = json.loads(target.read_text()) if target.is_file() else []
    # Preserve an existing caller proposal, including a deliberately wrong control.
    if not any(len(h) >= 2 and h[0:2] == proposal[0:2] for h in hints):
        hints.append(proposal)
    target.write_text(json.dumps(hints, indent=1) + '\n')
    return dict(file='lec_hints.json', untrusted=True, parameter_guard='ROW0=64',
                validation='native LEC induction/reset/kept-register/all-compare gates; no waiver')


def apply_kit(kit):
    kit = Path(kit)
    records = []
    for p in sorted((kit / 'rtl').glob('*.sv')):
        text = p.read_text()
        if re.search(r'\bmodule\s+qkd_static_kv_pc_path_fan_nc_b_head_p\b', text):
            # This generated PC-identity variant remains the same module/ports.
            # Add the optin parameter and forward it to its actual u_pce child.
            # RF-KV1 (DIE-KV-64/RF-B 11-03): idempotent -- a source that already carries the opt-in (the 11-01 HHP core
            # RTL) is left as is; a second insertion was a duplicate parameter (gold LEC frontend: elaboration error).
            hm = re.search(r'module\s+qkd_static_kv_pc_path_fan_nc_b_head_p\s*#\s*\((.*?)\)\s*\(', text, re.S)
            if not (hm and re.search(r'parameter\s+integer\s+CORE_CLOCK\b', hm.group(1))):
                text, n = re.subn(r'(module\s+qkd_static_kv_pc_path_fan_nc_b_head_p\s*#\s*\()', r'\1parameter integer CORE_CLOCK = 0,\n', text)
                if n != 1: raise ValueError('head-p module parameter census')
            if not re.search(r'qkd_static_kv_pc_path_emb_nc_b\s*#\s*\([^;]*?\.CORE_CLOCK\(', text):
                text, n = re.subn(r'(qkd_static_kv_pc_path_emb_nc_b\s*#\s*\()(?=\.MU\(MU\))', r'\1.CORE_CLOCK(CORE_CLOCK),', text)
                if n != 1: raise ValueError('head-p u_pce parameter census')
        # Actual physical PC/PC-head leaf, including private-port renamed copies.
        pattern = r'(qkd_static_kv_pc_path_fan_nc_b(?:_head_p)?\s*#\s*\()(?=\.MU\(1\))'
        # idempotent: an instance whose parameter list already sets CORE_CLOCK keeps it (no duplicate assignment)
        count = 0
        def _ins(m):
            nonlocal count
            plist = re.split(r'\)\s*u_\w+\s*\(', text[m.end():m.end() + 600], 1)[0]   # this instance's #( ... )
            if '.CORE_CLOCK(' in plist:
                return m.group(1)
            count += 1
            return m.group(1) + '.CORE_CLOCK(1),'
        text = re.sub(pattern, _ins, text)
        existing = sum('.CORE_CLOCK(1)' in re.split(r'\)\s*u_\w+\s*\(', text[m.end():m.end() + 600], 1)[0]
                       for m in re.finditer(r'qkd_static_kv_pc_path_fan_nc_b(?:_head_p)?\s*#\s*\(', text))
        if count or existing:
            records.append(dict(file=p.name, selected_u_pc_instances=max(count, existing)))
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
    r['calendar_alias_candidate'] = stage_calendar_alias_candidate(kit)
    (kit/'kvspc_core_clock.json').write_text(json.dumps(r,indent=1)+'\n')
    return r
