#!/usr/bin/env python3
"""Source-bound speculative invocation/lease MODEL; no arithmetic execution.

This compiles causal invocation identities, not a numerical drafter. It refuses
native admission without independently compiled position/stage operand views.
Golden source is inspected as a contract witness, never called by this model.
"""
import argparse
import ast
import functools
import hashlib
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / 'results/uarch/h4_hbm_baseline_bridge_20261003/mtp_invocation_r1'
PIN = '1b943fc383b1e03f0657e4ad796a105142582c9564a13ba6449c49f66fb488ca'
DRAIN = {'provider_old_response_absent', 'readers_empty', 'writes_empty',
         'forward_empty', 'return_empty', 'consumer_empty',
         'reverse_CDC_matched', 'both_reset_domains_accepted'}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@functools.lru_cache(maxsize=1)
def sources():
    manifest = (BASE / 'input_manifest.json').read_bytes()
    need(sha(manifest) == PIN, 'hard-pinned input manifest')
    out = {}
    for row in json.loads(manifest):
        path = (BASE / row['archive']).resolve()
        need(path.is_relative_to((BASE / 'inputs').resolve()), 'archive scope')
        raw = path.read_bytes()
        need(len(raw) == row['bytes'] and sha(raw) == row['sha256'], 'exact archive origin')
        out[path.name] = raw
    return out


def source_contract():
    raw = sources()['hdc_golden_v41.py']
    tree = ast.parse(raw)
    model = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Model')
    names = ('draft', 'generate_spec', 'truncate', 'dspark_seed', 'dspark_stage',
             'dspark_attention', 'main_hidden_part', 'forward_positions')
    methods = {n.name: n for n in model.body if isinstance(n, ast.FunctionDef)}
    witnesses = {}
    lines = raw.decode().splitlines(keepends=True)
    for name in names:
        node = methods[name]
        witnesses[name] = dict(first_line=node.lineno, last_line=node.end_lineno,
                              sha256=sha(''.join(lines[node.lineno - 1:node.end_lineno]).encode()))
    cfg = json.loads(sources()['inference_config.json'])
    need((cfg['n_layers'], cfg['n_mtp_layers'], cfg['dspark_block_size'],
          cfg['dspark_n_routed_experts'], cfg['dspark_n_activated_experts']) == (40, 3, 5, 128, 3),
         'released full-shape source, never old four-expert draft comment')
    return dict(configuration=cfg, methods=witnesses, source_sha256=sha(raw))


def identity(iteration, j, position, phase, rank, SM, version, generation, lease):
    for key, value in [('iteration', iteration), ('j', j), ('position', position),
                       ('rank', rank), ('SM', SM), ('generation', generation)]:
        need(type(value) is int and value >= 0, 'unsigned ' + key)
    need(rank < 96 and SM < 32 and generation < 16, 'source rank/SM/producer GEN4 envelope')
    need(version and lease and phase, 'explicit source version/lease/phase')
    return dict(iteration=iteration, j=j, position=position, phase=phase,
                rank=rank, SM=SM, version=version, generation=generation, lease=lease)


