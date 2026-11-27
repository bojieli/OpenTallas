"""SEAMHOLD-HB4-HOSTN-RST / SEAMHOLD-CTL-K5-DI (HEAD-INT-R2 11-26): opt-in HB4 pads, 0 flops / 0 cycles, default byte-same.
  reset.pin_entry_hb4 {reset,start}        -> ot_dp_rrelay_ph_hb #(.N) at u_rst_in / u_run_in (pin still feeds only the entry d)
  clock.landing_ctl_hold_hb4 {bus: N}      -> ot_dp_hd on the dataflow ring's ready/fault/fstart control inputs."""
import copy
import re
import shutil
import subprocess
from types import SimpleNamespace
import pytest
import clock_landings as CL
import gen_phys
import gen_rtl as G
import pin_entry_phase as PH
import reset_tree as R
from test_pin_entry_phase import tree, wrapper


def plan(hb=None, flag=True, straps=True):
    t = {'reset': {'pin_entry_phase': flag}}
    if hb is not None:
        t['reset']['pin_entry_hb4'] = hb
    if straps:
        t['id_straps'] = [dict(name=PH.STRAP, width=1)]
    return SimpleNamespace(types={'t': t})


def cfg(hb, t=None):
    return R._type_pin_entry_phase(plan(hb), 't', t or tree())


def test_reset_default_byte_same():
    base = '\n'.join(R.rtl_lines(cfg(None)))
    assert 'ot_dp_rrelay_ph u_rst_in' in base and '_hb' not in base and 'u_hdly' not in base
    assert not PH.uses_hb({'partition_types': plan(None).types})
    assert not G.uses_hold_hb4({'partition_types': plan(None).types})
    t = cfg({'reset': 0, 'start': 0})                      # zero counts = the legacy cell
    assert '\n'.join(R.rtl_lines(t)) == base
    assert not PH.uses_hb({'partition_types': plan({'reset': 0, 'start': 0}).types})


def test_reset_emits_pad_cell_zero_cycles():
    t = cfg({'reset': 1, 'start': 1})
    t0 = cfg(None)
    assert R.release_clocks(t) == R.release_clocks(t0) and R.entry_stages(t) == R.entry_stages(t0)
    assert t['pin_entry_added_flops'] == t0['pin_entry_added_flops']
    text = '\n'.join(R.rtl_lines(t))
    assert 'ot_dp_rrelay_ph_hb #(.N(1)) u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n), .ph(strap_rst_ph));' in text
    assert 'ot_dp_rrelay_ph_hb #(.N(1)) u_run_in (' in text
    assert R.summary(t)['pin_entry_hb4'] == dict(cell='HB4xp67_ASAP7_75t_R', reset=1, start=1, added_flops=0, added_whole_cycles=0)
    only_reset = '\n'.join(R.rtl_lines(cfg({'reset': 2})))
    assert '.N(2)) u_rst_in' in only_reset and 'ot_dp_rrelay_ph u_run_in' in only_reset
    assert G.uses_hold_hb4({'partition_types': plan({'reset': 1}).types})


@pytest.mark.parametrize('bad,match', [
    ({}, 'pin_entry_hb4'), ({'reset': True}, 'pin_entry_hb4'), ({'reset': 9}, 'pin_entry_hb4'),
    ({'reset': -1}, 'pin_entry_hb4'), ({'rst': 1}, 'pin_entry_hb4'), ([1], 'pin_entry_hb4')])
def test_reset_refusals(bad, match):
    with pytest.raises(R.ResetError, match=match):
        cfg(bad)


def test_reset_needs_phase_and_start():
    with pytest.raises(R.ResetError, match='needs reset.pin_entry_phase'):
        R._type_pin_entry_phase(plan({'reset': 1}, flag=False), 't', tree())
    t = tree(); t['start'] = False
    with pytest.raises(R.ResetError, match='START needs'):
        cfg({'start': 1}, t)


BENCH = r'''
`timescale 1ps/1fs
module tb;
 reg clk=0,r=0,s=0,ph=0; wire qr,qs,mr,ms; integer n=0,errors=0,mutants=0;
 always #5 clk=~clk;
 ref_ph a(clk,ph,r,qr); hb_ph b(clk,ph,r,qr2);  wrong_ph w(clk,ph,r,mr);
 wire qr2;
 always @(negedge clk) begin n=n+1; r<=(n%5<2); if (n==40) ph<=1; end
 always @(posedge clk) begin #0.01; if (n>3 && qr!==qr2) errors=errors+1; if (n>3 && qr!==mr) mutants=mutants+1;
   if (n==120) begin $display("RESULT errors%0d mutants%0d",errors,mutants); if (errors || !mutants) $fatal(1,"x"); $finish; end end
endmodule
module HB4xp67_ASAP7_75t_R(input A, output Y); assign Y=A; initial $display("TECH_CELL"); endmodule
'''


