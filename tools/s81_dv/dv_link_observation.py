#!/usr/bin/env python3
"""Extract the exact cut/programme link obligations without inventing a peer.

This is a source-model adapter, not an alternative to dv_cut_replay check.
It deliberately exits 2 until the original programme supplies complete payload
gold and an explicit far-end/PMA/landing calendar. Existing strict results stay
unchanged. No elastic latency is inferred from lane changes or fitted to a trace.
"""
import argparse
import hashlib
import json
from pathlib import Path

FULL = (1 << 1104) - 1


def load(path):
    raw = Path(path).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def model(replay_path, schedule_path):
    replay, replay_sha = load(replay_path)
    schedule, schedule_sha = load(schedule_path)
    _, manifest_sha = load(Path(schedule_path).parent / 'manifest.json')
    if manifest_sha != replay['prog_manifest_sha256']:
        raise ValueError('schedule parent manifest differs from original replay programme')
    lanes = {b['lane']: b for b in replay['boundary']}
    obligations, blockers = [], []
    instances = {e['inst'] for e in replay['offdie']}
    for e in schedule['events']:
        if e.get('boundary') != 'offdie' or e.get('inst') not in instances:
            continue
        inst = e['inst']
        side = 'W' if inst.startswith('u_s_0') else 'E' if inst.startswith('u_s_7') else None
        tier = inst[-1]
        names = [f'lt_lk_{side}{tier}{i}' for i in range(2)]
        if side is None or any(n not in lanes for n in names):
            blockers.append(f'{inst}: missing exact two-lane cut boundary')
            continue
        for edge, value, mask in e.get('words', []):
            word, bits = int(value, 16), int(mask, 16)
            if not 0 <= word <= FULL or not 0 <= bits <= FULL:
                raise ValueError('word or mask exceeds 1104-bit frame')
            peer_mask = (word >> 21) & 0xffff
            obligations.append(dict(
                source=inst, kind=e['kind'], tag=e['tag'],
                producer_programme_edge=edge,
                producer_ro_edge=edge + replay['t0'],
                epb_rov_edge=edge + replay['t0'] + 1,
                frame_hex=f'{word:0276x}', mask_hex=f'{bits:0276x}',
                destination_slice_mask=peer_mask,
                destination_sids=[i for i in range(16) if peer_mask & (1 << i)],
                payload_missing_bits=1104 - bits.bit_count(),
                lanes=[dict(lane=n, port=lanes[n]['port'],
                            local_peer=lanes[n]['peers'], age=lanes[n]['age'],
                            stations=lanes[n]['stations'], K=lanes[n]['K']) for n in names],
                # A local PHY endpoint is not the far die endpoint.
                far_die=None, far_endpoint=None, pma_lane_ages=None,
                remote_reset_clock_contract=None, landing_replay_calendar=None,
                consumer_edge=None,
            ))
    users = replay.get('mu', {}).get('users', [dict(user=0, shift=0, pos=0, copy='A')])
    obligations = [dict(e, user=u['user'], user_shift=u['shift'],
                        position=u['pos'], copy=u['copy'],
                        producer_ro_edge=e['producer_ro_edge'] + u['shift'],
                        epb_rov_edge=e['epb_rov_edge'] + u['shift'])
                   for u in users for e in obligations]
    if not obligations:
        blockers.append('no compiled offdie frame obligations selected')
    if any(e['payload_missing_bits'] for e in obligations):
        blockers.append('compiled offdie gold masks payload: actual row producer/golden placement required')
    blockers.extend([
        'die builder exposes local PHY peers only: remote die/endpoint and two PMA ages required',
        'remote reset/clock and fixed landing/replay/user ownership calendar required',
        'qualified producer, pair release, ml_wv/ml_rv and ri/mu_rt trace not collected',
        'positive and causal wrong-owner/corrupt/early/late/omitted-consumer RTL witnesses absent',
    ])
    return dict(schema='opentallas.s81.link_observation_adapter.v1',
                status='BLOCKED_SOURCE_CONTRACT', qualification=False,
                replay_sha256=replay_sha, schedule_sha256=schedule_sha,
                programme_manifest_sha256=manifest_sha,
                mu_slots_sha256=replay.get('mu', {}).get('slots_sha256'),
                die_v_sha256=replay['die_v_sha256'],
                original_verdict_kind=replay['verdict_kind'],
                original_t0=replay['t0'], obligations=obligations,
                blockers=blockers,
                receiver_observation=dict(
                    source='actual ot_s81sl_lep_core; no synthetic frame source',
                    frame='fr with push=rov||hp_go||kp_go; pair=bsel; parity=sq[pair]',
                    release='rel with h0/h1: parity equal, rb={h1[551:0],h0[551:0]}',
                    cutthrough='ri at release+1, valid only riv; full payload and mu_rt',
                    landing='ml_wv at release+1; full mwd stored, not immediate ri',
                    replay='ml_rv/ml_rd -> mrv/mrd -> ri (two sampled rising edges)',
                    identity='qualified user0 payload+mu_rt vs original SU at identical edges',
                    transport_age='elastic; never substituted by a constant',
                    scope='source model only; arithmetic/token/native qualification false'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--replay', required=True)
    p.add_argument('--schedule', required=True)
    p.add_argument('--kit', required=True, help='original compiled run kit, never a current RTL checkout')
    p.add_argument('--source-contract', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    result = model(a.replay, a.schedule)
    kit, kit_sha = load(Path(a.kit) / 'kit.json')
    contract, contract_sha = load(a.source_contract)
    lep = 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv'
    lep_sha = hashlib.sha256((Path(a.kit) / 'src' / lep).read_bytes()).hexdigest()
    if lep_sha != contract['source_sha256'][lep]:
        raise ValueError('run-snapshot LEP differs from pinned observation contract')
    result['source_identity'] = dict(run_kit_sha256=kit_sha,
                                   run_rtl_commit=kit['sha'],
                                   actual_lep_sha256=lep_sha,
                                   source_contract_sha256=contract_sha)
    Path(a.out).write_text(json.dumps(result, indent=2) + '\n')
    print(f"BLOCKED_SOURCE_CONTRACT {len(result['obligations'])} compiled frame obligations; qualification=false")
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
