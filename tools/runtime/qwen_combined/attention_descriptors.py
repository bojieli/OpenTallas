"""Opt-in descriptor-3 images derived from actual decoded Qwen W12 words.

No checkpoint/model/oracle import. Normal images stay intact. Only the old
attention instructions are omitted; the combined RTL owns QR streaming, all
real memory fences, near-HBM execution and final ATTN VM publication.
"""
import hashlib
import json
import os
from pathlib import Path

from tools import hdc_isa as I


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode_near(qr, attn, base):
    require(all(type(x) is int and 0 <= x < (1 << bits)
                for x, bits in ((qr, 24), (attn, 24), (base, 12))), 'descriptor3 aperture')
    require(qr % 16 == attn % 16 == 0, 'descriptor3 VM alignment')
    return 3 | (qr << 2) | (attn << 26) | (base << 50)


def decode_near(word):
    require(type(word) is int and 0 <= word < (1 << 62) and word & 3 == 3,
            'descriptor3 kind/reserved bits')
    return dict(qr_base=(word >> 2) & 0xffffff, attn_base=(word >> 26) & 0xffffff,
                prefix_program_base=(word >> 50) & 0xfff)


def control_patch(word):
    changes = dict(chase=0, chase_n=0, chase_rows=0, barrier=1)
    for name, value in changes.items():
        offset, width = I.LAYOUT[name]
        word = (word & ~(((1 << width) - 1) << offset)) | (value << offset)
    return word


def derive(words, descriptors, *, enable=False):
    require(enable, 'descriptor3 image transform default off')
    require(words and descriptors and len(words) < 4096, 'PAW12 source image required')
    require(all(type(w) is int and 0 <= w < (1 << 1024) for w in words), 'W12 raw instruction width')
    require(all(type(d) is int and 0 <= d < (1 << 64) and d & 3 != 3 for d in descriptors),
            'normal source descriptors only')
    bases = [(d >> 32) & 0xffff for d in descriptors]
    require(bases[0] == 0 and bases == sorted(set(bases)) and bases[-1] < len(words),
            'ordered normal program bases')
    require(descriptors[-1] & 3 == 0 and all(d & 3 == 1 for d in descriptors[:-1]),
            'decoder-layer collective/END source contract')
    ops = [I.decode(word) for word in words]
    ends = bases[1:] + [len(words)]
    for lo, hi in zip(bases, ends):
        require(ops[hi - 1]['unit'] == I.UNIT_END and ops[hi - 1]['barrier'] == 1,
                'every source segment must end with drained END')
    kv_ops = [pc for pc, op in enumerate(ops) if op['unit'] == I.UNIT_ME and op['me_wsrc']]
    require(len(kv_ops) == 2, 'exact single score/PV attention pair required')
    first, pv_pc = kv_ops
    require(pv_pc == first + 2 and first + 5 < ends[0], 'attention must stay inside first segment')
    score, exp, pv, recip, norm, projection = ops[first:first + 6]
    qr, scores = score['me_xbase'], score['me_obase'] * 16
    att, attn = pv['me_obase'] * 16, norm['d_base']
    require(score['me_k'] == 128 and score['me_d_nout'] == I.DYN_T
            and score['me_d_tiles'] == I.DYN_TTILES, 'score dynamic context/head geometry')
    require(exp['unit'] == I.UNIT_SU and exp['sfu'] == I.SFU_EXP and exp['red'] == I.RED_SUM
            and exp['su_nout'] == 8 and exp['su_d_nin'] == I.DYN_T
            and exp['a_base'] == scores and exp['d_base'] == scores, 'golden exponent/sum stage')
    require(pv['me_xbase'] == scores and pv['me_nout'] == 128 and pv['me_d_k'] == I.DYN_T,
            'PV dynamic context and score input')
    require(recip['unit'] == I.UNIT_SU and recip['sfu'] == I.SFU_RECIP
            and recip['a_base'] == exp['r_base'] and recip['su_nin'] == 8, 'golden reciprocal stage')
    require(norm['unit'] == I.UNIT_SU and norm['dst'] == I.DST_VM and norm['ma'] == I.MA_AB
            and norm['a_base'] == att and norm['b_base'] == recip['d_base']
            and norm['su_nout'] == 8 and norm['su_nin'] == 128, 'golden ATTN publication stage')
    require(projection['unit'] == I.UNIT_ME and not projection['me_wsrc']
            and projection['me_xbase'] == attn and projection['me_nout'] == 4096,
            'suffix must consume actual ATTN in output projection')
    q_writes = [op for op in ops[:first] if op['unit'] == I.UNIT_SU and op['dst'] == I.DST_VM
                and op['d_base'] in (qr, qr + 64)]
    require(len(q_writes) == 2 and all(op['su_nout'] == 8 and op['su_nin'] == 64 for op in q_writes),
            'prefix must produce both QR halves')
    require(sum(op['unit'] == I.UNIT_SU and op['dst'] == I.DST_KV for op in ops[:first]) == 3,
            'prefix must retain actual K/V writers')
    # Copy the source's drained END. It flushes QR/KV arithmetic before near
    # launch; the RTL still needs its actual write-ACK/link visibility fences.
    prefix_end = words[ends[0] - 1]
    suffix = first + 5
    result = words[:first] + [prefix_end] + words[suffix:]
    suffix_base = first + 1
    result[suffix_base] = control_patch(result[suffix_base])
    delta = 1 - (suffix - first)
    new_desc = [encode_near(qr, attn, 0)]
    for i, (desc, base) in enumerate(zip(descriptors, bases)):
        new_base = suffix_base if i == 0 else base + delta
        require(0 <= new_base < 4096, 'rebased suffix PAW12 aperture')
        new_desc.append((desc & ~(0xffff << 32)) | (new_base << 32))
    return result, new_desc, dict(
        source_prefix_pcs=list(range(first)), source_removed_attention_pcs=list(range(first, suffix)),
        source_suffix_pc=suffix, prefix_END_pc=first, suffix_program_base=suffix_base,
        qr_base=qr, attn_base=attn, query_bf16_beats=32, result_fp32_elements=1024,
        projection_control_patch=dict(chase=0, chase_n=0, chase_rows=0, barrier=1),
        normal_descriptor_nonbase_bits_unchanged=True, arithmetic_fields_unchanged=True,
        added_core_launches=1, added_END_instructions=1, added_descriptors=1,
        removed_attention_instructions=suffix - first, measured_extra_cycles=None,
        exact_RTL=False, composed_gain=None, adopt=False)


