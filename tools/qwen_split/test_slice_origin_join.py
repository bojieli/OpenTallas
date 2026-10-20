import copy,unittest
from slice_origin_join import audit
from test_shared_epoch_origin_guard import fixture

H='a'*64

def sample():
    packet=dict(source_commit='e0e05b43d',interfaces=[dict(top='qfd_dv_s5_lp',sha256=H,ports=[dict(port=p,direction='input',kind='data',width=w,lsb=0,msb=w-1)for p,w in [('ch_up_i',1095),('ch_dn_i',1038)]])])
    bindings={}
    for name,width in [('ch_up_i',1095),('ch_dn_i',1038)]:
        b=dict(source_packet_ref='702da6fe4',source_packet_sha256=H,source_commit='e0e05b43d',top='qfd_dv_s5_lp',source_sha256=H,port=name,width=width,msb=width-1,lsb=0,direction='input',
          receiver_endpoint='die/'+name,receiver_clock_pin='die/ck',receiver_reset_pin='die/rst_n',producer_endpoint='producer/'+name,
          first_valid_global_edge=117,compiled_age_edges=3,origin_contract=fixture())
        for k in ['upstream_origin_receipt_sha256','receiver_origin_receipt_sha256','native_receipt_sha256','actual_receiver_map_sha256','placement_receipt_sha256','phase_receipt_sha256','schedule_receipt_sha256']:b[k]=H
        lo=0;s=[]
        widths=[183,183,183,182,182,182]if width==1095 else[173]*6
        for i,w in enumerate(widths):
            s.append(dict(payload_lsb=lo,payload_msb=lo+w-1,native_lsb=0,native_msb=w-1,native_width=w,order='lsb_to_msb',age_edges=3,first_valid_global_edge=117,
              receiver_endpoint=f'die_{name}/slice{i}',native_receipt_sha256=H,actual_receiver_map_sha256=H,upstream_origin_receipt_sha256=H));lo+=w
        b['slices']=s;bindings[name]=b
    return packet,bindings

def run(p,b):return audit(p,b,'qfd_dv_s5_lp','702da6fe4',H)
class JoinTests(unittest.TestCase):
    def test_complete_typed_join_still_emits_no_K_or_adoption(self):
        r=run(*sample());self.assertEqual(r['status'],'MODEL_JOIN_COMPLETE_NOT_NATIVE_SIGNOFF');self.assertIsNone(r['K_emit']);self.assertFalse(r['qualified'])
    def test_deceptive_populated_split_age_coherent1095_rejected(self):
        p,b=sample();b['ch_up_i']['slices'][0]['age_edges']=5
        self.assertIn('COHERENT_FRONTIER_SPLIT_AGE_VALID_OR_ORIGIN',run(p,b)['ports'][0]['errors'])
    def test_deceptive_populated_1038_reorder_rejected(self):
        p,b=sample();b['ch_dn_i']['slices'].reverse()
        self.assertIn('SPLIT_REORDER_OVERLAP_OR_GAP',run(p,b)['ports'][1]['errors'])
    def test_covered_payload_native_bit_reverse_rejected(self):
        p,b=sample();b['ch_up_i']['slices'][0]['order']='msb_to_lsb'
        self.assertIn('BIT_ORDER_PADDING_OR_TRUNCATION',run(p,b)['ports'][0]['errors'])
    def test_partial_ack_or_null_origin_firstvalid_rxmap_rejected(self):
        p,b=sample();b.pop('ch_dn_i');b['ch_up_i']['actual_receiver_map_sha256']=None;b['ch_up_i']['first_valid_global_edge']=None
        r=run(p,b);self.assertEqual(r['status'],'BLOCKED');self.assertIn('INCOMPLETE_OR_EXTRA_WHOLE_FRONTIER_ACK',r['errors'])
    def test_D4_D8_source_mixing_rejected(self):
        p,b=sample();b['ch_up_i']['source_sha256']='b'*64;b['ch_up_i']['top']='qfd_dv_s5b_lp'
        self.assertIn('SOURCE_IDENTITY:top',run(p,b)['ports'][0]['errors'])
    def test_duplicate_actual_receiver_rejected(self):
        p,b=sample();s=b['ch_up_i']['slices'];s[1]['receiver_endpoint']=s[0]['receiver_endpoint']
        self.assertIn('DUPLICATE_PHYSICAL_RECEIVER',run(p,b)['ports'][0]['errors'])
    def test_placeholder_sha_rejected_despite_filled_endpoints(self):
        p,b=sample();b['ch_up_i']['phase_receipt_sha256']='TODO'*16
        self.assertIn('MISSING_OR_INVALID:phase_receipt_sha256',run(p,b)['ports'][0]['errors'])
if __name__=='__main__':unittest.main()
