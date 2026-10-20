#!/usr/bin/env python3
"""KV-RETIRE 10-19: build the complete KV token-retirement contract and price it.

Owner 10-19 09:39: compiler-proven functional work-complete cutoff covering every operation's nominal / missing check
and drain; fixed STATUS after the complete closed fault path from every source; compiled_end and link slots priced;
continuous sticky health stays live (never gated / cleared / masked at the cutoff); reset release after all
source-clear propagation; HOLD128 is no proof for 180-edge paths.

Inputs (all pinned by SHA in the output):
  * the canonical static programme (kv_static_programme.compile_all, die profile): rx_cmd, tx_first, service_end;
  * the attention controller RTL ages (qkd_native_attention_static_ctl, LAND=1): RX CMD / Q / RESULT / done / slot
    checks, each with its registered missing check;
  * the 357-source fault plane (codex/kv-dcal-fault-model-1019 successor.json: 351 landings + 4 KC + existing UFH +
    DCAL, leaf latency = edges from the source pin to the final sticky collector);
  * the GEN7 reset candidate (codex/kv-fault-reset-1019 reset_branch_candidate.json: per-source reset depth).

Every token operation declares nominal_check / missing_check / drain ages (run edge = age 0); every source names the
operations whose work it checks and a complete ordered observation path
  source_to_collector, ufh, afr, face, tx_capture, tx_landing, link, consumer.
kv_retirement.prove() takes the global cutoff = max(all deadlines) and requires STATUS >= cutoff + path for every
source.  Physical receipts do not exist yet (no native phase / loaded clock / measured lane ages), so every stage is
emitted qualified=False with the SHA of the model artifact it comes from: the result is LOGICAL_ONLY by construction and
compile_all keeps refusing a delayed production STATUS until real receipts replace them.

Pricing: per-layer mode (codex 670cefef6: every layer's STATUS moves, 36 tails / token) and the token-retirement
alternative (one tail / token, sticky health makes the last layer's STATUS cover all 36) are both reported.
"""
import argparse
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from kv_retirement import prove  # noqa: E402

ROLES = ['source_to_collector', 'ufh', 'afr', 'face', 'tx_capture', 'tx_landing', 'link', 'consumer']
# Controller-relative fixed edges (RTL qkd_native_attention_static_ctl LAND=1 + qkd_attn_fault_root):
AFR_EDGES = 1        # qkd_attn_fault_root pin register (d -> dq)
FACE_EDGES = 0       # result face folds |unit_fault into service_fault combinationally; ctl fault = OR (comb)
TX_CAPTURE_EDGES = 1  # LAND tx launch flop: tx_v_l <= codec_tx_valid && !fault
TX_LANDING_EDGES = 1  # D2D_OUT (layer_roots_from_link): programme TX slot -> d2d TX capture
CONSUMER_EDGES = 1    # compute-side STATUS capture
AHUB_UFH_EDGES = 34 + 2  # AHUB hf -> attention.ufh 34 plain edges (kv-reset-native-ownership) + hub u_core rn[3] 2 edges


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def operations(rx_cmd, tx_first, service_end):
    """Every token operation of one attention layer op, ages from the controller run edge.

    missing_check = the edge at which the controller's registered check of the operation's absence is visible on
    `fault` (comparisons are evaluated on the event edge and registered into local_fault / record_fault / slot_fault one
    edge later); drain = the last edge at which any beat of the operation can still sit in a KV-die station that checks
    it (RESULT beat 31 leaves through the LAND launch flop and the D2D_OUT stage)."""
    t = tx_first
    return [
        dict(id='cmd_rx', nominal_check=rx_cmd, missing_check=rx_cmd + 1, drain=rx_cmd + 1,
             basis='RX CMD on age RX_CMD (codec rx_expected compare, registered record_fault)'),
        dict(id='q_rx', nominal_check=rx_cmd + 32, missing_check=rx_cmd + 33, drain=rx_cmd + 34,
             basis='Q beats RX_CMD+1..+32; q_valid register +1'),
        dict(id='service', nominal_check=service_end, missing_check=t + 32, drain=t + 31,
             basis='service work (K/V/QK/PV/AHUB through the landing stations) ends at service_end; its absence is the '
                   'missing RESULT check result_valid != result_reserved on TX_FIRST..+31, registered at +32'),
        dict(id='result_tx', nominal_check=t + 31, missing_check=t + 32, drain=t + 33,
             basis='RESULT beats TX_FIRST..+31; beat 31 -> LAND launch flop (+1) -> D2D_OUT (+1)'),
        dict(id='done', nominal_check=t + 32, missing_check=t + 33, drain=t + 33,
             basis='result_done compare at TX_FIRST+32 registered into local_fault at +33'),
        dict(id='tx_slot', nominal_check=t + 32, missing_check=t + 33, drain=t + 33,
             basis='LAND slot pins land at +1 (ls_*), slot_chk on the landed copy; RESULT beat 31 checked at +32, '
                   'slot_fault visible +33'),
    ]


