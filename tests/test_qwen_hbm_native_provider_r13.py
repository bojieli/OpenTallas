import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_hbm_native_provider_r13 as m

class NativeTests(unittest.TestCase):
    def test_full_shape_metadata_four_stack_1GHz_calendar(self):
        x=m.scenario();self.assertEqual(x['writer_sector_completions'],272)
        self.assertEqual(x['reader_completions'],288);self.assertEqual(x['RMW_reads'],256)
        self.assertEqual({e['stack'] for e in x['bank_events']},{0,1,2,3})
        self.assertTrue(all(m.F(e['ps'])%1000==0 for e in x['bank_events']))
        self.assertFalse(x['physical_provider_runtime_ready']);self.assertEqual(x['source_completion_events'],0)
    def test_equal_local_address_different_stack_no_RAW_alias(self):
        rows=[dict(stack=0,sector=0,partial=False),dict(stack=1,sector=0,partial=False)]
        p=m.NativeProvider(rows);p.reserve(0,7,8);p.reserve(1,7,8)
        d=p.WR_column(0,(0,7,8));p.advance(d)
        self.assertIn((0,0),p.channel_backing);self.assertNotIn((1,0),p.channel_backing)
        with p.channel(0):self.assertTrue(p.RAW_read_ready(0))
        with p.channel(1):self.assertFalse(p.RAW_read_ready(0))
        self.assertIsNot(p.channels[0]['cal'],p.channels[1]['cal'])
    def test_return_capture_requires_actual_owner_and_time(self):
        rows=m.fixture()['sector_rows'];p=m.NativeProvider(rows);p.reserve(0,7,8)
        owner=(rows[0]['sector'],7,8);due=p.RMW_read(0,owner)
        with self.assertRaises(ValueError):p.capture_owned_read('RMW',0,owner)
        p.advance(due)
        with self.assertRaises(ValueError):p.capture_owned_read('RMW',0,(owner[0],9,8))
        with self.assertRaises(ValueError):p.RMW_result_commit(0,owner)
        p.capture_owned_read('RMW',0,owner);p.RMW_result_commit(0,owner)
        self.assertFalse(p.read_tags)
    def test_native_clock_configuration_does_not_mutate_r10_module(self):
        import qwen_hbm_shoreline_remedy_r10 as original
        self.assertEqual(original.PHY,512);self.assertEqual(m.base.PHY,1000)
    def test_out_of_capacity_refused_before_owner_accept(self):
        p=m.NativeProvider([dict(stack=0,sector=1<<32,partial=False)])
        with self.assertRaises(ValueError):p.reserve(0,7,8)
        self.assertFalse(p.live)

if __name__=='__main__':unittest.main()
