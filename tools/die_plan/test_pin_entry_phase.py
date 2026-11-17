"""Strap-selected reset/START entry phase: opt-in identity, refusals, labels, and the counted frame over the
measured HEAD skew range against a wrong-strap control."""
from types import SimpleNamespace
import math, re, shutil, subprocess
import pytest
import gen_rtl as G
import pin_entry_phase as PH
import reset_tree as R
import schema as S


def tree():
    return dict(type='t', entry='relayed', sync_stages=2, root=[10, 10], start=True,
                relays=[dict(name='u_rrl_0', d='rst_root_n', q='rst_n_t0', xy=[12, 10], depth=1, tap=0, kind='tap')],
                taps=['clk'], own_depth=1, depth=1, n_tree=1, n_pad=0, max_hop_um=2, reach_um=405, outs=[],
                core_resets=[], relay_driver=False, start_in=[10, 12], start_role='mission', tap_roles={0: 'mission'},
                start_tap=None)


def plan(flag=True, straps=True):
    t = {'reset': {'pin_entry_phase': flag}}
    if straps:
        t['id_straps'] = [dict(name=PH.STRAP, width=1)]
    return SimpleNamespace(types={'t': t})


def configured(t=None, **kw):
    return R._type_pin_entry_phase(plan(**kw), 't', t or tree())


def wrapper(t, module):
    return ('module ' + module + '(input clk,rst_raw_n_in,p_start,strap_rst_ph,output rst_raw_n_out,start);\n' +
            '\n'.join(R.rtl_lines(t, src='rst_raw_n_in', start_src='p_start')) +
            '\nassign rst_raw_n_out=rst_root_n;assign start=run_root;endmodule\n')


def test_absent_or_off_is_identity():
    t = tree()
    assert R._type_pin_entry_phase(SimpleNamespace(types={'t': {'reset': {}}}), 't', t) is t
    assert configured(t, flag=False) is t
    assert not PH.uses({'partition_types': {'t': {'reset': {}}}})
    assert R.pin_entry_ports(t) == '' and R.entry_stages(t) == 1
    assert 'ot_dp_rrelay_ph' not in '\n'.join(R.rtl_lines(t))


def test_on_emits_strap_cell_and_two_nominal_stages():
    new = configured()
    assert R.entry_stages(new) == 2 and R.release_clocks(new) == R.release_clocks(tree()) + 1
    text = '\n'.join(R.rtl_lines(new))
    assert 'ot_dp_rrelay_ph u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n), .ph(strap_rst_ph));' in text
    assert re.search(r'ot_dp_rrelay_ph u_run_in \(.*\.q\(run_root\), \.ph\(strap_rst_ph\)\);', text)
    assert PH.uses({'partition_types': plan().types})
    assert R.summary(new)['pin_entry_phase']['delay_cells'] == 0


def test_refusals():
    with pytest.raises(R.ResetError, match='boolean'):
        configured(flag=1)
    with pytest.raises(R.ResetError, match='id_strap'):
        configured(straps=False)
    t = tree(); t['entry'] = 'sync'
    with pytest.raises(R.ResetError, match='synchronous relayed'):
        configured(t)
    for other in ('pin_entry_fall', 'pin_entry_delay', 'pin_root_copies'):
        t = tree(); t[other] = {'x': 1}
        with pytest.raises(R.ResetError, match='cannot combine'):
            configured(t)


def test_labels():
    #        h: (strap, release delta vs two-stage nominal, die STA setup multiplier)
    want = {-2: (0, 1, 2), -1: (1, 0, 2), 0: (0, 0, 1), 1: (1, -1, 1), 2: (0, -1, 0), 3: (1, -2, 0), 4: (0, -2, -1),
            5: (1, -3, -1)}
    for h, w in want.items():
        assert (PH.strap_value(h), PH.release_delta(h), PH.setup_multiplier(h)) == w


def test_plan_errors_and_strap_width():
    types = {'t': {'reset': {'pin_entry_phase': True}, 'id_straps': [dict(name=PH.STRAP, width=1)]}, 'u': {}}
    ok = dict(partition_types=types, partitions=[dict(name='a', type='t', reset_entry_phase=3, id_straps={PH.STRAP: 1}),
                                                 dict(name='b', type='t', id_straps={PH.STRAP: 0}),
                                                 dict(name='c', type='u')])
    assert PH.plan_errors(ok) == [] and S._id_strap_errors(ok) == []
    bad = dict(partition_types=types, partitions=[dict(name='a', type='t', reset_entry_phase=3, id_straps={PH.STRAP: 0}),
                                                  dict(name='c', type='u', reset_entry_phase=1)])
    errs = PH.plan_errors(bad)
    assert len(errs) == 2 and 'mod 2' in errs[0] and 'without type' in errs[1]


