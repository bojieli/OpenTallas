"""Default-off serial drafter epilogue using the real shared target LM head.

Keep the explicit drafter final norm and all FP32 base logits in VM. The
released Markov head adds W2(W1[previous]) AFTER this projection, then selects
argmax. An ME argmax here would discard information and change that contract.
No weights, model inference, new engine RTL or overlap are introduced.
"""
import copy

import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_program_w12 as FP
import qwen_rom_verify_program_w12 as V
from qwen_rom_dspark_draft_isa import freeze_dyn
from qwen_rom_dspark_images import encode_program


def base_logits_program(lay, head_row, final_norm_base, slots, start, *, enabled=False):
    if not enabled:
        raise ValueError('DSpark head epilogue is default-off')
    if lay.tp != 4 or slots not in (3, 7) or start < 0 or start+slots > FP.TMAX:
        raise ValueError('requires TP4 and a valid drafter position block')
    if (head_row['rows'], head_row['columns']) != (37984, 4096) or final_norm_base < 0:
        raise ValueError('requires the actual shared target head and drafter norm')
    proxy = copy.copy(lay)
    proxy.cb = dict(lay.cb, final=final_norm_base)
    proxy.mat = dict(lay.mat)
    proxy.mat['lm_head'] = {'base': head_row['base'], 'n': head_row['rows'],
                          'k': head_row['k_per_split'], 'tiles': head_row['rounds'],
                          'split': head_row['split'], 'scale_base': head_row['scale_base']}
    vms, end = V.vm_map_p(slots)
    bases = [end + j*37984 for j in range(slots)]
    # Existing companion VM has 1M elements. Leave one reusable W2 output
    # after all base rows; W2(previous) is consumed one slot at a time.
    bias_base, vm_end = end + slots*37984, end + (slots+1)*37984
    if vm_end > 1 << 20:
        raise ValueError('base logits plus one bias row exceed companion VM')
    out = []
    for j, vm in enumerate(vms):
        with FP.program_geometry(vm):
            program = P.build_program(proxy, layers=[], embed=False, head=True,
                                      wchunk=512, scale_bases=True)
        for f in program:
            if f['unit'] == I.UNIT_END:
                continue
            f = freeze_dyn(f, proxy, start+j, start+slots)
            if f['unit'] == I.UNIT_ME:
                # Original chunk address is already its own output-row offset.
                # Preserve nout, tile/K geometry and true BF16 row-scale address.
                f.update(me_obase=f['me_obase'] + bases[j]//I.W_LANES,
                         me_oen=1, me_amax=0, me_amc=0, me_row0=0)
            out.append(f)
    out.append(dict(unit=I.UNIT_END, barrier=1, chase=0,
                    _coll=(P.COLL_END, 0, 0, 0)))
    return out, {'base_logits_vm': bases, 'markov_bias_vm': bias_base,
                 'vm_elements': vm_end, 'rank': lay.die,
                 'vocabulary_row0': lay.die*37984,
                 'binding_required': 'actual base+W2 biased stream argmax and inter-rank argmax'}


def encode_base_logits(lay, head_row, final_norm_base, slots, start, *, enabled=False):
    program, layout = base_logits_program(lay, head_row, final_norm_base, slots, start,
                                         enabled=enabled)
    words, desc = encode_program(program)
    return words, desc, layout
