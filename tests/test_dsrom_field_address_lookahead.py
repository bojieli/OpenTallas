import hashlib
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class AddressLookahead(unittest.TestCase):
    def test_preserved_original(self):
        p=ROOT/'rtl/v41die/ot_v41_spine_pq_w17w10.sv'
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), '0595a27f197dc81df0cd9bb4d1dbbeb40c3437219e73698b414c819618cfe3e6')

    def test_exact_next_state_address(self):
        # Independent old state transition, including modulo16 index and moduloSAW address.
        for saw in (8,14):
            mask=(1<<saw)-1
            for n in (0,1,2,3,33,97,32768,65535):
                for base in (0,1,16383,65520,65535):
                    for i in (0,1,2,31,96,32767,65533,65534,65535,(n-1)&65535,(n-2)&65535):
                        for filled in (False,True):
                            for ready in (False,True):
                                last=((i+1)&65535)==n
                                old=(base+(i if not filled else (0 if last else (i+1)&65535)))&mask
                                if not filled:
                                    # Legal initial fill has i=0; all other states unreachable.
                                    if i: continue
                                    ni,nfilled=0,True
                                elif ready:
                                    ni,nfilled=(0 if last else (i+1)&65535),True
                                else:
                                    ni,nfilled=i,True
                                expected=(base+(ni if not nfilled else (0 if ((ni+1)&65535)==n else (ni+1)&65535)))&mask
                                if not filled or ready:
                                    index=(0 if n==1 else 1) if not filled or last else (0 if ((i+2)&65535)==n else (i+2)&65535)
                                    proposed=(base+index)&mask
                                else: proposed=old
                                self.assertEqual(proposed,expected,(saw,n,base,i,filled,ready))

    def test_fixture_q_last_pair_legal(self):
        # Decoder math derives the last pair from full K, not a relaxed timeout.
        k=6144; u=(k//512)-1; b=7; sv=3
        need=u*512+256+b*32+32
        self.assertEqual(need,k)
        self.assertEqual(u*16+b,183)
        self.assertEqual(u*16+8+b,191)
        self.assertLess(191,k//32)
        self.assertGreater(95*512+256+32,k) # preserved failing r1 fixture
        bench=(ROOT/'rtl/test/dsrom_sys/tb_dsrom_field_addr.sv').read_text()
        self.assertIn("v[8:1]=8'd11;v[11:9]=3'd7",bench)

    def test_named_budget(self):
        # This independent analytical function has no full-token model dependencies.
        # Execute its literal source, avoiding unrelated import-time archived block records.
        tree=ast.parse((ROOT/'tools/uarch_model.py').read_text())
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='dsrom_field_address_lookahead_price']
        self.assertEqual(len(funcs),1)
        namespace={}
        exec(compile(ast.Module(body=funcs,type_ignores=[]),'uarch_model.py','exec'),namespace)
        m=namespace['dsrom_field_address_lookahead_price']()
        self.assertEqual(m['added_state_bits'],47)
        self.assertEqual(m['instances_per_field_die'],1)
        self.assertAlmostEqual(m['reservation_um2'],559.872)
        self.assertAlmostEqual(m['estimated_cell_um2'],81.32724)
        self.assertGreater(m['remaining_cell_budget_um2'],0)
        self.assertFalse(m['physical_admitted'])

    def test_source_only_expected_delta(self):
        old=(ROOT/'rtl/v41die/ot_v41_spine_pq_w17w10.sv').read_text()
        new=(ROOT/'rtl/v41die/ot_v41_spine_pq_addr_w17w10.sv').read_text()
        # All arithmetic, buffering, root accounting and publication code is literal unchanged.
        self.assertEqual(old[old.index('    // beat assembly'):],new[new.index('    // beat assembly'):])
        self.assertIn('parameter integer ADDR_LOOKAHEAD = 0',new)
        self.assertIn('if (can_go)',new)
        self.assertIn("wire [15:0] ahead_i = sm_i + 16'd2",new)

    def test_parent_hook_has_no_other_delta(self):
        old=(ROOT/'rtl/v41die/ot_v41_fieldtop_pq_w17w10.sv').read_text()
        new=(ROOT/'rtl/v41die/ot_v41_fieldtop_pq_addr_w17w10.sv').read_text()
        new=new.split('\n',1)[1].replace('module ot_v41_fieldtop_pq_addr_w17w10 #(','module ot_v41_fieldtop_pq_w17w10 #(',1).replace('    parameter integer ADDR_LOOKAHEAD = 0,\n','',1).replace('    ot_v41_spine_pq_addr_w17w10 #(','    ot_v41_spine_pq_w17w10 #(',1).replace(', .ADDR_LOOKAHEAD(ADDR_LOOKAHEAD)) u_sp (',') u_sp (',1)
        self.assertEqual(new,old)

if __name__=='__main__': unittest.main()
