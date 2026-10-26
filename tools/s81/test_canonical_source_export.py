"""Allocator topology export mechanism; synthetic geometry never qualifies a die."""
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).with_name('canonical_source_export.py')

class ExportTests(unittest.TestCase):
    def test_allocator_counts_and_actual_children_not_old_full_die_constants(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            stage=dict(region_bounds=[0,1,3], BF_site_IDs=[1],
                PHW_required_by_stage=[4]*89,provider_homes={},
                rank_dies=[dict(stage=s,rank=r,die_id=4*s+r) for s in range(89) for r in range(4)])
            frames={'0':dict(elems=[[0,'Q',0,0]]),
                    '1':dict(elems=[[1,'BF',0,0],[2,'Q',1,0]])}
            names=['cf0','cf1']
            for i in range(3):
                names += [f'e{i}',f's{i}']+[f'c{i}_{j}' for j in range(7)]
            names += ['e1w','e1e']
            plan=dict(frames=frames,insts=[[n,'fixture',0,0,1,1,'R0','fixture','fixture'] for n in names],scope='synthetic mechanism',calendar={})
            (d/'stage.json').write_text(json.dumps(stage));(d/'plan.json').write_text(json.dumps(plan))
            args=[sys.executable,str(SCRIPT),'--plan',str(d/'plan.json'),'--stage-map',str(d/'stage.json'),'--out',str(d/'out.gz')]
            run=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            result=json.load(gzip.open(d/'out.gz','rt'))
            self.assertEqual(result['counts'],dict(field_pairs=3,bf_pairs=1,roots=2,stages=89,rank_dies=356))
            self.assertTrue(all(r['programme_id'] is None for r in result['rank_programme_bindings']))
            self.assertFalse(result['native_qualified'])
            # FIELD homes must consume the same allocator identity and explicit
            # complete matrix count; a truncated source must fail.
            matrix=dict(compiled_NP=3,stage=88,layer=39,alias='fixture',
                rank_slices=[dict(rows=[r,r+1]) for r in range(4)],
                plans=[[0,2,1,1,128,0,1]])
            with gzip.open(d/'matrices.gz','wt') as f:f.write(json.dumps(matrix)+'\n')
            with gzip.open(d/'bindings.gz','wt') as f:pass
            verdict=dict(decoder_matrix_capacity_PASS=True,failures=[],counts=dict(declarations=1,placed=1))
            (d/'verdict.json').write_text(json.dumps(verdict))
            homes=[sys.executable,str(SCRIPT.with_name('canonical_field_homes.py')),
                '--canonical',str(d/'out.gz'),'--matrices',str(d/'matrices.gz'),
                '--bindings',str(d/'bindings.gz'),'--mapping-verdict',str(d/'verdict.json'),
                '--out',str(d/'homes')]
            run=subprocess.run(homes,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            entry=json.loads(gzip.open(d/'homes/field_fragment_homes.jsonl.gz','rt').read())
            self.assertEqual(entry['physical_die_ids'],[352,353,354,355])
            verdict['counts']=dict(declarations=2,placed=2)
            (d/'verdict.json').write_text(json.dumps(verdict))
            homes[-1]=str(d/'truncated')
            self.assertNotEqual(subprocess.run(homes,capture_output=True).returncode,0)
            stage['rank_dies'].pop();(d/'stage.json').write_text(json.dumps(stage))
            self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0)
            stage['rank_dies'].append(dict(stage=88,rank=3,die_id=355));(d/'stage.json').write_text(json.dumps(stage))
            plan['insts']=[i for i in plan['insts'] if i[0]!='c2_6'];(d/'plan.json').write_text(json.dumps(plan))
            self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0)

if __name__=='__main__': unittest.main()
