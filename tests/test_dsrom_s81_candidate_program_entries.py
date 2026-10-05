"""Focused source-only packing checks; no field allocation or native execution."""
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import hdc_isa_v41 as ISA
from dsrom_s81_execution_binding import CanonicalS81Execution
from dsrom_s81_source_plan_emit import emit, emit_candidate_dispatch, emit_native_transfer


class CandidateEntries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT/'results/uarch/dsrom_native_weight_address_join_20261002'
        demand = json.loads(gzip.decompress((base/'inputs/demand-r5.json.gz').read_bytes()))
        cls.nodes = {n['id']: n for n in demand['nodes']}
        cls.bindings = {r['node']: r for r in
                        map(json.loads, gzip.decompress((base/'r3/node_bindings.jsonl.gz')
                                                        .read_bytes()).splitlines())}
        cls.candidate = json.loads((ROOT/'results/uarch/dsrom_s81_service_home_candidate_20261004/candidate.json').read_text())

    def owner(self):
        # The test exercises literal nonfield compilation. The already-loaded
        # StageProgramJoin's field key lookup is not replayed or qualified.
        owner = CanonicalS81Execution.__new__(CanonicalS81Execution)
        owner.source = SimpleNamespace(nodes=self.nodes, bindings=self.bindings)
        owner.stage_join = SimpleNamespace(keys=lambda stage, rank: [0])
        return owner

    def context(self):
        return dict(token=16754, position=1048575, user=0, epoch=1)

    def test_actual_l20_nonfield_entries_are_packed(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t)/'candidate'
            result = emit_candidate_dispatch(self.owner(), self.candidate, self.context(),
                                             out, layers=[20], include_fields=False)
            self.assertFalse(result['parent_dispatch_ready'])
            self.assertFalse(result['active'])
            entries = [o['entry'] for o in result['offers'] if o['rank'] == 0]
            lengths = []
            runs = [r for r in self.candidate['ordered_nonfield_runs'] if r['layer'] == 20]
            for r in runs:
                lengths.append(len(r['nodes'])+1)  # actual API appends native END
            expected, position = [], 0
            for n in lengths:
                expected.append(position)
                position += n
            self.assertEqual(entries, expected)
            self.assertGreater(entries[1], 0)
            words = [int(w, 16) for w in (out/'s40_r0/prog.hex').read_text().splitlines()]
            self.assertEqual(len(words), position)
            for run, entry in zip(runs, entries):
                for pc, node in enumerate(run['nodes']):
                    fields = self.nodes[node]['instruction']
                    encoded = ISA.encode(full_shape=True, **{k:tuple(v) if isinstance(v,list) and
                                         not k.startswith('_') else v for k,v in fields.items()})
                    self.assertEqual(words[entry+pc], encoded)
            for group in result['ownerorderedgroups']:
                offers = [result['offers'][i] for i in group]
                self.assertEqual([o['rank'] for o in offers], [0,1,2,3])
                self.assertEqual(len({o['entry'] for o in offers}), 1)
                self.assertTrue(all(o['identity'] == (1 << 31)|1048575 for o in offers))
            events = {e.get('node'): e for e in result['source_order']}
            self.assertEqual(events['L20.A0']['source'], self.nodes['L20.A0'])
            self.assertEqual(events['L20.fence']['source'], self.nodes['L20.fence'])
            self.assertTrue(result['unassigned_dedicated_services'])
            self.assertFalse(result['native_END_is_whole_stage_or_head_completion'])
            with self.assertRaisesRegex(ValueError, 'inactive candidate'):
                emit(result, result['ownerorderedgroups_by_stage']['40'], 40, out/'caller.cpp')

    def test_runtime_eids_never_default_to_zero(self):
        owner = self.owner()
        # Static field dispatcher is supplied as a test double; indexed nodes
        # must NOT reach it until the caller supplies actual six live EIDs.
        calls = []
        def dispatch(node, rank, *, expert_ids=None):
            calls.append((node, rank, expert_ids))
            f = self.nodes[node]['instruction']
            return dict(predicate=f.get('pred',0), fragments=[dict(stage=37, rank=rank,
                        die_id=148+rank, phase=0, key=0, word=ISA.encode(full_shape=True,
                        **{k:tuple(v) if isinstance(v,list) and not k.startswith('_') else v
                           for k,v in f.items()}), gather_local_rows=[0,1],
                        ordered_K=[[0,32]], source_matrix_sha256='test-double')])
        owner.dispatch = dispatch
        # The selected test movement may be on stage38; preserve the actual
        # movement stage as checked by the real packing function.
        original = owner.dispatch
        def located(node, rank, **kw):
            d = original(node, rank, **kw)
            movement = next(m for m in self.candidate['field_movements'] if m['node']==node)
            d['fragments'][0]['stage'] = movement['field_stages'][0]
            d['fragments'][0]['die_id'] = 4*movement['field_stages'][0]+rank
            return d
        owner.dispatch = located
        with tempfile.TemporaryDirectory() as t:
            result = emit_candidate_dispatch(owner,self.candidate,self.context(),Path(t)/'a',
                                             layers=[20])
        indexed = {n for n in result['deferred_field_nodes']
                   if self.bindings[n].get('selector_slot') is not None}
        self.assertTrue(indexed)
        self.assertTrue(all(n not in indexed for n,_,_ in calls))
        chosen = sorted(indexed, key=list(self.nodes).index)[0]
        calls.clear()
        with tempfile.TemporaryDirectory() as t:
            result = emit_candidate_dispatch(owner,self.candidate,self.context(),Path(t)/'b',
                        layers=[20],expert_ids_by_node={chosen:[1,5,17,88,207,383]})
        self.assertEqual([c[2] for c in calls if c[0]==chosen],
                         [[1,5,17,88,207,383]]*4)
        self.assertNotIn(chosen,result['deferred_field_nodes'])

    def test_native_transfer_uses_actual_writer_and_source_extent(self):
        from dsrom_s81_execution_binding import minimum_vm_extents
        with tempfile.TemporaryDirectory() as t:
            result = emit_candidate_dispatch(self.owner(),self.candidate,self.context(),
                        Path(t)/'a',layers=[20],include_fields=False)
        source = next(o for o in result['offers'] if o['rank']==0 and
                      any(r['node']=='L20.I6' for r in o['source_pc']))
        record = next(r for r in source['source_pc'] if r['node']=='L20.I6')
        base,count = minimum_vm_extents(record['instruction'])[0]
        destination = dict(source, stage=37, physical_endpoint=37, die_id=148)
        program = [ISA.encode(full_shape=True,unit=ISA.UNIT_END,wait=31)]
        transfer = emit_native_transfer(source,'L20.I6',destination,program,
                                       base,base,min(count,32))
        self.assertEqual(transfer['transfer_hooks_additional_source_reads'],0)
        self.assertEqual(transfer['capture_owner'],'existing NativeSu publication')
        with tempfile.TemporaryDirectory() as directory:
            emitted=emit_native_transfer(source,'L20.I6',destination,[],base,base,16,
                                         out=Path(directory)/'writer')
            text=(Path(directory)/'writer/transfer.hpp').read_text()
            self.assertIn('return {9u,2u,',text)
            self.assertIn(f'p.enroll_literal(9u,{{{{{base}u,16u}}}});',text)
            self.assertEqual(len((Path(directory)/'writer/prog.hex').read_text().splitlines()),2)
        self.assertEqual(transfer['entry'],1)
        self.assertEqual(transfer['producer'],10)
        self.assertEqual(transfer['source']['producer'],record['producer'])
        instruction = ISA.decode(program[1],full_shape=True)
        self.assertEqual(instruction['unit'],ISA.UNIT_SU)
        self.assertEqual(instruction['su_vec'],ISA.VEC_I)
        self.assertEqual(instruction['su_nin'],min(count,32))
        self.assertEqual(instruction['dst'],ISA.DST_VM)
        for operand in 'abcd':
            self.assertEqual(instruction[operand+'_base'],base)
            self.assertEqual(instruction[operand+'_si'],1)
        self.assertEqual(transfer['publication_enrollment']['output_extents'],
                         [[base,min(count,32)]])
        self.assertEqual(transfer['destination_scalar_ACKs'],min(count,32))
        with self.assertRaisesRegex(ValueError,'not written'):
            emit_native_transfer(source,'L20.I6',destination,program,0,0,1)
        bad = dict(destination,identity=0)
        with self.assertRaisesRegex(ValueError,'context differs'):
            emit_native_transfer(source,'L20.I6',bad,program,base,base,1)

    def test_branch_endpoint_is_not_a_serial_stage(self):
        # Explicit endpoint fixture exercises the Maxwell branch shape;
        # it does not qualify physical adoption of that map.
        mapping = dict(homes=[dict(layer_provider=19,service_home=100,
                        rank_service_die_ids=[400,401,402,403])],matrix_fragments=[])
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'a'
            result=emit_candidate_dispatch(self.owner(),self.candidate,self.context(),
                         out,layers=[19],include_fields=False,endpoint_map=mapping)
            self.assertTrue((out/'s100_r0/prog.hex').is_file())
        self.assertTrue(all(o['stage']==38 and o['physical_endpoint']==100
                            and o['die_id']==400+o['rank'] for o in result['offers']))
        self.assertEqual(result['logical_serial_stages'],81)
        self.assertEqual(result['added_serial_stages'],0)
        self.assertIn('100',result['ownerorderedgroups_by_endpoint'])

    def test_actual_adjacent_model_uses_hub101_without_remapping_fields(self):
        model=json.loads((ROOT/'results/uarch/dsrom_s81_level2_service_stream_20261004/model.json').read_text())
        home=next(h for h in model['homes'] if h['layer']==20)
        self.assertEqual((home['hub_endpoint'],home['adjacent_field_stage']),(101,37))
        with tempfile.TemporaryDirectory() as t:
            result=emit_candidate_dispatch(self.owner(),self.candidate,self.context(),
                Path(t)/'p',layers=[20],include_fields=False,endpoint_map=model)
            self.assertTrue((Path(t)/'p/s101_r0/prog.hex').is_file())
            with self.assertRaisesRegex(ValueError,'inactive candidate'):
                emit(result,result['ownerorderedgroups_by_endpoint']['101'],37,Path(t)/'caller.cpp')
        self.assertTrue(all(o['physical_endpoint']==101 and o['die_id']==404+o['rank']
                            for o in result['offers']))
        self.assertTrue(all(o['stage']==40 for o in result['offers'])) # source witness, not execution home
        for offer in result['offers']:
            for op in offer['source_pc']:
                self.assertEqual(op['native_operation']['index'],9+op['native_pc'])
        fence=next(e for e in result['source_order'] if e.get('node')=='L20.fence')
        self.assertEqual(fence['assignment']['physical_endpoint'],101)
        self.assertEqual(result['node_order_by_endpoint']['101'],
                         [[result['offers'][i]['node'] for i in g]
                          for g in result['ownerorderedgroups_by_endpoint']['101']])
        self.assertFalse(result['parent_dispatch_ready'])

    def test_changed_native_run_refuses(self):
        candidate = dict(self.candidate)
        candidate['ordered_nonfield_runs'] = [dict(r) for r in candidate['ordered_nonfield_runs']]
        selected = next(r for r in candidate['ordered_nonfield_runs'] if r['layer']==20)
        selected['stage'] = 39
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, 'assignment differs'):
                emit_candidate_dispatch(self.owner(),candidate,self.context(),Path(t)/'x',layers=[20])

    def test_adopted_input_is_not_candidate_mode(self):
        candidate = dict(self.candidate, adopted=True)
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, 'inactive service candidate'):
                emit_candidate_dispatch(self.owner(),candidate,self.context(),Path(t)/'x',layers=[20])


if __name__ == '__main__':
    unittest.main()
