"""Input-only NP4 cache joins cannot authorize a speculative token run."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class CachedSlotsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        old=sys.path[:];sys.path.insert(0,str(ROOT/'tools'))
        try:
            spec=importlib.util.spec_from_file_location('dewey_cached_slots',ROOT/'tools/qwen_rom_combined_stream4_layer_prepare.py')
            self.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.mod)
        finally:sys.path[:]=old
        self.a=self.base/'a';self.b=self.base/'b';self.a.mkdir();self.b.mkdir()
        for directory,frames in ((self.a,{'8187':{'token':15}}),(self.b,{'8188':{'token':10952},'8189':{'token':18065},'8190':{'token':1269}})):
            (directory/'oracle.json').write_text(json.dumps(dict(tp=4,groups=6144,layers=1,per_position=frames)))
        self.sha=self.mod.selected.sha
        self.roots=[self.a,self.b,self.b,self.b];self.hashes=[self.sha(p/'oracle.json') for p in self.roots]

    def bind(self,**changes):
        args=dict(oracle_root=self.a,oracle_sha256=self.hashes[0],slot_roots=self.roots,
                  slot_hashes=self.hashes,position=8187,npos=4,layer=0)
        args.update(changes);return self.mod._cached_slot_frames(**args)

    def test_true_positions_and_tokens_retained(self):
        roots,paths,frames=self.bind()
        self.assertEqual([f['token'] for f in frames],[15,10952,18065,1269])
        self.assertEqual(roots[0],self.a)
        self.assertEqual(len(paths),4)

    def test_no_history_owner_substitution_or_slot_migration(self):
        for changes in (dict(slot_roots=[self.b]*4),dict(position=8188),dict(position=8189),dict(slot_hashes=self.hashes[:3])):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.bind(**changes)

    def test_mutated_slot_cache_refused(self):
        (self.b/'oracle.json').write_text('{}')
        with self.assertRaises(ValueError):self.bind()

    def test_blocks_and_cached_packing_are_not_drafter_outputs(self):
        for record in (dict(P1=8187,drafts=[10952,18065,1269]),
                       dict(status='actual_cached_slots_ready',position=8187,tokens=[15,10952,18065,1269]),
                       dict(schema='opentallas.qwen-dspark-drafter-layer-golden.v1',start=8188)):
            release=self.base/'release.json';release.write_text(json.dumps(record));out=self.base/'unauthorized'
            with self.subTest(record=record),self.assertRaisesRegex(ValueError,'released pending/draft step receipt absent'):
                self.mod.prepare_accept_head(release=release,release_sha256=self.sha(release),step='step1',
                    decoder_sources=[],decoder_images=[],head_images=[],head_manifest=self.base/'absent',
                    head_manifest_sha256='',preload=self.base/'absent',preload_sha256='',history=self.base,
                    layer=0,output=out,oracle_root=self.a,oracle_sha256=self.hashes[0])
            self.assertFalse(out.exists())

    def test_cross_position_drafter_output_refused_before_materialization(self):
        for change in (dict(start=49),dict(anchor=24),dict(kv='fp32'),dict(S=7)):
            draft=dict(start=8187,anchor=15,S=3,kv='fp8',draft_tokens=[10952,18065,1269]);draft.update(change)
            record=dict(schema='opentallas.qwen-dspark-oracle-gpu.v1',
                        step1=dict(P=8187,block_tokens=[15,10952,18065,1269]),step1_draft=draft)
            release=self.base/'release.json';release.write_text(json.dumps(record));out=self.base/'unauthorized'
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'drafter start/anchor/precision differs'):
                self.mod.prepare_accept_head(release=release,release_sha256=self.sha(release),step='step1',
                    decoder_sources=[],decoder_images=[],head_images=[],head_manifest=self.base/'absent',
                    head_manifest_sha256='',preload=self.base/'absent',preload_sha256='',history=self.base,
                    layer=0,output=out,oracle_root=self.a,oracle_sha256=self.hashes[0])
            self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
