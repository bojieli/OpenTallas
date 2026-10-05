#!/usr/bin/env python3
"""PSM EM on a completed IR window; never generate a floorplan, PDN or load.

Run remotely through the existing host admission guard. Threshold qualification
is separate from successful PSM execution: ASAP7 has no published EM rule.
"""
import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

INPUTS = ('run.tcl', 'top.def', 'loads.lef', 'vsrc_VDD.loc',
          'vsrc_VSS.loc', 'manifest.json')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def prepare(source, output, authority):
    """Copy completed raster IR inputs; change only the EM command arguments."""
    source = source.resolve()
    meta = json.loads((source / 'manifest.json').read_text())
    if not meta.get('peak') or meta.get('scale', 1.0) != 1.0:
        raise ValueError('requires original peak in-phase IR power, without scaling')
    if meta.get('case') != 'c':
        raise ValueError('requires selected raster case c, not macro-current control')
    if (source / 'run.log.exit').read_text().strip() != '0':
        raise ValueError('source IR case is not completed successfully')
    pins = {n: sha(source / n) for n in INPUTS}
    original = (source / 'run.tcl').read_text()
    if '-enable_em' in original:
        raise ValueError('existing EM input: reuse its result instead')
    # This recipe reads an already generated PDN DEF. No route/pdngen command
    # may slip into an EM-only job.
    if re.search(r'(?m)^\s*(global_route|detailed_route|pdngen)\b', original):
        raise ValueError('not an analysis-only completed window')
    pattern = r'analyze_power_grid[^\n}]*'
    commands = re.findall(pattern, original)
    if len(commands) != 1 or '-vsrc /work/vsrc_$net.loc' not in commands[0]:
        raise ValueError('unexpected rail/source command; requires explicit recipe')
    if 'foreach net {VDD VSS}' not in original:
        raise ValueError('both rails must be analyzed')
    old_command = commands[0]
    new_command = old_command + ' -enable_em -em_outfile /work/em_$net.csv'
    transformed = original.replace(old_command, new_command)
    assert transformed.replace(new_command, old_command) == original
    output.mkdir(parents=True, exist_ok=False)
    for n in INPUTS:
        shutil.copyfile(source / n, output / n)
    (output / 'source_run.tcl').write_text(original)
    (output / 'run.tcl').write_text(transformed)
    loads = [float(x) for x in re.findall(
        r'(?m)^set_pdnsim_inst_power -inst \S+ -power ([\d.eE+-]+)', original)]
    total = math.fsum(loads)
    if not loads or abs(total - meta['power_w']) > 0.001:
        raise ValueError('explicit instance power does not match original manifest')
    if pins != {n: sha(source / n) for n in INPUTS}:
        raise ValueError('source changed during copy')
    receipt = dict(schema='opentallas.die_window_em.input.v1', source=str(source),
        current_authority=authority, source_sha256=pins,
        prepared_sha256={n: sha(output / n) for n in INPUTS},
        rails=['VDD', 'VSS'], power_w_from_original_commands=total,
        original_manifest=meta, delta='only -enable_em and -em_outfile',
        PDN_changed=False, load_or_supply_changed=False,
        current_recovery_die_qualified=False, added_token_cycles=0,
        new_hardware_area_mm2=0, new_MACs=0, new_memory_ports=0,
        em_rule_authority=None, foundry_violation_count=None)
    save(output / 'input.json', receipt)
    return receipt


def currents(path, widths):
    layers = {}
    with path.open(newline='') as f:
        for row in csv.reader(f):
            if not row or row[0].startswith('Node0'):
                continue
            if len(row) < 7:
                raise ValueError('unrecognized PSM EM row')
            a, b = row[0], row[3]
            current = abs(float(row[6]))
            if not math.isfinite(current):
                raise ValueError('nonfinite EM current')
            key = a if a == b else a + '-' + b
            stat = layers.setdefault(key, dict(segments=0, max_current_a=0.0))
            stat['segments'] += 1
            if current >= stat['max_current_a']:
                stat.update(max_current_a=current, location=row[:6])
            if a == b and a in widths:
                stat['width_um_from_original_manifest'] = widths[a]
                stat['max_ma_per_um'] = stat['max_current_a'] * 1000 / widths[a]
    if not layers:
        raise ValueError('empty EM report is not qualification')
    return layers


