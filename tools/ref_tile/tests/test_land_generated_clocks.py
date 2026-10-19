import copy
import importlib.util
import itertools
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1]/'land_generated_clocks.py'
spec = importlib.util.spec_from_file_location('land_generated_clocks', MODULE)
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)

LIB = '''library(toy) {time_unit:"1ns";capacitive_load_unit(1,pf);
nom_voltage:1;nom_temperature:25;nom_process:1;
cell(ICG) {area:1;clock_gating_integrated_cell:latch_posedge;
pin(CK){direction:input;capacitance:0.001;clock:true;clock_gate_clock_pin:true;}
pin(E){direction:input;capacitance:0.001;clock_gate_enable_pin:true;}
pin(Q){direction:output;function:"CK & E";clock_gate_out_pin:true;}
}}'''.replace(':', ' : ')


class Contract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        def put(path, data):
            p=self.root/path; p.write_text(data if isinstance(data,str) else json.dumps(data))
            return dict(path=path,sha256=L.digest(p))
        self.put=put
        rtl=put('rtl.sv','module top; endmodule\n')
        lib=put('toy.lib',LIB)
        self.netlist='module top(input ck,ck_s,en);\n'+''.join(f'ICG {side}{bank}(.CK({port}),.E(en),.Q());\n' for side,port in [('r','ck'),('w','ck_s')] for bank in range(4))+'endmodule\n'
        netlist=put('mapped.v',self.netlist)
        self.banks=[dict(name=f'{s}{b}_clk',side=side,bank=b,source_port=port,source_clock=clock,cell=f'{s}{b}',master='ICG',clock_pin='CK',enable_pin='E',output_pin='Q') for s,side,port,clock in [('w','write','ck_s','write'),('r','read','ck','read')] for b in range(4)]
        topology=put('topology.json',dict(mapped_sha256=netlist['sha256'],banks={b['cell']:{k:b[k] for k in ('master','source_port','clock_pin','enable_pin','output_pin')} for b in self.banks}))
        witness=put('witness.log','actual witness fixture\n')
        rows=[]
        for k,phase,extra,reset in itertools.product(range(8),range(8),range(3),range(2)):
            for bank in range(4):
                w=bank; delta=extra if phase>=2 else extra+1; r=(bank+delta)%4
                rows.append(dict(K=k,phase_index=phase,extra_age_cycles=extra,reset_order=reset,bank=bank,write_phase_cycles=w,read_phase_cycles=r,write_generated_edges=[1+2*w,2+2*w,9+2*w],read_generated_edges=[1+2*r,2+2*r,9+2*r],checks=1,min_age_T=(r-w)%4+phase/8,max_age_T=(r-w)%4+phase/8,min_overwrite_gap_T=4-((r-w)%4+phase/8)))
        self.cert=dict(status='BEHAVIORAL_EDGE_WINDOW_PASS_NOT_PHYSICAL_TIMING',two_boot_epochs=True,period_T=4,high_pulse_T=.5,witness_sha256=witness['sha256'],rows=rows)
        self.compiled=dict(schema='ot.land-compiled-scenario.v1',sources=[rtl],top='top',params={},defines=[],case=dict(K=0,phase_index=7,extra_age_cycles=0,reset_order=0),root_waveforms_ns=dict(ck_s=[10,0,5],ck=[10,8.75,13.75]),reset_origin=dict(write=20,read=24,first_usable=32),enable_witness=witness,mapped_netlist=netlist,mapped_topology=topology,compiler_inputs=[put('compiler.json',dict(K=0))])
        behavioral=put('behavioral.json',dict(sources=[rtl],top='top',params={},defines=[],certificate_sha256=L.digest(self.root/'certificate.json') if (self.root/'certificate.json').exists() else '',witness_sha256=witness['sha256']))
        self.c=dict(behavioral_binding=behavioral,schema=L.SCHEMA,sources=[rtl],top='top',params={},defines=[],certificate=put('certificate.json',self.cert),compiled=put('compiled.json',self.compiled),banks=self.banks,reserves_ps=dict(same_setup=60,cross_setup=150,cross_setup_slow=210,hold=25,cross_hold=100),icg=dict(master='ICG',clock_pin='CK',enable_pin='E',output_pin='Q',liberty=lib))
        self.refresh_behavioral()
        self.spec=dict(clock='multiple_cts_roots',top='top',sources=['rtl.sv'],params={},defines=[],clock_ports=['ck','ck_s'],land_generated_clocks=self.c)

    def refresh_behavioral(self):
        self.c['behavioral_binding']=self.put('behavioral.json',dict(sources=self.c['sources'],top=self.c['top'],params=self.c['params'],defines=self.c['defines'],certificate_sha256=self.c['certificate']['sha256'],witness_sha256=self.cert['witness_sha256']))

    def sync(self):
        self.c['certificate']=self.put('certificate.json',self.cert)
        self.c['compiled']=self.put('compiled.json',self.compiled)
        self.refresh_behavioral()

    def test_exact_phase_preserved(self):
        text=L.emit(self.spec,self.root)
        self.assertIn('8.75 root_rise',text)
        self.assertIn('-edges {3 4 11}',text)
        for illegal in ('set_false_path','set_multicycle_path','set_clock_groups','create_clock -name'):
            self.assertNotIn(illegal,text)

    def test_missing_case(self):
        self.cert['rows'].pop();self.sync()
        with self.assertRaisesRegex(ValueError,'missing|incomplete'):L.emit(self.spec,self.root)

    def test_wrong_phase(self):
        self.compiled['root_waveforms_ns']['ck']=[10,0,5];self.sync()
        with self.assertRaisesRegex(ValueError,'native root phase'):L.emit(self.spec,self.root)

    def test_phase_collapse(self):
        for r in self.cert['rows']:
            if r['phase_index']==7:r['min_age_T']=1;r['max_age_T']=1
        self.sync()
        with self.assertRaisesRegex(ValueError,'phase collapsed'):L.emit(self.spec,self.root)

    def test_stale_source(self):
        (self.root/'rtl.sv').write_text('changed')
        with self.assertRaisesRegex(ValueError,'stale artifact'):L.emit(self.spec,self.root)

    def test_foreign_and_double_prefix(self):
        for field,value,regex in [('source_port','foreign','foreign clock'),('cell','u_ot_pr_core/u_ot_pr_core/w0','double wrapper')]:
            old=self.banks[0][field];self.banks[0][field]=value
            with self.assertRaisesRegex(ValueError,regex):L.emit(self.spec,self.root)
            self.banks[0][field]=old

    def test_custom_hooks(self):
        for key in ('sdc_extra','boundary_tcl','pre_cts_extra'):
            self.spec[key]=['rogue.tcl']
            with self.assertRaisesRegex(ValueError,'custom timing hooks'):L.emit(self.spec,self.root)
            del self.spec[key]

    def test_reserves_and_enable_witness(self):
        self.c['reserves_ps']['cross_setup']=60
        with self.assertRaisesRegex(ValueError,'reserves'):L.emit(self.spec,self.root)
        self.c['reserves_ps']['cross_setup']=150
        self.compiled['enable_witness']=self.put('fake.log','fake');self.sync()
        with self.assertRaisesRegex(ValueError,'waveform witness'):L.emit(self.spec,self.root)

    def test_wrong_edges_and_master(self):
        self.cert['rows'][0]['write_generated_edges']=[3,4,11]
        # Change a selected row (the earlier row is still independently covered).
        for r in self.cert['rows']:
            if all(r[k]==self.compiled['case'][k] for k in L.CASE):r['write_generated_edges']=[2,3,10]
        self.sync()
        with self.assertRaisesRegex(ValueError,'waveform'):L.emit(self.spec,self.root)

    def test_stale_behavior_and_params(self):
        self.c['params']={'W':180}
        with self.assertRaisesRegex(ValueError,'parameter'):L.emit(self.spec,self.root)
        self.c['params']={}
        self.c['behavioral_binding']=self.put('behavioral.json',dict(sources=[],top='top',params={},defines=[],certificate_sha256=self.c['certificate']['sha256'],witness_sha256=self.cert['witness_sha256']))
        with self.assertRaisesRegex(ValueError,'behavioral source'):L.emit(self.spec,self.root)

    def test_native_liberty_semantics(self):
        self.c['icg']['liberty']=self.put('wrong.lib',LIB.replace('clock_gate_enable_pin : true','clock_gate_enable_pin : false'))
        with self.assertRaisesRegex(ValueError,'enable_pin'):L.emit(self.spec,self.root)

    def test_actual_land_certificate(self):
        source=os.environ.get('OT_ACTUAL_LAND_CERTIFICATE')
        if not source:self.skipTest('actual source-pinned LAND certificate supplied on fleet')
        cert=json.loads(Path(source).read_text())
        rows,cases=L.validate_certificate(cert)
        self.assertEqual(len(rows),4*cert['scenario_count'])
        self.assertEqual(len(cases),384)
        self.assertTrue(any(r['phase_index']==7 and abs(r['min_age_T']-.875)<1e-7 for r in rows))
        bad=copy.deepcopy(cert);bad['rows'].pop()
        with self.assertRaisesRegex(ValueError,'missing|incomplete'):L.validate_certificate(bad)

    def native(self,mutation=''):
        if os.environ.get('OT_LAND_NATIVE')!='1':self.skipTest('fleet-only OpenSTA')
        text=L.emit(self.spec,self.root)
        (self.root/'emit.tcl').write_text(text)
        shared=os.environ['OT_CLOCK_FAMILY_TCL']
        script='''read_liberty /run/toy.lib
read_verilog /run/mapped.v
link_design top
create_clock -name read -period 10 -waveform {8.75 13.75} [get_ports ck]
create_clock -name write -period 10 -waveform {0 5} [get_ports ck_s]
source /shared/clock_family.tcl
set ::ot_land_mapped_netlist /run/mapped.v
set ::ot_land_loaded_liberty /run/toy.lib
'''+mutation+'\nsource /run/emit.tcl\not_cf_refresh\n'+''.join(f'ot_land_close [sta::time_sta_ui [[get_clocks {side}{bank}_clk] period]] 40 bank_period\not_land_close [sta::time_sta_ui [lindex [[get_clocks {side}{bank}_clk] waveform] 0]] {phase+10*bank} generated_rise\n' for side,phase in [('w',0),('r',8.75)] for bank in range(4))+'puts LAND_NATIVE_PASS\nexit\n'
        (self.root/'run.tcl').write_text(script)
        result=subprocess.run(['docker','run','--rm','-v',f'{self.root}:/run:ro','-v',f'{Path(shared).parent}:/shared:ro','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta','-exit','/run/run.tcl'],text=True,capture_output=True)
        print(result.stdout,result.stderr)
        return result

    def test_native_positive(self):
        p=self.native();self.assertEqual(p.returncode,0);self.assertIn('LAND_NATIVE_PASS',p.stdout);self.assertNotIn('Error',p.stdout)

    def test_native_foreign_lineage(self):
        p=self.native('delete_clock [get_clocks write]\ncreate_clock -name foreign -period 10 [get_ports ck_s]\ncreate_clock -name write -period 10 [get_ports en]')
        self.assertIn('LAND: foreign primary source',p.stdout);self.assertNotIn('LAND_NATIVE_PASS',p.stdout)

    def test_native_wrong_phase(self):
        p=self.native('delete_clock [get_clocks read]\ncreate_clock -name read -period 10 [get_ports ck]')
        self.assertIn('LAND: wrong root_rise',p.stdout);self.assertNotIn('LAND_NATIVE_PASS',p.stdout)

if __name__=='__main__':unittest.main()
