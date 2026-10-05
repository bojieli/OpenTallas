"""Default-off PC10 finite software endpoint join; no physical admission.

PC0..9 must execute in the SAME provider context. Digest-only journals cannot
restore RF payloads. This adapter never loads expected outputs as operands.
"""
import hashlib
from pathlib import Path
from h3_ds_connected_provider_r37 import ROOT, peer
from ds_hbm_bound_engine_r43 import engine_class as reference_engine_class
from h4_hbm_pc10_r41_lineage import ProductionPC10
from h4_hbm_w19_pc10_endpoints import ProductionSharedFactory, inputs


def primitive_sources():
    base = ROOT / 'results/uarch/h3_complete_native_calendar_20261002/bounded_provider_milestone'
    sources = dict(bounded_native=(base / 'bounded_entrypoint.py.source').read_bytes(),
                   arithmetic_helpers=(base / 'baseline.py.source').read_bytes())
    import h3_complete_native_calendar as calendar
    calendar.load_group_native_primitive_factory(sources)  # exact hashes before any request
    return sources


def calendar_view(bound):
    """Share admitted ownership state; expose the exact inherited df6 body.

    R43's run wrapper changes only receipt lineage, but the calendar explicitly
    requires the original source function/globals for its reverse-credit proof.
    Keep that check intact. This view does not rerun or bypass a constructor.
    It is created ONLY after the full R43 engine constructor has succeeded.
    """
    original = peer('h4_c0_ds_tiled_continuation').TiledContinuation
    path = Path(original.run.__code__.co_filename)
    if hashlib.sha256(path.read_bytes()).hexdigest() != '1fbcc6ba439d1b1bc8798aa300d9c5f65c116e638a04d0b66b65b9aede5ae96b':
        raise ValueError('exact inherited continuation source required')
    if bound.lineage['status'] != 'PASS_EXACT_BOUND_NATIVE_LINEAGE':
        raise ValueError('full R43 constructor lineage required')
    class View(original):
        def __init__(self): self.__dict__ = bound.__dict__
    return View()


class PC10Groups:
    def __init__(self, bound, endpoint, retired, shared, sources):
        self.bound = bound
        self.endpoint = endpoint
        self.retired = retired
        self.shared = shared
        self.sources = sources
        self.calendar_continuation = calendar_view(bound)

    def __getattr__(self, name): return getattr(self.bound, name)

    def run(self, PC, rank, *, generation, identity, source_store_view):
        if PC != 10:
            return self.bound.run(PC, rank, generation=generation, identity=identity,
                                  source_store_view=source_store_view)
        if not set(range(10)) <= self.retired:
            raise ValueError('PC0..9 actual source retirement required; no cached producer substitute')
        if generation != self.endpoint.provider.generation or identity != self.endpoint.identity(rank):
            raise ValueError('exact PC10 writer identity required')
        parent = self.plan.parents[10]
        if source_store_view != parent['writes'][0]['native_result_binding']:
            raise ValueError('exact source result binding required')
        if self.failed or (10, rank, generation) in self.completed:
            raise ValueError('failed/completed PC10 continuation; no retry')
        # Complete 64-rank actual RF directory check BEFORE shared allocation,
        # source acquisition, publication, or journal mutation.
        self.endpoint.ready(rank)
        import h3_complete_native_calendar as calendar
        result = self.endpoint.execute(self.calendar_continuation, calendar, rank=rank,
                                       shared_factory=self.shared, primitive_sources=self.sources)
        # NativeExecution validates this same actual source publication receipt.
        result['publication'] = result['actual_publication']
        result['original_native_artifact_sha256'] = self.lineage['original_native_artifact_sha256']
        result['native_artifact_sha256'] = self.lineage['bound_native_artifact_sha256']
        result['hardware_qualified'] = False
        result['physical_primitive_port_calendar_bound'] = False
        return result


def engine_class(prefix, *, finite_pc10=False, physical_backend=False):
    if type(finite_pc10) is not bool or type(physical_backend) is not bool:
        raise ValueError('explicit boolean opt-in required')
    if physical_backend:
        raise ValueError('actual primitive port-bound calendar absent; software ticks are not physical edges')
    reference = reference_engine_class(prefix)
    if not finite_pc10:
        return reference  # unchanged CPU continuation reference is the default
    class Engine(reference):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)  # every original dispatch/40group check
            endpoint = ProductionPC10(self.provider)
            if endpoint.lineage != 'R41_full_source_regeneration':
                raise ValueError('complete 290730-home R41 engine directory required')
            sources = primitive_sources()
            shared = ProductionSharedFactory(self.provider.journal_budget)
            self.groups = PC10Groups(self.groups, endpoint, self.retired, shared, sources)
            self.pc10_endpoint_scope = dict(opt_in=True, same_process_actual_PC9_required=True,
                CPU_group_reference_independent=True, physical_primitive_port_calendar_bound=False,
                hardware_qualified=False, full_token_GO=False)
    return Engine


