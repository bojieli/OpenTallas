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


def build(work, case, donor_sources, jobs, live_swiglu=False):
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
    if live_swiglu:
        # Exact selected numerical source closure, not a replacement arithmetic unit.
        import dsrom_su_swiglu as SW
        receipt = ROOT / 'results/rtl/dsrom_recovery_20261004/su_swiglu/r4/run_rtl_W64_NB32_m5a4q5_swiglu.json'
        retained = json.loads(receipt.read_text())
        numerical = list(dict.fromkeys(SW.RTL + SW.LIB + [SW.ADD6]))
        for name in numerical:
            if sha(ROOT / name) != retained['source_sha256'][name]:
                raise ValueError('selected numerical producer changed: ' + name)
        paths = list(dict.fromkeys(paths + numerical))
        if not (case / 'producer/source_pin.json').is_file():
            raise ValueError('prepare the retained actual GU boundary before a live producer build')
    work.mkdir(parents=True, exist_ok=False)
    command = ['verilator', '--binary', '--timing', '-O2', '-Wno-fatal',
               '--top-module', TB, '--Mdir', str(work / 'obj'), '-j', str(jobs),
               '-I' + str(case), *[str(ROOT / name) for name in paths]]
    if live_swiglu:
        command.insert(1, '-GLIVE_SWIGLU=1')
    (work / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    (work / 'source_pin.json').write_text(json.dumps(
        {name: sha(ROOT / name) for name in paths}, indent=2) + '\n')
    with (work / 'compile.log').open('w') as log:
        rc = subprocess.run(command, cwd=ROOT, stdout=log,
                            stderr=subprocess.STDOUT).returncode
    (work / 'compile.exit').write_text(str(rc) + '\n')
    if rc:
        raise SystemExit(rc)


def run(work, case, original_prefix, live_swiglu=False):
    # Required owner-resolved ORIGINAL NS2 images, prior to installed overlays.
    for partition in range(2):
        if not Path(f'{original_prefix}_d0_p{partition}.hex').is_file():
            raise ValueError('actual original NS2 image prefix required before launch')
    if (work / 'runtime.log').exists():
        raise ValueError('preserve previous runtime; no automatic retry')
    args = (case / 'args.txt').read_text().split()
    command = [str(work / 'obj' / ('V' + TB)), f'+DIR={case}',
               f'+gpu_sys_mem_prefix={original_prefix}', *args]
    if live_swiglu:
        producer = case / 'producer'
        pin = json.loads((producer / 'source_pin.json').read_text())
        for name, digest in pin['prepared_sha256'].items():
            if sha(producer / name) != digest:
                raise ValueError('retained GU boundary changed: ' + name)
        compile_command = json.loads((work / 'command.json').read_text())
        if '-GLIVE_SWIGLU=1' not in compile_command:
            raise ValueError('live producer requires its explicitly selected private executable')
        command += [f'+PRODUCER_DIR={producer}', '+SWIGLU_LIMIT=' + pin['limit_bits']]
    with (work / 'runtime.log').open('w') as log:
        rc = subprocess.run(command, cwd=case, stdout=log,
                            stderr=subprocess.STDOUT).returncode
    (work / 'runtime.exit').write_text(str(rc) + '\n')
    marker = ('PASS_LIVE_SWIGLU_W2_CONNECTED_PUBLICATION_CPL' if live_swiglu
              else 'PASS_NATIVE_W2_CONNECTED_PUBLICATION_CPL')
    if rc or marker not in (work / 'runtime.log').read_text():
        raise SystemExit(rc or 1)


def prepare_producer(case, retained_gu, router_config):
    """Copy actual retained GU/route input files, never compute producer outputs.

    Existing native_swiglu input files carry original GU BF16 and source router
    weights. The SwiGLU/FP8 outputs and x.hex active operands are comparators only.
    """
    import struct
    seq = hexwords(case / 'seq.hex')
    if len(seq) != 16 or seq[14:16] != [0, 1] or seq[9] != 0 or seq[12] != 16:
        raise ValueError('only measured original L20 SM4 first pair is admitted')
    config = json.loads(router_config.read_text())
    limit = float(config['swiglu_limit'])
    limit_bits = struct.unpack('<I', struct.pack('<f', limit))[0]
    if not 0 < limit_bits < 0x7f800000:
        raise ValueError('actual finite positive source SwiGLU limit required')
    source_hashes, assembled = {}, {}
    for name in ('g.mem', 'u.mem', 'w.mem'):
        words = []
        for expert in (41, 65):
            path = retained_gu / f'expert{expert}' / name
            values = hexwords(path)
            if len(values) != 2304 or any(v > 0xffffffff or (v & 0x7f800000) == 0x7f800000 for v in values):
                raise ValueError('retained actual GU/route extent or finite contract: ' + str(path))
            if name != 'w.mem' and any(v & 0xffff for v in values):
                raise ValueError('original GU BF16 rounding boundary changed')
            source_hashes[str(path)] = sha(path)
            words += values
        assembled[name] = words
    out = case / 'producer'
    out.mkdir(exist_ok=False)
    for name, words in assembled.items():
        writehex(out / name, words, 8)
    source_hashes[str(router_config)] = sha(router_config)
    (out / 'source_pin.json').write_text(json.dumps(dict(
        scope='retained actual GU and source route inputs; live SwiGLU only',
        experts=[41, 65], elements_per_expert=2304,
        limit_bits=f'{limit_bits:08x}', source_sha256=source_hashes,
        prepared_sha256={name: sha(out / name) for name in assembled}), indent=2) + '\n')
    print('PREPARED_RETAINED_GU_FOR_LIVE_SWIGLU_ONLY experts=41,65 elements=4608', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('step', choices=('prepare', 'prepare-producer', 'build', 'run'))
    for name in ('native-case', 'sector-case', 'allocation', 'case', 'work', 'donor-sources'):
        p.add_argument('--' + name, type=Path)
    p.add_argument('--jobs', type=int, default=16)
    p.add_argument('--live-swiglu', action='store_true', help='private default-off numerical boundary join')
    p.add_argument('--retained-gu', type=Path)
    p.add_argument('--router-config', type=Path)
    p.add_argument('--original-prefix', type=Path)
    a = p.parse_args()
    if a.step == 'prepare':
        prepare(a.native_case.resolve(), a.sector_case.resolve(),
                a.allocation.resolve(), a.case.resolve())
    elif a.step == 'prepare-producer':
        prepare_producer(a.case.resolve(), a.retained_gu.resolve(), a.router_config.resolve())
    elif a.step == 'build':
        build(a.work.resolve(), a.case.resolve(), a.donor_sources.resolve(), a.jobs, a.live_swiglu)
    else:
        run(a.work.resolve(), a.case.resolve(), a.original_prefix.resolve(), a.live_swiglu)


if __name__ == '__main__':
    main()
