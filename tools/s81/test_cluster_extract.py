"""Flattened-vs-hierarchical sequential equivalence and boundary rejection tests."""
import copy
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from cluster_extract import cmd_extract, extract_columns, parse_die_v, transport_audit


def fixture(tmp_path):
    source = tmp_path / 'flat.v'
    source.write_text('''module flat (ck, d, y);
input ck;
input [3:0] d;
output [3:0] y;
wire [3:0] mid;
leaf cf0 (.ck(ck), .i(d), .salt(1'b0), .o(mid));
leaf cf1 (.ck(ck), .i(mid), .salt(1'b0), .o(y));
endmodule
''')
    lef = tmp_path / 'pins.lef'
    rows = ['MACRO leaf']
    for name, direction in [('ck', 'INPUT'), ('salt', 'INPUT')] + [
            (f'{p}[{k}]', direction) for p, direction in [('i', 'INPUT'), ('o', 'OUTPUT')] for k in range(4)]:
        rows += [f'PIN {name}', f'DIRECTION {direction} ;', f'END {name}']
    rows.append('END leaf')
    lef.write_text('\n'.join(rows))
    plan = dict(die=[100, 100], insts=[
        ['cf0', 'leaf', 0, 0, 10, 10, 'R0', 'cfifo', 'frame_0'],
        ['cf1', 'leaf', 20, 0, 10, 10, 'R0', 'cfifo', 'frame_1']],
        frames={'0': dict(x=0, y=0, h=10, elems=[]), '1': dict(x=20, y=0, h=10, elems=[])})
    path = tmp_path / 'plan.json'
    path.write_text(json.dumps(plan))
    return source, lef, plan, path


def test_cycle_exact_and_data_mutant(tmp_path):
    source, lef, plan, path = fixture(tmp_path)
    out = tmp_path / 'out'
    cmd_extract(SimpleNamespace(plan=str(path), die_v=str(source), lef=[str(lef)], out=str(out)))
    hier = out / 'die_hier.v'
    hier.write_text(hier.read_text().replace('module flat ', 'module hier '))
    models = tmp_path / 'models.sv'
    models.write_text('''module leaf(input ck, input [3:0] i, input salt, output reg [3:0] o);
always @(posedge ck) o <= i + salt + 1;
endmodule
module tb;
reg ck=0; always #5 ck=~ck;
reg [3:0] d=0; wire [3:0] a,b;
flat f(ck,d,a); hier h(ck,d,b);
integer k;
initial begin
 for(k=0;k<40;k=k+1) begin
  @(negedge ck); d=(k*7+3)%16;
  if(k>2 && a!==b) $fatal(1,"hierarchy mismatch");
 end
 $display("EXACT_PASS"); $finish;
end
endmodule
''')
    def simulate():
        subprocess.run(['iverilog', '-g2012', '-s', 'tb', '-o', str(tmp_path/'sim'), str(source), str(hier), str(models)], check=True, capture_output=True)
        return subprocess.run(['vvp', str(tmp_path/'sim')], capture_output=True, text=True)
    result = simulate()
    assert result.returncode == 0 and 'EXACT_PASS' in result.stdout
    receipt = json.loads((out/'clusters.json').read_text())
    assert len(receipt['clusters']) == 1  # actual reusable master, two roots
    text = hier.read_text()
    assert '.salt(1\'b0)' in text
    hier.write_text(text.replace('.salt(1\'b0)', '.salt(1\'b1)'))
    assert simulate().returncode != 0


def test_constant_and_missing_clock_mutants_refused(tmp_path):
    from cluster_extract import lef_directions
    source, lef, plan, path = fixture(tmp_path)
    dv = parse_die_v(source)
    directions = lef_directions([lef])
    dv['insts']['cf1'][1]['salt'] = "1'b1"
    with pytest.raises(AssertionError, match='constant mismatch'):
        extract_columns(plan, dv, directions)
    dv = parse_die_v(source)
    directions.pop(('leaf', 'ck'))
    with pytest.raises(AssertionError, match='missing LEF pin direction'):
        extract_columns(plan, dv, directions)


def test_street_transport_cannot_hide_in_cluster(tmp_path):
    _, _, plan, _ = fixture(tmp_path)
    plan['insts'].append(['cx0', 'relay', 8, 2, 3, 3, 'R0', 'relay', 'trunk'])
    report = transport_audit(plan)
    assert report['status'] == 'FAIL'
    assert report['collisions'][0]['instance'] == 'cx0'
    plan['insts'][-1][2] = 12
    assert transport_audit(plan)['status'] == 'HOMES_CLEAR_ONLY'
