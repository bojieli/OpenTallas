"""Forwarded clocks remain propagated networks, rather than register-D seam paths."""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_sta as D

CELLS = {'BUF': dict(pins={'A': 'input', 'Y': 'output'}, seq=False, clock=set())}


def fixture_parts(tmp_path):
    parts = {}
    for m, text, clock in (
        ('sender', '''module sender (clk, data, forwarded, fclk_data);
 input clk;
 input data;
 output forwarded;
 output fclk_data;
 BUF c0 (.A(clk), .Y(forwarded));
 BUF d0 (.A(data), .Y(fclk_data));
endmodule
''', 'clk'),
        ('receiver', '''module receiver (receiver_clock, fclk_named_data);
 input receiver_clock;
 input fclk_named_data;
 wire clock_leaf;
 BUF r0 (.A(receiver_clock), .Y(clock_leaf));
endmodule
''', 'receiver_clock'),
    ):
        p = tmp_path / m
        p.mkdir()
        (p / '6_final.v').write_text(text)
        (p / '6_final.sdc').write_text(f'create_clock -period 833 [get_ports {clock}]\n')
        parts[m] = p
    return parts


def seams():
    def seam(src, dst):
        return dict(net=f'n_{src}_{dst}', src='a', src_pin=src, dst='b', dst_pin=dst, dst_bus=dst)
    return [seam('forwarded', 'receiver_clock'), seam('forwarded', 'fclk_named_data'),
            seam('fclk_data', 'receiver_clock')]


def test_only_clock_with_both_explicit_and_library_witnesses_is_classified(tmp_path):
    parts = fixture_parts(tmp_path)
    data, clocks = D.classify_clock_transfers(seams(), parts, {'a': 'sender', 'b': 'receiver'}, CELLS)
    assert len(clocks) == 1 and clocks[0]['source_clock_input'] == 'clk'
    assert clocks[0]['source_buffer_chain'] == ['c0']
    # A data pin named fclk stays a data seam; an actual clock input driven by
    # ordinary data stays unproved and retains the existing fail-closed gate.
    assert {(s['src_pin'], s['dst_pin']) for s in data} == {
        ('forwarded', 'fclk_named_data'), ('fclk_data', 'receiver_clock')}
    assert 'false_path' not in '\n'.join(D.clock_transfer_tcl(clocks, 'pulse.rpt'))
    assert 'set_propagated_clock' not in '\n'.join(D.clock_transfer_tcl(clocks, 'pulse.rpt'))


def test_missing_declaration_or_unknown_cell_cannot_discard_data(tmp_path):
    parts = fixture_parts(tmp_path)
    (parts['sender'] / '6_final.sdc').unlink()
    data, clocks = D.classify_clock_transfers(seams(), parts, {'a': 'sender', 'b': 'receiver'}, CELLS)
    assert data == seams() and clocks == []
    (parts['sender'] / 'ilm.json').write_text(json.dumps({'clock_ports': ['clk']}))
    data, clocks = D.classify_clock_transfers(seams(), parts, {'a': 'sender', 'b': 'receiver'}, {})
    assert data == seams() and clocks == []
    _, clocks = D.classify_clock_transfers(seams(), parts, {'a': 'sender', 'b': 'receiver'}, CELLS)
    assert clocks[0]['source_clock_declaration'] == 'ilm.json:clock_ports'


def test_linked_clock_witness_fails_when_common_clock_is_missing(tmp_path):
    if not shutil.which('tclsh'):
        pytest.skip('no tclsh')
    transfer = dict(src='a', src_pin='forwarded', dst='b', dst_pin='receiver_clock')
    code = '\n'.join(D.clock_transfer_tcl([transfer], 'pulse.rpt'))
    prefix = r'''
set fh stdout
proc get_pins {args} {return [lindex $args end]}
proc get_full_name {p} {return $p}
proc report_check_types {args} {return {}}
'''
    for receiver_clock, expected in (('clk', 'PASS'), ('other', 'FAIL'), ('', 'FAIL')):
        body = prefix + '\nproc get_property {p prop} {if {$p eq "a/forwarded"} {return clk}; return {' + receiver_clock + '}}\n' + code
        r = subprocess.run(['tclsh'], input=body, text=True, capture_output=True)
        assert not r.stderr, r.stderr
        assert f'CLOCK_TRANSFER a->b/receiver_clock {expected}' in r.stdout
        assert 'CLOCK_PULSE_REPORT pulse.rpt' in r.stdout


def test_verdict_needs_linked_clock_witness_and_still_rejects_missing_data():
    seam = dict(max=dict(worst=10, neg=0), min=dict(worst=10, neg=0))
    corner = dict(exit=0, seams={'a->b/data': seam},
                  clock_endpoint_coverage=dict(status='NO_UNEXPANDED_CHILD_ETM', verdict='PASS'))
    res = dict(mode='flat', corners={'TT': copy.deepcopy(corner), 'FF': copy.deepcopy(corner)}, seam_groups=1,
               clock_transfers=[dict(src='a', src_pin='forwarded', dst='b', dst_pin='receiver_clock')])
    assert D.verdict(res)['status'].startswith('FAIL (clock transfer')
    for c in ('TT', 'FF'):
        res['corners'][c]['clock_transfers'] = {'a->b/receiver_clock': dict(status='PASS')}
    assert D.verdict(res)['status'] == 'PASS'
    res['corners']['FF']['seams']['a->b/data']['min'] = None
    assert D.verdict(res)['status'].startswith('FAIL')
