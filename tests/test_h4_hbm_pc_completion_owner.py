import importlib.util
import pathlib
import unittest
P=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('owner',P/'tools/h4_hbm_pc_completion_owner.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def identity(n=1):return dict(generation=1,sequence=n,rank=0,SM=0,lease=n,provider_reference=1,sector=0,address=0,local_address=0,source_command_sha256='a'*64,provider_sha256='b'*64)
def owner(pc):return m.CompletionOwner(pc,local_owners=m.LocalACKOwners())
class OwnerTests(unittest.TestCase):
    def finish(self,o,t,i):
        o.local_issue(t,'RF');self.assertFalse(o.local_ack(0,'RF',valid=True,ready=False,physical_tag=t))
        self.assertTrue(o.local_ack(0,'RF',valid=True,ready=True,physical_tag=t))
        for e in ('visibility','consumer','reverse'):o.advance(t,e,identity=i)
        self.assertFalse(o.release(t,reverse_valid=True,reverse_ready=False));self.assertTrue(o.release(t,reverse_valid=True,reverse_ready=True))
    def test_full_no_ready_capture_capacity_and_no_backend_retire(self):
        o=owner(0);tags=[]
        for c in range(6):
            for n in range(16):tags.append(o.reserve(c,n,identity(c*16+n+1),write=True))
        self.assertEqual(len(o.rows),96)
        for t in reversed(tags):o.capture(t,write=True)
        self.assertEqual(len(o.rows),96)
        with self.assertRaises(ValueError):o.reserve(0,1,identity(),write=True)
        with self.assertRaises(ValueError):o.release(tags[0],reverse_valid=True,reverse_ready=True)
    def test_generation_stale_after_reuse(self):
        o=owner(0);i=identity();t=o.reserve(0,77,i,write=True);self.assertEqual(o.capture(t,write=True),77);self.finish(o,t,i)
        new=o.reserve(0,77,identity(2),write=True);self.assertNotEqual(t,new)
        with self.assertRaises(ValueError):o.capture(t,write=True)
        self.assertEqual(len(o.rows),1);o.capture(new,write=True)
    def test_unmatched_and_wrong_direction_never_retire(self):
        o=owner(0);t=o.reserve(1,99,identity(),write=True)
        for bad in (t^(1<<32),t^(1<<7),t^15):
            with self.assertRaises(ValueError):o.capture(bad,write=True)
        with self.assertRaises(ValueError):o.capture(t,write=False,data=bytes(32))
        self.assertEqual(o.rows[t&127]['phase'],'BACKEND');o.capture(t,write=True)
        with self.assertRaises(ValueError):o.capture(t,write=True)
    def test_read_data_held_and_original_tag_restored(self):
        o=owner(127);i=dict(identity(),address=127);t=o.reserve(5,2**32-1,i,write=False);data=bytes(range(32))
        self.assertEqual(o.capture(t,write=False,data=data),2**32-1);self.assertEqual(o.rows[t&127]['data'],data)
        self.finish(o,t,i)
    def test_local_owner_blocks_other_until_common_ACK(self):
        o=owner(0);a=o.reserve(0,1,identity(),write=True);b=o.reserve(1,2,identity(2),write=True)
        for t in (a,b):o.capture(t,write=True)
        self.assertFalse(o.local_issue(a,'RF',sink_ready=False));self.assertEqual(o.rows[a&127]['phase'],'CAPTURED');o.local_issue(a,'RF')
        with self.assertRaises(ValueError):o.local_issue(b,'RF')
        with self.assertRaises(ValueError):o.local_ack(0,'RF',valid=True,ready=True,physical_tag=b)
        o.local_ack(0,'RF',valid=True,ready=True,physical_tag=a);self.assertEqual(o.rows[a&127]['common_copy_mask'],3);o.local_issue(b,'RF')
    def test_causal_order_and_lineage_required(self):
        o=owner(0);t=o.reserve(0,1,identity(),write=True);o.capture(t,write=True)
        with self.assertRaises(ValueError):o.advance(t,'visibility',identity=identity())
        o.local_issue(t,'shared');o.local_ack(0,'shared',valid=True,ready=True,physical_tag=t)
        with self.assertRaises(ValueError):o.advance(t,'visibility',identity=identity(2))
        with self.assertRaises(ValueError):o.advance(t,'reverse',identity=identity())
    def test_generation_exhaustion_never_wraps(self):
        o=owner(0);o.generations[:16]=[2**25-1]*16
        with self.assertRaises(ValueError):o.reserve(0,0,identity(),write=True)
        self.assertEqual(o.rows,{})
    def test_source_and_storage_complete_protected_envelope(self):
        x=m.model();self.assertEqual(x['context']['entries'],12288);self.assertEqual(x['context']['held_local_owners'],64)
        self.assertEqual(x['context']['storage_rows']['provenance']['protected_bits'],576)
        self.assertEqual(x['ports']['capture_flag_write_ports_per_plane'],2)
        self.assertEqual(x['context']['held_control_queues_per_PC'],4)
        self.assertGreater(x['storage_bits_per_die'],12288*512);self.assertFalse(x['engine_build_ready'])
        self.assertEqual(x['physical']['source_bound_retained_context']['Qwen']['retained_SMs'],32)
        self.assertFalse(x['physical']['source_bound_retained_context']['Qwen']['fit'])
        self.assertIsNone(x['latency']['whole_token_ns']);self.assertIsNone(x['physical']['clock_PG_via_cut_allocation'])
    def test_interval_join_once_only_missing_and_unknown_refuse(self):
        sha=m.model()['source_sha256']['PC.sv'];rows=[dict(id=e,event=e,operator='PC10',PC=0,lease='actual-ref',start_ns=i,end_ns=i+1,source_sha256=sha) for i,e in enumerate(m.TERMS)]
        x=m.compose_intervals(rows+[rows[0]]);self.assertEqual(x['unique_occurrences'],9);self.assertEqual(x['proposed_occupied_ns'],9)
        for bad in (rows[:-1],[],[dict(r,end_ns=r['start_ns']) for r in rows]):
            with self.assertRaises(ValueError):m.compose_intervals(bad)
        with self.assertRaises(ValueError):m.compose_intervals(rows+[dict(rows[0],end_ns=5)])
        bad=[dict(r) for r in rows];bad[3]['start_ns']=1
        with self.assertRaises(ValueError):m.compose_intervals(bad)
        self.assertFalse(x['hardware_admitted']);self.assertIsNone(x['composed_critical_path_ns'])
    def test_shared_SM_owner_across_PC_tag_collision(self):
        directory=m.LocalACKOwners();a=m.CompletionOwner(0,local_owners=directory);b=m.CompletionOwner(1,local_owners=directory)
        ta=a.reserve(0,1,identity(),write=True);tb=b.reserve(0,1,dict(identity(),address=1),write=True)
        self.assertEqual(ta,tb);a.capture(ta,write=True);b.capture(tb,write=True);a.local_issue(ta,'RF')
        with self.assertRaises(ValueError):b.local_issue(tb,'RF')
        with self.assertRaises(ValueError):b.local_ack(0,'RF',valid=True,ready=True,physical_tag=tb)
        a.local_ack(0,'RF',valid=True,ready=True,physical_tag=ta);b.local_issue(tb,'RF')
    def test_exact_replay(self):self.assertEqual((m.BASE/'model.json').read_bytes(),m.canonical(m.model()))
if __name__=='__main__':unittest.main()
