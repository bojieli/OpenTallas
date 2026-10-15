#!/usr/bin/env python3
"""Actual RTL memory/engine fixture, then observed structural/provenance mutants."""
import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('coverage', HERE/'native_operation_coverage.py')
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)

class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        rtl = cls.root/'real_native.sv'
        rtl.write_text('''module memory(input ck, input we, input [7:0] wr_data, output [7:0] rd_data);
reg [7:0] bank[0:3]; reg [1:0] index=0;
always @(posedge ck)begin index<=index+1; if(we)bank[index]<=wr_data;end
assign rd_data=bank[index]; endmodule
module engine(input [7:0] a, output [7:0] y);assign y=a+8'd1;endmodule
module top(input ck, input we, output [7:0] y);wire [7:0] a;
memory m(ck,we,y,a);engine e(a,y);endmodule
''')
        subprocess.run(['yosys','-Q','-T','-p','read_verilog -sv real_native.sv; hierarchy -top top; proc; write_json target.json'], cwd=cls.root,check=True,capture_output=True)
        cls.program = cls.root/'program.json'
        cls.program.write_text(json.dumps({'ops':[{'id':'add','eng':'ADD','start':0}]}))
        op = coverage.operations(cls.program)[0]
        cls.manifest = {'program_sha256':coverage.sha(cls.program),'required_components':['engine','memory','control'], 'components':{'engine':{'implementation':'rtl','instance':'top/e'},'memory':{'implementation':'rtl','instance':'top/m'},'control':{'implementation':'rtl','instance':'top'}},'elaboration':{'netlist':'target.json','netlist_sha256':coverage.sha(cls.root/'target.json'),'source_sha256':{'real_native.sv':coverage.sha(rtl)},'top':'top'},'operations':{'add':{**op,'instance':'top/e','output_provider':'target_rtl','components':['engine','memory','control'],'operands':[{'port':'a','memory_instance':'top/m','memory_port':'rd_data'}],'results':[{'port':'y','memory_instance':'top/m','memory_port':'wr_data'}]}}}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def check(self, mutate=None):
        m=copy.deepcopy(self.manifest)
        if mutate: mutate(m)
        return coverage.audit(self.root,self.program,m)

    def test_actual_instantiated_memory_and_engine_pass(self):
        self.assertTrue(self.check()['native_operation_coverage_pass'])

    def test_missing_emitted_operation_fails(self):
        r=self.check(lambda m:m['operations'].clear())
        self.assertFalse(r['native_operation_coverage_pass'])
        self.assertIn('EMITTED_OPERATION_UNBOUND',r['operations'][0]['reasons'])

    def test_injected_golden_compute_fails(self):
        self.assertFalse(self.check(lambda m:m['operations']['add'].update(output_provider='oracle',dut_output_override=True))['native_operation_coverage_pass'])

    def test_modeled_on_chip_memory_fails(self):
        self.assertFalse(self.check(lambda m:m['components']['memory'].update(implementation='cpp'))['native_operation_coverage_pass'])

    def test_uninstantiated_engine_fails(self):
        self.assertFalse(self.check(lambda m:m['operations']['add'].update(instance='top/missing'))['native_operation_coverage_pass'])

    def test_wrong_operand_memory_port_fails(self):
        self.assertFalse(self.check(lambda m:m['operations']['add']['operands'][0].update(memory_port='wr_data'))['native_operation_coverage_pass'])

    def test_substituted_source_fails(self):
        self.assertFalse(self.check(lambda m:m['elaboration']['source_sha256'].update({'real_native.sv':'0'*64}))['native_operation_coverage_pass'])

    def test_incomplete_target_inventory_fails(self):
        def mutate(m):
            m['components'].pop('control')
            m['required_components'].remove('control')
            m['operations']['add']['components'].remove('control')
        self.assertFalse(self.check(mutate)['native_operation_coverage_pass'])

    def test_runtime_credit_wait_fails(self):
        self.assertFalse(self.check(lambda m:m['components']['engine'].update(runtime_flow_control=True))['native_operation_coverage_pass'])

    def test_expected_only_observer_is_permitted(self):
        self.assertTrue(self.check(lambda m:m['components'].update(expected={'role':'expected_observer','implementation':'python','drives_dut':False}))['native_operation_coverage_pass'])

    def test_observer_driving_dut_fails(self):
        self.assertFalse(self.check(lambda m:m['components'].update(expected={'role':'expected_observer','implementation':'python','drives_dut':True}))['native_operation_coverage_pass'])

if __name__=='__main__':unittest.main()