def source_ops(sid):
    if sid.startswith('dcal'):
        return ['result_tx', 'tx_slot']     # link calibration health covers the RESULT transmit on the link
    return ['service', 'result_tx']         # landings / KC / AHUB carry or check this op's service traffic


def build(successor, reset_candidate, prog, link_edges, dcal_sink=None, skew=64):
    succ = json.loads(Path(successor).read_text())
    rc = json.loads(Path(reset_candidate).read_text())
    succ_sha, rc_sha = sha(successor), sha(reset_candidate)
    leaf = succ['leaf_latencies']
    clears = {c['id']: c for c in rc['source_clears']}
    ops = operations(prog['compiled_rx_cmd'], prog['compiled_tx_first'], prog['service_end'])
    sources = []
    for s in succ['sources']:
        sid = s['id']
        ufh = AHUB_UFH_EDGES if sid == 'existing_ufh' else 0
        to_coll = int(leaf[sid])
        model = succ_sha
        if sid.startswith('dcal') and dcal_sink is not None:
            to_coll = int(dcal_sink) + 1   # KV-DCAL d5af5a15e: dcal flt -> relayed ks_af_ufd -> afr d[8]
            model = hashlib.sha256(b'claude/kv-dcal-1019 d5af5a15e kv_static_die OT_KV_DCAL_FLT ks_af_ufd').hexdigest()
        edges = [to_coll, ufh, AFR_EDGES, FACE_EDGES, TX_CAPTURE_EDGES, TX_LANDING_EDGES, link_edges, CONSUMER_EDGES]
        path = [dict(role=r, edges=e, qualified=False, receipt_sha256=(model if i == 0 else succ_sha))
                for i, (r, e) in enumerate(zip(ROLES, edges))]
        c = clears.get(sid)
        if c is None:   # DCAL (successor only): link_rst_n -> 2 plain -> region -> 1 plain -> release_q 2 edges
            depth = 2 + 1 + 1 + 2
        else:
            depth = int(c['depth'])
        sources.append(dict(id=sid, ops=source_ops(sid), path=path, clock=s.get('clock'),
                            reset_clear_age=depth + skew, reset_propagation_edges=to_coll + ufh,
                            sink_release_age=None, reset_qualified=False,
                            reset_basis='depth from its reset root + diagnostic cross-root assertion skew %d (UNMEASURED)'
                                        % skew))
    need = max(s['reset_clear_age'] + s['reset_propagation_edges'] for s in sources)
    for s in sources:
        s['sink_release_age'] = need
    for o in ops:
        o['fault_sources'] = [s['id'] for s in sources if o['id'] in s['ops']]
        o['deadline_qualified'] = False
    ops = [o for o in ops if o['fault_sources']] + [
        dict(o, fault_sources=[sources[0]['id']]) for o in ops if not o['fault_sources']]
    return dict(schema='opentallas.kv_retirement_contract.v1',
                operation_inventory=[o['id'] for o in ops], source_inventory=[s['id'] for s in sources],
                edge_basis_qualified=False, inventory_qualified=False,
                operations=ops, sources=sources,
                inputs=dict(successor_sha256=succ_sha, reset_candidate_sha256=rc_sha, programme=prog),
                reset=dict(required_sink_release_depth=need, hold_counter_bits=max(8, math.ceil(math.log2(need))),
                           diagnostic_root_skew=skew,
                           note='qkd_rst_region HOLD >= this depth needs hold_counter_bits; 10-19 RTL sizes it'))


def required_status(contract, tx_first):
    cutoff = max(max(o[k] for k in ('nominal_check', 'missing_check', 'drain')) for o in contract['operations'])
    path = max(sum(p['edges'] for p in s['path']) for s in contract['sources'])
    return cutoff, path, max(cutoff + path, tx_first + 33)


