import unittest
from gen_phys import audit_pin_records

class AuditPins(unittest.TestCase):
    def test_source_declared_ports_preserve_face_rows_and_interior_exclusions(self):
        face = [dict(bus='data',bit=0,layer='M5',x=0,y=3,face='W')]
        planned = [dict(name='data[0]',layer='M5',x=.1,y=3),
                   dict(name='cland_dn_fault',layer='M5',x=2,y=4),
                   dict(name='strap_ca_kbits[2]',layer='M7',x=5,y=6),
                   dict(name='clk_c0',layer='M7',x=8,y=9)]
        result = audit_pin_records(face, planned)
        self.assertEqual(result[0],face[0])
        self.assertEqual(len(result),3)
        self.assertEqual(result[1],dict(bus='cland_dn_fault',bit=None,layer='M5',x=2,y=4,face='island'))
        self.assertEqual(result[2]['bit'],2)
        self.assertEqual(len(face),1)
    def test_inconsistent_declarations_rejected(self):
        with self.assertRaises(ValueError):
            audit_pin_records([dict(bus='undeclared',bit=None)],[])
        with self.assertRaises(ValueError):
            audit_pin_records([], [dict(name='dup'),dict(name='dup')])
    def test_planned_reset_start_controls_are_strict_rows(self):
        planned = [dict(name=n,layer="M7",x=1.0+i,y=2.0) for i,n in enumerate(
            ["rst_o_0","rst_o_1","start_i","start_o_0","start_o_1","arst_n","clk","clk_t3","ft_ck_i","mp_isl0"])]
        rows = audit_pin_records([], planned)
        self.assertEqual([r["bus"] for r in rows], ["rst_o_0","rst_o_1","start_i","start_o_0","start_o_1"])
        self.assertTrue(all(r["face"]=="island" and r["bit"] is None for r in rows))
    def test_packed_native_scalar_resolves_by_alias_not_extra(self):
        import pin_audit as PA
        want = {PA.pin_key(r): r for r in audit_pin_records([], [dict(name="rst_o_0",layer="M7",x=1,y=2)])}
        self.assertEqual(PA.scalar_aliases(want, ["rst_o_0[0]"]), {"rst_o_0[0]": "rst_o_0"})