def emit(source, output, *, program_sha256, descriptors_sha256, enable=False):
    require(enable, 'descriptor3 image transform default off')
    source, output = Path(source).resolve(strict=True), Path(output)
    require(sha(source / 'program.hex') == program_sha256
            and sha(source / 'segments.hex') == descriptors_sha256, 'actual source image pins')
    words = [int(x, 16) for x in (source / 'program.hex').read_text().split()]
    desc = [int(x, 16) for x in (source / 'segments.hex').read_text().split()]
    words, desc, record = derive(words, desc, enable=True)
    payloads = ('matrix_int8.hex', 'matrix_scale_bf16.hex', 'crom.hex')
    require(all((source / name).is_file() for name in payloads), 'original matrix/constant payloads required')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'program.hex').write_text(''.join(f'{w:0256x}\n' for w in words))
    (output / 'segments.hex').write_text(''.join(f'{d:016x}\n' for d in desc))
    for name in payloads:
        os.symlink((source / name).resolve(), output / name)
    record.update(source=str(source), source_program_sha256=program_sha256,
                  source_descriptors_sha256=descriptors_sha256,
                  program_sha256=sha(output / 'program.hex'), descriptors_sha256=sha(output / 'segments.hex'),
                  schema='opentallas.qwen-rom-near-descriptor-images.v1', payloads_regenerated=False)
    (output / 'descriptor_binding.json').write_text(json.dumps(record, indent=2) + '\n')
    require(sha(source / 'program.hex') == program_sha256
            and sha(source / 'segments.hex') == descriptors_sha256, 'normal source images changed')
    return record