def link_price(status_delay):
    import kv_static_programme as C
    with tempfile.TemporaryDirectory() as ta, tempfile.TemporaryDirectory() as tb:
        base = C.link_calendar(ta, 0)
        tail = C.link_calendar(tb, status_delay)
    pick = lambda c: c['program']['token_period']
    occ = lambda c: dict(entries={k: len(v) if isinstance(v, list) else v for k, v in c['entries'].items()},
                         token_period_pad=c['program'].get('token_period_pad'),
                         retirement=c['program'].get('retirement'))
    return dict(base=pick(base), tail=pick(tail), base_slots=occ(base), tail_slots=occ(tail),
                status_slot_moves=[(m.get('seg'), m['cyc']) for m in tail['messages'] if m.get('kind') == 4][:4])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--successor', required=True)
    ap.add_argument('--reset-candidate', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--dcal-relay', type=int, default=None,
                    help='KV-DCAL ks_af_ufd relay stages (dcal flt -> afr d[8]); default = successor tail join')
    ap.add_argument('--no-link', action='store_true', help='skip the link-calendar compile (unit tests)')
    a = ap.parse_args()
    import kv_static_programme as C
    r = C.compile_all(C.profile('die', json.loads((C.ROOT / C.AGES).read_text())))
    att = r['attention']
    prog = dict(compiled_rx_cmd=att['compiled_rx_cmd'], compiled_tx_first=att['compiled_tx_first'],
                compiled_end=att['compiled_end'], service_end=att['service_end'],
                token_period=r['link']['token_period'])
    link_edges = 6 + 5   # LINK_ARGS --txl 6 --phy 5
    c = build(a.successor, a.reset_candidate, prog, link_edges, a.dcal_relay)
    tx_first = prog['compiled_tx_first']
    cutoff, path, status_age = required_status(c, tx_first)
    proof = prove(c, tx_first, status_age)
    try:
        prove(c, tx_first, status_age - 1)
        raise SystemExit('one-edge-early STATUS accepted')
    except ValueError as e:
        early = str(e)
    delay = status_age - tx_first - 33
    period = prog['token_period']
    price = dict(status_age=status_age, compiled_end=status_age + 1, status_delay=delay,
                 legacy_status_age=tx_first + 33, legacy_compiled_end=prog['compiled_end'],
                 per_layer=dict(token_added_edges=36 * delay, token_period=period + 36 * delay,
                                loss_pct=round(100.0 * 36 * delay / (period + 36 * delay), 3)),
                 token_retirement=dict(token_added_edges=delay, token_period=period + delay,
                                       loss_pct=round(100.0 * delay / (period + delay), 3),
                                       note='one delayed retirement STATUS per token (last layer); sticky health makes '
                                            'it cover all 36 layers; per-layer STATUS = progress only. Needs a '
                                            'per-layer compiled_end (L35) or a token-run retirement slot: OWNER + '
                                            'compute-consumer acceptance'))
    if not a.no_link:
        lp = link_price(delay)
        price['link_calendar'] = lp
        ub, ut = (lp[k]['token_period_pad']['unpadded'] for k in ('base_slots', 'tail_slots'))
        if ut - ub != 36 * delay or lp['base_slots']['entries'] != lp['tail_slots']['entries']:
            raise SystemExit('link calendar does not price exactly 36 tails on unchanged slot tables: %s' % lp)
        price['per_layer'].update(token_period_padded=lp['tail'], padded_added_edges=lp['tail'] - lp['base'],
                                  padded_loss_pct=round(100.0 * (lp['tail'] - lp['base']) / lp['tail'], 3))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'contract.json').write_text(json.dumps(c, indent=1) + '\n')
    hist = {}
    for s in c['sources']:
        e = sum(p['edges'] for p in s['path'][:2])
        hist[e] = hist.get(e, 0) + 1
    summary = dict(schema='opentallas.kv_retirement_price.v1', status=proof['status'], qualified=proof['qualified'],
                   cutoff=cutoff, max_observation_edges=path, sources=len(c['sources']),
                   operations=c['operation_inventory'], price=price, early_refusal=early,
                   reset=c['reset'], continuous_health=proof['continuous_health'],
                   collector_edge_histogram=dict(sorted(hist.items())),
                   worst_sources=sorted(((sum(p['edges'] for p in s['path']), s['id']) for s in c['sources']))[-5:],
                   manifest_sha256=proof['manifest_sha256'])
    (out / 'price.json').write_text(json.dumps(summary, indent=1) + '\n')
    # whole-path bench inputs: every source's pre-AFR edges (source_to_collector + ufh), injected at the cutoff
    (out / 'bench_sources.txt').write_text(''.join('%d %s %d\n' % (i, s['id'], sum(p['edges'] for p in s['path'][:2]))
                                                  for i, s in enumerate(c['sources'])))
    suffix = max(sum(p['edges'] for p in s['path'][5:]) for s in c['sources'])
    (out / 'bench.env').write_text('CUTOFF=%d\nSTATUS=%d\nTXF=%d\nRX=%d\nLEGACY=%d\nSUFFIX=%d\nDMAX=%d\n' % (
        cutoff, status_age, tx_first, prog['compiled_rx_cmd'], tx_first + 33, suffix,
        max(sum(p['edges'] for p in s['path'][:2]) for s in c['sources'])))
    print(json.dumps(dict((k, summary[k]) for k in ('status', 'cutoff', 'max_observation_edges', 'sources', 'price',
                                                     'reset')), indent=1))


if __name__ == '__main__':
    main()
