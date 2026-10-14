#!/usr/bin/env python3
"""Actual checkpoint-weighted TP8 layer oracle; never an RTL verdict."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import hdc_golden as G
import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_program_w12 as FP
from hdc_qwen_fullshape_placement_w12 import TP, GROUPS
from hdc_qwen_int8_image_w12 import shipped_vocab_rows
from qwen_o4_layer0_oracle_w12 import Image, DieMachine
from qwen_tp8_payload_fused_lower import lower_image

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hex_vector(path, values):
    path.write_text(''.join(f'{int(x):08x}\n' for x in G.bits(values)))
    return {'elements': int(np.size(values)), 'sha256': sha(path)}


def fp8_decode(codes):
    codes = np.asarray(codes, dtype=np.uint8)
    exp = ((codes >> 3) & 15).astype(np.int32)
    mant = (codes & 7).astype(np.float32)
    value = np.where(exp == 0, mant * np.float32(2**-9),
                     (1 + mant/8) * np.exp2(exp-7)).astype(np.float32)
    return np.where(codes & 128, -value, value).astype(np.float32)


class NativeOracleMachine(DieMachine):
    def me(self, fields, dynamic):
        if not fields['me_wsrc']:
            return super().me(fields, dynamic)
        # TP8 owns FOUR live Q heads. Legacy IL8 computes unused rows as well;
        # those are not defined VM effects and overflow the four-head S map.
        # This oracle explicitly evaluates only the native four-head contract.
        context = self.pos + 1
        if self.lay.NH != 4 or self.lay.KV != 1 or self.lay.HD != 128:
            raise ValueError('requires native four-Q/one-KV head ownership')
        if fields['me_d_tiles'] == I.DYN_TTILES:
            keys = self.kv[np.array([[self.lay.k_elem(0, 0, t, dim) for dim in range(128)] for t in range(context)])]
            for head in range(4):
                qb = fields['me_xbase'] + head*128
                scores = G.matvec_il(keys, G.to_bf16(self.vm[qb:qb+128]), 128)
                base = fields['me_obase']*16 + head*fields['me_ojs']*16
                self.vm[base:base+context] = scores
                self.vm[fields['me_mbase']+head] = np.max(scores)
        elif fields['me_d_k'] == I.DYN_T:
            values = self.kv[np.array([[self.lay.v_elem(0, 0, t, dim) for dim in range(128)] for t in range(context)])]
            for head in range(4):
                eb = fields['me_xbase'] + head*fields['me_xjs']
                result = G.matvec_il(values.T, G.to_bf16(self.vm[eb:eb+context]), 256)
                base = fields['me_obase']*16 + head*fields['me_ojs']*16
                self.vm[base:base+128] = result
        else:
            raise ValueError('unsupported dynamic attention instruction')


def production_tp8_fold(partials):
    """Existing TP8 rank=4*DIE+PKG contract; preserve every FP32 add."""
    if len(partials) != 8:
        raise ValueError('production TP8 collective requires eight ranks')
    return G.fold([G.add(partials[p], partials[p+4]) for p in range(4)])


def generate(image_root, snapshot, out, position=255, token=0, collective_profile='legacy_linear8', layer=0, x_input=None):
    if collective_profile not in ('legacy_linear8', 'production_tp8_two_level'):
        raise ValueError('unknown collective reference profile')
    if TP != 8 or GROUPS != 3072 or I.SU_WIDTH != 64 or G.KV_FMT != 'fp8':
        raise ValueError('requires QWEN_O4_TP8/GROUPS3072/HDC_SU_WIDTH64/KV_FMTfp8 environment')
    if not 0 <= position < 8192:
        raise ValueError('position outside native layer capacity')
    out.mkdir(parents=True, exist_ok=True)
    vm_map, _ = FP.vm_map()
    images = [Image(image_root / f'die{die}', layer=layer) for die in range(8)]
    if any(image.descriptors != images[0].descriptors for image in images[1:]):
        raise ValueError('eight rank collective descriptor mismatch')
    lowered = [lower_image(image.dir, layer=layer) for image in images]
    effect_mask = np.ones(FP.vm_map()[1], dtype=np.bool_)
    for lo, hi in lowered[0]['removed_intermediate_intervals'].values():
        effect_mask[lo:hi] = False
    if x_input is None:
        if layer != 0:
            raise ValueError('later checkpoint layer requires committed previous-layer X input')
        embedding = shipped_vocab_rows(snapshot, 'embedding', start=token, count=1)
        codes = embedding['codes'].numpy()[0].astype(np.float32)
        scale = embedding['scales'].float().numpy()[0, 0]
        x_initial = G.mul(codes, np.float32(scale))
    else:
        words = Path(x_input).read_text().split()
        if len(words) != 4096 or any(word.startswith('@') for word in words):
            raise ValueError('later-layer X input requires4096exact FP32 words')
        x_initial = G.from_bits(np.array([int(word,16) for word in words], dtype=np.uint32))
    (out / 'vm_x_fp32.hex').write_text('@1000\n' + ''.join(f'{int(x):08x}\n' for x in G.bits(x_initial)))
    machines = [NativeOracleMachine(image) for image in images]
    report = {'schema': 'opentallas.qwen-tp8-native-layer-oracle.v1',
              'status': 'CHECKPOINT_WEIGHTED_ISA_ORACLE_ONLY', 'tp': 8, 'groups': 3072,
              'position': position, 'token': token, 'layers': [0],
              'input_policy': 'Actual locked checkpoint W8 matrices/constants and token embedding. Prior K/V is a declared deterministic FP8 fixture, not a model prefill trace.',
              'claim_boundary': 'Immutable full-layer arithmetic inputs/expected effects only; not an RTL run, realistic token latency or model-level decode proof.',
              'x_preload_sha256': sha(out / 'vm_x_fp32.hex'), 'ranks': {},
              'native_attention_order': {'S': 128, 'PV': 256, 'heads': 4, 'KV_heads': 1},
              'legacy_unused_IL8_writes': 'Excluded: only four live head rows are defined in native TP8 ownership; unused legacy rows can exceed VM map.',
              'effect_comparison': 'VM snapshots carry an explicit defined-effect mask excluding removed fused attention intermediates. KV-write instructions additionally retain their exact addressed quantized commit expectations.',
              'source_sha256': {name: sha(ROOT / name) for name in
                    ('tools/qwen_tp8_native_layer_oracle.py', 'tools/qwen_o4_layer0_oracle_w12.py',
                     'tools/hdc_golden.py', 'tools/hdc_program.py', 'tools/hdc_isa.py',
                     'tools/qwen_tp8_payload_fused_lower.py', 'tools/qwen_tp8_fused_attention_lower.py')}}
    report['payload_layer'] = layer
    report['x_source'] = {'kind':'checkpoint_embedding' if x_input is None else 'previous_layer_X', 'sha256': None if x_input is None else sha(x_input)}
    report['collective_reference_profile'] = collective_profile
    report['production_tp8_collective_compatible'] = collective_profile == 'production_tp8_two_level'
    if collective_profile == 'production_tp8_two_level':
        report['collective_reference_contract'] = {
            'rank': '4*DIE+PKG', 'pair': 'rank[p]+rank[p+4]',
            'package_fold': '((P0+P1)+P2)+P3',
            'rtl/rom/ot_coll_tp8_die.sv': sha(ROOT/'rtl/rom/ot_coll_tp8_die.sv'),
            'tools/qwen_coll_tp8_bench.py': sha(ROOT/'tools/qwen_coll_tp8_bench.py')}
    for die, machine in enumerate(machines):
        machine.pos = position
        machine.vm[vm_map['X']:vm_map['X']+4096] = x_initial
        directory = out / f'die{die}'; directory.mkdir(exist_ok=True)
        t, dim = np.meshgrid(np.arange(position), np.arange(128), indexing='ij')
        # Safe finite signed E4M3 values, serialized as the exact receiver bytes.
        k_codes = (((t*11+dim*7+die*13+layer*19) % 48)+24).astype(np.uint8) | (((t+dim+die)%2)*128).astype(np.uint8)
        v_codes = (((t*3+dim*5+die*17+layer*23) % 48)+24).astype(np.uint8) | (((t+2*dim+die)%2)*128).astype(np.uint8)
        for name, values in (('K', k_codes), ('V', v_codes)):
            (directory / f'prior_{name}_fp8.bin').write_bytes(values.tobytes())
        keys, values = fp8_decode(k_codes), fp8_decode(v_codes)
        for t in range(position):
            machine.kv[[machine.lay.k_elem(0, 0, t, d) for d in range(128)]] = keys[t]
            machine.kv[[machine.lay.v_elem(0, 0, t, d) for d in range(128)]] = values[t]
        report['ranks'][str(die)] = {'image_sha256': images[die].manifest['image_sha256'],
                                    'lowered_program_sha256': lowered[die]['candidate_program_sha256'],
                                    'prior_K_sha256': sha(directory / 'prior_K_fp8.bin'),
                                    'prior_V_sha256': sha(directory / 'prior_V_fp8.bin'), 'effects': {}}
    descriptors = images[0].descriptors
    with FP.program_geometry(vm_map):
        dynamics = [P.dyn_values(machine.lay, token=token, pos=position) for machine in machines]
        for segment_index, descriptor in enumerate(descriptors):
            begin = descriptor['program_base']
            end = descriptors[segment_index+1]['program_base'] if segment_index+1 < len(descriptors) else len(images[0].program)
            for die, (machine, image, dynamic) in enumerate(zip(machines, images, dynamics)):
                directory = out / f'die{die}'
                for pc in range(begin, end):
                    fields = image.program[pc]
                    if fields['unit'] == I.UNIT_ME:
                        machine.me(fields, dynamic)
                    elif fields['unit'] == I.UNIT_SU:
                        machine.su(fields, dynamic)
                    if pc not in range(11, 15) and fields['unit']:
                        candidate_pc = lowered[die]['original_to_candidate_pc'][11 if pc == 15 else pc]
                        path = directory / f'candidate_pc{candidate_pc}_vm.npz'
                        np.savez_compressed(path, vm_bits=G.bits(machine.vm), defined_effect_mask=effect_mask)
                        report['ranks'][str(die)]['effects'][str(candidate_pc)] = {'source_pc': pc, 'full_VM_sha256': sha(path)}
                        if fields['unit'] == I.UNIT_SU and fields['dst'] == I.DST_KV:
                            count = fields['su_nin'] + dynamic[fields['su_d_nin']]
                            addresses = machine.stream(fields, dynamic, 'd', fields['su_nout'], count)
                            kv_path = directory / f'candidate_pc{candidate_pc}_KV_commits.npz'
                            np.savez_compressed(kv_path, element_addresses=addresses,
                                                quantized_FP32_bits=G.bits(machine.kv[addresses]))
                            report['ranks'][str(die)]['effects'][str(candidate_pc)]['KV_commit_sha256'] = sha(kv_path)
                    if pc == 10:
                        q = machine.vm[vm_map['QR']:vm_map['QR']+512].copy()
                        report['ranks'][str(die)]['Q_input'] = hex_vector(directory / 'Q_input_fp32.hex', q)
                        for name, index in (('K', machine.lay.k_elem), ('V', machine.lay.v_elem)):
                            row = machine.kv[[index(0, 0, position, dim) for dim in range(128)]]
                            report['ranks'][str(die)][f'new_{name}_row'] = hex_vector(directory / f'new_{name}_row_fp32.hex', row)
                    if pc == 15:
                        report['ranks'][str(die)]['ATTN'] = hex_vector(directory / 'ATTN_fp32.hex', machine.vm[vm_map['ATTN']:vm_map['ATTN']+512])
            if descriptor['kind'] == P.COLL_ALLREDUCE:
                lo = descriptor['vm_word']*16; hi = lo+descriptor['words']*16
                partials = [machine.vm[lo:hi].copy() for machine in machines]
                folded = production_tp8_fold(partials) if collective_profile == 'production_tp8_two_level' else G.fold(partials)
                for die, machine in enumerate(machines):
                    machine.vm[lo:hi] = folded
                    report['ranks'][str(die)][f'collective{segment_index}_partial'] = hex_vector(out / f'die{die}/collective{segment_index}_partial.hex', partials[die])
                    report['ranks'][str(die)][f'collective{segment_index}_return'] = hex_vector(out / f'die{die}/collective{segment_index}_return.hex', folded)
            elif descriptor['kind'] != P.COLL_END:
                raise ValueError('unexpected layer collective kind')
    for die, machine in enumerate(machines):
        report['ranks'][str(die)]['X_final'] = hex_vector(out / f'die{die}/X_final_fp32.hex', machine.vm[vm_map['X']:vm_map['X']+4096])
    (out / 'oracle.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"pinned actual eight-rank checkpoint-weighted layer oracle at position{position}; RTL unproved")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image-root', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--position', type=int, default=255)
    parser.add_argument('--token', type=int, default=0)
    parser.add_argument('--layer', type=int, choices=range(36), default=0)
    parser.add_argument('--x-input', type=Path)
    parser.add_argument('--collective-profile', choices=('legacy_linear8', 'production_tp8_two_level'), default='legacy_linear8')
    args = parser.parse_args()
    generate(args.image_root, args.snapshot, args.out, args.position, args.token, args.collective_profile, args.layer, args.x_input)

if __name__ == '__main__':
    main()
