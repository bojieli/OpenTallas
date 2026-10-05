#!/usr/bin/env python3
"""One exact decode reference from retained prior KV; never performs prefill.

Uses the original GPU ISA golden unchanged. Decode image hex on a remote host
with qwen_rom_position_oracle_gpu.py --prep first. No target X is an input.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def validate_history(book, position, token):
    require(book['position'] == position and book['token'] == token, 'prior KV position/token mismatch')
    require(set(book['history']) == {f'L{n}_die{d}' for n in range(36) for d in range(4)},
            'all 144 actual prior KV bindings required')
    return book['history']

def run(a):
    # No import of torch/NumPy until the previous GPU owner has actually exited.
    require(not Path(f'/proc/{a.wait_for_pid}').exists(), 'existing GPU producer still owns slot')
    owners = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid',
                                     '--format=csv,noheader,nounits'], text=True)
    require(not owners.strip(), 'GPU slot occupied')
    require(sha(a.inputs) == a.inputs_sha256, 'selected prior KV input book changed')
    require(sha(a.prep / 'prep.json') == a.prep_sha256, 'decoded image source book changed')
    require(sha(a.tokens) == a.tokens_sha256, 'actual prompt changed')
    require(sha(a.released_oracle) == a.released_oracle_sha256, 'released arithmetic reference changed')
    tokens = [int(t) for t in a.tokens.read_text().split()]
    require(tokens[a.position] == a.token, 'actual pending token mismatch')
    book = json.loads(a.inputs.read_text())
    history = validate_history(book, a.position, a.token)
    require(book['preload']['sha256'] == a.preload_sha256, 'preload not bound to actual input book')
    require(sha(a.reference / 'oracle.json') == a.reference_sha256, 'retained control reference changed')
    require(not a.out.exists(), 'fresh output required')
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    os.environ.update(QWEN_O4_GROUPS='6144', QWEN_O4_TP='4', HDC_SU_WIDTH='1024', HDC_KV_FMT='fp8')
    sys.path.insert(0, str(ROOT / 'tools'))
    import numpy as np
    import torch
    import qwen_hbmacc_position_oracle_gpu as gpu
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    released = json.loads(a.released_oracle.read_text())
    require(released['tp'] == 4 and released['layers'] == 36 and released['kv_format'] == 'fp8',
            'released full TP4 reference required')
    require(released['tokens_sha256'] == a.tokens_sha256, 'actual prompt differs from released reference')
    require(sha(a.decoded_pins) == a.decoded_pins_sha256, 'retained image pins changed')
    require(sha(a.binding) == a.binding_sha256, 'released checkpoint binding changed')
    binding = json.loads(a.binding.read_text())
    require(binding['checkpoint_revision'] == 'b968826d9c46dd6066d109eabc6255188de91218' and
            binding['checkpoint_lock_sha256'] == '5cd6273118054c4a9140682bcd7a32488d8697db26bedf5d7ece8de99e141607',
            'released checkpoint/contract binding required')
    image_pins = json.loads(a.decoded_pins.read_text())
    for name, digest in released['oracle_source_sha256'].items():
        require(sha(ROOT/name) == digest, 'released golden source changed: '+name)
    require(torch.cuda.is_available(), 'CUDA only, no CPU fallback')
    prep = json.loads((a.prep / 'prep.json').read_text())
    for entry in prep['images']:
        pins = (image_pins['layer_image_sha256'][f"L{entry['layer']}"][entry['die']]
                if entry['kind'] == 'layer' else image_pins[f"head_die{entry['die']}"]['image_sha256'])
        if entry['kind'] == 'head':
            pins = dict(pins, **{'crom.hex':binding['program_sha256']['head_final_norm_crom.hex']})
        require(all(pins[name] == digest for name,digest in entry['image_sha256'].items()),
                'decoded matrix/scale/constant source differs from retained image')
        if entry['kind'] == 'layer':
            require(prep['programs'][f"layer_d{entry['die']}"]['program_sha256'] == pins['program.hex'] and
                    prep['programs'][f"layer_d{entry['die']}"]['segments_sha256'] == pins['segments.hex'],
                    'actual native layer program differs from decoded source')
        require(sha(a.prep / entry['npz']) == entry['npz_sha256'], 'decoded image changed')
    require({(e['kind'], e['layer'], e['die']) for e in prep['images']} ==
            {('layer', n, d) for n in range(36) for d in range(4)} |
            {('head', -1, d) for d in range(4)}, '36 layers plus head on all four ranks required')
    m = gpu.GpuTP(gpu.torch_golden(torch.device('cuda:0')), a.prep, range(36), head=True)
    head_programs, head_hashes = gpu.head_programs(prep)
    require(head_hashes == released['head_program_sha256'], 'released head program changed')
    require(sha(a.preload) == a.preload_sha256, 'actual embedding preload changed')
    words = [int(s, 16) for s in a.preload.read_text().split() if not s.startswith('@')]
    require(len(words) == 4096, 'one actual embedding row required')
    x = np.asarray(words, dtype='<u4').view('<f4')
    vm = torch.zeros((4, m.VM_ELEMS), dtype=torch.float32, device='cuda:0')
    vm[:, m.VM['X']:m.VM['X'] + 4096] = torch.from_numpy(x).to('cuda:0')[None]
    a.out.mkdir(parents=True)
    pdir = a.out / f'P{a.position}'
    (pdir / 'kv_at_P').mkdir(parents=True)
    (pdir / 'kv_pre').mkdir()
    (pdir / 'x_preload.hex').write_bytes(a.preload.read_bytes())
    frame = dict(token=a.token, x_preload_sha256=sha(a.preload), layer_x_sha256={},
                 kv_pre_sha256={}, kv_at_P_sha256={})
    record = dict(schema='opentallas.qwen-rom-tp4-position-oracle-gpu.v1', status='running_single_position',
                  layers=36, head=True, tp=4, groups=6144, su_width_arith=1024, kv_format='fp8',
                  positions=[a.position], tokens_used=tokens[:a.position + 1], tokens_sha256=a.tokens_sha256,
                  input_book_sha256=a.inputs_sha256, prep_sha256=a.prep_sha256,
                  decoded_image_pins_sha256=a.decoded_pins_sha256, binding_sha256=a.binding_sha256,
                  historical_released_prep_sha256=released['prep_sha256'],
                  decoded_source_join='all148 image payload pins and all layer/head instruction hashes matched; fresh metadata',
                  head_program_sha256=head_hashes, per_position={str(a.position):frame},
                  oracle_source_sha256={str(Path(__file__).relative_to(ROOT)):sha(__file__),
                      **{name:sha(ROOT/name) for name in (
                          'tools/qwen_hbmacc_position_oracle_gpu.py', 'tools/qwen_rom_position_oracle_w12.py',
                          'tools/qwen_o4_layer0_oracle_w12.py', 'tools/qwen_o4_token_oracle_w12.py',
                          'tools/hdc_golden.py', 'tools/hdc_program.py', 'tools/hdc_isa.py',
                          'tools/hdc_qwen_fullshape_isa_w12.py', 'tools/hdc_qwen_fullshape_program_w12.py')}},
                  claim_boundary='Exact ISA golden of one actual token using retained prior KV; no prefill, DUT verdict or rate claim')
    def save():
        (a.out / 'oracle.json').write_text(json.dumps(record, indent=2) + '\n')
    start = time.time()
    save()
    for n in range(36):
        rows = []
        for d in range(4):
            key = f'L{n}_die{d}'
            b = history[key]
            raw = a.history_directory / (key + '.bin')
            require(sha(raw) == b['raw_sha256'], 'actual prior KV payload changed: ' + key)
            bits = np.fromfile(raw, dtype='<u4')
            require(bits.shape == (m.kv_elems,), 'actual prior KV extent mismatch')
            rows.append(bits.view('<f4'))
            prior = pdir / 'kv_pre' / (key + '.npy')
            np.save(prior, bits, allow_pickle=False)
            frame['kv_pre_sha256'][key] = sha(prior)
        m.kv[n].copy_(torch.from_numpy(np.stack(rows)).to('cuda:0'))
        m.run_layer(n, vm, a.token, a.position)
        kv = m.kv[n].cpu().numpy().view(np.uint32)
        actual = vm.cpu().numpy()
        for d in range(4):
            key = f'L{n}_die{d}'
            lay = m.lays[d]
            kel = [lay.k_elem(0, h, a.position, i) for h in range(lay.KV) for i in range(lay.HD)]
            vel = [lay.v_elem(0, h, a.position, i) for h in range(lay.KV) for i in range(lay.HD)]
            path = pdir / 'kv_at_P' / (key + '.json')
            path.write_text(json.dumps(dict(k_elem=kel, k_bits=[f'{int(v):08x}' for v in kv[d][kel]],
                                           v_elem=vel, v_bits=[f'{int(v):08x}' for v in kv[d][vel]])) + '\n')
            frame['kv_at_P_sha256'][key] = sha(path)
            path = pdir / f'L{n:02d}_die{d}_x.hex'
            gpu.write_hex(path, actual[d, m.VM['X']:m.VM['X'] + 4096])
            frame['layer_x_sha256'][key] = sha(path)
            retained = a.reference / f'P{a.position}' / path.name
            if retained.exists():
                control = np.array([int(v,16) for v in retained.read_text().split()], dtype='<u4')
                require(np.array_equal(actual[d, m.VM['X']:m.VM['X']+4096].view(np.uint32), control),
                        'actual existing layer control differs: '+key)
        save()
        print(f'layer {n} complete wall_seconds={time.time()-start:.3f}', flush=True)
    head, logits = m.run_head(vm, a.token, a.position, head_programs)
    np.save(pdir / 'logits.npy', logits)
    actual = vm.cpu().numpy()
    for d in range(4):
        path = pdir / f'head_die{d}_xnorm.hex'
        gpu.write_hex(path, actual[d, 8192:8192 + 4096])
        head[f'head_die{d}']['xnorm_sha256'] = sha(path)
    head['logits_sha256'] = sha(pdir / 'logits.npy')
    (pdir / 'head.json').write_text(json.dumps(head, indent=2) + '\n')
    frame['head'] = head
    record.update(status='ISA_golden_only', wall_seconds=time.time()-start)
    save()
    print(json.dumps(dict(status=record['status'], position=a.position, next_token=head['next_token'])), flush=True)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs', 'prep', 'tokens', 'preload', 'reference', 'released-oracle', 'decoded-pins', 'binding', 'history-directory', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    for name in ('inputs-sha256', 'prep-sha256', 'tokens-sha256', 'preload-sha256', 'reference-sha256', 'released-oracle-sha256', 'decoded-pins-sha256', 'binding-sha256'):
        p.add_argument('--'+name, required=True)
    p.add_argument('--position', type=int, required=True)
    p.add_argument('--token', type=int, required=True)
    p.add_argument('--wait-for-pid', type=int, required=True)
    run(p.parse_args())

if __name__ == '__main__':
    main()