def resource_model():
    # Source executor: 64 tiles/rank; 8 contributor write/read pairs + one
    # output write/read pair/tile; every 512B transfer has sixteen sectors.
    ranks, tiles, transfers, sectors = 96, 64, 18, 16
    return dict(schema='DS_PC10_FINITE_ENGINE_R44', default_on=False,
        ranks=ranks, SMs_per_rank=32, tiles_per_rank=tiles,
        shared_transfers512=ranks*tiles*transfers,
        scratch64_commands=ranks*tiles*transfers*8,
        sector32_transactions=ranks*tiles*transfers*sectors,
        shared_payload_bytes=ranks*tiles*transfers*512,
        shared_reserved_bytes=ranks*32*65536, shared_tag_capacity_per_SM=1,
        max_RF_vectors_per_tile=32, parent_unpublished_output_bytes=32768,
        operand_and_staging_bound_bytes=41472,
        RF_source_span_acquisitions=ranks*tiles*8,
        RF_source_payload_bytes=ranks*tiles*8*512,
        additional_hardware_buffers=0, additional_hardware_area_credit=0,
        existing_physical_port_costs_replaced=False,
        physical_RF_pair_return_bytes=ranks*tiles*8*1024,
        physical_primitive_endpoint_latency=None, routing_or_clock_fit=None,
        hardware_admitted=False, runtime_admitted=False,
        missing=['actual same-context PC9 producers', 'complete PC0..10 comparison/launcher admission',
                 'source-matched aggregate journal projection including shared and call records',
                 'actual primitive port-bound calendar and installed physical reservations'],
        journal_is_payload_restore=False)


from ds_hbm_prefix_observed_outputs_r42 import Witness as PrefixWitness
PC10_REFERENCE = ROOT / 'results/uarch/h4_c0_ds_pc10_golden_20261002/r1/expected_outputs.json'
PC10_REFERENCE_SHA = 'ccc0b2003b87b530b95665b937a1fbb1f523cf42347e1f915005a573bc4f87a2'


class Witness(PrefixWitness):
    """Observe 1664 publications; reference bytes never enter the executor."""
    def __init__(self, provider, original_native, prefix_reference):
        import json
        super().__init__(provider, original_native, prefix_reference)
        raw = PC10_REFERENCE.read_bytes()
        if hashlib.sha256(raw).hexdigest() != PC10_REFERENCE_SHA:
            raise ValueError('exact independently committed PC10 expectations required')
        ref = json.loads(raw)
        if any(ref[k] != self.reference[k] for k in ('checkpoint_revision', 'native_program_sha256', 'input_manifest_sha256')):
            raise ValueError('PC10 reference source provenance mismatch')
        from h4_hbm_w19_pc10_endpoints import canonical
        if hashlib.sha256(canonical(provider.native)).hexdigest() != ref['R41_effective_native_content_sha256']:
            raise ValueError('PC10 reference complete bound native lineage')
        required = set()
        op = original_native['instructions'][10]
        for owned in op['rank_bindings']:
            if owned.get('empty_owned_extent'): continue
            for w in op['writes']:
                required.add((10, w['version'], owned['rank'], provider.generation, 'data'))
        offered = {(r['PC'], r['version'], r['rank'], r['generation'], r['field']):r for r in ref['expectations']}
        if len(offered) != len(ref['expectations']) or set(offered) != required or len(required) != 96:
            raise ValueError('complete exact 96-writer PC10 expectation coverage')
        self.expected.update(offered)

    def observe(self, identity, fields, receipt):
        if identity['PC'] != 10: return super().observe(identity, fields, receipt)
        import numpy as np
        if self.failed: raise ValueError('failed numerical witness; no retry')
        hashes = {f:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest() for f,a in fields.items()}
        peer('h3_deepseek_full_token_driver').publication_receipt(receipt, identity, hashes)
        for f,a in fields.items():
            key = (10, identity['version'], identity['rank'], identity['generation'], f)
            row = self.expected.get(key)
            exact = (row is not None and key not in self.seen and identity['home_indices'] == row['home_indices']
                     and list(a.shape) == row['shape'] and a.dtype.str == row['dtype'] and hashes[f] == row['payload_sha256'])
            self.events.append(dict(event='DS_r44_PC10_observed_output', identity=identity, field=f,
                shape=list(a.shape), dtype=a.dtype.str, payload_sha256=hashes[f], byte_exact=exact,
                reference_sha256=PC10_REFERENCE_SHA, hardware_qualified=False))
            if not exact:
                self.failed = True
                raise ValueError('actual PC10 output differs in key/shape/dtype/home/bytes')
            self.seen.add(key)

    def finish(self):
        result = super().finish()
        result['PC10_reference_sha256'] = PC10_REFERENCE_SHA
        result['prefix_stop'] = 10
        return result
