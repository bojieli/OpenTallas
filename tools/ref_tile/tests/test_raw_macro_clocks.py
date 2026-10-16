"""Exact raw-memory opt-in contracts and runtime ownership rejection."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import raw_macro_clocks as R
import ref_tile as RT
ROOT = Path(__file__).resolve().parents[3]
MASTER = 'ot_rom_4096x266_m8'
VIEW = 'physical/asap7_memory_macros/' + MASTER


def spec():
    return dict(kind='cluster', clock='hybrid_entries', clock_ports=['ck','child'],
                clock_cts_roots=['ck'], children=[],
                macros=[dict(view=VIEW, inst='u_rom', count=1)],
                soft_root_macro_masters=[MASTER],
                soft_root_macro_bindings={'u_rom': dict(master=MASTER, clock_pin='clk', root='ck')})


class Contract(unittest.TestCase):
    def test_actual_tt_ff_memory_and_exact_generated_binding(self):
        bindings, paths = R.contract(spec(), ROOT)
        self.assertEqual(bindings, spec()['soft_root_macro_bindings'])
        self.assertEqual(paths, [f'{VIEW}/{MASTER}_ff.lib', f'{VIEW}/{MASTER}_tt.lib'])
        self.assertIn('{u_rom} {master '+MASTER+' clock_pin clk root ck}', R.tcl(bindings)[0])

    def test_default_remains_closed(self):
        self.assertEqual(R.contract({}, ROOT), ({}, []))
        for key in ('soft_root_macro_masters','soft_root_macro_bindings'):
            s=spec(); s.pop(key)
            with self.subTest(key=key), self.assertRaises(ValueError): R.contract(s,ROOT)

    def test_ownership_mutants(self):
        for case in ('tile','mode','grant','unbound','extra','master','pin','root','count','entry','hard_child','path','duplicate'):
            s=spec(); b=s['soft_root_macro_bindings']['u_rom']
            if case=='tile': s['kind']='tile'
            if case=='mode': s['clock']='multiple_cts_roots'
            if case=='grant': s['clock_ports']=['child']
            if case=='unbound': s['macros'][0]['inst']='other'
            if case=='extra': s['soft_root_macro_bindings']['other']=dict(b)
            if case=='master': b['master']='arbitrary_hard'
            if case=='pin': b['clock_pin']='ce_in'
            if case=='root': b['root']='child'
            if case=='count': s['macros'][0]['count']=2
            if case=='entry': s['macros'][0]['clock_entry']={'port':'child'}
            if case=='hard_child': s['children']=[dict(view=VIEW)]
            if case=='path': s['macros'][0]['view']='../'+VIEW
            if case=='duplicate': s['macros'].append(dict(s['macros'][0]))
            with self.subTest(case=case), self.assertRaises(ValueError): R.contract(s,ROOT)

    def test_raw_liberty_required_and_hardened_view_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); v=root/VIEW; v.mkdir(parents=True)
            original=(ROOT/VIEW/f'{MASTER}_tt.lib').read_text()
            for corner in ('tt','ff'): (v/f'{MASTER}_{corner}.lib').write_text(original)
            R.contract(spec(),root)
            for marker in ('insertion.json','abstract.json','export.json'):
                (v/marker).write_text('{}')
                with self.subTest(marker=marker), self.assertRaises(ValueError): R.contract(spec(),root)
                (v/marker).unlink()
            for bad in ('cell(other) {}', 'cell('+MASTER+') {ff(IQ,IQN){} pin(clk){direction:input;clock:true;}}',
                        'cell('+MASTER+') {memory(){type:rom;address_width:12;word_width:0;}pin(clk){direction:input;clock:true;}}'):
                (v/f'{MASTER}_ff.lib').write_text('library(x){'+bad+'}')
                with self.subTest(lib=bad), self.assertRaises(ValueError): R.contract(spec(),root)

    def test_gen_hooks_calls_contract_before_emitting(self):
        s=spec();s['soft_root_macro_bindings']['u_rom']['clock_pin']='ce_in'
        with self.assertRaises(RT.SpecError): RT.gen_hooks(s,'unused')


class RuntimeOwnership(unittest.TestCase):
    def test_actual_tcl_helper_positive_and_negative_sinks(self):
        # Execute the production Tcl proc; mock only OpenDB/STA object accessors.
        helper=(ROOT/'physical/common_flow/clock_entries.tcl').read_text()
        helper=helper[:helper.index('if {[info procs clock_tree_synthesis]')]
        base='''
proc m {op} {if {$op eq "isBlock"} {return 1};return ot_rom_4096x266_m8}
proc i {op} {if {$op eq "getMaster"} {return m};return u_rom}
proc get_full_name {pin} {return $pin}
set ::ot_ce_raw_memory_seen {}
set ::ot_ce_raw_memory_bindings {u_rom {master ot_rom_4096x266_m8 clock_pin clk root ck}}
'''
        cases={
            'pass': ('ot_ce_raw_memory_sink i u_rom/clk ck', '1'),
            'wrong_root': ('ot_ce_raw_memory_sink i u_rom/clk child', 'ERROR'),
            'wrong_pin': ('ot_ce_raw_memory_sink i u_rom/ce_in ck', 'ERROR'),
            'wrong_master': ('dict set ::ot_ce_raw_memory_bindings u_rom master other; ot_ce_raw_memory_sink i u_rom/clk ck', 'ERROR'),
            'unlisted_hard': ('unset ::ot_ce_raw_memory_bindings;ot_ce_raw_memory_sink i u_rom/clk ck', '0'),
            'registered_hard': ('set ::ot_ce_counts {ot_rom_4096x266_m8 1};ot_ce_raw_memory_sink i u_rom/clk ck', '0'),
            'duplicate': ('ot_ce_raw_memory_sink i u_rom/clk ck;ot_ce_raw_memory_sink i u_rom/clk ck','ERROR')}
        for case,(body,expected) in cases.items():
            script=helper+base+'\nif {[catch {'+body+'} result]} {puts ERROR} else {puts $result}\n'
            p=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True)
            with self.subTest(case=case): self.assertEqual(p.stdout.strip(),expected,p.stderr)

if __name__=='__main__': unittest.main()
