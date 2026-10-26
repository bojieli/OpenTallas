import unittest
from dataclasses import replace
from hostb_envelope import (Context, HOST_WORD, KS_DESCRIPTOR, ARM, STAGE_RETURN,
    crc32c, host_word, ks_word, arm_word, return_word, decode_header, decode_stream,
    encode_boot, wire_cost, validate_g8_walk_return, G8_KIT_SOURCE)
from ks_descriptor import encode as encode_ks


class EnvelopeTest(unittest.TestCase):
    def context(self):
        # Explicit adversarial field values, never a production stage/epoch.
        return Context(stage_id=240,rank=3,transaction_id=65535,user=1023,
                       position=1048575,token=16754,epoch_identity=0x12345678,
                       programme_id64=0xfedcba9876543210)

    def test_crc_reference(self):
        self.assertEqual(crc32c(b'123456789'),0xe3069283)

    def test_full_legacy_width_and_all_classes_roundtrip(self):
        c=self.context()
        for cls in range(4):
            data=(1<<511)|(0x19 if cls%2==0 else 0x17)|(0xabcdef<<200)
            legacy=(cls<<513)|(data<<1)|1
            h,b=host_word(legacy,c,body_capture_edge=20)
            self.assertEqual(b,data)
            self.assertEqual(decode_stream([(10,h),(20,b)],c)[0]['legacy515'],legacy)

    def test_header_shaped_raw_body_is_legal_when_crc_and_slot_match(self):
        c=self.context()
        body=ks_word(encode_ks(user=c.user,token=c.token,position=c.position),5,c,deadline=100)
        legacy=(3<<513)|(body<<1)|1
        h,b=host_word(legacy,c,body_capture_edge=20)
        self.assertEqual(decode_stream([(10,h),(20,b)],c)[0]['legacy515'],legacy)

    def test_bad_crc_wrong_slot_missing_body_and_interleaved_header_refused(self):
        c=self.context();h,b=host_word((1<<514)|0x13579,c,body_capture_edge=20)
        for records in [[(10,h),(20,b^1)],[(10,h),(19,b)],[(10,h),(21,b)],[(10,h)],
                        [(10,h),(20,arm_word(63,c,deadline=100))]]:
            with self.assertRaises(ValueError):decode_stream(records,c)

    def test_wrong_identity_length_version_and_stage_refused(self):
        c=self.context();h,b=host_word(0x123,c,body_capture_edge=20)
        for bit in (40,48,50,78,88,109,130,210,66,32):
            with self.assertRaises(ValueError):decode_stream([(10,h^(1<<bit)),(20,b)],c)
        with self.assertRaises(ValueError):replace(c,stage_id=241)
        with self.assertRaises(ValueError):replace(c,rank=4)

    def test_ks_context_and_raw_return_bits_preserved(self):
        c=self.context();ks=encode_ks(user=c.user,token=c.token,position=c.position)
        fields=decode_header(ks_word(ks,5,c,deadline=100))
        self.assertEqual(fields['inline']&((1<<53)-1),ks)
        with self.assertRaises(ValueError):ks_word(ks^1,5,c,deadline=100)
        with self.assertRaises(ValueError):ks_word(ks,6,c,deadline=100)
        th=(1<<77)-1;tk=(1<<54)-1
        f=decode_header(return_word(th,tk,c,deadline=100))
        self.assertEqual(f['inline']&((1<<77)-1),th)
        self.assertEqual(f['inline']>>77,tk)
        self.assertEqual(decode_header(arm_word(63,c,deadline=100))['inline'],63)

    def test_417_words_plus_ks_have_exact_835_record_cost(self):
        c=self.context();words=[((i&3)<<513)|((1<<511|i)<<1)|1 for i in range(417)]
        slots=[dict(head_header_edge=10+4*i,head_body_edge=11+4*i,
                    receiver_header_edge=30+4*i,receiver_body_capture_edge=31+4*i) for i in range(417)]
        records=encode_boot(words,c,slots,ks53=encode_ks(user=c.user,token=c.token,position=c.position),
            ks_slots=dict(head_edge=2000,receiver_edge=2020,deadline=2020,slot=0))
        self.assertEqual(len(records),835)
        self.assertEqual(wire_cost(834)['minimum_wire_cycles'],1092)
        self.assertEqual(wire_cost(835)['ring_beats'],835)
        # A source/receiver slot collision must not silently reorder the pair.
        slots[1]['head_header_edge']=slots[0]['head_body_edge']
        with self.assertRaises(ValueError):encode_boot(words,c,slots,
            ks53=encode_ks(user=c.user,token=c.token,position=c.position),
            ks_slots=dict(head_edge=2000,receiver_edge=2020,deadline=2020,slot=0))

    def test_nonlocal_body_slots_use_each_adapter_counter(self):
        c=self.context()
        route=[dict(adapter_id='test-transit-A',receiver_clock_identity='test-clock-A',
                    source_sha256='a'*64,configured=True,expected_header_stage=c.stage_id)]
        book=dict(adapter_id='test-transit-A',receiver_header_edge=900,header_slot=900,transit_body_edge=905)
        slots=[dict(head_header_edge=1,head_body_edge=2,receiver_header_edge=20,
                    receiver_body_capture_edge=25,transit=[book])]
        ks=dict(head_edge=3,receiver_edge=26,deadline=26,slot=0,
                transit=[dict(adapter_id='test-transit-A',receiver_header_edge=906,header_slot=906)])
        records=encode_boot([0x123],c,slots,ks53=encode_ks(user=c.user,token=c.token,position=c.position),
                            ks_slots=ks,transit_route=route)
        self.assertEqual(decode_header(int(records[0]['payload512'],16))['date48'],25)
        self.assertEqual(records[0]['transit_slot_books'][0]['slots']['transit_body_edge'],905)
        # These are different counters; no900->20 phase/latency is inferred.
        for broken in [[],[dict(book,transit_body_edge=899)],
                       [dict(book,header_slot=901)],[dict(book,adapter_id='wrong')]]:
            with self.assertRaises(ValueError):
                encode_boot([0x123],c,[dict(slots[0],transit=broken)],
                    ks53=encode_ks(user=c.user,token=c.token,position=c.position),ks_slots=ks,transit_route=route)
        with self.assertRaises(ValueError):
            encode_boot([0x123],c,slots,ks53=encode_ks(user=c.user,token=c.token,position=c.position),
                        ks_slots=ks,transit_route=[dict(route[0],configured=False)])

    def test_full_sync_arm_payloads_do_not_collapse_into_inline_mask(self):
        c=self.context();words=[0x123]
        slots=[dict(head_header_edge=1,head_body_edge=2,receiver_header_edge=11,receiver_body_capture_edge=12)]
        csr=[(((1<<511)|(0x123456789abc<<64)|op)<<1)|1 for op in (0x19,0x17)]
        cs=[dict(head_header_edge=3+2*i,head_body_edge=4+2*i,
                 receiver_header_edge=13+2*i,receiver_body_capture_edge=14+2*i) for i in range(2)]
        kwargs=dict(ks53=encode_ks(user=c.user,token=c.token,position=c.position),
                    ks_slots=dict(head_edge=8,receiver_edge=18,deadline=18,slot=0))
        records=encode_boot(words,c,slots,starter_words=csr,starter_slots=cs,
            arm_slots=dict(head_edge=7,receiver_edge=17,deadline=17,mask6=63),**kwargs)
        decoded=decode_stream([(r['receiver_capture_edge'],int(r['payload512'],16)) for r in records],c)
        self.assertEqual([r['legacy515'] for r in decoded if r['opcode']==HOST_WORD],words+csr)
        self.assertEqual([r['inline'] for r in decoded if r['opcode']==ARM],[63])
        with self.assertRaises(ValueError):encode_boot(words,c,slots,
            arm_slots=dict(head_edge=7,receiver_edge=17,deadline=17,mask6=63),**kwargs)

    def test_kit_identity_validation_is_bound_to_actual_g8_source_only(self):
        c=self.context();kd=(1<<53)|(c.token<<32);th=(1<<77)-1
        fields=decode_header(return_word(th,kd,c,deadline=100))
        r=validate_g8_walk_return(fields,**G8_KIT_SOURCE)
        self.assertEqual(r['raw_t_host77'],th);self.assertEqual(r['raw_t_kd54'],kd)
        self.assertFalse(r['user_position_encoded_in_KIT'])
        with self.assertRaises(ValueError):decode_stream([(10,return_word(th,kd,c,deadline=100))],c)
        self.assertEqual(decode_stream([(10,return_word(th,kd,c,deadline=100))],c,
            return_contract=G8_KIT_SOURCE)[0]['inline'],fields['inline'])
        for bad in (kd^(1<<32),kd|1):
            with self.assertRaises(ValueError):validate_g8_walk_return(
                decode_header(return_word(th,bad,c,deadline=100)),**G8_KIT_SOURCE)
        with self.assertRaises(ValueError):validate_g8_walk_return(fields,
            seqhost_sha256='0'*64,issuer_sha256=G8_KIT_SOURCE['issuer_sha256'])


if __name__=='__main__':unittest.main()
