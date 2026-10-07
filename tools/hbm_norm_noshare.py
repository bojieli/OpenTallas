#!/usr/bin/env python3
"""Prepare an independent full-shape MEM1 synthesis fallback; never launch a job.

The input is the generated synth.ys from the pinned cc383b8fc full-shape run.
Only SAT resource sharing is disabled. Existing source and runs stay immutable.
Run emitted scripts only after admission against measured host headroom.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex

PIN = 'cc383b8fcb76d8e8bd05436dc00f409335838f2e'
TOP = 'ot_hbm_norm_engine_view'


def model():
    from uarch_model import hbm_norm_engine_mem1_model
    base = hbm_norm_engine_mem1_model()
    return dict(schema='opentallas.uarch.hbm_norm_noshare.v1',
        source_pin=PIN, adopted=False, default_enabled=False,
        change='Disable synthesis SAT resource sharing; identical full-shape MEM1 RTL',
        base_model=base,
        delta=dict(cycles=0, ports=0, logical_storage_bits=0,
                   arithmetic_operations=0, engine_replicas=0,
                   mapped_area=None, mapped_clock_sinks=None),
        composed_engine_cycles=323,
        area_policy='No assumed area benefit; measure complete mapped area and refit slot before physical admission',
        synthesis_policy='Preserve all existing progressing jobs; independent no-SHARE output directory',
        qualification=dict(source_exact=True, mapped_equivalence=False,
                           SS_setup=False, FF_hold=False, DRC0=False),
        remaining=['Run full-shape synthesis under admission',
                   'Run emitted mapped-equivalence script with functional cell and SRAM models',
                   'Reset/full-shape golden simulation plus negative controls',
                   'Measured macro inventory, area, clock sinks, timing and context closure'])


def prepare(original, out):
    anchor = f'synth -top {TOP} -flatten'
    if original.splitlines().count(anchor) != 1:
        raise ValueError('Expected exactly one unchanged full-shape host synthesis command')
    lines = original.splitlines()
    mapped = next((line.split()[-1] for line in lines if line.startswith('write_verilog -noattr ')), None)
    stat = next((line.split()[2] for line in lines if line.startswith('tee -o ') and ' stat' in line), None)
    if not mapped or not stat:
        raise ValueError('Missing expected mapped-netlist/stat output anchors')
    # Paths in Yosys scripts are not shell syntax. Reject whitespace or command
    # delimiters rather than inventing quoting rules for this narrow runner.
    for path in (str(out), mapped, stat):
        if any(c.isspace() or c in ';"\\' for c in path):
            raise ValueError('Unsupported Yosys path characters')
    return original.replace(anchor, anchor + ' -noshare').replace(mapped, str(out / 'mapped.raw.v')).replace(stat, str(out / 'stat.txt'))


def proof_script(original, out):
    """Proof deliberately fails closed on unsupported primitives or unmatched state.

    Libraries must contain functional models, not black boxes. Matching SRAM
    blackboxes are not accepted as proof of storage behavior. Provide simulation
    SRAM models in mapped_models.ys. Reset simulation remains a separate gate:
    equiv_induct proves convergence-conditioned sequential equivalence.
    """
    reads = [x for x in original.splitlines() if x.startswith('read_verilog ')]
    return '\n'.join(reads + [
        f'hierarchy -check -top {TOP}', 'proc', 'memory', 'flatten',
        'select -assert-none A:blackbox', 'select -clear',
        f'rename {TOP} gold', 'design -stash gold',
        '# User-supplied read_liberty/read_verilog commands for FUNCTIONAL cell/SRAM models.',
        f'script {out}/mapped_models.ys',
        f'read_verilog {out}/mapped.raw.v', f'hierarchy -check -top {TOP}',
        'proc', 'memory', 'flatten', 'select -assert-none A:blackbox', 'select -clear',
        f'rename {TOP} gate', 'design -copy-from gold gold',
        'equiv_make gold gate equiv', 'hierarchy -top equiv',
        'equiv_simple', 'equiv_induct -seq 8', 'equiv_status -assert', ''])


def validate_sources(root, script=None):
    manifest = Path(__file__).resolve().parents[1] / 'results/uarch/hbm_norm_noshare_20261007/source_manifest.json'
    records = json.loads(manifest.read_text())
    if records['source_pin'] != PIN:
        raise ValueError('Unexpected source manifest pin')
    for rel, entry in records['files'].items():
        if hashlib.sha256((root / rel).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Source pin mismatch: ' + rel)
    if script is not None:
        for line in script.splitlines():
            if line.startswith('read_verilog '):
                fields = line.split()
                if len(fields) != 3 or fields[1] != '-sv':
                    raise ValueError('Unsupported generated read_verilog command')
                rel = str(Path(fields[2]).resolve().relative_to(root.resolve()))
                if rel not in records['files']:
                    raise ValueError('Unpinned input RTL: ' + rel)
    return len(records['files'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model-out', type=Path)
    ap.add_argument('--input-script', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--source-root', type=Path)
    args = ap.parse_args()
    if args.model_out:
        args.model_out.write_text(json.dumps(model(), indent=2) + '\n')
    if args.input_script:
        if args.out is None or args.out.exists():
            ap.error('--out must name a new private directory')
        if args.source_root is None:
            ap.error('--source-root is required to validate all 30 pinned files')
        original = args.input_script.read_text()
        validate_sources(args.source_root, original)
        patched = prepare(original, args.out)
        proof = proof_script(original, args.out)
        args.out.mkdir(parents=True)
        (args.out / 'synth_noshare.ys').write_text(patched)
        (args.out / 'mapped_equivalence.ys').write_text(proof)
        (args.out / 'mapped_models.ys').write_text('# Supply functional standard-cell and SRAM models. This fails closed until then.\n')
        record = model()
        record.update(input_script_sha256=hashlib.sha256(original.encode()).hexdigest(),
                      output_script_sha256=hashlib.sha256(patched.encode()).hexdigest(),
                      launch_ready=False, blocked_by='Measured admission, pinned input manifest and functional mapped models required')
        (args.out / 'recipe.json').write_text(json.dumps(record, indent=2) + '\n')
        print('After admission, using the source run\'s pinned Yosys executable:')
        for name in ('synth_noshare', 'mapped_equivalence'):
            print('"$PINNED_YOSYS" -l ' + shlex.quote(str(args.out / (name + '.log'))) + ' -s ' + shlex.quote(str(args.out / (name + '.ys'))))
    elif not args.model_out:
        ap.error('Specify --model-out and/or --input-script with --out')


if __name__ == '__main__':
    main()