def summarize(work, exit_code):
    receipt = json.loads((work / 'input.json').read_text())
    meta = receipt['original_manifest']
    # Selected raster windows expose only M8/M9 wires and their common width.
    # Do not reuse the reduced-block signoff tool's unrelated 0.8um default.
    width = meta['stripes']['width_um']
    widths = {'M8': width, 'M9': width}
    log = (work / 'run.log').read_text()
    rails = {}
    for net in receipt['rails']:
        path = work / ('em_' + net + '.csv')
        ok = (exit_code == 0 and 'OT_IR net=' + net + ' status=PASS' in log
              and 'OT_PSM net=' + net + ' status=PASS' in log and path.exists())
        rails[net] = dict(analysis_completed=ok)
        if ok:
            stats = currents(path, widths)
            rails[net].update(per_layer=stats, report_sha256=sha(path),
                segments_above_existing_assumed_limit=None)
            # Maxima are a screening comparison only, not a foundry rule.
            rails[net]['layers_above_existing_assumed_1ma_per_um'] = [
                k for k, s in stats.items() if s.get('max_ma_per_um', 0) > 1.0]
    result = dict(schema='opentallas.die_window_em.actual.v1', exit_code=exit_code,
        rails=rails, analysis_completed=all(x['analysis_completed'] for x in rails.values()),
        authority=receipt['current_authority'], power_w=receipt['power_w_from_original_commands'],
        input_receipt_sha256=sha(work / 'input.json'),
        log_sha256=sha(work / 'run.log'),
        foundry_violation_count=None, em_rule_authority=None,
        qualification='MEASURED_PSM_CURRENTS_ONLY_EM_LIMIT_NOT_AVAILABLE',
        current_recovery_die_qualified=False, PDN_changed=False,
        assumed_screen_basis='existing tools/signoff_analysis.py uses assumed1mA/um; ASAP7 publishes no EM limit')
    save(work / 'result.json', result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['prepare', 'run', 'summarize'])
    p.add_argument('--source', type=Path)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--authority', default='')
    p.add_argument('--image', default='openroad/orfs:asap7lock')
    p.add_argument('--threads', type=int, default=8)
    p.add_argument('--exit-code', type=int, default=0)
    a = p.parse_args()
    if a.mode == 'prepare':
        prepare(a.source, a.work, a.authority)
    elif a.mode == 'run':
        receipt = json.loads((a.work / 'input.json').read_text())
        if receipt['prepared_sha256'] != {n: sha(a.work / n) for n in INPUTS}:
            raise ValueError('prepared inputs changed')
        cmd = ['docker', 'run', '--rm', '--name', a.work.name + '-rawls-em',
               '-v', str(a.work.resolve()) + ':/work', '-w', '/work', a.image,
               'openroad', '-no_init', '-exit', '-threads', str(a.threads), '/work/run.tcl']
        save(a.work / 'command.json', dict(argv=cmd, timeout_seconds=None,
            image_inspect=subprocess.check_output(['docker', 'image', 'inspect', a.image], text=True)))
        with (a.work / 'run.log').open('w') as f:
            rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)
        (a.work / 'exit.txt').write_text(str(rc) + '\n')
        result = summarize(a.work, rc)
        print(json.dumps(result))
        if not result['analysis_completed']:
            raise SystemExit(rc or 1)
    else:
        print(json.dumps(summarize(a.work, a.exit_code)))


if __name__ == '__main__':
    main()
