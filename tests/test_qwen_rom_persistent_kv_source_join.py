"""Independent source issue/address checks for the transport successor."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_persistent_kv_g0 import Homes, burst_assembly, PublishedProvider, Owner, calendar

class SourceJoinTests(unittest.TestCase):
    def test_fill_destinations_follow_emitted_split_issue_order(self):
        import hdc_golden as golden
        import qwen_o4_kv_slice_map_w12 as source
        sk,sv = golden.attn_splits(128,6144)
        self.assertEqual((sk,sv),(128,512))
        source.KV_NH=2; source.KV_VB=2<<16
        homes=Homes()
        for kind in ('K','V'):
            for head in range(2):
                for position in (0,15,16,511,512,8191):
                    for dim in range(128):
                        if kind=='K':
                            q,c=position//16%48,dim
                            group=q*sk+c
                            word=((head*512+position//16)*128+dim)
                            lane=position%16
                        else:
                            q,c=dim//16,position%sv
                            group=q*sv+c
                            word=(2<<16)+(head*8192+position)*8+dim//16
                            lane=dim%16
                        expected=(group//4,source.local(word,6144),(group%4)*16+lane)
                        self.assertEqual(homes.tile(kind,head,position,dim),expected,
                                         (kind,head,position,dim))
    def test_burst_credits_cover_source_destination_fanout(self):
        binding=burst_assembly()
        self.assertEqual(binding['per_burst_destinations'],{'K':16,'V':64})
        self.assertEqual(binding['required_slots_per_stack'],1024)
    def test_existing_actual_compiler_and_state_provider_join(self):
        from qwen_hbm_complete_program import compile_program
        from qwen_hbm_complete_executor import PersistentMemory
        graph=compile_program(tp=2,context=8192,groups=6144)
        memory=PersistentMemory(graph)
        provider=PublishedProvider(memory,0,7)
        owner=Owner(0,3,35,7)
        with self.assertRaisesRegex(ValueError,'prefix absent'): provider.validate(owner,1)
        # Only explicit fixture bytes enter the existing provider; no tensor or
        # golden numerical run and no promoted software fence hardware ACK.
        memory.published[35,1,0]=0
        address=memory._address(1,35,'K',3,0,127)
        memory.bytes[address]=231
        self.assertEqual(provider.read_byte(owner,'K',1,0,127),231)
        self.assertNotEqual(address,memory._address(1,34,'K',3,0,127))
    def test_idle_refresh_does_not_accumulate_false_debt(self):
        small=calendar(range(256)); large=calendar(range(512))
        # Independent regression witness: invalid inherited calendar consumed
        # 3,684,535cycles for256sectors. A background serviced interval remains
        # proportional; refresh and row-opening phase permit small variation.
        self.assertLess(small['cycles_1p2GHz'],200000)
        self.assertLess(large['cycles_1p2GHz'],small['cycles_1p2GHz']*3)
        self.assertEqual(large['command_audit']['status'],'PASS_COMMAND_TIMING_INEQUALITIES')
    def test_stack_command_calendar_includes_idle_refresh_and_rmw(self):
        result=calendar(range(1024))
        self.assertEqual(result['read_sectors'],1024)
        self.assertGreater(result['dram_events'],1024)
        rmw=calendar([(0,False),(0,True)])
        self.assertEqual((rmw['read_sectors'],rmw['write_sectors']),(1,1))
if __name__=='__main__': unittest.main()