def test_sta_rows_select_and_mask():
    P = SimpleNamespace(types=plan().types, parts={'a': dict(type='t', reset_entry_phase=3),
                                                    'b': dict(type='t', reset_entry_phase=0)})
    rows = {(r['part'], r['entry']): r for r in PH.sta_rows(P)}
    a, b = rows[('a', 'u_rst_in')], rows[('b', 'u_run_in')]
    assert (a['capture'], a['false_path_to'], a['setup_multiplier']) == ('u_rst_in/cap_f', 'u_rst_in/cap_r', 0)
    assert (b['capture'], b['false_path_to'], b['setup_multiplier']) == ('u_run_in/cap_r', 'u_run_in/cap_f', 1)
    tcl = PH.sta_tcl_lines(PH.sta_rows(P))
    assert sum('set_multicycle_path 0 -setup' in x for x in tcl) == 2 and sum('set_false_path' in x for x in tcl) == 4
    assert 'OT_ENTRY_PHASE_MISS' in tcl[0] and tcl[-1] == 'puts "OT_ENTRY_PHASE rows 4"'


BENCH = r'''
`timescale 1ps/1fs
module tb;
 parameter real T=833.0, SKEW=0.0, DATA=209.0;
 parameter integer J=2, PHV=0, OFF=4;
 reg sc=0,rc=0,rs=0,ss=0;wire rw,sw,r,s,mr,ms;
 integer sn=-1,rn=-1-OFF,errors=0,mutants=0;
 function automatic ra(input integer n);ra=n>=0 && (n%5==0 || n%5==2 || n%5==3);endfunction
 function automatic sa(input integer n);sa=n>=0 && (n%7==0 || n%7==1 || n%7==4);endfunction
 // launch edge n at 8T + n*T; capture edge n at 8T + n*T + SKEW (SKEW > -4T): rn starts OFF edges early
 initial begin #(8*T) sc=1;forever #(T/2) sc=~sc;end
 initial begin #(8*T+SKEW-OFF*T) rc=1;forever #(T/2) rc=~rc;end
 always @(posedge sc)begin sn=sn+1;rs<=ra(sn);ss<=sa(sn);end
 assign #(DATA) rw=rs;assign #(DATA) sw=ss;
 wire ph=PHV[0];
 actual dut(rc,rw,sw,ph,r,s);actual wrong(rc,rw,sw,~ph,mr,ms);
 always @(posedge rc)begin
  rn=rn+1;#0.01;
  if(rn>=8)begin
   if(r!==ra(rn-J)||s!==sa(rn-J))errors=errors+1;
   if(mr!==ra(rn-J)||ms!==sa(rn-J))mutants=mutants+1;
  end
  if(rn==120)begin $display("RESULT errors%0d mutants%0d",errors,mutants);$finish;end
 end
endmodule
'''


def best_h(skew, data, T=833.0):
    """the label the plan model picks: max of min(setup, hold) at the declared edge."""
    return max(range(-8, 9), key=lambda h: min((T + skew - h * T / 2) - data, data - (skew - h * T / 2)))


def test_counted_frame_over_measured_skew_range(tmp_path):
    if not shutil.which('iverilog'):
        pytest.skip('iverilog required')
    (tmp_path / 'dut.sv').write_text(G.CELLS + PH.CELL_RTL + wrapper(configured(), 'actual') + BENCH)
    seen, mutants = set(), 0
    # r4 census range: capture - launch skew -906 .. +1725 ps, minimum data delay 99 .. 344 ps
    for skew in range(-906, 1726, 97):
        for data in (99.0, 209.0, 344.0):
            h = best_h(skew, data)
            margin = min((833 + skew - h * 416.5) - data, data - (skew - h * 416.5))
            assert margin >= 200, (skew, data, h, margin)
            seen.add(h)
            j = PH.NOMINAL_STAGES + PH.release_delta(h)
            cmd = ['iverilog', '-g2012', '-s', 'tb', '-o', str(tmp_path / 'sim')]
            cmd += [f'-Ptb.{k}={v}' for k, v in dict(SKEW=float(skew), DATA=data, J=j, PHV=PH.strap_value(h)).items()]
            c = subprocess.run(cmd + [str(tmp_path / 'dut.sv')], capture_output=True, text=True)
            assert c.returncode == 0, c.stderr
            run = subprocess.run(['vvp', str(tmp_path / 'sim')], capture_output=True, text=True)
            m = re.search(r'RESULT errors(\d+) mutants(\d+)', run.stdout)
            assert m, (run.stdout, run.stderr)
            assert int(m[1]) == 0, (skew, data, h, j, run.stdout)
            mutants += int(m[2])
    assert {-2, -1, 0, 1, 2, 3, 4} <= seen and mutants > 0
