import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cb',ROOT/'tools/prepare_dsrom_ckv_callbacks.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class CallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.im=m.images();cls.ev=m.fixture(cls.im)
    def broken(self,kind,field,value,index=0):
        ev=copy.deepcopy(self.ev);matches=[e for e in ev if e['kind']==kind];matches[index][field]=value
        with self.assertRaises(ValueError):m.validate(ev,self.im)
    def test_full512_both_passes(self):
        r=m.validate(self.ev,self.im)
        self.assertEqual((r['selected_rows_stored'],r['selected_rows_staged'],r['stage_rows'],r['stored_ACKs'],r['owner_visible_sectors']),(2048,4096,5120,1533,9))
        self.assertFalse(r['actual_RTL_measured'])
    def test_selection_atomic_clear_and_epoch(self):
        for field,value in [('ready',False),('old_lease_drained',False),('count_after',1),('epoch',2)]:
            with self.subTest(field=field):self.broken('selection_accept',field,value,index=3)
    def test_storage_actual_admission(self):
        for field,value in [('ready',False),('write_strobe',False),('gid',4095),('row_sha','bad'),('count_before',1),('count_after',2),('source',3),('edge',1)]:
            with self.subTest(field=field):self.broken('storage_accept',field,value)
    def test_duplicate_storage_rejected(self):
        ev=copy.deepcopy(self.ev);i=next(i for i,e in enumerate(ev) if e['kind']=='storage_accept');ev.insert(i+1,copy.deepcopy(ev[i]))
        with self.assertRaises(ValueError):m.validate(ev,self.im)
    def test_registered_ACK_chain_and_generation(self):
        for kind,field,value in [('stored_ACK_emit','edge',3),('stored_ACK_return','epoch',0),('stored_ACK_return','pending_before',False),('stored_ACK_return','pending_after',True),('stored_ACK_return','destination',0)]:
            with self.subTest(kind=kind,field=field):self.broken(kind,field,value)
        for kind in ['stored_ACK_emit','stored_ACK_return']:
            ev=copy.deepcopy(self.ev);i=next(i for i,e in enumerate(ev) if e['kind']==kind);ev.insert(i+1,copy.deepcopy(ev[i]))
            with self.subTest(duplicate=kind),self.assertRaises(ValueError):m.validate(ev,self.im)
    def test_rejected_RX_no_mutation_and_reason_binding(self):
        ev=copy.deepcopy(self.ev);i=next(i for i,e in enumerate(ev) if e['kind']=='stored_ACK_emit');base=ev[i]
        rejection=dict(kind='rx_reject',edge=base['edge'],group=base['group'],die=1,epoch=1,offered_epoch=0,rank=0,gid=0,source=0,valid=True,ready=False,write_strobe=False,count_before=1,count_after=1,row_before=self.im['rows'][0]['row_sha'],row_after=self.im['rows'][0]['row_sha'],fault=True,reason='stale')
        ev.insert(i,rejection);self.assertEqual(m.validate(ev,self.im)['rejected_offers'],1)
        for field,value in [('write_strobe',True),('count_after',2),('row_after','bad'),('offered_epoch',1),('ready',True)]:
            bad=copy.deepcopy(ev);bad[i][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):m.validate(bad,self.im)
    def test_each_invalid_reason_requires_no_storage_mutation(self):
        for reason,overrides in [('duplicate',{}),('wrong_gid',{'gid':3}),('wrong_owner',{'source':2}),('range',{'rank':512,'row_before':None,'row_after':None}),('malformed',{'format_valid':False})]:
            ev=copy.deepcopy(self.ev);i=next(i for i,e in enumerate(ev) if e['kind']=='stored_ACK_emit');base=ev[i]
            rejection=dict(kind='rx_reject',edge=base['edge'],group=base['group'],die=1,epoch=1,offered_epoch=1,rank=0,gid=0,source=0,valid=True,ready=False,write_strobe=False,count_before=1,count_after=1,row_before=self.im['rows'][0]['row_sha'],row_after=self.im['rows'][0]['row_sha'],fault=True,reason=reason)
            rejection.update(overrides)
            # Build via update to allow override of offered fields without duplicate keywords.
            ev.insert(i,rejection)
            with self.subTest(reason=reason):self.assertEqual(m.validate(ev,self.im)['rejected_offers'],1)
    def test_archive_pin_refuses_changed_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            saved=m.BASE;m.BASE=Path(tmp)/'inputs'
            try:
                m.BASE.mkdir();(m.BASE/'input_pins.json').write_text('[{"archive":"changed","sha256":"wrong"}]');(m.BASE/'changed').write_text('tampered')
                with self.assertRaisesRegex(ValueError,'source pin mismatch'):m.prepare(Path(tmp)/'package')
            finally:m.BASE=saved
    def test_full16_generation_echo_not_current_epoch(self):
        ev=m.fixture(self.im,epoch=0xA123)
        self.assertEqual(m.validate(ev,self.im)['stored_ACKs'],1533)
        for kind,field in [('storage_accept','offered_epoch'),('stored_ACK_emit','echo_epoch'),('stored_ACK_return','echo_epoch')]:
            bad=copy.deepcopy(ev);next(e for e in bad if e['kind']==kind)[field]=0x0123
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'carried generation'):m.validate(bad,self.im)
    def test_staging_and_descriptor_frozen(self):
        for field,value in [('mask',7),('ready',False),('row_base',4),('stage_addr',1),('packed_hashes',[]),('phase','PV')]:
            with self.subTest(field=field):self.broken('stage_write',field,value)
        self.broken('stage_write','descriptor_generation',2,index=4)
        self.broken('descriptor_retire','descriptor_generation',2)
    def test_public_output_drain(self):
        for field,value in [('actual_desc_done',False),('actual_engine_idle',False),('output_write_mask',1)]:
            with self.subTest(field=field):self.broken('descriptor_retire',field,value)
        self.broken('output_write','actual_write',False)
    def test_nine_owner_completions(self):
        for field,value in [('actual_wr_done',False),('backing_write_observed',False),('word_sha','bad'),('address',0),('gid',0)]:
            with self.subTest(field=field):self.broken('owner_write_visible',field,value,index=8)
        ev=[e for e in self.ev if not(e['kind']=='owner_write_visible' and e['sector']==8)]
        with self.assertRaises(ValueError):m.validate(ev,self.im)
    def test_terminal_markers_and_identity_strict(self):
        for ev in [self.ev[:-1],self.ev+[self.ev[-1]]]:
            with self.assertRaises(ValueError):m.validate(ev,self.im)
        for kind,field,value in [('storage_accept','rank',512),('storage_accept','rank',True),('storage_accept','group',1),('storage_accept','kind','foreign')]:
            with self.subTest(field=field):self.broken(kind,field,value)
    def test_unbounded_stall_no_claim_or_timeout(self):
        ev=copy.deepcopy(self.ev)
        for e in ev:
            if e['kind'] in ['stage_write','output_write','descriptor_retire','end']:e['edge']+=10**12
        self.assertFalse(m.validate(ev,self.im)['actual_RTL_measured'])
    def test_input_words_reformat_independently(self):
        for row in self.im['rows']:
            raw=int(row['row_hex'],16);parts=[]
            for group in range(16):
                codes=(raw>>(group*128))&((1<<128)-1)
                scales=(raw>>(2048+group*16))&65535
                parts.append((1<<264)|(scales<<128)|codes)
            packed=sum(word<<(265*g) for g,word in enumerate(parts))
            self.assertEqual(m.digest(packed,530),row['packed_sha'])
        self.assertEqual(len(self.im['own_capture_BF16_in_FP32_hex']),16)
        for beat in self.im['own_capture_BF16_in_FP32_hex']:
            v=int(beat,16)
            for i in range(32):self.assertEqual((v>>(32*i))&65535,0)
    def test_package_replay_no_expected_driver_ports(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a';b=Path(tmp)/'b';m.prepare(a);m.prepare(b)
            self.assertEqual({p.name:p.read_bytes() for p in a.iterdir()},{p.name:p.read_bytes() for p in b.iterdir()})
            header=(a/'ckv_callback_v1.hpp').read_text()
            self.assertNotIn('expected',header)
            for callback in ['selection','storage','stored_ack_emit','stored_ack_return','staging','retire','owner_write','reset_barrier','table_publish','broadcast_accept','rx_reject','output_write','end']:
                self.assertIn('void '+callback+'(',header)
            abi=json.loads((a/'callback_abi.json').read_text());self.assertFalse(abi['build_GO']);self.assertEqual(abi['capacity']['staging_bytes_per_rank'],339200)
            with self.assertRaisesRegex(ValueError,'fresh output'):m.prepare(a)

if __name__=='__main__':unittest.main(verbosity=2)
