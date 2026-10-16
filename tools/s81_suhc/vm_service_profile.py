#!/usr/bin/env python3
"""Exact, source-pinned S81 VM service profiles for the static reservation checker (S-ELEM-A, 2026-10-15).

The generic checker (static_vm_reservations.check) only enforces caller-supplied MINIMUM path delays and one
commit_cycle per write, so stale minima (L15 read / K11 commit) were admitted for the selected native VM
(compiler audit results/arch/s81_vm_compiler_audit_20261015).  A profile is opt-in: a contract that names
"vm_service_profile" is checked against the exact fixed calendar below; a contract without it keeps the
historical/default behaviour unchanged (no global default switch).

Selected native construction READ_PIPE=4 / CAP_PIPE=2 / WSCATTER_PIPE=1 (measured on the full 128-SRAM VM):
  read : external pin P -> macro r_ce edge P+7 (raw read), returned data at P+16
  write: core source pin P -> macro w_ce edge P+10+lane (raw write), returned commit at P+12+lane, lane 0..2 =
         the scheduled same-bank capture lane
  visibility: a dependent read sees the new value only if its raw read edge is strictly after the matching raw
         write edge (macro is read-before-write on the same edge): Q+7 > P+10+lane, i.e. Q >= P+4+lane.
WSCATTER_PIPE=0 (same READ/CAP) is kept as its own measured profile: raw write P+9+lane, returned P+11+lane.
All cycles are stream edges (VM stream clock).  Every number is fixed: equality, never a minimum.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# name -> exact calendar + the receipts that measured it (paths must exist and hash-match the contract evidence)
PROFILES = {
    's81_vm_r4_c2_w1': dict(
        rtl_tuple={'READ_PIPE': 4, 'CAP_PIPE': 2, 'WSCATTER_PIPE': 1},
        read_raw=7, read_return=16, write_raw=10, write_return=12, max_lane=2,
        receipts=['results/rtl/s81_vm_raw_read_calendar_20261015/record.json',
                  'results/rtl/s81_vm_scatter_pipe1_raw_20261015/record.json',
                  'results/rtl/s81_vm_master_current_scatter_20261015/record.json']),
    's81_vm_r4_c2_w0': dict(
        rtl_tuple={'READ_PIPE': 4, 'CAP_PIPE': 2, 'WSCATTER_PIPE': 0},
        read_raw=7, read_return=16, write_raw=9, write_return=11, max_lane=2,
        receipts=['results/rtl/s81_vm_master_current_scatter_20261015/record.json']),
}
# These measurements are immutable evidence, rather than caller-provided
# claims about the current checkout. A changed measurement needs a reviewed
# new profile; evidence_for() cannot create a new measurement by rehashing RTL.
MEASURED_MANIFEST = 'results/rtl/s81_vm_master_current_scatter_20261015/source_manifest.json'
MEASURED_ARTIFACT_SHA256 = {'results/rtl/s81_vm_master_current_scatter_20261015/source_manifest.json': '62c13808cdc88702a8d0349150bc3fd9ccc7c552f5257f0bea23bcd4736ef0ac', 'results/rtl/s81_vm_raw_read_calendar_20261015/record.json': 'aa3e5047b8261c0a0b87142f19fbc5634029fab94ad60ddd7b0b131c747c7b51', 'results/rtl/s81_vm_scatter_pipe1_raw_20261015/record.json': '6f4e4b93032c35ab6f9d9a34de018bd5acd8bbbb8531d979ba3ed3e11a66f057', 'results/rtl/s81_vm_master_current_scatter_20261015/record.json': '5dab5cf5e2b5d2901f66c4df7af450aa21d7e24d7ea5f1a4c8338d9b63821ce1'}
# The profile starts at read pins / core write-source pins. The serial CDC
# adapter's reset implementation lies outside that boundary; its own fixed
# phase, startup and physical proof remain separate. The testbench is evidence
# machinery, never an implementation of the measured core data path.
OUTSIDE_PROFILE_BOUNDARY = {
    'rtl/dsrom_sys/s81_ph/vm/ot_s81_vm_x34.sv': 'Serial-to-stream CDC upstream of the core source-pin boundary; separately qualified',
    'rtl/dsrom_sys/s81_ph/test/tb_dsfd_sp_vm_static.sv': 'Testbench, not instantiated production RTL',
}

# RTL whose bytes define the calendar; the contract must pin every one (stale source -> invalid profile)
RTL_SOURCES = [
    'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm_static.sv',
    'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_core.sv',
    'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static512_suhc.sv',
    'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_slice128_suhc.sv',
    'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_scatter_b8_out.sv',
    'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_bank128.sv',
    'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_read_router_p.sv',
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(contract: dict, source_root: Path | None = None):
    """-> (profile dict | None, [invalid reasons]).  None + [] = no profile requested (legacy behaviour)."""
    req = contract.get('vm_service_profile')
    if req is None:
        return None, []
    if not isinstance(req, dict) or req.get('name') not in PROFILES:
        return None, ['unknown_vm_service_profile']
    prof = PROFILES[req['name']]
    bad = []
    if req.get('rtl_tuple') != prof['rtl_tuple']:
        bad.append('vm_service_profile_rtl_tuple_mismatch')
    # Every logical 512-bit row spans four physical 128-bit SRAMs;
    # there are 32 address banks, selected by the actual RTL XOR map.
    # A different map can conceal collisions even with correct edge ages.
    if contract.get('banks') != 32 or contract.get('bank_mapping', 'rowmod') != 'xor_row7_5_shift2':
        bad.append('vm_service_profile_bank_mapping_mismatch')
    if contract.get('bank_port_capacities') is None and contract.get('bank_ops_per_cycle') != 1:
        bad.append('vm_service_profile_bank_capacity_mismatch')
    root = (source_root or ROOT).resolve()
    pinned = {}
    for item in req.get('evidence') or []:
        if not isinstance(item, dict) or 'path' not in item or 'sha256' not in item:
            bad.append('invalid_vm_service_profile_evidence'); continue
        pinned[item['path']] = item['sha256']
    for path in prof['receipts'] + [MEASURED_MANIFEST] + RTL_SOURCES:
        if path not in pinned:
            bad.append(f'vm_service_profile_unpinned:{path}'); continue
        p = (root / path).resolve()
        try:
            if not p.is_relative_to(root) or sha(p) != pinned[path]:
                bad.append(f'vm_service_profile_stale:{path}')
        except OSError:
            bad.append(f'vm_service_profile_missing:{path}')
    for path in prof['receipts'] + [MEASURED_MANIFEST]:
        try:
            if sha(root / path) != MEASURED_ARTIFACT_SHA256[path]:
                bad.append(f'vm_service_profile_unmeasured_artifact:{path}')
        except OSError:
            bad.append(f'vm_service_profile_missing_measurement:{path}')
    try:
        manifest_path = root / MEASURED_MANIFEST
        if sha(manifest_path) == MEASURED_ARTIFACT_SHA256[MEASURED_MANIFEST]:
            measured = json.loads(manifest_path.read_text())
            for path, expected in measured.items():
                if path in OUTSIDE_PROFILE_BOUNDARY:
                    continue
                source = (root / path).resolve()
                if not source.is_relative_to(root) or sha(source) != expected:
                    bad.append(f'vm_service_profile_unmeasured_source:{path}')
    except (OSError, ValueError, TypeError):
        bad.append('vm_service_profile_invalid_measured_manifest')
    if req.get('measured_native_bounds_override') is not None:
        bad.append('vm_service_profile_forbids_caller_bounds_override')
    return (prof if not bad else None), bad


def evidence_for(name: str, source_root: Path | None = None) -> list:
    """the evidence list a compiler emits for the CURRENT source (helper for producers and tests)."""
    root = (source_root or ROOT)
    return [dict(path=p, sha256=sha(root / p)) for p in PROFILES[name]['receipts'] + [MEASURED_MANIFEST] + RTL_SOURCES]


def check_event(prof: dict, event: dict) -> list:
    """exact calendar of one read/write event (issue_cycle = the VM pin edge P); returns violation dicts."""
    out = []
    eid = event.get('id')
    p = event['issue_cycle']
    if type(event.get('raw_cycle')) is not int or event['raw_cycle'] < 0:
        out.append(dict(kind='profile_raw_cycle_unbound', event=eid, actual=event.get('raw_cycle')))
    if event['kind'] == 'read':
        if event.get('raw_cycle') != p + prof['read_raw']:
            out.append(dict(kind='profile_read_raw_edge', event=eid, expected=p + prof['read_raw'], actual=event.get('raw_cycle')))
        if event['response_cycle'] != p + prof['read_return']:
            out.append(dict(kind='profile_read_return_edge', event=eid, expected=p + prof['read_return'], actual=event['response_cycle']))
    else:
        lane = event.get('lane')
        if type(lane) is not int or not 0 <= lane <= prof['max_lane']:
            out.append(dict(kind='profile_write_lane_unbound', event=eid, lane=lane)); return out
        if event.get('raw_cycle') != p + prof['write_raw'] + lane:
            out.append(dict(kind='profile_write_raw_edge', event=eid, expected=p + prof['write_raw'] + lane, actual=event.get('raw_cycle')))
        if event['commit_cycle'] != p + prof['write_return'] + lane:
            out.append(dict(kind='profile_write_returned_commit_edge', event=eid, expected=p + prof['write_return'] + lane,
                            actual=event['commit_cycle']))
    return out


def check_dependency(prof: dict, producer: dict, consumer: dict) -> list:
    """new-value visibility on the raw macro edges (read-before-write on the same edge)."""
    pr, cr = producer.get('raw_cycle'), consumer.get('raw_cycle')
    if type(pr) is not int or type(cr) is not int:
        return [dict(kind='profile_dependency_raw_unbound', producer=producer.get('id'), consumer=consumer.get('id'))]
    if cr <= pr:
        return [dict(kind='profile_consume_before_raw_write', producer=producer.get('id'), consumer=consumer.get('id'),
                     raw_write=pr, raw_read=cr, min_read_issue=pr - prof['read_raw'] + 1)]
    return []
