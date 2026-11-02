"""Generator/refusal tests, explicitly not native ODB/PG qualification."""
import copy
from pathlib import Path
import subprocess
import tempfile
import unittest
import exact_native_clock as E


def fixture():
    names=['native[0]$_DFF_P_','native[1]$_DFF_P_','g_leaf[0].u_sram']
    pins=['CLK','CLK','clk'];kinds=['FF','FF','SRAM']
    rects=[[20,20,20.05,20.2],[24,24,24.05,24.2],[40,40,40.024,40.024]]
    m=dict(status='DISABLED_NATIVE_INTERNAL_CLOCK_GEOMETRY_PREP',
        radius_metric='Maximum Manhattan over full BUFx24 Y output metal and targetCLK',
        outline_um=[400,300],entry_island_um=[95,95,105,105],native_sinks=dict(FF=2,SRAM=1,total=3),budget_ps=dict(TT=250,FF=202.5),
        entry={'clk':{'rect_um':[100.008,99.76,100.056,100.24]},
               'rst_n':{'rect_um':[100.2,99.76,100.248,100.24]}},
        roots=[dict(reserved_master='BUFx24_ASAP7_75t_R',reservation_um=[21.6,20.52,23.22,20.79],
                    xy_um=[22.41,20.655],sink_indices=[0,1,2],sink_count=3)],
        sinks=[dict(instance=n,pin=p,kind=k,rect_um=b) for n,p,k,b in zip(names,pins,kinds,rects)])
    s=[dict(instance=n,pin=p,kind=k,master='FF_MASTER' if k=='FF' else 'SRAM_MASTER',
            source_clock_port='clk',actual_net='clk') for n,p,k in zip(names,pins,kinds)]
    o=dict(outline_um=[400,300],macros=[dict(name=names[-1],rect_um=[40,40,50,50])])
    return m,s,o


class ExactNativeClock(unittest.TestCase):
    def test_data_is_literal_and_has_no_odb_mutation(self):
        m,s,o=fixture();text=E.emit(m,s,o)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data.tcl';p.write_text(text)
            script=f'source {E.word(p)}\nputs [llength $::ot_enc_sinks]\nputs [lindex [lindex $::ot_enc_sinks 0] 0]\n'
            result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True)
            self.assertEqual(result.stderr,'')
            self.assertEqual(result.stdout.splitlines(),['3','native[0]$_DFF_P_'])
        self.assertNotIn('odb::',text)

    def test_duplicate_ownership_refuses(self):
        m,s,o=fixture();m['roots'][0]['sink_indices']=[0,0,2]
        with self.assertRaisesRegex(ValueError,'duplicate'):E.emit(m,s,o)

    def test_missing_endpoint_refuses(self):
        m,s,o=fixture();m['roots'][0]['sink_indices']=[0,1];m['roots'][0]['sink_count']=2
        with self.assertRaisesRegex(ValueError,'unassigned'):E.emit(m,s,o)

    def test_source_clock_alias_refuses(self):
        m,s,o=fixture();s[1]['actual_net']='other_clock'
        with self.assertRaisesRegex(ValueError,'aliased'):E.emit(m,s,o)

    def test_centre_pass_output_pin_fail_refuses(self):
        m,s,o=fixture();x,y=m['roots'][0]['xy_um'];m['sinks'][0]['rect_um']=[x+219.6,y,x+219.6,y]
        with self.assertRaisesRegex(ValueError,'output-to-clock'):E.emit(m,s,o)

    def test_off_native_row_refuses(self):
        m,s,o=fixture();m['roots'][0]['reservation_um']=[21.61,20.52,23.23,20.79]
        with self.assertRaisesRegex(ValueError,'native planned row'):E.emit(m,s,o)

    def test_changed_budget_refuses(self):
        m,s,o=fixture();m['budget_ps']['FF']=205
        with self.assertRaisesRegex(ValueError,'budget'):E.emit(m,s,o)

    def test_default_off_and_missing_native_engine(self):
        runtime=Path(E.__file__).with_suffix('.tcl')
        script=f'''source {E.word(runtime)}
puts [dict get [ot_enc::apply absent absent] status]
set ::env(OT_EXACT_NATIVE_CLOCK_PLAN) 1
if {{![catch {{ot_enc::apply absent absent}} why]}} {{error "missing engine accepted"}}
puts $why
'''
        result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True)
        self.assertEqual(result.stderr,'')
        self.assertEqual(result.stdout.splitlines(),['DISABLED_EXACT_NATIVE_CLOCK_CONSUMER',
            'OT_ENC_NATIVE_PG_API_REQUIRED ot_pg_native_birth_begin'])

    def test_clock_connect_exception_restores_cell_protection(self):
        # Unit-only signal-terminal fixture; no PG capability/ODB claim.
        runtime=Path(E.__file__).with_suffix('.tcl')
        script=f'source {E.word(runtime)}\n'+r'''
set protected 1
set net root
proc fixture_inst {method args} {
  if {$method eq "isDoNotTouch"} {return $::protected}
  if {$method eq "setDoNotTouch"} {set ::protected [lindex $args 0];return}
  error "unexpected instance method"
}
proc fixture_term {method args} {
  switch $method {
    getInst {return fixture_inst}
    getNet {return $::net}
    disconnect {set ::net NULL}
    connect {
      if {[lindex $args 0] eq "bad"} {error "injected signal connect failure"}
      if {[lindex $args 0] eq "silent"} {return}
      set ::net [lindex $args 0]
    }
    default {error "unexpected terminal method"}
  }
}
if {![catch {ot_enc::source_reconnect fixture_term bad}]} {error "failure not exercised"}
if {$protected!=1} {error "source cell protection lost on exception"}
if {![catch {ot_enc::source_reconnect fixture_term silent}]} {error "silent connect failure accepted"}
ot_enc::source_reconnect fixture_term root
if {$net ne "root" || $protected!=1} {error "caller signal rollback failed"}
puts UNIT_SIGNAL_RECONNECT_PROTECTION_PASS
'''
        result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True)
        self.assertEqual(result.stderr,'')
        self.assertEqual(result.stdout.strip(),'UNIT_SIGNAL_RECONNECT_PROTECTION_PASS')


if __name__=='__main__':unittest.main()
