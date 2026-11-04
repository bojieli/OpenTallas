import copy
import unittest
from head_boot_recipe import compile_recipe

PARAMS = dict(LOCAL_STAGE=1, LOCAL_RANK=0, PHASE_BOUND=1, CLOCK_RESET_ID=9,
              BOOT_HEADER_EDGE=100, BOOT_COMMIT_EDGE=110)

def fixture():
    types = {n: {'reset': {'start_role': 'bootstrap'}, 'contents': []} for n in ('h', 'c', 'l', 's')}
    types['h']['contents'] = [dict(module='ot_s81hd_host_ep_core', params=PARAMS)]
    types['c']['contents'] = [dict(module='ot_s81hd_ctl_core')]
    parts = [dict(name=n, type=t) for n, t in [('host','h'),('ctl','c'),('link','l'),('sp','s')]]
    def port(n, a, b): return dict(id=n, src=dict(part=a[0], bus=a[1]), dst=dict(part=b[0], bus=b[1]))
    ports = [port('i0',('link','a'),('host','coll_i0')), port('i1',('link','b'),('host','coll_i1')),
             port('r0',('host','h_rx_o'),('sp','hu_i')), port('r1',('sp','hu_o'),('ctl','h_rx_i'))]
    plan = dict(reset=dict(start='broadcast'), partition_types=types, partitions=parts, ports=ports,
                lanes=[dict(id='in0',ports=['i0']),dict(id='in1',ports=['i1']),dict(id='config',ports=['r0','r1'])],
                latency=dict(lanes=dict(in0=dict(cycles=2),in1=dict(cycles=2),config=dict(cycles=5))))
    offsets = dict(start=dict(mode='broadcast',bootstrap_types=sorted(types)),
                   parts={p['name']:dict(type=p['type'],release={'host':10,'ctl':12,'link':4,'sp':6}[p['name']]) for p in parts})
    def header(op, date): return 0x31434248 | (1<<32) | (op<<36) | (1<<40) | (9<<114) | (date<<242)
    programme = dict(test_only=True, start=dict(producer='external_host_sequence',die_edge=200),
        host_boot_counter_zero_global_edge=20,
        transport=dict(peer_to_hbc_input=7,peer_to_host_frame=3,peer_to_ctl_csr_apply=9,
                       hbc_commit_to_context_valid=1,peer_frame_period=4),
        hbc_records=[dict(receive_edge=100,payload=header(0,104)),dict(receive_edge=104,payload=0),
                     dict(receive_edge=110,payload=header(1,110))],
        config=dict(plen=9,glen=0,group=4,rbase=1,issue_offset=20,issue_period=100,merge_deadline=30),
        csr_apply_edges={'0':160,'1':164,'2':168,'3':172,'4':176,'9':180,'10':184,'8':188})
    return plan, offsets, programme

def split_fixture():
    """DH55-HSPLIT: hd_host -> W (HBC, coll_i0, h_rx_o) + E (lane1 coll_i1), one E->W seam lane (DH56: plan 4 cycles = 2 wrapper boundary flops + fixed E mid + W landing = +4 data cycles)."""
    p, o, a = fixture()
    p['partition_types']['h']['contents'][0]['module'] = 'ot_s81hd_host_w_core'
    p['partition_types']['e'] = {'reset': {'start_role': 'bootstrap'}, 'contents': [dict(module='ot_s81hd_host_e_core')]}
    p['partitions'].append(dict(name='host_e', type='e'))
    for x in p['ports']:
        if x['id'] == 'i1':
            x['dst']['part'] = 'host_e'
    p['ports'].append(dict(id='s0', src=dict(part='host_e', bus='l1_rx_o'), dst=dict(part='host', bus='l1_rx_i')))
    p['lanes'].append(dict(id='seam', ports=['s0']))
    p['latency']['lanes']['seam'] = dict(cycles=4)               # E mid + E u_bout + W u_bin + W core landing (fixed 2)
    o['start']['bootstrap_types'] = sorted(p['partition_types'])
    o['parts']['host_e'] = dict(type='e', release=10)
    return p, o, a

