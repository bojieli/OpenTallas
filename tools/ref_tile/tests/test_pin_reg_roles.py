"""Exercise literal control-role planning and the production wrapper generator."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/ref_tile'))
import ref_tile as RT
import port_latency as PL
import pre_route_gate as PG

PORTS = '''input [0:0] ck
input [0:0] ckv
input [0:0] rst
input [0:0] rsv
input [7:0] command
output [7:0] result'''
SPEC = dict(top='example', clock_port='ck', clock_ports=['ck', 'ckv'],
            reset_ports=['rst', 'rsv'], pin_regs=dict(enable=True, clock='ck'))


def generate(path, clocks='ck,ckv', resets='rst,rsv', ports=PORTS, reset_regex=None, exclude=None):
    # Only the elaborated Yosys port-list IO is stubbed. Classification,
    # generated Verilog and latency table are the actual production helper.
    script = '''set ::env(DESIGN_NAME) example
set ::env(OT_PIN_REGS_CLOCK) {%s}
set ::env(OT_PIN_REGS_RESET_PORTS) {%s}
set ::env(RESULTS_DIR) {%s}
proc yosys {args} {
 if {[lindex $args 0] eq "tee"} {
  set f [open [lindex $args 3] w]
  puts $f {%s}
  close $f
 }
}
if {[catch {source {%s}} message]} {puts stderr $message; exit 1}
''' % (clocks, resets, path, ports, ROOT/'physical/common_flow/ot_pin_regs.tcl')
    if reset_regex is not None:
        script=script.replace('set ::env(RESULTS_DIR)', 'set ::env(OT_PIN_REGS_RESET) {' + reset_regex + '}\nset ::env(RESULTS_DIR)',1)
    if exclude is not None:
        script=script.replace('set ::env(RESULTS_DIR)', 'set ::env(OT_PIN_REGS_EXCLUDE) {' + exclude + '}\nset ::env(RESULTS_DIR)',1)
    if resets is None:
        script=script.replace('set ::env(OT_PIN_REGS_RESET_PORTS) {None}\n','')
    return subprocess.run(['tclsh'], input=script, text=True, capture_output=True)


class Roles(unittest.TestCase):
    def test_intended_tcl_data_exclusions_match_actual_wrapper(self):
        spec = dict(SPEC, pin_regs=dict(enable=True, clock='ck', exclude=r'\mcommand\M'))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            self.assertEqual(generate(path, exclude=r'\mcommand\M').returncode, 0)
            wrapper = path/'ot_pin_regs_wrapper.v'
            report = PL.export(path/'ot_pin_regs.tsv', wrapper, 'example', 'a'*40)
            self.assertEqual(PL.validate_roles(report, wrapper, spec, lambda _:None)['excluded_data_ports'], ['command'])
            # Reproduce the Make-corrupted pattern population, with controls still correct.
            self.assertEqual(generate(path, exclude='^no_match$').returncode, 0)
            report = PL.export(path/'ot_pin_regs.tsv', wrapper, 'example', 'a'*40)
            with self.assertRaisesRegex(ValueError, 'excluded data'):
                PL.validate_roles(report, wrapper, spec, lambda _:None)
            report['ports']['command']['register_edges'] = 0
            with self.assertRaisesRegex(ValueError, 'not direct'):
                PL.validate_roles(report, wrapper, spec, lambda _:None)

    def test_unintended_data_bypass_and_invalid_tcl_pattern_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            self.assertEqual(generate(path, exclude='^command$').returncode, 0)
            wrapper = path/'ot_pin_regs_wrapper.v'
            report = PL.export(path/'ot_pin_regs.tsv', wrapper, 'example', 'a'*40)
            with self.assertRaisesRegex(ValueError, 'intended data'):
                PL.validate_roles(report, wrapper, SPEC, lambda _:None)
        with self.assertRaisesRegex(ValueError, 'invalid intended Tcl'):
            PL.excluded_ports('[', ['command'])

    def test_plan_preserves_secondary_clock_independent_of_clock_policy(self):
        plan = RT.pin_regs_plan(SPEC)
        self.assertEqual(plan['clock_ports'], ['ck', 'ckv'])
        self.assertEqual(plan['reset_ports'], ['rst', 'rsv'])
        self.assertIn("--orfs-var OT_PIN_REGS_RESET_PORTS='rst,rsv'", RT.pin_regs_vars(SPEC))
        for change in (dict(reset_ports=['ckv']), dict(clock_ports=['ck*']),
                       dict(pin_regs=dict(clock='unknown'))):
            with self.assertRaises(RT.SpecError):
                RT.pin_regs_plan(dict(SPEC, **change))

    def test_actual_generated_wrapper_roles_and_independent_raw_phase(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            run = generate(path)
            self.assertEqual(run.returncode, 0, run.stderr)
            wrapper = path/'ot_pin_regs_wrapper.v'
            report = PL.export(path/'ot_pin_regs.tsv', wrapper, 'example', 'a'*40)
            roles = PL.validate_roles(report, wrapper, SPEC, lambda _: None)
            self.assertEqual(roles['clocks'], ['ck', 'ckv'])
            self.assertEqual({n: r['register_edges'] for n,r in report['ports'].items()},
                             dict(ck=0, ckv=0, rst=0, rsv=0, command=1, result=1))
            # Inspect the actual transformed DUT instance across clock phases.
            # Keep ck stopped: any clock/reset stage clocked by ck is observable.
            core = '''module example__ot_pr_core(input ck,ckv,rst,rsv,input[7:0] command,output[7:0] result);
assign result=command; endmodule
module tb;
reg ck=0,ckv=0,rst=1,rsv=1; reg[7:0] command=0;wire[7:0] result;
example dut(ck,ckv,rst,rsv,command,result);
initial begin
 #1; ckv=1; rsv=0;
 #1; if(dut.u_ot_pr_core.ckv!==1 || dut.u_ot_pr_core.rsv!==0) $fatal(1,"raw phase/reset changed");
 ckv=0;rsv=1;
 #1; if(dut.u_ot_pr_core.ckv!==0 || dut.u_ot_pr_core.rsv!==1) $fatal(1,"release phase changed");
 $display("RAW_PHASE_PASS");$finish;end
endmodule
'''
            (path/'core.sv').write_text(core)
            for name, body, expected in [('positive', wrapper.read_text(), 0),
                ('registered_clock', wrapper.read_text().replace('.ckv(ckv)', '.ckv(ckv__mut)').replace('  example__ot_pr_core', '  reg ckv__mut; always @(posedge ck) ckv__mut <= ckv;\n  example__ot_pr_core'), 1),
                ('registered_reset', wrapper.read_text().replace('.rsv(rsv)', '.rsv(rsv__mut)').replace('  example__ot_pr_core', '  reg rsv__mut; always @(posedge ck) rsv__mut <= rsv;\n  example__ot_pr_core'), 1)]:
                source=path/(name+'.v');source.write_text(body)
                subprocess.run(['iverilog','-g2012','-s','tb','-o',str(path/'sim'),str(source),str(path/'core.sv')],check=True,capture_output=True)
                sim=subprocess.run(['vvp',str(path/'sim')],capture_output=True,text=True)
                self.assertEqual(sim.returncode,expected,sim.stdout+sim.stderr)
                if expected:
                    with self.assertRaises(ValueError):PL.validate_roles(report,source,SPEC,lambda _:None)

    def test_literal_bits_resolve_or_fail_before_transformation(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)
            self.assertEqual(generate(path,'ck[0],ckv[0]','rst[0],rsv[0]').returncode,0)
            for clocks,resets,ports in [('ck,missing','rst,rsv',PORTS),
                ('ck,ckv[1]','rst,rsv',PORTS),('ck,ckv','rst,ckv',PORTS),
                ('ck,ckv[0]','rst,rsv',PORTS.replace('[0:0] ckv','[1:0] ckv')),
                ('ck,ckv',None,PORTS)]:
                run=generate(path,clocks,resets,ports)
                self.assertNotEqual(run.returncode,0)
                self.assertIn('OT_PIN_REGS:',run.stderr)

    def test_gate_rejects_registered_control_immediately_and_forged_table(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)
            generate(path, 'ck', '')  # actual old selection: ckv and rsv data
            (path/'kit.env').write_text("EXTRA=('--orfs-var' 'OT_PIN_REGS=1')")
            def output():
                enc=lambda f:base64.b64encode(zlib.compress((path/f).read_bytes())).decode()
                return 'GATE_PIN_REGS_B64 '+enc('ot_pin_regs.tsv')+' '+enc('ot_pin_regs_wrapper.v')+'\n'
            gate=PG.Gate();PG.check_port_latency(gate,path,SPEC,output(),'a'*40)
            self.assertEqual(gate.verdict,'FAIL')
            table=path/'ot_pin_regs.tsv';table.write_text(table.read_text().replace('ckv\tinput\t1\t1\tpin register','ckv\tinput\t1\t0\tclock').replace('rsv\tinput\t1\t1\tpin register','rsv\tinput\t1\t0\treset'))
            gate=PG.Gate();PG.check_port_latency(gate,path,SPEC,output(),'a'*40)
            self.assertEqual(gate.verdict,'FAIL')

    def test_quoted_literal_options_and_ambiguous_variables(self):
        from kit_orfs_vars import parse
        self.assertEqual(parse("EXTRA=('--orfs-var' 'OT_PIN_REGS=1' '--orfs-var' 'X=^(x|y)$')")['OT_PIN_REGS'], '1')
        self.assertEqual(parse('EXTRA=() # --orfs-var OT_PIN_REGS=1'), {})
        with self.assertRaises(ValueError):
            parse("EXTRA=('--orfs-var' 'OT_PIN_REGS=1' '--orfs-var' 'OT_PIN_REGS=0')")
        with tempfile.TemporaryDirectory() as td:
            path=Path(td);(path/'kit.env').write_text('EXTRA=("$UNKNOWN_OPTIONS")')
            gate=PG.Gate();PG.check_port_latency(gate,path,SPEC,'', 'a'*40)
            self.assertEqual(gate.verdict,'FAIL')

    def test_unknown_sdc_clock_role_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td);generate(path)
            report=PL.export(path/'ot_pin_regs.tsv',path/'ot_pin_regs_wrapper.v','example','a'*40)
            spec=dict(SPEC,sdc_extra=['unknown.sdc'])
            for text in (None,'create_clock -period 100 [get_ports $unknown]'):
                with self.assertRaises(ValueError):
                    PL.validate_roles(report,path/'ot_pin_regs_wrapper.v',spec,lambda _:text)

if __name__=='__main__':unittest.main()
