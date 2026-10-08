import unittest
from hbm_relay_bank_inventory import RollbackIndex, candidate_positions, square, validate, complex_connect

class BankInventoryTests(unittest.TestCase):
    def test_rollback_releases_physical_and_bucket_state(self):
        i=RollbackIndex([1000,1000]);i.add([10,10,30,30]);mark=len(i.boxes);i.add([210,210,242.4,242.4]);i.rollback(mark)
        self.assertEqual(len(i.boxes),1);self.assertTrue(i.legal([210,210,242.4,242.4]));self.assertFalse(i.legal([10,10,30,30]))
    def test_real_bank_size(self):
        b=square([100,100],32.4);self.assertAlmostEqual(b[2]-b[0],32.4)
    def test_edge_candidate_in_narrow_bay(self):
        i=RollbackIndex([1000,1000]);i.add([10,10,100,900]);i.add([124.3201,10,900,900])
        pts=candidate_positions([110,100],20,i,[(0,0)])
        self.assertTrue(any(i.legal(square(p,20)) for p in pts))
    def test_independent_latency_and_collision_replay(self):
        a,b=square([100,100],20),square([200,100],20)
        result={'outline_um':[1000,1000],'endpoint_boxes':[a,b],'chains':[{'bus':'test','bit_indices':[0],'stations':[{'kind':'source','box_um':a,'cycles':1},{'kind':'sink','box_um':b,'cycles':1}],'hops':[{'path_um':[[100,100],[200,100]]}]}]}
        v=validate(result,{'insts':[]});self.assertEqual(v['errors'],[{'wrong_latency':'test'}])
        result['chains'][0]['stations'][0]['cycles']=71
        self.assertEqual(validate(result,{'insts':[]})['errors'],[{'invalid_primitive_latency':'test'}])
        # Restoring contract and injecting physical obstruction cannot pass replay.
        result['chains'][0]['stations'][0]['cycles']=1
        self.assertGreater(validate(result,{'insts':[{'x':140,'y':90,'w':20,'h':20}]})['error_count'],1)
    def test_full_mixed_seventy_two_cycle_chain(self):
        cycles=[1]+[8]*8+[1]*7
        stations=[]
        for i,n in enumerate(cycles):
            stations.append({'kind':'source' if i==0 else ('sink' if i==15 else ('delay_bank8' if n==8 else 'single_cycle')),'cycles':n,'box_um':square([100+50*i,100],32.4 if n==8 else 20)})
        hops=[{'path_um':[[100+50*i,100],[150+50*i,100]]} for i in range(15)]
        r={'outline_um':[2000,1000],'endpoint_boxes':[stations[0]['box_um'],stations[-1]['box_um']],'chains':[{'bus':'mixed','bit_indices':list(range(64)),'stations':stations,'hops':hops}]}
        self.assertEqual(validate(r,{'insts':[]})['error_count'],0)
        stations[1]['box_um']=square([150,100],20)
        self.assertGreater(validate(r,{'insts':[]})['error_count'],0)

    def test_complex_route_cannot_jump_wall(self):
        i=RollbackIndex([1000,1000]);i.add([140,1,160,999]);self.assertIsNone(complex_connect([100,100],[200,100],i,set(),5.12,260))
if __name__=='__main__':unittest.main()
