#!/usr/bin/env python3
"""Portable Q2 review packet; no simulation, model adoption or physical build."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALENDAR = 'results/uarch/qwen_rom_KV_owner_calendar_20261002/blocked_join_r2.json'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_snapshot(packet):
    manifest = json.loads((packet / 'provider_manifest.json').read_text())
    if (packet / 'proposal.json').exists():
        proposal = json.loads((packet / 'proposal.json').read_text())
        raw = (packet / 'calendar_snapshot.json').read_bytes()
        if digest(raw) != proposal['calendar_sha256']:
            raise ValueError('Calendar snapshot hash mismatch')
        calendar = json.loads(raw)
        pins = {item['source_path']: item['sha256'] for item in manifest['files']}
        if pins != calendar['provider_source_sha256'] or manifest['provider_ref'] != calendar['provider_ref']:
            raise ValueError('Provider manifest differs from source-pinned calendar')
    for item in manifest['files']:
        if digest((packet / item['snapshot']).read_bytes()) != item['sha256']:
            raise ValueError('Provider snapshot hash mismatch: ' + item['source_path'])
    return manifest


def finite_service_scenarios(raw):
    names = ['REQ', 'CL', 'BURST', 'RSP', 'RP', 'RCDRD', 'RFC']
    ps = {n: int(re.search(r'parameter integer ' + n + r'_PS\s*=\s*(\d+)', raw).group(1)) for n in names}
    hit = sum(ps[n] for n in ['REQ', 'CL', 'BURST', 'RSP'])
    scenarios = {'row_hit': hit, 'row_conflict': hit + ps['RP'] + ps['RCDRD'],
                 'row_conflict_plus_refresh': hit + ps['RP'] + ps['RCDRD'] + ps['RFC']}
    return {name: {'service_ps': latency, 'cycles_at_1p2GHz': (latency * 3 + 2499) // 2500,
                   'serialized_service_only_cycles_per_4MiB_layer': 131072 * ((latency * 3 + 2499) // 2500)}
            for name, latency in scenarios.items()}


def create(provider_root, output):
    if output.exists():
        raise ValueError('Refusing to overwrite evidence')
    calendar = json.loads((ROOT / CALENDAR).read_text())
    ref = calendar['provider_ref']
    snapshots = []
    blobs = {}
    for path, expected in calendar['provider_source_sha256'].items():
        raw = subprocess.check_output(['git', 'show', ref + ':' + path], cwd=provider_root)
        if digest(raw) != expected:
            raise ValueError('Provider differs from pinned calendar')
        destination = 'provider_snapshot/' + path
        blobs[destination] = raw
        snapshots.append(dict(source_path=path, snapshot=destination, sha256=expected))
    from qwen_rom_integration_preflight import MAPPING
    source_paths = list(MAPPING.values()) + [
        'tools/uarch_model.py', 'tools/qwen_rom_q2_g0_packet.py',
        'rtl/hdc/kv/ot_hdc_qwen_kv_system.sv',
        'rtl/hdc/kv/ot_hdc_qwen_hbm_sector_bridge.sv',
        'rtl/hdc/kv/ot_hdc_qwen_kv_phys_arbiter.sv',
        'rtl/hdc/kv/ot_hdc_qwen_kv_tail_bank_port.sv',
        'rtl/hdc/kv/ot_hdc_hbm_model.sv']
    sources = {path: (ROOT / path).read_bytes() for path in source_paths}
    bridge = sources[source_paths[-4]].decode()
    arbiter = sources[source_paths[-3]].decode()
    if 'assign phys_req_len = 1;' not in bridge or 'state<=is_write ? IDLE : RSP;' not in arbiter:
        raise ValueError('Re-review changed serialization/visibility contract')
    proposal = dict(
        schema='opentallas.qwen-rom-q2-g0-proposal.v1', status='BLOCKED_G0',
        predecessor_commits=['475004314', '36c0fb00e'],
        calendar_record=CALENDAR, calendar_sha256=digest((ROOT / CALENDAR).read_bytes()),
        source_sha256={p: digest(raw) for p, raw in sources.items()},
        source_identity_scope='Seven current w12 runtime files separately pinned; not asserted equal to captured original or any physical netlist.',
        configuration=dict(tp=4, layers=36, context=8192, heads_per_die=2, head_dim=128,
                           groups=6144, tiles_per_die=1536, successor_arithmetic_extra=55),
        storage=dict(persistent_logical_bytes_per_die=150994944, layer_bytes=4194304,
                     physical_allocation_reserved=False, tile_sram_bytes_per_die=12582912,
                     macro_only_area_mm2_per_die=129.67316324351998,
                     finite_tail_ports_replicas_mux_area=None),
        refill=dict(sector_bytes=32, sectors_per_layer=131072, outstanding_read_requests=1,
                    current_write_completion_input=False, incremental_aggregate_bytes=0,
                    source_timing_scenarios=finite_service_scenarios(sources[source_paths[-1]].decode()),
                    timing_boundary='Legacy HBM model assumptions, including 10ns request and response paths; cycles converted analytically at 1.2GHz. Excludes FSM/codec/credit/CDC stalls. Scenarios are not measured latency or a worst-case bound.',
                    unified_exposed_refill_cycles=None),
        next_g0=[
            dict(owner='Euclid + Maxwell', task='Re-pin seven runtime sources and +55 whole MLAT/tree/MUL/KV_PREP path to current unified model; retain +54 FAIL.'),
            dict(owner='Maxwell + Kepler', task='Bind 72 logical homes to physical bases/stacks, TP4 rank identity, finite read/write credits, actual write visibility and reverse retirement. Price serialized service and tail ports once against existing KV byte ledger.'),
            dict(owner='Archimedes + Euclid', task='Match exact tile/spine elaboration and macro views to source pins; price 1536 tiles/die with logic, halos, hub routing, clock/PG and service slots. Close SS setup 60ps and FF hold 25ps at 0.833333ns; historical TT or different arithmetic cannot transfer.')],
        runtime_proposal=dict(immediate='Offline portable manifest replay and focused source/model tests only',
                              execution_admitted=False, engine_build_admitted=False, place_route_admitted=False,
                              second_position_queued=False, full_token_repeat_queued=False,
                              live_handle=None, heavy_jobs_launched=0,
                              requested_local_hardcaps=dict(cpu=2, memory_MiB=2048, aggregate_disk_MiB=256,
                                                          wall_seconds=None,CPU_time_seconds=None,RLIMIT_FSIZE='unlimited',
                                                          incremental_objects_retained=True),
                              resource_boundary='Review caps only, not measured simulator requirements; no PVE2/PVE3 tasks. Any subsequent physical execution needs composed G0 and parent admission.'),
        adoption=False, actual_provider_join=False)
    if any((ROOT / p).read_bytes() != raw for p, raw in sources.items()):
        raise ValueError('Sources changed during capture')
    output.mkdir(parents=True)
    (output / 'calendar_snapshot.json').write_bytes((ROOT / CALENDAR).read_bytes())
    for path, raw in blobs.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (output / 'provider_manifest.json').write_text(json.dumps(dict(provider_ref=ref, files=snapshots,
        boundary='Exact external r14 calendar-review inputs; portable review snapshot, not compile closure or actual provider join.'), indent=2) + '\n')
    (output / 'proposal.json').write_text(json.dumps(proposal, indent=2, sort_keys=True) + '\n')
    verify_snapshot(output)
    return proposal


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--provider-root', type=Path)
    ap.add_argument('--packet', type=Path, required=True)
    ap.add_argument('--verify', action='store_true')
    args = ap.parse_args()
    if args.verify:
        verify_snapshot(args.packet)
        print('PASS portable provider snapshot integrity; G0 remains blocked')
        return 0
    if args.provider_root is None:
        ap.error('--provider-root required for capture only')
    print(json.dumps(create(args.provider_root, args.packet)['runtime_proposal'], indent=2))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
