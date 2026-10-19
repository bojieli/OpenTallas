"""Adversarial mapped pin fixtures for the standalone SAFE prototype."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import safe_source_contract as S

LIB = '''library (fixture) {
cell (DFF) { ff (IQ, IQN) { clocked_on : "CLK"; next_state : "D"; clear : "!RN"; }
 pin (CLK) { direction : input; clock : true; } pin (RN) { direction : input; }
 pin (D) { direction : input; } pin (Q) { direction : output; function : "IQ"; } }
cell (ODD_BUFFER_NAME) { pin (A) { direction : input; } pin (Y) { direction : output; function : "A"; } }
cell (ODD_INVERTER_NAME) { pin (A) { direction : input; } pin (Y) { direction : output; function : "!A"; } }
cell (BUF_FAKE) { pin (A) { direction : input; } pin (B) { direction : input; }
 pin (Y) { direction : output; function : "A & B"; } }
cell (RAM) { memory (m) { address_width : 1; word_width : 1; }
 pin (CK) { direction : input; clock : true; } pin (ADDR) { direction : input; }
 pin (WE) { direction : input; } pin (Q) { direction : output; } }
cell (TIE) { pin (Y) { direction : output; function : "1"; } }
}'''

def cell(master, **pins):
    outs = {'Q', 'Y'}
    return dict(type=master, connections={k:[v] for k,v in pins.items()},
                port_directions={k:'output' if k in outs else 'input' for k in pins})

def net(cells, inputs=(2,3,4), outputs=()):
    return dict(modules={'top':dict(ports={**{f'i{i}':dict(direction='input',bits=[b]) for i,b in enumerate(inputs)},
                                         **{f'o{i}':dict(direction='output',bits=[b]) for i,b in enumerate(outputs)}},cells=cells)})

class CensusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.lib = Path(self.tmp.name)/'fixture.lib'
        self.lib.write_text(LIB)
        self.native = S.native_cells([self.lib])

    def audit(self, n):
        return S.census(n, 'top', self.native)

    def root(self, report, identity):
        return next(r for r in report['drivers'] if r['driver']==identity)

    def test_multilevel_inversion_and_exact_pin_count(self):
        cs = {'b':cell('ODD_BUFFER_NAME', A=2,Y=10),'n':cell('ODD_INVERTER_NAME',A=10,Y=11)}
        cs.update({f'f{i}':cell('DFF',CLK=3,RN=4,D=11,Q=20+i) for i in range(33)})
        r=self.audit(net(cs))
        root=self.root(r,'port:i0[0]')
        self.assertEqual(root['loads'],33)
        self.assertTrue(all(e['inverted'] for e in root['endpoints']))
        self.assertEqual(r['verdict'],'FAIL')
        self.assertEqual(root['endpoint_roles'],{'data':33})

    def test_opposite_polarity_forks_count_distinct_native_pins(self):
        r=self.audit(net({'b':cell('ODD_BUFFER_NAME',A=2,Y=10),
                         'n':cell('ODD_INVERTER_NAME',A=2,Y=11),
                         'f':cell('DFF',CLK=10,RN=11,D=10,Q=12)}))
        root=self.root(r,'port:i0[0]')
        self.assertEqual((root['loads'],root['clock_loads']),(2,1))
        self.assertEqual({e['pin']:e['inverted'] for e in root['endpoints']},
                         {'cell:f/D':False,'cell:f/RN':True})
        self.assertEqual(root['sink_classes'],{'ff':2})

    def test_pin_count_not_cell_count(self):
        r=self.audit(net({'a':cell('BUF_FAKE',A=2,B=2,Y=10)}))
        self.assertEqual(self.root(r,'port:i0[0]')['loads'],2)

    def test_merged_kept_copy_detected(self):
        cs={f'f{i}':cell('DFF',CLK=3,RN=4,D=2,Q=100+i) for i in range(33)}
        r=self.audit(net(cs,outputs=tuple(100+i for i in range(33))))
        self.assertEqual(r['max_loads'],33)
        self.assertIn('port:i0[0]',r['violations'])
        self.assertIn('port:i2[0]',r['violations'])  # reset is not waived

    def test_clock_names_do_not_exempt_data(self):
        n=net({'a':cell('BUF_FAKE',A=2,B=2,Y=10)},inputs=())
        n['modules']['top']['ports']={'clock':dict(direction='input',bits=[2])}
        self.assertEqual(self.root(self.audit(n),'port:clock[0]')['loads'],2)

    def test_clock_only_native_role(self):
        r=self.audit(net({'a':cell('DFF',CLK=2,RN=3,D=4,Q=10)}))
        self.assertEqual(self.root(r,'port:i0[0]')['loads'],0)
        self.assertEqual(self.root(r,'port:i0[0]')['clock_loads'],1)
        self.assertEqual(self.root(r,'port:i1[0]')['endpoint_roles'],{'reset':1})

    def test_mixed_clock_data_net_counts_data(self):
        r=self.audit(net({'a':cell('DFF',CLK=2,RN=3,D=2,Q=10)}))
        root=self.root(r,'port:i0[0]')
        self.assertEqual((root['loads'],root['clock_loads']),(1,1))

    def test_native_macro_static_and_literal_roles(self):
        cs={'t':cell('TIE',Y=10),'m':cell('RAM',CK=3,ADDR=2,WE=10,Q=11),
            'g':cell('BUF_FAKE',A=11,B='0',Y=12)}
        r=self.audit(net(cs,outputs=(12,)))
        self.assertEqual(self.root(r,'cell:t/Y')['role'],'static')
        self.assertEqual(self.root(r,'literal:0')['loads'],1)
        self.assertEqual(r['verdict'],'HOLD')
        self.assertEqual(r['unphysicalized_literals'],['literal:0'])
        self.assertEqual(self.root(r,'cell:m/Q')['role'],'macro')
        self.assertEqual(self.root(r,'port:i0[0]')['loads'],1)

    def test_no_names_only_buffer_collapse(self):
        r=self.audit(net({'a':cell('BUF_FAKE',A=2,B=3,Y=10),
                          'f':cell('DFF',CLK=3,RN=4,D=10,Q=11)}))
        self.assertFalse(self.root(r,'cell:a/Y')['transparent'])
        self.assertEqual(self.root(r,'port:i0[0]')['loads'],1)

    def test_registered_input_output_ownership_and_output_sharing(self):
        r=self.audit(net({'a':cell('DFF',CLK=3,RN=4,D=2,Q=10),
                         'b':cell('ODD_INVERTER_NAME',A=10,Y=11)},outputs=(10,11)))
        self.assertTrue(next(x for x in r['input_registration'] if x['port']=='port:i0[0]')['registered_data_endpoints_only'])
        self.assertEqual([x['driver'] for x in r['output_ownership']],['cell:a/Q']*2)
        self.assertEqual(self.root(r,'cell:a/Q')['loads'],2)

    def test_rejects_unknown_master_pin_direction_and_undriven(self):
        good=net({'a':cell('DFF',CLK=3,RN=4,D=2,Q=10)})
        for mutation in ('master','direction','pin','undriven'):
            with self.subTest(mutation=mutation):
                n=copy.deepcopy(good); a=n['modules']['top']['cells']['a']
                if mutation=='master':a['type']='DFF_unknown'
                if mutation=='direction':a['port_directions']['D']='output'
                if mutation=='pin':del a['connections']['RN']
                if mutation=='undriven':a['connections']['D']=[999]
                with self.assertRaises(S.ContractError):self.audit(n)

    def test_rejects_multidriver_x_and_buffer_cycle(self):
        variants=[net({'a':cell('TIE',Y=10),'b':cell('TIE',Y=10)}),
                  net({'a':cell('BUF_FAKE',A='x',B=2,Y=10)}),
                  net({'a':cell('ODD_BUFFER_NAME',A=11,Y=10),'b':cell('ODD_BUFFER_NAME',A=10,Y=11)})]
        for n in variants:
            with self.assertRaises(S.ContractError):self.audit(n)

    def test_duplicate_library_and_unsupported_bus_fail_closed(self):
        with self.assertRaises(S.ContractError):S.native_cells([self.lib,self.lib])
        self.lib.write_text('library (x) { cell (bad) { bus (A) { direction : input; } } }')
        with self.assertRaises(S.ContractError):S.native_cells([self.lib])

    def test_reported_max_cannot_override_recomputation(self):
        n=net({'g':cell('BUF_FAKE',A=2,B=2,Y=10)})
        n['reported_max']=0
        self.assertEqual(self.audit(n)['max_loads'],2)

    def test_exact_contract_hashes_and_opt_in_guards(self):
        root=Path(self.tmp.name)
        source=root/'input.sv'; source.write_text('// source identity fixture\n')
        mapped=root/'mapped.json'; mapped.write_text(json.dumps(net({'a':cell('DFF',CLK=3,RN=4,D=2,Q=10)})))
        def item(p):return dict(path=p.name,sha256=S.sha(p))
        c=dict(schema=S.SCHEMA,enabled=True,new_kit=True,production_activation=False,top='top',
               sources=[item(source)],netlist=item(mapped),libraries=[item(self.lib)])
        cp=root/'contract.json';cp.write_text(json.dumps(c))
        self.assertEqual(S.run(cp)['verdict'],'PASS')
        for key,value in [('enabled',False),('new_kit',False),('production_activation',True)]:
            bad=dict(c);bad[key]=value;cp.write_text(json.dumps(bad))
            with self.assertRaises(S.ContractError):S.run(cp)
        cp.write_text(json.dumps(c));source.write_text('// changed\n')
        with self.assertRaises(S.ContractError):S.run(cp)

if __name__=='__main__':unittest.main(verbosity=2)
