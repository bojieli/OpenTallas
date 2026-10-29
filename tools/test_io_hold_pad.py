"""OT_IO_HOLD_PAD (S81-CORES-R24): default OFF; opt-in pads only input-port -> register-data hold paths with
ceil((-slack + margin) / hb4) HB4 cells each, fails closed above the per-bit cap, before the structural count."""
import pathlib
import subprocess
import tempfile
import unittest

HELPER = pathlib.Path(__file__).with_name("orfs_hold_mm.tcl")

SCRIPT = r'''
source @HELPER@
set ::ot_mm_synced 1
set ::ot_mm_active 1
set ::env(REPORTS_DIR) @REPORTS@
@ENV@
# fake design: paths {slack start end}; ports in/ck; regs r1 r2 (r2/RN async)
set ::paths {@PATHS@}
set ::inserts {}
proc find_timing_paths {args} {
  if {[lsearch -exact $args -slack_max] >= 0} { set out {}; foreach p $::paths { if {[lindex $p 0] < 0} { lappend out $p } }; return $out }
  return [list [lindex [lsort -real -index 0 $::paths] 0]]
}
proc get_property {o prop} {
  switch $prop {
    slack { return [lindex $o 0] }
    startpoint { return [lindex $o 1] }
    endpoint { return [lindex $o 2] }
    sources { return ck }
  }
}
proc get_full_name {o} { return $o }
proc all_clocks {} { return clk }
proc all_registers {args} {
  if {[lsearch $args -async_pins] >= 0} { return {r2/RN} }
  return {r1/D r2/D r2/RN}
}
proc get_lib_cells {args} { return HB4 }
proc unset_dont_use {c} {}
proc set_dont_use {c} {}
namespace eval ord {}
proc ord::get_db_block {} { return blk }
proc ord::dbu_to_microns {v} { return $v }
namespace eval sta {}
proc sta::sta_to_db_inst {i} { return dbi }
proc dbi {m} { return {10 20} }
foreach r {r1/D r2/D r2/RN} { proc $r {m} { return inst } }
proc insert_buffer {args} { lappend ::inserts [lindex $args [expr {[lsearch $args -load_pins]+1}]] }
proc log_cmd {args} {}
proc estimate_parasitics {args} {}
set code [catch {ot_io_hold_pad} msg]
puts "RESULT $code $msg"
puts "INSERTS [llength $::inserts] [lsort $::inserts]"
'''


class IoHoldPad(unittest.TestCase):
    def run_case(self, paths, env, stage=None):
        with tempfile.TemporaryDirectory() as d:
            if stage is not None:  # ot_hold_stage: RESULTS_DIR/4_1_cts.odb present -> grt, else cts
                res = pathlib.Path(d) / 'res'
                res.mkdir()
                if stage == 'grt':
                    (res / '4_1_cts.odb').write_text('')
                env = dict(env, RESULTS_DIR='{' + str(res) + '}')
            s = (SCRIPT.replace('@HELPER@', '{' + str(HELPER) + '}').replace('@REPORTS@', '{' + d + '}')
                 .replace('@ENV@', '\n'.join(f'set ::env({k}) {v}' for k, v in env.items()))
                 .replace('@PATHS@', ' '.join('{' + p + '}' for p in paths)))
            return subprocess.run(['tclsh'], input=s, text=True, capture_output=True, check=True).stdout

    def test_default_off_inserts_nothing(self):
        out = self.run_case(['-74 in r1/D'], {})
        self.assertIn('INSERTS 0', out)

    def test_pads_only_port_to_register_data(self):
        # -74 -> ceil(79/37)=3 cells; reg->reg, clock port, async pin and met paths untouched
        out = self.run_case(['-74 in r1/D', '-27 r1/Q r2/D', '-30 ck r2/D', '-40 in r2/RN', '5 in r2/D'],
                            {'OT_IO_HOLD_PAD': 1})
        self.assertIn('RESULT 0', out)
        self.assertIn('INSERTS 3 r1/D r1/D r1/D', out)

    def test_cap_fails_closed(self):
        out = self.run_case(['-160 in r1/D'], {'OT_IO_HOLD_PAD': 1})
        self.assertIn('RESULT 1', out)
        self.assertIn('needs 5 HB4 > 4', out)
        self.assertIn('INSERTS 0', out)

    # FLOW-CLOCK-R6: OT_IO_HOLD_PAD_STAGE (default cts) for kits whose first FF hold repair is the GRT step
    def test_default_stage_skips_grt(self):
        out = self.run_case(['-74 in r1/D'], {'OT_IO_HOLD_PAD': 1}, stage='grt')
        self.assertIn('INSERTS 0', out)
        self.assertIn('OT_IO_HOLD_PAD skip: stage grt (pad stage cts)', out)

    def test_grt_stage_pads_at_grt(self):
        # E0 class: input port -> face register at -53.09 -> ceil(58.09/37) = 2 HB4
        out = self.run_case(['-53.09 in r1/D', '-12 r1/Q r2/D', '-40 in r2/RN'],
                            {'OT_IO_HOLD_PAD': 1, 'OT_IO_HOLD_PAD_STAGE': 'grt'}, stage='grt')
        self.assertIn('RESULT 0', out)
        self.assertIn('INSERTS 2 r1/D r1/D', out)

    def test_grt_stage_skips_cts(self):
        out = self.run_case(['-74 in r1/D'], {'OT_IO_HOLD_PAD': 1, 'OT_IO_HOLD_PAD_STAGE': 'grt'}, stage='cts')
        self.assertIn('INSERTS 0', out)

    def test_bad_stage_fails_closed(self):
        out = self.run_case(['-74 in r1/D'], {'OT_IO_HOLD_PAD': 1, 'OT_IO_HOLD_PAD_STAGE': 'route'}, stage='grt')
        self.assertIn('RESULT 1', out)
        self.assertIn('want cts or grt', out)
        self.assertIn('INSERTS 0', out)


if __name__ == '__main__':
    unittest.main()