def test_cell_identity_both_phases_and_wrong_polarity(tmp_path):
    if not shutil.which('iverilog'):
        pytest.skip('iverilog required')
    ref = PH.CELL_RTL.replace('module ot_dp_rrelay_ph ', 'module ref_ph ')
    hb = PH.CELL_RTL_HB.replace('ot_dp_rrelay_ph_hb #(parameter integer N = 1)', 'hb_ph #(parameter integer N = 2)')
    wrong = PH.CELL_RTL.replace('module ot_dp_rrelay_ph ', 'module wrong_ph ').replace('cap_r <= d', 'cap_r <= ~d')
    inst = 'hb_ph b(clk,ph,r,qr2);'
    for synth in (False, True):
        f = tmp_path / f'b{int(synth)}.sv'
        f.write_text(ref + hb + wrong + G.HOLD_CELLS + BENCH)
        c = subprocess.run(['iverilog', '-g2012', '-s', 'tb', '-o', str(tmp_path / 'sim')] + (['-DSYNTHESIS'] if synth else []) + [str(f)],
                           capture_output=True, text=True)
        assert c.returncode == 0, c.stderr
        p = subprocess.run(['vvp', str(tmp_path / 'sim')], capture_output=True, text=True)
        assert p.returncode == 0 and 'RESULT errors0 mutants' in p.stdout, p.stdout + p.stderr
        assert p.stdout.count('TECH_CELL') == (2 if synth else 0)        # N=2 HB4 in the SYNTHESIS form


def test_ctl_helper_default_and_refusals():
    p = {'partition_types': {'t': {'clock': {}}, 'u': {'clock': {'landing_ctl_hold_hb4': {'d_i': 3}}}}}
    assert CL.ctl_hold_hb4(p, 't', 'd_i') == 0 and CL.ctl_hold_hb4(p, 'u', 'd_i') == 3
    assert CL.ctl_hold_hb4(p, 'u', 'other_i') == 0 and CL.ctl_hold_hb4(p, 'u__s1', 'd_i') == 3
    assert G.uses_hold_hb4(p) and not G.uses_hold_hb4({'partition_types': {'t': {'clock': {}}}})
    for bad in ({}, {'d_i': 0}, {'d_i': 9}, {'d_i': True}, {'d i': 1}, [1]):
        q = copy.deepcopy(p); q['partition_types']['u']['clock']['landing_ctl_hold_hb4'] = bad
        with pytest.raises(CL.LandingError):
            CL.ctl_hold_hb4(q, 'u', 'd_i')


def test_dont_touch_tcl_counts_pad_cells():
    P = SimpleNamespace(raw={}, types={'k': dict(buses=[], ft_slots=[], clock={'landing_ctl_hold_hb4': {'d_i': 3}}, reset={}),
                               'h': dict(buses=[], ft_slots=[], clock={}, reset={'pin_entry_hb4': {'reset': 1, 'start': 1}}),
                               'z': dict(buses=[], ft_slots=[], clock={}, reset={})})
    for tn, lohi in (('k', (9, 12)), ('h', (2, 4))):
        tcl = gen_phys.hold_pad_dont_touch_tcl(P, tn)
        assert 'u_hdly_' in tcl and f'plan {lohi[0]}..{lohi[1]}' in tcl, tcl
    assert gen_phys.hold_pad_dont_touch_tcl(P, 'z') == ''


def test_raw_hold_is_default_off_and_exact_type_scoped():
    t = "hd_spn_wshim_rx"
    flag = "landing_raw_data_hold_hb4"
    types = {t: {"clock": {}}}
    raw = {"partition_types": types}
    assert CL.raw_landing_hold_hb4(raw, t) == 0
    assert not G.uses_hold_hb4(raw)
    types[t]["clock"][flag] = 2
    assert CL.raw_landing_hold_hb4(raw, t) == 2
    assert CL.raw_landing_hold_hb4(raw, t + "__one") == 2
    assert G.uses_hold_hb4(raw)
    for value in (None, False, 0, 1, 3, "2"):
        types[t]["clock"][flag] = value
        with pytest.raises(CL.LandingError, match="two pads"):
            CL.raw_landing_hold_hb4(raw, t)
    other = {"partition_types": {"hd_spn_eshim_rx": {"clock": {flag: 2}}}}
    with pytest.raises(CL.LandingError, match="exact hd_spn_wshim_rx"):
        CL.raw_landing_hold_hb4(other, "hd_spn_eshim_rx")


def test_raw_hold_exact_native_quantity_and_existing_control(tmp_path):
    t = "hd_spn_wshim_rx"
    types = {t: dict(clock={"landing_raw_data_hold_hb4": 2, "landing_ctl_hold_hb4": {"link_i": 2}}, reset={})}
    p = SimpleNamespace(types=types, raw={})
    (tmp_path / "rtl").mkdir()
    f = tmp_path / "rtl" / "rx.sv"
    ctl = "ot_dp_hd #(.W(2), .N(2)) u_hdly_cland_ctl_link_i (.a(c), .y(cd));\n"
    start = "ot_dp_hd #(.W(1), .N(2)) u_hdly_cland_fs_link_i (.a(s), .y(sd));\n"
    f.write_text(ctl + start)
    with pytest.raises(ValueError, match="raw landing data pads absent"):
        gen_phys.hold_pad_dont_touch_tcl(p, t, tmp_path)
    f.write_text(ctl + start + "ot_dp_hd #(.W(566), .N(2)) u_hdly_cland_data_link_i (.a(link_i), .y(raw_hd));\n")
    tcl = gen_phys.hold_pad_dont_touch_tcl(p, t, tmp_path)
    assert "plan 1138..1138" in tcl
    assert "u_hdly_cland_data_link_i" in tcl and "$raw_hb != 1132" in tcl
