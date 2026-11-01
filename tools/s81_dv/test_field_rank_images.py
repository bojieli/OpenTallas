import copy
import json
from pathlib import Path
import tempfile
import unittest
import field_rank_images as F


class RankImages(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.images=self.root/'source';self.images.mkdir()
        self.frame='u_f_0L01'
        self.field=dict(frame=self.frame,phases=[
            dict(phase=0,op='attn.a_proj',rows=2,row_index=[200,201]),
            dict(phase=1,op='ffn.experts_gu',fmt='fp4',rows=2,row_index=[10,11],gi=0,sel=[0,1]),
            dict(phase=2,op='ffn.router',fmt='bf16',rows=1,row_index=[7])])
        self.groups={'ffn.experts_gu':[dict(rows=[10,11],cap_tags=[400,900])]}
        self.data={(0,b):[0]*512 for b in range(7)}
        self.values={(0,0):(0xa5a5a5<<48)|(0x12345678<<16)|200,
                     (0,4):(0x321abc<<48)|(0x87654321<<16),
                     (1,4):(0xc0ffee<<48)|(0x34567890<<16)|1,
                     (2,4):(0x654321<<48)|0x8001,
                     (1,5):(0xabcdef<<48)|0x1234,
                     (0,8):(0xaabbcc<<48)|(0x9988<<16)|7}
        for (bank,address),value in self.values.items():
            # Independent physical layout fixture: 72 sense columns, mux8.
            for bit in range(72):
                if value&(1<<bit):self.data[0,bank][address//8]|=1<<(8*bit+address%8)
        self.flush()
        (self.images/'weight.viamap.hex').write_bytes(b'unchanged weight payload\n')

    def flush(self):
        for (pair,bank),data in self.data.items():
            (self.images/f'{self.frame}_c{pair}_{bank}.viamap.hex').write_text(''.join(f'{v:0144x}\n' for v in data))

    def test_fp_rank_ids_preserve_bf_descriptors_and_other_cells(self):
        out=self.root/'ranked'
        result=F.rewrite(self.field,self.groups,self.images,out,already_ranked=[0])
        self.assertEqual(result['changed_cfg_words'],{0:0,1:2})
        self.assertEqual(result['bf_unmapped_phases'],[2])
        self.assertFalse(result['production_enabled'])
        actual={b:[int(v,16) for v in (out/f'{self.frame}_c0_{b}.viamap.hex').read_text().split()] for b in range(7)}
        for (bank,address),value in self.values.items():
            expected=(value&~0xffff)|{(0,4):400,(1,4):900}.get((bank,address),value&0xffff)
            self.assertEqual(F.word(actual[bank],address),expected)
        for bank in range(7):
            self.assertTrue(all((a^b)>>128==0 for a,b in zip(self.data[0,bank],actual[bank])))
        self.assertEqual((out/'weight.viamap.hex').read_bytes(),(self.images/'weight.viamap.hex').read_bytes())
        for (pair,bank),data in self.data.items():
            self.assertEqual(data,[int(v,16) for v in (self.images/f'{self.frame}_c{pair}_{bank}.viamap.hex').read_text().split()])
        with self.assertRaisesRegex(ValueError,'preserve prior'):
            F.rewrite(self.field,self.groups,self.images,out,already_ranked=[0])

    def test_upper24_bit_drop_control_is_caught(self):
        source=self.data[0,0]
        legacy48=[value&((1<<384)-1) for value in source]
        with self.assertRaisesRegex(AssertionError,'BF descriptor'):
            F.check_preserved_planes(source,legacy48)

    def test_source_ownership_and_alias_controls_refused(self):
        variants=[]
        wrong=copy.deepcopy(self.groups);wrong['ffn.experts_gu'][0]['rows'][0]=12;variants.append(wrong)
        wrong=copy.deepcopy(self.groups);wrong['ffn.experts_gu'][0]['cap_tags']=[400,400];variants.append(wrong)
        wrong=copy.deepcopy(self.groups);wrong['ffn.experts_gu'][0]['cap_tags'][0]=16384;variants.append(wrong)
        for groups in variants:
            with self.assertRaises(ValueError):F.tag_plan(self.field,groups)
        wrong=copy.deepcopy(self.field);wrong['phases'][1]['sel'][0]=-1
        with self.assertRaises(ValueError):F.tag_plan(wrong,self.groups)

    def test_wrong_local_or_claimed_ranked_input_refused(self):
        # A phase-local row outside the source phase must not truncate/wrap.
        F.set_tag(self.data[0,0],4,9);self.flush()
        with self.assertRaisesRegex(ValueError,'phase-local'):
            F.rewrite(self.field,self.groups,self.images,self.root/'bad_local',already_ranked=[0])
        self.assertFalse((self.root/'bad_local').exists())
        F.set_tag(self.data[0,0],4,0);F.set_tag(self.data[0,0],0,199);self.flush()
        with self.assertRaisesRegex(ValueError,'already-ranked'):
            F.rewrite(self.field,self.groups,self.images,self.root/'bad_ranked',already_ranked=[0])


if __name__=='__main__':unittest.main()
