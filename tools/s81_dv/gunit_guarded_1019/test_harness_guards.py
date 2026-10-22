"""Bounded receipt-preservation checks; never invoke a simulator."""
import importlib.util
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent


def test_import_has_no_execution(tmp_path, capsys):
    # No manifest, vectors, output directory or binary exists in this copy.
    shutil.copyfile(HERE/'selector.py', tmp_path/'selector.py')
    for name, source in [('selection', HERE/'test_selection.py'),
                         ('cases', HERE/'hop/run_cases.py')]:
        target = tmp_path/(name+'.py')
        shutil.copyfile(source, target)
        before = {p.relative_to(tmp_path) for p in tmp_path.rglob('*')}
        spec = importlib.util.spec_from_file_location('guarded_import_'+name, target)
        module = importlib.util.module_from_spec(spec)
        # Suppress Python bytecode writes so any other write is visible.
        import sys
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous
        assert {p.relative_to(tmp_path) for p in tmp_path.rglob('*')} == before
    assert capsys.readouterr().out == ''


def test_shell_existing_output_preserved(tmp_path):
    for relative, output in [('run.sh', 'out'), ('hop/run.sh', 'out_hop')]:
        root = tmp_path/output
        script = root/'tools/s81_dv/gunit_guarded_1019'/relative
        script.parent.mkdir(parents=True)
        shutil.copyfile(HERE/relative, script)
        directory = root/output
        directory.mkdir()
        receipt = directory/'build.log'
        receipt.write_bytes(b'FAILED original receipt\n')
        result = subprocess.run(['bash', str(script)], capture_output=True, text=True)
        assert result.returncode == 2
        assert 'GUARDED_OUTPUT_EXISTS' in result.stderr
        assert receipt.read_bytes() == b'FAILED original receipt\n'
        assert list(directory.iterdir()) == [receipt]


def test_standalone_case_targets_preserved(tmp_path):
    names = ('positive', 'old_main_age', 'wrong_age_plus1')
    targets = ['results.json', 'kit_sorted']
    for name in names:
        targets.extend((name, name+'.argv.json', name+'.log'))
    # Each independent target must refuse before attempting any source/binary read.
    for index, target in enumerate(targets):
        root = tmp_path/str(index)
        output = root/'out_hop'
        output.mkdir(parents=True)
        receipt = output/target
        receipt.write_bytes(b'FAILED original receipt\n')
        result = subprocess.run(['python3', str(HERE/'hop/run_cases.py'), str(root), '--sorted'],
                                capture_output=True, text=True)
        assert result.returncode != 0
        assert 'GUARDED_OUTPUT_EXISTS' in result.stderr
        assert receipt.read_bytes() == b'FAILED original receipt\n'
        assert list(output.iterdir()) == [receipt]
