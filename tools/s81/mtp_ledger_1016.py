#!/usr/bin/env python3
"""S81 per-user MTP / AR rate with the honest VM ledger (S-FUNC 2026-10-16).

Selected-die relay mode requires --relay-stages, --vm-paths, --stages and
--compiled-out. See tools/s81/vm_relay_stages.md. No missing-path fallback.

Historical screen (--legacy-relay-screen only) inputs (all committed):
  results/arch/accepted_cost_ledger_1013.json             current S81 rows (accepted / proposed)
  results/arch/s81_mtp_ledger_1016/hub_faces_5037_hop*.json   a2f_hub_faces.py screen of the adopted 5,037 x 4,600.8 VM
                                                           (vmc2 cross faces, caprow, read_near) on today's tools
  results/rtl/s81_vm_a2f_parent_bc297977c/record.json       measured A2-F core ages (hop-1 vs hop-2 vs legacy w1)
  results/arch/s81_mtp_ledger_1016/affine_vmc26b_hop1.json   a2f_affine_reach.py per-client relay edges (vmc_26b hub plan)
  results/arch/s81_rom_trade_1015/alloc/p1973s89h, p2065s84h  allocator points (19- vs 20-pair frames)

Model (same as tools/s81/c5_schedule_audit.py and the ledger): hop-only rate from the 81-stage headline
(AR 1,447.7 / MTP 4,238.4 at tau 4.159) plus (stages - 81) measured full-KP4 hops; ledger losses ADDED (conservative).
VM relay edges are priced with a2f_reach_price.price (token-path longest path, +W+R on every node, the VM.RELAY basis);
the A2 core / commit-relay remainder on VM-class nodes (the VM.A2_COMMIT_REMAINDER basis).
Grade: COMPOSED (measured unit rows + measured hop + screened relay counts); not a native 89/84-stage token run.
"""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_vm'))
sys.path.insert(0, str(ROOT / 'tools/throughput'))
import a2f_reach_price as RP  # noqa: E402
from vm_relay_stages import bind as bind_vm_relays
import die_relay_stages as DRS

LEDGER = 'results/arch/accepted_cost_ledger_1013.json'
OUT = 'results/arch/s81_mtp_ledger_1016'
HOP = 1004 + 171 / 84                    # measured full-KP4 hop + mean cable flight (stream cycles at 1.2 GHz)
ANCHOR = {'ar': (1447.7, 1.0), 'mtp': (4238.4, 4.159)}


def hop_only(stages):
    add = (stages - 81) * HOP / 1200
    return {wl: t * 1e6 / (t * 1e6 / a + add) for wl, (a, t) in ANCHOR.items()}


def edges(path):
    r = json.loads((ROOT / path).read_text())['by_reach']['900.0']
    return {k: r[k]['added_edges'] for k in ('write', 'read', 'commit')}


