#!/usr/bin/env python3
"""One private connected W2 pair; retained native producer bits, no inference.

The original native GU/SwiGLU run is NOT repeated. Comparators never drive
weights, operands, results, ACK, shared release or CP completion.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TB = 'tb_hbm_integrated_gu_w2_hubble'
EXTRA = [
    'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
    'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_prior_debt.sv',
    'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_sm0_borrow.sv',
    'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w2_result_sink.sv',
    'rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w2_sector_adapter.sv',
    'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv',
    'rtl/gpu_sys/ot_gpu_xbar.sv',
    'rtl/gpu_sys/ot_gpu_l2_slice.sv',
    'rtl/gpu_sys/ot_gpu_hbm_partition.sv',
    'rtl/gpu_sys/ot_gpu_memsys.sv',
    'rtl/hdc/kv/ot_hdc_hbm_model.sv',
    f'rtl/test/hbm_accel/integrated_20261005/{TB}.sv',
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hexwords(path):
    return [int(line, 16) for line in Path(path).read_text().split()]


def writehex(path, values, width):
    Path(path).write_text(''.join(f'{value:0{width}x}\n' for value in values))


def prepare(native, sectors, allocation, out):
    """Select original L20/sm4 pair0; restore R3 source index, not addr*136."""
    seq = hexwords(native / 'seq.hex')[:16]
    if (len(seq) != 16 or seq[:14] !=
            [4, 8, 2, 2, 64, 1, 1, 16, 1, 0, 1, 32, 16, 16]
            or seq[14] == seq[15]):
        raise ValueError('require the original first real two-row paired descriptor')
    allocation_text = allocation.read_text()
    required = {'RAM_BYTES': 134217728, 'BASE_A': 119265280,
                'LIMIT_A': 119265344, 'BASE_B': 119265344,
                'LIMIT_B': 119265408}
    for key, value in required.items():
        match = re.search(r'\b' + key + r'\s*=\s*(?:32\x27d)?(\d+)', allocation_text)
        if not match or int(match[1]) != value:
            raise ValueError('use Rawls actual Program.put include, not invented extents')
    full_maps = hexwords(sectors / 'maps.hex')
    full_lines = hexwords(sectors / 'expected.hex')
    if len(full_maps) != 1344 or len(full_lines) != 1344:
        raise ValueError('complete existing literal sector compiler output required')
    lookup = {}
    for word, expected in zip(full_maps, full_lines):
        key = ((word >> 23) & 7, (word >> 26) & 0xffffffff)
        if key in lookup:
            raise ValueError('source map alias')
        lookup[key] = word, expected
    # Native request join restores A/B's original logical 32-line addresses.
    # Original full SM4 holds three rows: (r,g,t) -> t*6+r*2+g.
    # First paired descriptor holds two: (r,g,t) -> t*4+r*2+g.
    # Expert B is the next original 48-line source extent, NOT compact bytes.
    maps, expected = [], []
    original_lines = hexwords(native / 'lines.hex')[:64]  # comparator ONLY
    if len(original_lines) != 64:
        raise ValueError('incomplete original native pair comparator')
    for address in range(64):
        expert_slot, local = divmod(address, 32)
        t, row_group = divmod(local, 4)
        source_index = expert_slot * 48 + t * 6 + row_group
        word, line = lookup[4, source_index]
        if line != original_lines[address]:
            raise ValueError('paired restored source differs from literal installed bytes')
        word = (word & ~(0xffffffff << 26)) | (address << 26)
        if (word >> 250) & ((1 << 96) - 1):
            raise ValueError('source compiler must not fabricate physical tag grants')
        maps.append(word)
        expected.append(line)
    values = {}
    for line in (native / 'out.txt').read_text().splitlines():
        if line.startswith('#'):
            continue
        op, row, bits = line.split()
        key = int(op), int(row)
        if key in values:
            raise ValueError('duplicate original arithmetic comparator')
        values[key] = int(bits, 16)
    rows = [values[op, row] for op in seq[14:16] for row in (0, 1)]
    x = hexwords(native / 'x.hex')[:32]
    if len(x) != 32 or any(value.bit_length() > 27264 for value in x):
        raise ValueError('original native FP8 operand extent')
    addresses = hexwords(sectors / 'memory_addresses.hex')
    data = hexwords(sectors / 'memory.hex')
    if len(addresses) != len(data) or len(set(addresses)) != len(addresses):
        raise ValueError('installed sector alias/extent')
    if addresses != sorted(addresses):
        raise ValueError('installed address order')
    if not all(a in addresses for a in
               (required['BASE_A'], required['BASE_A'] + 32,
                required['BASE_B'], required['BASE_B'] + 32)):
        raise ValueError('allocated output seats absent from emitted source fixture')
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(allocation, out / 'private_alloc.svh')
    for name in ('memory_addresses.hex', 'memory.hex', 'w2_p0.hex', 'w2_p1.hex'):
        shutil.copyfile(sectors / name, out / name)
    writehex(out / 'seq.hex', seq, 8)
    writehex(out / 'x.hex', x, 6816)
    writehex(out / 'maps.hex', maps, 112)
    writehex(out / 'expected_lines.hex', expected, 272)
    writehex(out / 'expected_rows.hex', rows, 64)
    (out / 'args.txt').write_text(f'+NWORDS={len(addresses)}\n')
    print('PREPARED_ONE_RETAINED_NATIVE_L20_SM4_PAIR', seq[14:16], flush=True)


def build(work, case, donor_sources, jobs):
    if not 1 <= jobs <= 16:
        raise ValueError('make worker policy 1..16')
    donor = json.loads(donor_sources.read_text())
    paths = []
    for name, digest in donor.items():
        if name.startswith('rtl/test/'):
            continue  # autonomous test top is the ONLY replaced boundary
        if sha(ROOT / name) != digest:
            raise ValueError(f'preserve actual retained W2 engine source: {name}')
        paths.append(name)
    paths = list(dict.fromkeys([EXTRA[0]] + paths + EXTRA[1:]))
    work.mkdir(parents=True, exist_ok=False)
    command = ['verilator', '--binary', '--timing', '-O2', '-Wno-fatal',
               '--top-module', TB, '--Mdir', str(work / 'obj'), '-j', str(jobs),
               '-I' + str(case), *[str(ROOT / name) for name in paths]]
    (work / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    (work / 'source_pin.json').write_text(json.dumps(
        {name: sha(ROOT / name) for name in paths}, indent=2) + '\n')
    with (work / 'compile.log').open('w') as log:
        rc = subprocess.run(command, cwd=ROOT, stdout=log,
                            stderr=subprocess.STDOUT).returncode
    (work / 'compile.exit').write_text(str(rc) + '\n')
    if rc:
        raise SystemExit(rc)


def run(work, case, original_prefix):
    # Required owner-resolved ORIGINAL NS2 images, prior to installed overlays.
    for partition in range(2):
        if not Path(f'{original_prefix}_d0_p{partition}.hex').is_file():
            raise ValueError('actual original NS2 image prefix required before launch')
    if (work / 'runtime.log').exists():
        raise ValueError('preserve previous runtime; no automatic retry')
    args = (case / 'args.txt').read_text().split()
    command = [str(work / 'obj' / ('V' + TB)), f'+DIR={case}',
               f'+gpu_sys_mem_prefix={original_prefix}', *args]
    with (work / 'runtime.log').open('w') as log:
        rc = subprocess.run(command, cwd=case, stdout=log,
                            stderr=subprocess.STDOUT).returncode
    (work / 'runtime.exit').write_text(str(rc) + '\n')
    if rc or 'PASS_NATIVE_W2_CONNECTED_PUBLICATION_CPL' not in (work / 'runtime.log').read_text():
        raise SystemExit(rc or 1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('step', choices=('prepare', 'build', 'run'))
    for name in ('native-case', 'sector-case', 'allocation', 'case', 'work', 'donor-sources'):
        p.add_argument('--' + name, type=Path)
    p.add_argument('--jobs', type=int, default=16)
    p.add_argument('--original-prefix', type=Path)
    a = p.parse_args()
    if a.step == 'prepare':
        prepare(a.native_case.resolve(), a.sector_case.resolve(),
                a.allocation.resolve(), a.case.resolve())
    elif a.step == 'build':
        build(a.work.resolve(), a.case.resolve(), a.donor_sources.resolve(), a.jobs)
    else:
        run(a.work.resolve(), a.case.resolve(), a.original_prefix.resolve())


if __name__ == '__main__':
    main()
