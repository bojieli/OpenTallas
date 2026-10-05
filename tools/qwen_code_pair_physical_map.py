#!/usr/bin/env python3
"""Map the exact minimum CODE context for a pre-route cell/load price.

No placement or route runs here. Unplaced SS/FF timing is a logic-price input,
not contextual closure; Kant's clock/wire reserves and real macro LUTs remain
required. The mapped objects are retained for the one admitted physical flow.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TOP = 'ot_qwen_hbm_code_pair_context'
MACROS = ['ot_sram_1r1w_1024x256_m2_r2c2', 'ot_sram_1r1w_128x256_m1_r2c2']
FAMILIES = ['AO', 'INVBUF', 'OA', 'SEQ', 'SIMPLE']
SOURCES = ['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv', 'rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv'] + [
    f'physical/asap7_memory_macros/{m}/{m}_bb.v' for m in MACROS] + [
    'rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_payload_pair_banklocal.sv',
    'rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_read_pipeline.sv',
    'physical/qwen_code_pair/ot_qwen_hbm_code_pair_context.sv']


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(cmd, log):
    with log.open('w') as output:
        result = subprocess.run(cmd, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
    log.with_suffix('.exit').write_text(str(result.returncode) + '\n')
    if result.returncode:
        raise SystemExit(result.returncode)


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--work', type=Path, required=True)
    a.add_argument('--libraries', type=Path, required=True)
    a.add_argument('--yosys', required=True)
    args = a.parse_args()
    work = args.work.resolve()
    if work.exists():
        raise SystemExit('fresh physical mapping output required; retain previous objects')
    work.mkdir(parents=True)
    ss = [next(args.libraries.glob(f'asap7sc7p5t_{family}_RVT_SS_nldm*.lib')) for family in FAMILIES]
    manifest = dict(scope='physical-flow mapped cell/load price ONLY; no PNR or SS/FF context claim',
                    sources={s: digest(ROOT / s) for s in SOURCES},
                    libraries={str(p): digest(p) for p in sorted(args.libraries.glob('*.lib'))},
                    period_ps=833.333333, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                    engines_unchanged=True, extra_wrapper_registers=0, route_admitted=False)
    (work / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    libargs = ' '.join('-liberty ' + str(p) for p in ss)
    script = '\n'.join([
        'read_slang --top ' + TOP + ' -G ENABLE=1 -G COLUMN_BASE=0 -G ROWS=4496 ' + ' '.join(str(ROOT / s) for s in SOURCES),
        f'hierarchy -check -top {TOP}', f'synth -top {TOP} -flatten',
        'dfflibmap -liberty ' + str(ss[3]),
        'abc ' + libargs + ' -dont_use *x1p*_ASAP7* -dont_use *xp*_ASAP7* -dont_use SDF* -dont_use ICG* -D 833.333333',
        # Match the standard ASAP7 ORFS mapping front door. Physical fanout
        # repair supplies local ties; never reinterpret literals as PG rails.
        'hilomap -singleton -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L',
        'splitnets -ports', 'opt_clean -purge',
        f'tee -o {work}/stat.txt stat ' + libargs,
        f'write_verilog -noattr {work}/mapped.v', f'write_json {work}/mapped.json', ''])
    (work / 'map.ys').write_text(script)
    run([args.yosys, '-s', str(work / 'map.ys')], work / 'map.log')
    # Resolve the actual hard-macro count without changing RTL or mapping.
    design = json.loads((work / 'mapped.json').read_text())['modules'][TOP]
    counts = {m: sum(c['type'] == m for c in design['cells'].values()) for m in MACROS}
    (work / 'macro_census.json').write_text(json.dumps(counts, indent=2) + '\n')
    if counts != {m: 10 for m in MACROS}:
        raise SystemExit('mapped macro census is not the actual twenty-macro pair')
    (work / 'mapping_complete').write_text('actual-source SS mapping complete; contextual timing still unqualified\n')


if __name__ == '__main__':
    main()