def selected_plan_summary(plan_path, paths_path, ledger, stages):
    """Replace only VM.RELAY. Unmeasured core/commit remainder stays charged."""
    plan = DRS.load(plan_path)
    paths = json.loads(Path(paths_path).read_text())
    relay, compiled = bind_vm_relays(plan, paths)
    price = RP.price(relay['write'], relay['read'])
    rates = {}
    for wl, anchor in hop_only(stages).items():
        losses = {status: {r['group']: r['per_workload'][wl]['e2e_loss_pct']
                           for r in ledger['rows'] if r['design'] == 's81' and
                           r['status'] == status and wl in r['per_workload']}
                  for status in ('accepted', 'proposed')}
        losses['accepted']['VM.RELAY'] = price[wl]['upper_every_node']['e2e_loss_pct']
        accepted = sum(losses['accepted'].values())
        proposed = sum(losses['proposed'].values())
        rates[wl] = dict(hop_only=anchor, accepted_loss_pct=accepted, proposed_loss_pct=proposed,
                         accepted_tok_s=anchor * (1 - accepted / 100),
                         accepted_and_proposed_tok_s=anchor * (1 - (accepted + proposed) / 100))
    compiled['compiled']['loaded_from'] = str(plan_path)
    return dict(schema='opentallas.s81.mtp-ledger.v1', grade='COMPOSED_NOT_NATIVE',
                relay_input=relay, stages=stages, rates=rates, native_qualified=False,
                open=['Native path/operation coverage and exact timeline remain unproven.',
                      'Only VM.RELAY is replaced; existing VM core/commit ledger rows remain charged.',
                      'Owner-declared path alternatives are not a completeness proof.']), compiled


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', default=f'{OUT}/summary.json')
    ap.add_argument('--relay-stages', type=Path, help='selected S81 die relay-stage table')
    ap.add_argument('--vm-paths', type=Path, help='source/digest-bound VM bus paths')
    ap.add_argument('--compiled-out', type=Path, help='table for die_relay_check.py')
    ap.add_argument('--stages', type=int, help='selected allocator stage count; required with relay table')
    ap.add_argument('--legacy-relay-screen', action='store_true', help='explicit historical geometry diagnostic')
    a = ap.parse_args()
    selected = a.relay_stages is not None or a.vm_paths is not None
    if selected and (a.legacy_relay_screen or not all((a.relay_stages, a.vm_paths, a.compiled_out, a.stages))):
        ap.error('selected-plan mode requires --relay-stages, --vm-paths, --compiled-out, --stages; no legacy fallback')
    if not selected and not a.legacy_relay_screen:
        ap.error('select --relay-stages and --vm-paths; historical screen requires --legacy-relay-screen')
    if selected and a.stages < 81:
        ap.error('--stages below the 81-stage anchor is unsupported')
    led = json.loads((ROOT / LEDGER).read_text())
    if selected:
        res, compiled = selected_plan_summary(a.relay_stages, a.vm_paths, led, a.stages)
        p = ROOT / a.out
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(res, indent=1) + '\n')
        DRS.write(a.compiled_out, compiled)
        print('MTP_LEDGER COMPOSED_NOT_NATIVE', json.dumps(res['rates']))
        return
    rows = [r for r in led['rows'] if r['design'] == 's81']
    loss = {st: {wl: {r['group']: r['per_workload'][wl]['e2e_loss_pct'] for r in rows
                      if r['status'] == st and wl in r['per_workload']} for wl in ANCHOR}
            for st in ('accepted', 'proposed')}
    cal = json.loads((ROOT / 'results/rtl/s81_vm_a2f_parent_bc297977c/record.json').read_text())['calendar']
    e2, e1 = edges(f'{OUT}/hub_faces_5037_hop2.json'), edges(f'{OUT}/hub_faces_5037_hop1.json')
    # Core ages vs the legacy w1 price basis of the token path (measured, bc297977c LAT lines):
    #   hop-2: commit P+14 (+2), read return Q+16 (0); hop-1: commit P+12 (0), read return Q+14 (-2).
    core = {'hop2': dict(commit=+2, read=0), 'hop1': dict(commit=0, read=-2)}
    rem = {'hop2': e2['commit'] + core['hop2']['commit'] + core['hop2']['read'],
           'hop1': e1['commit'] + core['hop1']['commit'] + core['hop1']['read']}
    relay_wr = {'hop2': e2['write'] + e2['read'], 'hop1': e1['write'] + e1['read']}
    price = {}
    for d in set(relay_wr.values()) | set(rem.values()) | {27, 28}:
        price[d] = RP.price(d, 0)

    def scenario(name, stages, relay, remainder, note):
        out = dict(stages=stages, note=note, relay_edges=relay, remainder_edges=remainder, rates={})
        ho = hop_only(stages)
        for wl in ANCHOR:
            acc = dict(loss['accepted'][wl]); pro = dict(loss['proposed'][wl])
            if relay is not None:
                acc['VM.RELAY'] = price[relay][wl]['upper_every_node']['e2e_loss_pct']
            if remainder is not None:
                pro['VM.A2_COMMIT_REMAINDER'] = price[remainder][wl]['vm_class_nodes']['e2e_loss_pct']
            sa, sp = sum(acc.values()), sum(pro.values())
            out['rates'][wl] = dict(hop_only=round(ho[wl], 1), accepted_loss_pct=round(sa, 3), proposed_loss_pct=round(sp, 3),
                                    accepted_tok_s=round(ho[wl] * (1 - sa / 100), 1),
                                    accepted_and_proposed_tok_s=round(ho[wl] * (1 - (sa + sp) / 100), 1),
                                    multiplied_accepted_and_proposed_tok_s=round(ho[wl] * math.prod(1 - x / 100 for x in [*acc.values(), *pro.values()]), 1),
                                    VM_RELAY_pct=round(acc['VM.RELAY'], 3), VM_A2_REMAINDER_pct=round(pro.get('VM.A2_COMMIT_REMAINDER', 0.0), 3))
        return out

    sc = {
        'ledger_as_is_89': scenario('ledger_as_is_89', 89, None, None, 'current main ledger rows unchanged (VM.RELAY 28, A2 remainder +5 basis)'),
        'honest_hop2_89': scenario('honest_hop2_89', 89, relay_wr['hop2'], rem['hop2'],
                                   'today-tools 5,037 screen relays W+R and commit relay with the A2-F hop-2 core'),
        'honest_hop1_89': scenario('honest_hop1_89', 89, relay_wr['hop1'], rem['hop1'],
                                   'same screen with the measured hop-1 core (commit P+12, read return Q+14)'),
        'honest_hop1_affine_89': scenario('honest_hop1_affine_89', 89, 27, rem['hop1'],
                                          'hop-1 + best capacity-feasible client-affine slice homes (worst pair W+R 27; commit unchanged)'),
        'honest_hop1_84_frames20': scenario('honest_hop1_84_frames20', 84, relay_wr['hop1'], rem['hop1'],
                                            '20-pair frames: 2,065 pairs/die (+92), allocator p2065s84h, 84 stages / 336 rank dies'),
    }
    res = dict(schema='opentallas.s81.mtp-ledger.v1', grade='HISTORICAL_GEOMETRY_SCREEN_NOT_NATIVE',
               relay_screen=dict(hop2=e2, hop1=e1, reach_um=900, outline_um=[5037.0, 4600.8],
                                 note='today-tools screen gives write 11 (front_scatter 2), the 2210 summary recorded write 10: VM.RELAY is 29 W+R edges, not 28; commit relay 5 was never in VM.RELAY'),
               core_ages=cal.get('a2f_hop1 (HOP1 1, production)'), core_vs_legacy=core,
               remainder_edges=rem, relay_wr_edges=relay_wr, scenarios=sc,
               allocator=dict(
                   p1973s89h=dict(pairs=1973, bf=424, stages=89, rank_dies=356, declarations_placed='46719/46719', home_order='PASS',
                                  words_max_over_mean=1.024),
                   p2065s84h=dict(pairs=2065, bf=424, stages=84, rank_dies=336, declarations_placed='46671/46671', home_order='PASS',
                                  words_max_over_mean=1.030, last_stage_fill=0.244,
                                  command='tools/dsrom_s73_pair1.py --stages 84 --pairs 2065 --bf 424 --homes-from <p2065s84 home_order_check> (fixed point after 1 iteration)',
                                  refuted='83 stages: 46 failed groups (layer 39); 82: 236',
                                  delta='-5 stages, -20 rank dies (system 408 -> 388 if the 52 non-rank dies are unchanged), +18.0 MTP tok/s hop-only; '
                                        '+92 pairs/die costs +19.1 mm2 of frame area per die (S-NET+FILL) -- die fit is S-DIE\'s call')),
               open=['VM.READ (accepted 9.093 % AR / 7.556 % MTP) prices the legacy dsfd_vm_bgr leaf-hop-2 chain; the die VM is the static/A2-F core (read return Q+14 + relays). Re-measure when the static VM closes; until then it stays charged.',
                     'Relay counts are a planning screen at R 900 um (driver->farthest sink basis for affine, Prim basis for VM.RELAY), not GRT/native.',
                     'Native 89/84-stage operator recut, actual VM service reservations and full-token run remain open.'])
    p = ROOT / a.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res, indent=1) + '\n')
    for k, v in sc.items():
        print(k, v['stages'], {wl: (r['accepted_tok_s'], r['accepted_and_proposed_tok_s']) for wl, r in v['rates'].items()})


if __name__ == '__main__':
    main()
