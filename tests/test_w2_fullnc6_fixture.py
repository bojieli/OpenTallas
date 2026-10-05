import importlib.util
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('w2_fixture',ROOT/'tools/w2_fullnc6_fixture.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

class OracleTests(unittest.TestCase):
    def test_fullwidth_sixclient_identity(self):
        o=m.Oracle()
        for client in range(6):
            k=m.Identity(client,0xffffffff,15,False)
            self.assertEqual(k.provider_tag,client<<32|0xffffffff)
            self.assertEqual(k.scoped39,k.provider_tag<<4|15)
            o.cycle(issue=k)
        self.assertEqual(len(o.entries),6)

    def test_all330_accepted_request_bits_and_high_patterns(self):
        req=m.Request(m.Identity(5,0xfedcba98,15,True),0x300000020,(1<<255)|0x9876)
        self.assertEqual(req.address>>32,3)
        self.assertEqual(req.data>>255,1)
        m.check_accepted_request(req,req.wire_tuple)
        for field,width in enumerate((1,34,35,4,256)):
            for bit in range(width):
                mutant=list(req.wire_tuple);mutant[field]^=1<<bit
                with self.assertRaises(m.ProtocolError):m.check_accepted_request(req,mutant)

    def test_r5_withdraw_change_negative_original_lease_is_retained(self):
        # Independent full-tuple negative control, not an RTL scheduling replay.
        # The blocked17th offer inherited data15. Withdrawal without
        # admission_stop does not authorize replacing its original lease.
        identity=m.Identity(0,99,1,False)
        original=m.Request(identity,0x300000020,(1<<255)|15)
        later_issue=m.Request(identity,0x300000020,(1<<255)|99)
        self.assertEqual(original.wire_tuple[:4],later_issue.wire_tuple[:4])
        self.assertNotEqual(original.data,later_issue.data)
        with self.assertRaisesRegex(m.ProtocolError,'held caller original'):
            m.check_accepted_request(original,later_issue.wire_tuple)
        # The corrected stimulus captures data99 BEFORE first offering it,
        # and keeps that entire original through the actual acceptance.
        corrected_original=m.Request(identity,0x300000020,(1<<255)|99)
        m.check_accepted_request(corrected_original,later_issue.wire_tuple)

    def test_fixture_checks_original_tuple_and_uses_actual_echoes(self):
        text=(ROOT/'rtl/test/w2_fullnc6_functional_20261003/tb.sv').read_text()
        self.assertIn('{observed_pwe,observed_pa,observed_pt,observed_pg,observed_pd} !==',text)
        self.assertIn('{caller_we[c],caller_addr[c],3\'(c),caller_tag[c],caller_gen[c],caller_data[c]}',text)
        self.assertIn('receipt_pt[c][r]=observed_pt;receipt_pg[c][r]=observed_pg;',text)
        self.assertIn('accepted_echo(c,t,g,0,prt,prg)',text)
        self.assertIn('accepted_echo(c,t,g,1,pwt,pwg)',text)
        self.assertNotIn('receipt_next',text)
        self.assertIn('34\'h300000020',text)
        self.assertIn('HIGH_DATA=256\'b1<<255',text)

    def test_oldstate_sameedge_return_failclosed(self):
        o=m.Oracle();k=m.Identity(5,0xfedcba98,15,False)
        with self.assertRaises(m.ProtocolError):o.cycle(issue=k,read=(k,123))
        self.assertEqual(o.entries,{k:('issued',None)})
        self.assertTrue(o.fault)

    def test_held_credit_joint_retirement(self):
        o=m.Oracle();r=m.Identity(1,0xffffffff,7,False);w=m.Identity(2,0xffffffff,7,True)
        o.cycle(issue=r);o.cycle(issue=w)
        o.cycle(read=(r,2**255+19),write=w)
        for _ in range(30):o.cycle()
        self.assertEqual(o.entries[r],('held',2**255+19))
        self.assertEqual(len(o.entries),2)
        o.cycle(consume=(r,w));self.assertFalse(o.entries)

    def test_wrong_tag_gen_client_direction_and_duplicate(self):
        good=m.Identity(1,0xfedcba98,3,False)
        for bad in (m.Identity(2,good.tag,3,False),m.Identity(1,good.tag+1,3,False),
                    m.Identity(1,good.tag,2,False),m.Identity(1,good.tag,3,True)):
            o=m.Oracle();o.cycle(issue=good)
            with self.assertRaises(m.ProtocolError):o.cycle(read=(bad,1))
            self.assertEqual(o.entries[good],('issued',None))
        o=m.Oracle();o.cycle(issue=good);o.cycle(read=(good,12))
        with self.assertRaises(m.ProtocolError):o.cycle(read=(good,13))
        self.assertEqual(o.entries[good],('held',12))

    def test_full16_no_sameedge_credit_bypass(self):
        o=m.Oracle();keys=[m.Identity(0,i,15,False) for i in range(16)]
        for k in keys:o.cycle(issue=k)
        o.cycle(read=(keys[0],100))
        with self.assertRaises(m.ProtocolError):o.cycle(issue=m.Identity(0,99,15,False),consume=(keys[0],))
        self.assertEqual(len(o.entries),16)

    def test_fences_never_implied_by_empty(self):
        for provider,reverse,reset in ((False,True,True),(True,False,True),(True,True,False)):
            with self.assertRaises(m.ProtocolError):m.Oracle().fence(provider=provider,reverse=reverse,reset=reset)
        o=m.Oracle();o.fence(provider=True,reverse=True,reset=True)
        self.assertEqual(o.epoch,1)
        k=m.Identity(0,1,0,False);o.cycle(issue=k)
        with self.assertRaises(m.ProtocolError):o.fence(provider=True,reverse=True,reset=True)
        self.assertIn(k,o.entries)

    def test_bounds(self):
        for c,t,g in ((6,0,0),(-1,0,0),(0,2**32,0),(0,0,16)):
            with self.assertRaises(m.ProtocolError):m.Identity(c,t,g,False)

    def test_fixture_no_force_no_currentclean_substitution(self):
        s=(ROOT/'rtl/test/w2_fullnc6_functional_20261003/tb.sv').read_text()
        self.assertNotIn('force ',s)
        self.assertNotIn('@@',s)
        self.assertNotIn('dut.outstanding',s)
        self.assertNotIn('dut.state',s)
        self.assertIn('reverse_fenced',s)
        self.assertIn('fault_matrix',s)
        self.assertIn('full_double_pairs',s)
        self.assertEqual(s.count('get_cw=dut.'),219)
        self.assertEqual(s.count('=value;'),219)

    def test_reset_reference_preserves_external_receipts_and_full_no_reset_equation(self):
        s=(ROOT/'rtl/test/w2_fullnc6_functional_20261003/tb.sv').read_text()
        self.assertIn('always @(negedge rst_n)',s)
        self.assertIn('if(receipt_active[c][r])receipt_reset_quarantined[c][r]=1;',s)
        self.assertIn('if(reset_orphans==0&&projected!=accepted[c])',s)
        self.assertIn('projected!=live_receipts||accepted[c]!=projected+reset_orphans',s)
        self.assertIn('accepted[c]!=live_count+orphan_count',s)
        self.assertIn('client terminal consumed quarantined reset orphan',s)
        self.assertIn('rejected stale return retired reset-orphan debt',s)
        self.assertEqual(s.count('synthetic_provider_discard_all_receipts();'),1)
        for mutant in ('omit','drop','drop_debt','consume'):
            self.assertIn('$test$plusargs("oracle_reset_'+mutant+'")',s)
        inv=json.loads((ROOT/'results/uarch/w2_fullnc6_fixture_20261003/preparation.json').read_text())
        self.assertFalse(inv['reset_receipt_reference']['reference_mutants_run'])
        self.assertFalse(inv['reset_receipt_reference']['updated_fixture_run'])

    def test_coverage_declared_sampled_not_allpairs(self):
        inv=json.loads((ROOT/'results/uarch/w2_fullnc6_fixture_20261003/preparation.json').read_text())
        self.assertEqual(len(inv['words']),219)
        self.assertEqual(sum(x['bank']=='primary' for x in inv['words']),182)
        self.assertEqual(inv['controller_campaign']['singles'],15768)
        self.assertEqual(inv['controller_campaign']['doubles_sampled'],15768)
        self.assertEqual(inv['controller_campaign']['allpair_controller_cases'],559764)
        self.assertFalse(inv['controller_campaign']['allpair_controller_run'])
        self.assertFalse(inv['compiled'])
        bench=ROOT/'rtl/test/w2_fullnc6_functional_20261003/tb.sv'
        self.assertEqual(inv['fixture_sha256'],hashlib.sha256(bench.read_bytes()).hexdigest())
        self.assertEqual(len(inv['directed_cases']),30)
        self.assertEqual(len(set(inv['directed_cases'])),30)

    def test_source_selects_actual_acyclic_secondary(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            primary=root/'rtl/experimental/w2_nc6_primary_20261003/ot_w2_nc6_protected_completion.sv'
            primary.parent.mkdir(parents=True)
            primary.write_text('ot_w2_nc6_coded_secondary_acyclic #(.OPT_PROTECTION(1)) secondary();')
            self.assertEqual(m.selected_secondary(root).parent,primary.parent)
            self.assertEqual(m.selected_secondary(root).name,'ot_w2_nc6_coded_secondary_acyclic.sv')
            primary.write_text('ot_w2_nc6_coded_secondary #(.OPT_PROTECTION(1)) secondary();')
            self.assertEqual(m.selected_secondary(root).name,'ot_w2_nc6_coded_secondary.sv')

    def test_physical_mapping_parser(self):
        s='function automatic integer global_index(input integer i); case(i) 0:global_index=0; 1: global_index=189; endcase endfunction'
        self.assertEqual(m.case_mapping(s),{0:0,1:189})

if __name__=='__main__':unittest.main()


class ConnectedReceiptTests(unittest.TestCase):
    def original(self):
        return m.Request(m.Identity(5,0xfedcba98,15,True),0x300000020,(1<<255)|99)

    def test_connected_source_to_backend_to_old_terminal(self):
        o=m.ConnectedReceiptObserver(None);r=self.original()
        o.held[127,5]=r;o.events=[('caller',127,r),('backend',127,r.wire_tuple)]
        o.after_edge();self.assertEqual(o.backend_accepts,1)
        o.events=[('terminal',127,r.identity)];o.after_edge()
        self.assertEqual(o.client_terminals,1);self.assertFalse(o.receipts)

    def test_connected_full_tuple_mutation_never_normalized(self):
        r=self.original()
        for field,width in enumerate((1,34,35,4,256)):
            for bit in range(width):
                o=m.ConnectedReceiptObserver(None);o.receipts[127,r.identity]=r
                wrong=list(r.wire_tuple);wrong[field]^=1<<bit
                o.events=[('backend',127,tuple(wrong))]
                with self.assertRaises(m.ProtocolError):o.after_edge()

    def test_connected_reset_retains_external_orphan_and_refuses_aba(self):
        class ResetPins:
            book={'pins':{name:{'count':128} for name in ('w2_rst_n','w2_c_req_v','w2_p_req_v','w2_c_rsp_v','w2_c_wr_done_v')}}
            def get(self,name):return 0
        r=self.original();o=m.ConnectedReceiptObserver(ResetPins())
        o.receipts[127,r.identity]=r;o.issued.add((127,r.identity))
        o.before_edge();o.after_edge()
        self.assertEqual(o.receipts,{(127,r.identity):r})
        self.assertIn((127,r.identity),o.orphans)
        o.events=[('terminal',127,r.identity)]
        with self.assertRaises(m.ProtocolError):o.after_edge()
        o.held[127,5]=r;o.events=[('caller',127,r)]
        with self.assertRaises(m.ProtocolError):o.after_edge()

    def test_connected_sameedge_terminal_cannot_spend_new_receipt(self):
        r=self.original();o=m.ConnectedReceiptObserver(None);o.held[127,5]=r
        o.events=[('caller',127,r),('backend',127,r.wire_tuple),('terminal',127,r.identity)]
        with self.assertRaises(m.ProtocolError):o.after_edge()
        self.assertIn((127,r.identity),o.receipts)

    def test_connected_request_pin_snapshot_uses_full_actual_fields(self):
        r=self.original()
        class Wires:
            book={'pins':{name:{'count':128} for name in ('w2_rst_n','w2_c_req_v','w2_p_req_v','w2_c_rsp_v','w2_c_wr_done_v')}}
            def __init__(self):self.leaf=dict(admission_stop=0,c_req_rdy=32,
                c_req_tag=r.identity.tag<<(5*32),c_req_gen=15<<(5*4),c_req_we=32,
                c_req_addr=r.address<<(5*34),c_req_data=r.data<<(5*256),
                c_rsp_v=0,c_rsp_rdy=0,c_wr_done_v=0,c_wr_done_rdy=0)
            def get(self,name):
                return dict(w2_rst_n=(1<<128)-1,w2_c_req_v=32<<(127*6),
                    w2_p_req_v=0,w2_c_rsp_v=0,w2_c_wr_done_v=0).get(name,self.leaf.get(name,0))
            def component(self,block,index):
                assert (block,index)==('w2',127)
                return self
        o=m.ConnectedReceiptObserver(Wires());o.before_edge();o.after_edge()
        self.assertEqual(o.receipts[127,r.identity],r)


class RankedConnectedReceiptTests(unittest.TestCase):
    def test_same_inner_tag_on_two_ranks_is_not_aliased(self):
        class SourceBook:
            book={'pins':{name:{'count':256} for name in
                ('w2_rst_n','w2_c_req_v','w2_p_req_v','w2_c_rsp_v','w2_c_wr_done_v')}}
        o=m.ConnectedReceiptObserver(SourceBook())
        r=m.Request(m.Identity(5,0xffffffff,15,True),0x300000020,1<<255)
        for bank in (127,255):
            o.held[bank,5]=r
            o.events=[('caller',bank,r),('backend',bank,r.wire_tuple)]
            o.after_edge()
        self.assertEqual(o.instances,256)
        self.assertEqual(len(o.receipts),2)
        o.events=[('terminal',127,r.identity)];o.after_edge()
        self.assertEqual(o.receipts,{(255,r.identity):r})

    def test_mismatched_actual_portbank_inventory_refuses(self):
        class SourceBook:
            book={'pins':{name:{'count':256} for name in
                ('w2_rst_n','w2_c_req_v','w2_p_req_v','w2_c_rsp_v','w2_c_wr_done_v')}}
        pins=SourceBook();pins.book={'pins':dict(pins.book['pins'])}
        pins.book['pins']['w2_p_req_v']={'count':128}
        with self.assertRaises(m.ProtocolError):m.ConnectedReceiptObserver(pins)


class RankedActualPinSnapshotTests(unittest.TestCase):
    def test_rank1_pc127_snapshot_calls_explicit_rank_api(self):
        r=m.Request(m.Identity(5,0xfedcba98,15,True),0x300000020,1<<255)
        class RankedWires:
            book={'pins':{name:{'count':256} for name in
                ('w2_rst_n','w2_c_req_v','w2_p_req_v','w2_c_rsp_v','w2_c_wr_done_v')}}
            def __init__(self):self.calls=[]
            def get(self,name):
                return dict(w2_rst_n=(1<<256)-1,w2_c_req_v=32<<(255*6),
                    w2_p_req_v=0,w2_c_rsp_v=0,w2_c_wr_done_v=0,
                    c_req_rdy=32,admission_stop=0,c_req_tag=r.identity.tag<<(5*32),
                    c_req_gen=15<<(5*4),c_req_we=32,c_req_addr=r.address<<(5*34),
                    c_req_data=r.data<<(5*256),c_rsp_v=0,c_rsp_rdy=0,
                    c_wr_done_v=0,c_wr_done_rdy=0)[name]
            def component(self,block,index,*,rank):
                self.calls.append((block,index,rank));return self
        pins=RankedWires();o=m.ConnectedReceiptObserver(pins)
        o.before_edge();o.after_edge()
        self.assertEqual(pins.calls,[('w2',127,1)])
        self.assertEqual(o.receipts,{(255,r.identity):r})
