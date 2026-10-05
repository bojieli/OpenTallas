import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import uarch_model_qwen_kv_beat_retirement as B
from qwen_kv_word_retirement_contract import WordRetirement

class CausalTests(unittest.TestCase):
    def fixture(self,v=False):return WordRetirement(0,589824 if v else 0,16,(9,13),4)
    def capture(self,d,key,accepted=True):
        st,b=key;sector=d.base+b
        d.capture(d.epoch,st,b,sector,B.A.pc_of(sector),bytes([st*16+b])*32,accepted)
    def test_address_mapping_four_quarters_matches_source_cohort(self):
        for d in (self.fixture(),self.fixture(True)):
            words,_=B.A.cohort_words(0,d.base,16)
            self.assertEqual(set(d.required),words)
            self.assertEqual(len(words),32)
            self.assertTrue(all(len(q)==4 for q in d.required.values()))
    def test_word_dispatch_precedes_unrelated_member_but_tag_quarantine(self):
        d=self.fixture();w=next(iter(d.required));keys={k for k,o in d.required[w].values()}
        for key in keys:self.capture(d,key)
        self.assertEqual(len(d.commit(d.epoch,w,True)),64)
        for key in keys:
            if d.beat_words[key]<={w}:d.ack(d.epoch,key,True)
        with self.assertRaisesRegex(ValueError,'quarantine'):d.release(d.epoch,True)
        self.assertFalse(d.released)
    def test_V_multiword_beat_waits_all_words_and_readers(self):
        d=self.fixture(True);key=(0,0);words=d.beat_words[key];self.assertGreater(len(words),1)
        needed={k for w in words for k,o in d.required[w].values()}
        for k in needed:self.capture(d,k)
        w=next(iter(words));d.commit(d.epoch,w,True)
        with self.assertRaises(ValueError):d.ack(d.epoch,key,True)
        for other in words-{w}:d.commit(d.epoch,other,True)
        d.borrow(d.epoch,w)
        with self.assertRaisesRegex(ValueError,'reader'):d.ack(d.epoch,key,True)
        d.drain(d.epoch,w);d.ack(d.epoch,key,False);self.assertFalse(d.acked)
        d.ack(d.epoch,key,True)
    def test_epoch_duplicate_and_backpressure_do_not_mutate(self):
        d=self.fixture();self.capture(d,(0,0),False);self.assertFalse(d.captured)
        with self.assertRaises(ValueError):d.capture((10,13),0,0,0,B.A.pc_of(0),b'x'*32,True)
        with self.assertRaises(ValueError):d.capture(d.epoch,0,0,1,B.A.pc_of(0),b'x'*32,True)
        self.assertFalse(d.captured);self.capture(d,(0,0))
        with self.assertRaises(ValueError):self.capture(d,(0,0))
    def test_all_ACK_reader_remaining_PC_drains_before_generation_reuse(self):
        d=self.fixture()
        for key in d.beat_words:self.capture(d,key)
        for w in d.required:d.commit(d.epoch,w,True)
        for key in d.beat_words:d.ack(d.epoch,key,True)
        self.assertFalse(any(d.remaining_PC.values()));d.release(d.epoch,True)
        with self.assertRaisesRegex(ValueError,'reused'):d.borrow(d.epoch,next(iter(d.required)))
    def test_Ampere_price_named_once_and_unknown_protection_nonzero_scope(self):
        old=json.loads((B.ROOT/'results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json').read_text())
        price=B.price(old)
        self.assertEqual(price['Ampere_gross_control']['FFs'],169472)
        self.assertTrue(price['Ampere_ready_controls_charged_once'])
        self.assertGreater(price['incremental_known_mm2'],.1455818832)
        self.assertIsNone(price['mutable_storage_protection_area_mm2'])
        self.assertFalse(price['existing_macros_or_fill_root_recharged'])

if __name__=='__main__':unittest.main()
