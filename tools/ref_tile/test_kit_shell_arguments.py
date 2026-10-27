"""Load real generated kits in Bash; retain exact physical-flow arguments."""
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ref_tile as RT
import pre_route_gate as G


def test_generated_extra_keeps_regex_defines_and_pdn_as_separate_arguments(tmp_path):
    marker = tmp_path / 'must_not_execute'
    regex = r'^(xv|xd|e_v)\[[0-9]+\]$'
    literal = '$(touch${IFS}' + str(marker) + ')'
    spec = dict(name='shell_case', top='top', kind='tile', sources=[], params={},
                pins={'S': ['a'], 'N': ['b']}, clock_port='ck', clock='cts',
                inter=[], route={}, defines=['A=1', 'B=2'], reset_ports=[],
                orfs_vars={'OT_OFLOP_PORT_RE': regex, 'OT_LITERAL': literal})
    env = RT.gen_env(spec, 'physical/ref_tile/shell_case', 21.6, 21.6,
                     {'rlayers': ['M2', 'M5'], 'pg_layer': 'M5'}, [])
    kit = tmp_path / 'kit.env'
    kit.write_text(env)
    subprocess.run(['bash', '-n', str(kit)], check=True)
    run = subprocess.run(['bash', '-c', 'source "$1"; printf "%s\\0" "${EXTRA[@]}"',
                          'test', str(kit)], capture_output=True, check=True)
    args = run.stdout.decode().rstrip('\0').split('\0')
    assert len(args) % 2 == 0
    pairs = list(zip(args[::2], args[1::2]))
    assert ('--orfs-var', 'OT_OFLOP_PORT_RE=' + regex) in pairs
    assert ('--orfs-var', 'VERILOG_DEFINES=-DSYNTHESIS -DA=1 -DB=2') in pairs
    assert ('--orfs-var', 'PDN_TCL=/src/physical/ref_tile/shell_case/pdn.tcl') in pairs
    assert ('--orfs-var', 'OT_LITERAL=' + literal) in pairs
    assert not marker.exists()
    gate = G.Gate()
    assert G.check_kit_shell(gate, tmp_path)


def test_route_stops_before_physical_tool_on_invalid_kit(tmp_path):
    kit = tmp_path / 'broken.env'
    # The trailing assignment makes even `source` return 0 after the array error.
    kit.write_text('TOP=top\nEXTRA=(--orfs-var OT_OFLOP_PORT_RE=^(xv|xd))\nFOO=1\n')
    (tmp_path / 'kit.env').write_bytes(kit.read_bytes())
    gate = G.Gate()
    assert not G.check_kit_shell(gate, tmp_path)
    assert any(item['check'] == 'kit_shell' and item['severity'] == 'FAIL' for item in gate.items)
    # The physical runner is intentionally absent: reaching it would be a bug.
    run = subprocess.run(['bash', str(Path(RT.__file__).with_name('ref_route.sh')),
                          str(kit), 'broken', str(tmp_path / 'out')],
                         env={'PATH': '/usr/bin:/bin', 'SRC': str(tmp_path)},
                         capture_output=True, text=True)
    assert run.returncode == 2
    assert 'invalid kit shell syntax' in run.stderr
    assert not (tmp_path / 'out/broken/flow.log').exists()


def test_route_rejects_valid_shell_kit_that_fails_to_load(tmp_path):
    kit = tmp_path / 'bad_load.env'
    kit.write_text('TOP=top\nreturn 9\n')
    run = subprocess.run(['bash', str(Path(RT.__file__).with_name('ref_route.sh')),
                          str(kit), 'broken', str(tmp_path / 'out')],
                         env={'PATH': '/usr/bin:/bin', 'SRC': str(tmp_path)},
                         capture_output=True, text=True)
    assert run.returncode == 2
    assert 'could not load kit' in run.stderr
    assert not (tmp_path / 'out/broken/flow.log').exists()


def test_physical_failure_still_records_status(tmp_path):
    kit = tmp_path / 'kit.env'
    kit.write_text("TOP=top\nSRCS=''\nPARAMS=()\nPINS=()\nEXTRA=()\nMACROS=()\n"
                   "KIT=/src/test\nFW=21.6\nFH=21.6\nRLAYERS='M2 M5'\n"
                   "CLKPORT=ck\nPIN_H=M5\nPIN_V=M4\nREFGLOB='*'\nINTER=none_\n")
    (tmp_path / 'tools').mkdir()
    (tmp_path / 'tools/run_abi3_physical.py').write_text('raise SystemExit(7)\n')
    run = subprocess.run(['bash', str(Path(RT.__file__).with_name('ref_route.sh')),
                          str(kit), 'failed', str(tmp_path / 'out'), 'cts'],
                         env={'PATH': '/usr/bin:/bin', 'SRC': str(tmp_path)},
                         capture_output=True, text=True)
    assert run.returncode == 7
    assert (tmp_path / 'out/failed/status').read_text() == 'flow_rc=7\n'