class HeadBootRecipe(unittest.TestCase):
    def test_split_host_keeps_hbc_dates_and_charges_the_seam_on_csr(self):
        p, o, a = split_fixture()
        a['transport']['peer_to_ctl_csr_apply'] = 13; a['transport']['peer_to_host_frame'] = 7   # +4 seam each
        r = compile_recipe(p, o, PARAMS, a)
        self.assertEqual(r['status'], 'TEST_RECIPE', r['blockers'])
        self.assertEqual((r['host_part'], r['host_e_part'], r['host1_seam_cycles']), ('host', 'host_e', 4))
        bp, bo, ba = fixture()
        b = compile_recipe(bp, bo, PARAMS, ba)
        self.assertEqual([f for f in r['frames'] if f['lane'] == 0], [f for f in b['frames'] if f['lane'] == 0])
        l1 = lambda rr: [(f['csr_apply_global_edge'], f['launch_global_edge']) for f in rr['frames'] if f['lane'] == 1]
        self.assertEqual(l1(r), [(ap, la - 4) for ap, la in l1(b)])         # same apply dates, launch 4 earlier
        p2, o2, a2 = split_fixture()                    # transport age == config plan cycles: seam cycle not charged
        a2['transport']['peer_to_ctl_csr_apply'] = 8    # < config 5 + seam 4
        r2 = compile_recipe(p2, o2, PARAMS, a2)
        self.assertEqual(r2['status'], 'BLOCKED'); self.assertIn('HOST-to-CTL', r2['blockers'][0])

    def test_relative_source_recipe_and_csr9_encoding(self):
        p,o,a=fixture();r=compile_recipe(p,o,PARAMS,a)
        self.assertEqual(r['status'],'TEST_RECIPE',r['blockers'])
        self.assertEqual(r['first_issue_global_edge'],232)
        self.assertEqual(len(r['frames']),11)
        csr=next(x for x in r['frames'] if x.get('csr_address')==9)
        self.assertEqual(csr['csr_value'],(20<<16)|100)
        self.assertEqual((int(csr['frame553'],16)>>24)&((1<<64)-1),csr['csr_value'])
    def test_rank_three_is_actually_written_to_controller(self):
        p,o,a=fixture();p['partition_types']['h']['contents'][0]['params']=dict(PARAMS,LOCAL_RANK=3)
        for i in (0,2):a['hbc_records'][i]['payload'] |= 3<<48
        r=compile_recipe(p,o,PARAMS,a)
        self.assertEqual(r['status'],'TEST_RECIPE',r['blockers'])
        self.assertEqual(next(x['csr_value'] for x in r['frames'] if x.get('csr_address')==2),3)
        del a['csr_apply_edges']['2']
        self.assertEqual(compile_recipe(p,o,PARAMS,a)['status'],'BLOCKED')
    def test_mission_transport_has_no_pre_start_reset_contract(self):
        p,o,a=fixture();p['partition_types']['s']['reset']['start_role']='mission'
        o['start']['bootstrap_types'].remove('s')
        r=compile_recipe(p,o,PARAMS,a)
        self.assertEqual(r['status'],'BLOCKED');self.assertEqual(r['frames'],[])
        self.assertEqual(r['routes'][2]['mission_reset_blockers'][0]['part'],'sp')
    def test_invalid_provider_defaults_cannot_be_promoted_by_programme(self):
        p,o,a=fixture();p['partition_types']['h']['contents'][0]['params']={}
        invalid=dict(PARAMS,PHASE_BOUND=0,CLOCK_RESET_ID=0,LOCAL_STAGE=255,LOCAL_RANK=4)
        r=compile_recipe(p,o,invalid,a)
        self.assertEqual(r['status'],'BLOCKED');self.assertEqual(r['frames'],[])
    def test_transport_overrides_preserve_mission_leaf_role(self):
        p,o,a=fixture()
        for t,buses in (('l',['a','b']),('s',['hu_i','hu_o'])):
            p['partition_types'][t]['reset']=dict(start_role='mission',bootstrap_buses=buses)
            o['start']['bootstrap_types'].remove(t)
        r=compile_recipe(p,o,PARAMS,a)
        self.assertEqual(r['status'],'TEST_RECIPE',r['blockers'])
        self.assertEqual(p['partition_types']['s']['reset']['start_role'],'mission')
        p['partition_types']['s']['reset']['bootstrap_buses'].remove('hu_o')
        self.assertEqual(compile_recipe(p,o,PARAMS,a)['status'],'BLOCKED')
    def test_source_authority_and_configuration_mutants(self):
        for change in ('producer','start','run','header','old_offsets'):
            with self.subTest(change=change):
                p,o,a=fixture()
                if change=='producer':a['start']['producer']='ctl.job_active_o'
                if change=='start':a['start']['die_edge']=150
                if change=='run':a['csr_apply_edges']['8']=170
                if change=='header':a['hbc_records'][0]['payload']^=1<<242
                if change=='old_offsets':o['start']['bootstrap_types']=[]
                if change=='old_offsets':
                    with self.assertRaises(ValueError):compile_recipe(p,o,PARAMS,a)
                else:
                    r=compile_recipe(p,o,PARAMS,a)
                    self.assertEqual(r['status'],'BLOCKED');self.assertEqual(r['frames'],[])

if __name__=='__main__':unittest.main()
