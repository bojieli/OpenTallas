#!/usr/bin/env python3
"""128-row live ROM-to-return seam; explicitly not a complete SU/MU token."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = [
    'rtl/rom/collectives/ot_rom_coll_pkg.sv',
    'rtl/rom/collectives/ot_rom_coll_skid.sv',
    'rtl/dsrom_sys/s81_native_head/ot_rom_argmax_rows.sv',
    'rtl/v41rom/ot_dsrom_head_bundle.sv', 'rtl/v41rom/ot_dsrom_head_elem.sv',
    'rtl/v41rom/ot_v41_fadd.sv', 'rtl/common/ot_prefix.sv',
    'rtl/v41rom/ot_v41_bmul2.sv', 'rtl/v41rom/ot_dsrom_bmul3.sv',
    'rtl/hdc/ot_hdc_delay.sv',
    'physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v',
    'rtl/dsrom_sys/s81_native_head_connect/ot_s81_bundle_token_return.sv',
    'rtl/dsrom_sys/s81_native_head_connect/test/tb_s81_bundle_token_return.sv']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def macro(data, work, inst):
    # Exact existing native head image law: logical skew11, two interleaved
    # ROM4096 banks, mux8 physical via map. No analytical dot or expected roots.
    p = np.arange(8192)[:, None]
    j = np.arange(16)[None, :]
    img = data[(p - 11*(j % 8)) % 8192, np.broadcast_to(j, (8192, 16))]
    for bank in (0, 1):
        rows = [0]*512
        for adr in range(4096):
            rr, sub = divmod(adr, 8)
            for lane in range(16):
                value = int(img[2*adr+bank, lane])
                for bit in range(16):
                    if value & (1 << bit):
                        rows[rr] |= 1 << ((16*lane+bit)*8+sub)
        (work/f'{inst}_{bank}.viamap.hex').write_text(''.join(f'{x:0548x}\n' for x in rows))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fixture', required=True, type=Path)
    ap.add_argument('--work', required=True, type=Path)
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((a.fixture/'files.json').read_text())
    # Hash only the small actual input and independent checker files. The full
    # immutable weight manifest is retained; slice SHA binds exactly used bytes.
    for rel in ('ops/head.norm.scale.bin', 'ops/head.lm_head.bin'):
        if sha(a.fixture/rel) != manifest[rel]['sha256']:
            raise ValueError(f'fixture hash mismatch: {rel}')
    desc = manifest['weights/head.bin']
    if desc['format'] != 'BF16' or desc['rows'] != [0, 32320]:
        raise ValueError('actual rank0 BF16 head weights required')
    weights = np.memmap(a.fixture/'weights/head.bin', dtype='<u2', mode='r', shape=(32320, 5120))
    data = np.array(weights[21888:22016], copy=True)
    x = np.fromfile(a.fixture/'ops/head.norm.scale.bin', dtype='<f4').view('<u4')
    if len(x) != 5120 or np.any(x & 65535):
        raise ValueError('input must be exact declared BF16 final norm')
    x16 = x >> 16
    for q in range(4):
        macro(data[q*32:q*32+32, :4096].reshape(8192, 16), a.work, f'ha{q}')
    perm = np.array([32*(n % 4)+n//4 for n in range(128)])
    macro(data[perm, 4096:].reshape(8192, 16), a.work, 'hb')
    for name, v in [('xa', x16[:4096]), ('xb', x16[4096:])]:
        (a.work/f'{name}.hex').write_text(''.join(''.join(f'{int(t):04x}' for t in v[i:i+16][::-1])+'\n' for i in range(0, len(v), 16)))
    logits = np.fromfile(a.fixture/'ops/head.lm_head.bin', dtype='<f4')[21888:22016]
    (a.work/'logits.hex').write_text(''.join(f'{int(t):08x}\n' for t in logits.view('<u4')))
    winner = int(np.argmax(logits))
    (a.work/'expect.hex').write_text(f'{21888+winner:08x}\n{int(logits.view("<u4")[winner]):08x}\n')
    source_hashes = {p: sha(ROOT/p) for p in SRC}
    obj = a.work/'obj'
    exe = obj/'Vtb_s81_bundle_token_return'
    if exe.exists():
        if json.loads((a.work/'build_sources.json').read_text()) != source_hashes:
            raise ValueError('refuse to reuse binary with different source')
    else:
        vl = Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
        with (a.work/'build.log').open('w') as log:
            subprocess.run([str(vl), '--binary', '--timing', '-j', '8', '-Wno-fatal', '-Wno-lint',
                            '-O2', '--top-module', 'tb_s81_bundle_token_return', '--Mdir', str(obj),
                            *[str(ROOT/p) for p in SRC]], stdout=log, stderr=subprocess.STDOUT, check=True)
        (a.work/'build_sources.json').write_text(json.dumps(source_hashes, indent=2)+'\n')
    cases = []
    deadline = None
    for mode, mut in [(0,0), (1,0), (1,1), (1,2), (1,3)]:
        cmd = [str(exe), f'+DIR={a.work}', f'+OT_ROM_DIR={a.work}', f'+MODE={mode}', f'+MUT={mut}']
        if deadline is not None:
            cmd.append(f'+DEADLINE={deadline}')
        run = subprocess.run(cmd, capture_output=True, text=True)
        output = run.stdout+run.stderr
        (a.work/f'run_mode{mode}_mut{mut}.log').write_text(output)
        expected = 'FAIL' if mut else 'PASS'
        if run.returncode or f'LIVE_HEAD_RETURN {expected}' not in output:
            raise RuntimeError(f'mode{mode} mut{mut} unexpected result: {output[-2000:]}')
        ages = [int(t) for t in re.findall(r'RETURN .* age=(\d+)', output)]
        if deadline is None:
            deadline = ages[0]
        cases.append(dict(mode=mode, mutant=mut, expected=expected, ages=ages))
        print(output, flush=True)
    rec = dict(schema='opentallas.s81.live_head_return.v1', gate='PASS', full_token_qualified=False,
               scope='128-row actual native ROM bundle live logits -> existing argmax -> registered same-clock owner return; fixture normalized input',
               production_multi_user_qualified=False, fixed_slot_interval=9000, rows=128,
               actual_go_to_return_edges=deadline, added_return_capture_edges=1, cases=cases,
               input_kind='fixture head.norm.scale, not actual production VM/HCP producer',
               weights_slice_sha256=hashlib.sha256(data.tobytes()).hexdigest(),
               fixture_manifest_sha256=sha(a.fixture/'files.json'), source_hashes=source_hashes)
    (a.work/'receipt.json').write_text(json.dumps(rec, indent=2)+'\n')
    print(json.dumps(rec, indent=2), flush=True)


if __name__ == '__main__':
    main()