class InvocationCompiler:
    """Actual source control order, explicit caller placement, no AR multiplier.

    Binding is an input rather than rank%32. Every invocation retains its
    operand-view qualification status; protocol controls cannot qualify native
    arithmetic, homes, expert selection, KV addresses or physical clocks.
    """
    def compile(self, iteration, anchor, pending, drafts, targets, accepted, bindings,
                generation=0, max_position=None):
        cfg = source_contract()['configuration']
        need(type(iteration) is int and iteration >= 0 and type(anchor) is int and anchor >= 0,
             'actual iteration and last committed anchor')
        need(type(generation) is int and 0 <= generation < 16, 'producer GEN4')
        need(0 <= len(drafts) <= 5 and len(targets) == len(drafts) + 1, 'actual verify inputs')
        need(type(accepted) is int and 0 <= accepted <= len(drafts), 'accepted prefix receipt')
        # Acceptance is external; validate its longest-prefix receipt without
        # invoking the golden or claiming an acceptance-quality experiment.
        need(all(drafts[i] == targets[i] for i in range(accepted)), 'prefix equality receipt')
        need(accepted == len(drafts) or drafts[accepted] != targets[accepted], 'longest prefix receipt')
        for token in [pending] + list(drafts) + list(targets):
            need(type(token) is int and 0 <= token < cfg['vocab_size'], 'full-width token namespace')
        need(bindings and len({b['rank'] for b in bindings}) == len(bindings), 'explicit unique requester ranks')
        for b in bindings:
            need(b.get('scope') == 'protocol_control' and b.get('directory_sha256') and
                 b.get('provider_reference') and type(b.get('SM')) is int and 0 <= b['SM'] < 32 and
                 type(b.get('rank')) is int and 0 <= b['rank'] < 96,
                 'explicit rank/SM/provider witness; production directory/view join still required')
        if max_position is not None:
            need(type(max_position) is int and anchor + 1 + len(drafts) < max_position,
                 'source sequence boundary; caller clips gamma before draft/verify')
        invocations = []
        def emit(phase, j, pos, label, source_method, dependency):
            for b in bindings:
                version = f'DeepSeek.MTP.iter{iteration}.{phase}.{label}.j{j}.r{b["rank"]}'
                lease = f'{version}.pos{pos}.g{generation}'
                key = f'i{iteration}/{phase}/{label}/j{j}/r{b["rank"]}'
                invocations.append(dict(eventID=key, identity=identity(iteration, j, pos, phase,
                    b['rank'], b['SM'], version, generation, lease), dependencies=dependency,
                    provider_reference=b['provider_reference'], directory_sha256=b['directory_sha256'],
                    source_method=source_method, native_operand_views=None,
                    version_scope='invocation SSA namespace, not a checkpoint physical home',
                    arithmetic_unchanged=True, native_execution_admitted=False))
            return [v['eventID'] for v in invocations[-len(bindings):]]
        previous = []
        # Golden drafts the whole five-row block even when gamma is clipped;
        # all rows attend all five rows, no causal mask inside the draft block.
        if drafts:
            for stage in range(3):
                stage_events = []
                for j in range(5):
                    stage_events += emit('draft', j, anchor + 1 + j, f'stage{stage}',
                                         'dspark_stage', previous)
                previous = stage_events
            for j in range(5):
                # Five dependent Markov bias/sample steps. A token is an input
                # to the next Markov embedding, never five independent argmaxes.
                previous = emit('markov', j, anchor + 1 + j, 'sample', 'draft', previous)
        # The six (or clipped) positions are processed layer-major. This is a
        # control skeleton, not six copies of the one-position2213-PC calendar.
        for layer in range(40):
            layer_events = []
            for j in range(len(drafts) + 1):
                layer_events += emit('verify', j, anchor + 1 + j, f'layer{layer}',
                                     'forward_positions', previous)
            previous = layer_events
        head = []
        for j in range(len(drafts) + 1):
            head += emit('verify_head_seed', j, anchor + 1 + j, 'head_seed',
                         'dspark_seed', previous)
        retained = list(range(anchor + 1, anchor + 2 + accepted))
        rejected = list(range(anchor + 2 + accepted, anchor + 2 + len(drafts)))
        return dict(schema='SOURCE_MTP_INVOCATION_CONTROL_R1', iteration=iteration,
            anchor=anchor, pending_input=pending, gamma=len(drafts), accepted=accepted,
            invocations=invocations, terminal_dependencies=head,
            processed_input_tokens=[pending] + list(drafts),
            committed_positions=retained, rejected_positions=rejected,
            next_anchor=anchor + 1 + accepted, bonus=targets[accepted],
            bonus_position=anchor + 2 + accepted, bonus_KV_published=False,
            emitted_tokens=list(targets[:accepted + 1]),
            compressor_rebuild=dict(source='truncate', count=anchor + 2 + accepted,
                                   source_slotrec_required=True, native_rebuild=None),
            ring8=dict(required_verify_plus_anchor=len(drafts) + 2, capacity=8,
                       engram_snapshot_required=True, physical_alias_and_drain_proof=None),
            source_shape=dict(draft_experts=128, draft_topk=3, main_experts=384,
                              main_topk=6, main_hidden_layers=[37, 38, 39]),
            actual_native_iteration_admitted=False, whole_token_ns=None)


class PositionLeases:
    """Persistent KV publication/rollback debts, never fabricated RF home SM.

    Byte arithmetic/compressor rebuilding is outside this bounded control model.
    Publication/reuse requires a caller-supplied bound version and source fence.
    """
    def __init__(self):
        self.rows = {}

    def reserve(self, ident, home):
        need(ident['lease'] not in self.rows, 'duplicate live generation/lease')
        need(home.get('kind') == 'HBM_NATIVE_STATE' and home.get('provider_reference') and
             home.get('physical_home_reference') and home.get('version') == ident['version'],
             'persistent state provider/version witness')
        need(not any(r['home']['physical_home_reference'] == home['physical_home_reference']
                     and r['home']['provider_reference'] == home['provider_reference']
                     for r in self.rows.values()), 'no live physical state home reuse across generations')
        # Requester SM lives in identity. Persistent state need not own a fixedSM.
        self.rows[ident['lease']] = dict(identity=dict(ident), home=dict(home),
                                        state='reserved', debts=set(), visible=False)

    def debt(self, lease, request):
        row = self.rows[lease]
        need(row['state'] == 'reserved' and request not in row['debts'], 'unique accepted request debt')
        row['debts'].add(request)

    def visible(self, lease):
        row = self.rows[lease]
        need(row['state'] == 'reserved' and not row['visible'], 'once-only source-visible publication')
        row['visible'] = True

    def resolve(self, plan):
        staged = []
        for row in self.rows.values():
            ident = row['identity']
            if ident['iteration'] != plan['iteration']:
                continue
            if ident['position'] in plan['committed_positions']:
                need(row['visible'], 'accepted position must have actual publication')
                staged.append((row, 'committed'))
            elif ident['position'] in plan['rejected_positions']:
                staged.append((row, 'rejected'))
            else:
                raise ValueError('bonus/unprocessed position cannot fabricate KV')
        for row, state in staged:
            row['state'] = state

    def reverse(self, lease, request, matched):
        row = self.rows[lease]
        need(matched is True and request in row['debts'], 'exact matched accepted reverse receipt')
        row['debts'].remove(request)

    def discard(self, lease, drain, rebuild_receipt):
        row = self.rows[lease]
        need(row['state'] == 'rejected' and not row['debts'], 'rejected suffix retains all accepted debts')
        need(set(drain) == DRAIN and all(v is True for v in drain.values()), 'all-copy physical drain witness')
        need(rebuild_receipt.get('source_slotrec_rebuilt') is True and
             rebuild_receipt.get('engram_snapshot_restored') is True,
             'compressor open group and Engram restore, not dead-row assertion')
        del self.rows[lease]


