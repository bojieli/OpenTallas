import gzip, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT))
import dsrom_s82_payload_interface as P
import dsrom_s73_pair1 as M
import dsrom_s82_source_inventory as E

BASE=ROOT/'results/uarch/dsrom_s73_pair1_20261003/baseline_s82_successor_r1'
OLD=ROOT/'results/uarch/dsrom_native_weight_address_join_20261002'

class PayloadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrices=list(M.C.readrows(BASE/'matrix_map.jsonl.gz'))
        cls.source=P.Checkpoint()
    @classmethod
    def tearDownClass(cls):cls.source.close()
    def test_real_payload_code_scale_and_inverse_word(self):
        cases={}
        for m in self.matrices:
            cases.setdefault((m['format'],m['conversion']),m)
        self.assertEqual(len(cases),4)
        checked=0
        for m in cases.values():
            for rank in m['physical_owner_ranks']:
                for row,k in [(0,0),(m['rows']-1,m['K']-1)]:
                    a=M.physical_address(m,rank,row,k)
                    macro,pr=a['physical_macro'],a['physical_row']
                    coords=P.word_coordinates(m,rank,macro,pr)
                    self.assertIn((row,k,a['bit_range'][0],a['bit_range'][1]-a['bit_range'][0]),coords)
                    w=P.matrix_word(m,self.source,rank,macro,pr)
                    self.assertEqual((w>>a['bit_range'][0])&((1<<(a['bit_range'][1]-a['bit_range'][0]))-1),P.payload_value(m,self.source,rank,row,k))
                    if m['format']=='fp4':
                        sr,sk=a['source_row'],a['source_col']
                        raw=self.source.element(m['tensor'],sr,sk//2)
                        self.assertEqual((w>>a['bit_range'][0])&15,(raw>>(4*(sk%2)))&15)
                        sb=128+136*(k%512//256)
                        self.assertEqual((w>>sb)&255,self.source.element(m['source_scale_tensor'],sr,sk//32))
                        self.assertEqual(w>>272,0)
                    elif m['format']=='fp8':
                        sr,sk=a['source_row'],a['source_col']
                        self.assertEqual((w>>a['bit_range'][0])&255,self.source.element(m['tensor'],sr,sk))
                        self.assertEqual((w>>256)&255,self.source.element(m['source_scale_tensor'],sr//32,sk//32))
                        self.assertEqual(w>>264,0)
                    checked+=1
        self.assertEqual(checked,32)
    def test_interleaved_superrows_and_multicast_owner(self):
        m=next(m for m in self.matrices if any(r[3]>1 for r in m['plans']))
        run=next(r for r in m['plans'] if r[3]>1)
        si,p,first,n,stride,start,w=run
        e=m['segments'][si][0]
        for j in range(n):
            a=M.physical_address(m,0,2*(first+j*stride),e)
            coords=P.word_coordinates(m,0,a['physical_macro'],a['physical_row'])
            self.assertTrue(any(row==2*(first+j*stride) and k==e for row,k,_,_ in coords))
        mc=next(m for m in self.matrices if m['physical_owner_ranks']==[0])
        with self.assertRaises(ValueError):P.word_coordinates(mc,1,0,0)
        self.assertTrue(P.execution_fragments([mc],mc['layer'],mc.get('original_alias',mc['alias']),1)[0]['result_multicast_required'])
    def test_all_source_descriptor_bindings(self):
        demand=json.load(gzip.open(OLD/'inputs/demand-r5.json.gz','rt'))
        bindings=list(M.C.readrows(OLD/'r3/node_bindings.jsonl.gz'))
        ex=P.SourceExecution(self.matrices,bindings,demand)
        resolved=0
        for b in bindings:
            if not b.get('address_bound'):continue
            ids=[0,1,2,3,4,383] if b['selector_slot'] is not None else None
            for rank in range(4):
                r=ex.resolve(b['node'],rank,ids)
                self.assertTrue(r['source_identity_verified']);resolved+=1
        self.assertEqual(resolved,4*sum(bool(b.get('address_bound')) for b in bindings))
        self.assertEqual(resolved,4596)
        b=next(b for b in bindings if b.get('selector_slot') is not None)
        with self.assertRaises(ValueError):ex.resolve(b['node'],0,[0,1,2,3,4,4])
    def test_auxiliary_payload_byte_binding(self):
        aux=json.loads((BASE/'auxiliary_map.json').read_text())['tensors']
        t=aux[0]
        for offset in [0,t['source_storage_bytes']-1]:
            a=P.auxiliary_address(t,offset)
            byte=self.source.raw(t['tensor'],offset,1)[0]
            word=P.auxiliary_word(aux,self.source,a['stage'],a['rank'],a['macro'],a['row'])
            self.assertEqual((word>>a['bit'])&255,byte)
            self.assertLess(a['macro'],9552);self.assertLess(a['row'],4096)
        with self.assertRaises(ValueError):P.auxiliary_address(t,t['source_storage_bytes'])
    def test_minimal_intake_and_retained_cost(self):
        self.assertEqual(len(E.FILES),19)
        self.assertTrue(all((ROOT/p).is_file() for p in E.FILES))
        self.assertFalse(any('attempt_r' in p or 'successor_r4' in p for p in E.FILES))
        c=json.loads((BASE/'physical_contract.json').read_text())
        self.assertEqual(c['return_contract']['RD'],64)
        self.assertAlmostEqual(c['return_contract']['FF50_reservation_mm2'],52.89758742528)
        self.assertFalse(c['physical_admission'])
    def test_native_HE_CROM_offsets_and_payload(self):
        providers=json.loads((ROOT/(E.BASE+'baseline_s82_mapping_r1/providers.json')).read_text())
        for p in providers[:2]:
            cursor=0
            for d in p['declarations']:
                if p['kind']=='HE':
                    d['native_bank_word_base']=cursor;cursor+=d['rows']*((d['K']+63)//64)
                else:
                    d['native_FP32_element_base']=cursor;cursor+=d['elements']
            for d in p['declarations']:
                a=M.P.provider_tensor_address(p,d['alias'],0,0)
                macro=4*a['pair']+2*a['mb']+a['parity']
                w=P.provider_word(p,self.source,macro,a['physical_row'])
                expected=self.source.element(d['tensor'],0,0)
                if d.get('dtype')=='BF16':expected<<=16
                self.assertEqual((w>>a['bit_range'][0])&0xffffffff,expected)
                self.assertEqual(w>>256,0)
    def test_actual_die_macro_to_payload_inventory_join(self):
        providers=json.loads((ROOT/(E.BASE+'baseline_s82_mapping_r1/providers.json')).read_text())
        for p in providers:
            cursor=0;p['physical_owner_rank']=0
            for d in p['declarations']:
                if p['kind']=='HE':d['native_bank_word_base']=cursor;cursor+=d['rows']*((d['K']+63)//64)
                else:d['native_FP32_element_base']=cursor;cursor+=d['elements']
        aux=json.loads((BASE/'auxiliary_map.json').read_text())['tensors']
        m=self.matrices[0];a=M.physical_address(m,0,0,0)
        die=P.DieROM(m['stage'],0,self.matrices,providers,aux)
        self.assertEqual(die.read(self.source,a['physical_macro'],a['physical_row']),P.matrix_word(m,self.source,0,a['physical_macro'],a['physical_row']))
        provider=next(p for p in providers if p['stage']==m['stage'])
        macro=4*provider['pairs'][0]
        self.assertEqual(die.read(self.source,macro,0),P.provider_word(provider,self.source,macro,0))
        t=aux[0];a=P.auxiliary_address(t,0)
        die=P.DieROM(a['stage'],a['rank'],self.matrices,providers,aux)
        self.assertEqual(die.read(self.source,a['macro'],a['row']),P.auxiliary_word(aux,self.source,a['stage'],a['rank'],a['macro'],a['row']))
        self.assertEqual(die.inventory()['physical_weight_macros'],9552)
        with self.assertRaises(ValueError):die.read(self.source,9552,0)

if __name__=='__main__':unittest.main()
