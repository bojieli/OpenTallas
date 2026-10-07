#!/usr/bin/env python3
"""Prepare an independent full-shape MEM1 synthesis fallback; never launch a job.

Production uses the pinned ORFS synth.tcl with SYNTH_ARGS=-noshare.
The optional host-script mode is a separately tested utility, not the live flow.
Only SAT resource sharing is disabled. Existing source and runs stay immutable.
Run emitted scripts only after admission against measured host headroom.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import re

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
        production_flow=dict(kind='ORFS container synth.tcl',
            change='Append -noshare to SYNTH_ARGS in a new private config.mk',
            input='Same immutable cc383b8fc source, constraints, image digest and synthesis Tcl',
            correction='The initial recipe inferred a host synth.ys; live inspection found ORFS Tcl instead',
            observation=dict(observer='fleet_live', process=4108792,
                SHARE_elapsed_minutes=103, RSS_GB=18.6,
                observation_is_peak=False),
            reservation=dict(GB=80, threads=16,
                basis='Retain original MEM1 admission reservation; 18.6 GB current RSS is not a peak',
                measured_headroom_required=True)),
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


def prepare_orfs(case, synth_tcl, out, source_root, image_id):
    """Copy production inputs only; leave the running case and RTL untouched."""
    validate_sources(source_root)
    if out.exists():
        raise ValueError('Output must be a new private directory')
    if not image_id.startswith('sha256:') or len(image_id) != 71:
        raise ValueError('Record the complete actual image digest, not a mutable tag')
    config = (case / 'config.mk').read_text()
    production = Path(__file__).resolve().parents[1] / 'results/uarch/hbm_norm_noshare_20261007/orfs_production_inputs.json'
    expected = json.loads(production.read_text())
    if image_id != expected['image_id']:
        raise ValueError('Image differs from the observed production image')
    inputs = set(re.findall(r'/src/([^\s]+)', config))
    if inputs != set(expected['source_inputs']):
        raise ValueError('ORFS source/library input inventory changed')
    for rel in inputs:
        if hashlib.sha256((source_root / rel).read_bytes()).hexdigest() != expected['source_inputs'][rel]:
            raise ValueError('ORFS source/library hash mismatch: ' + rel)
    for name, content in [('norm-orfs-config.mk', config.encode()),
                          ('norm-orfs-constraint.sdc', (case / 'constraint.sdc').read_bytes()),
                          ('norm-orfs-synth.tcl', synth_tcl.read_bytes())]:
        if hashlib.sha256(content).hexdigest() != expected['input_hashes'][name]:
            raise ValueError('Production input hash mismatch: ' + name)
    if TOP not in config or 'export SYNTH_HIERARCHICAL = 0' not in config:
        raise ValueError('Expected full-shape flat norm ORFS config')
    tcl = synth_tcl.read_text()
    for required in ('set synth_full_args [env_var_or_empty SYNTH_ARGS]',
                     'synth -flatten -run :fine {*}$synth_full_args',
                     'synth -top $::env(DESIGN_NAME) -run fine: -noabc {*}$synth_full_args'):
        if required not in tcl:
            raise ValueError('Production ORFS SYNTH_ARGS propagation changed: ' + required)
    if '-noshare' in config:
        raise ValueError('Input already disables SHARE; refusing a duplicate fallback')
    constraint = case / 'constraint.sdc'
    if not constraint.is_file():
        raise ValueError('Missing production constraint.sdc')
    patched = config.rstrip() + '\n\n# Independent full-shape no-SHARE fallback; original case remains live.\nexport SYNTH_ARGS += -noshare\n'
    out.mkdir(parents=True)
    (out / 'config.mk').write_text(patched)
    shutil.copy2(constraint, out / 'constraint.sdc')
    record = model()
    record.update(image_id=image_id, source_root=str(source_root), original_case=str(case),
        original_config_sha256=hashlib.sha256(config.encode()).hexdigest(),
        config_sha256=hashlib.sha256(patched.encode()).hexdigest(),
        constraints_sha256=hashlib.sha256(constraint.read_bytes()).hexdigest(),
        synth_tcl_sha256=hashlib.sha256(tcl.encode()).hexdigest(),
        preparation_complete=True, launched=False,
        mapping_gate='Functional standard-cell/SRAM models plus fail-closed mapped equivalence and reset simulation remain required')
    (out / 'recipe.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model-out', type=Path)
    ap.add_argument('--input-script', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--source-root', type=Path)
    ap.add_argument('--orfs-case', type=Path)
    ap.add_argument('--orfs-synth-tcl', type=Path)
    ap.add_argument('--image-id')
    args = ap.parse_args()
    if args.model_out:
        args.model_out.write_text(json.dumps(model(), indent=2) + '\n')
    if args.orfs_case:
        if not all((args.out, args.source_root, args.orfs_synth_tcl, args.image_id)):
            ap.error('ORFS mode requires --out --source-root --orfs-synth-tcl --image-id')
        if args.input_script:
            ap.error('Choose ORFS or host-script mode')
        prepare_orfs(args.orfs_case, args.orfs_synth_tcl, args.out, args.source_root, args.image_id)
        print('Private ORFS config ready; launch the same pinned container source mounts under admission.')
        print('Use the original 1_2_yosys.v make target with WORK_HOME=/work and the new directory mounted at /work.')
    elif args.input_script:
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