def reconcile(existing, replacements):
    """Replace matched service receipts once; reject an invented fetch debit."""
    need(len({r['eventID'] for r in existing}) == len(existing), 'unique baseline intervals')
    table = {r['eventID']: dict(r) for r in existing}
    seen = set()
    for row in replacements:
        key = row['eventID']
        need(key in table and key not in seen, 'exact once-only replacement identity')
        need(row.get('source_receipt') == table[key].get('source_receipt') and row.get('source_receipt'),
             'source receipt lineage, never blanket38.97us fetch subtraction')
        for name in ('ns', 'clock_source'):
            need(row.get(name), 'positive composed cost/sourceclock')
        need(type(row['ns']) in (int, float) and math.isfinite(row['ns']) and row['ns'] > 0,
             'missing service latency cannot become zero')
        table[key] = dict(row)
        seen.add(key)
    return [table[r['eventID']] for r in existing]


def compose_selected_intervals(plan, intervals):
    """Finite source-control DAG with one reserved invocation slot per SM.

    Costs are explicit interval inputs, not operator1ns constants. This is a
    conservative model for selected invocations only: full primitive resource
    occupancy and actual source spans still need Dewey's emitted calendar join.
    A missing span refuses instead of contributing zero latency.
    """
    keys = [v['eventID'] for v in plan['invocations']]
    need(len(keys) == len(set(keys)), 'unique native invocation identities')
    need(len(intervals) == len(keys) and {r['eventID'] for r in intervals} == set(keys),
         'complete exact invocation span coverage, never a blind AR multiplier')
    spans = {r['eventID']: r for r in intervals}
    finish = {}
    SM_ready = {}
    events = []
    for inv in plan['invocations']:
        span = spans[inv['eventID']]
        need(type(span.get('ns')) in (int, float) and math.isfinite(span['ns']) and span['ns'] > 0 and
             span.get('clock_source') and span.get('source_receipt'), 'positive source clock/span receipt')
        need(span.get('scope') == 'protocol_control', 'actual native interval admission not yet implemented')
        SM = inv['identity']['SM']
        ready = max([finish[k] for k in inv['dependencies']] + [SM_ready.get(SM, 0)])
        end = ready + span['ns']
        events.append(dict(eventID=inv['eventID'], start_ns_assumed=ready, end_ns_assumed=end,
                           SM=SM, dependencies=inv['dependencies'], source_receipt=span['source_receipt'],
                           clock_source=span['clock_source'], resource='one selected invocation slot perSM'))
        finish[inv['eventID']] = end
        SM_ready[SM] = end
    return dict(events=events, selected_invocation_span_ns_assumed=max(finish.values()),
                full_iteration_ns=None, commit_rollback_service_ns=None,
                primitive_resource_occupancy_joined=False, physical_latency_qualified=False)


def model():
    src = sources()
    contract = source_contract()
    return dict(schema='MTP_SOURCE_INVOCATION_LEASE_MODEL_R1',
        source_sha256={k: sha(v) for k, v in src.items()}, source_contract=contract,
        native_AR_PC_count=2213, AR_program_is_MTP=False,
        required_invocation_fields=['iteration', 'j', 'position', 'phase', 'version',
                                    'rank', 'SM', 'generation', 'lease'],
        actual_draft_native_program=None, actual_position_native_program=None,
        actual_provider_binding_and_calendar=None, full_iteration_calibrated_ns=None,
        reference_subtotal_us_ONLY=765.72, missing_costs_are_zero=False,
        build_allowed=False, whole_MTP_admitted=False,
        remaining=['actual full-shape draft128/top3 primitive expansion and weight homes',
                   'position-specific native SSA/views/homes rather than cloned AR',
                   'paired all96 rank requester SM/provider mapping',
                   'actual accepted/visible/consumer/reverse finite calendars',
                   'source slotrec compressor rebuild and ring8 ownership/Engram restore',
                   'full-design clocks/area/ports/routes and measured latency'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    raw = canonical(model())
    if args.verify:
        need((BASE / 'model.json').read_bytes() == raw, 'exact MTP model replay')
    else:
        need(args.output is not None, 'explicit output')
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / 'model.json').write_bytes(raw)
    print('PASS source invocation/lease model; full native MTP and hardware admission remain FAIL')


if __name__ == '__main__':
    main()
