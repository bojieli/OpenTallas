#!/usr/bin/env python3
"""Opt-in actual configuration-header producer; runtime operand lowering stays open.

These CTLs write job-derived configuration into the existing VP SRAM, then
RDOUT it through the real XR HB1 packer. No q-pin payload image is produced.
This is a bounded compiler component, not a replacement for Job.schedule().
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lower_vpx import send_cfg, _vp, _payload


def header(typ, tag, spec, pos, user):
    if not (0 <= tag < 256 and 0 <= user < 1024 and 0 <= pos < 2**21):
        raise ValueError('invalid configured identity')
    return typ << 508 | 1 << 503 | tag << 495 | pos << 459 | user << 449 | spec


def compile_headers(tag, *, sid=6, leaf=0, wb=256, sb=4096, user=3,
                    pos=777, window=128, stack=0, po=395, pvo=482, pio=285):
    """Existing target5 row writes -> target0 RDOUT -> target4 SEND-B.

    Caller must reserve rows480..491 and the actual CTL/VP ports. Configuration
    can be boot-written; no runtime Q, own-row code, SMJ operand or sink values
    may enter this function. No adoption happens without actual port-calendar
    composition. Times below are this component's local XR input edge domain.
    """
    if not (sid in (6, 8) and 0 <= leaf < 5 and 0 <= stack < 4 and 1 <= window <= 128):
        raise ValueError('not a central HB1 producer/profile')
    values = [
        ('CFG', header(12, tag, wb | 1 << 32 | stack << 30, pos, user)),
        ('WIN_LOAD', header(2, tag, sb | window << 81 | (pos-window+1) << 99, pos, user)),
        ('GO', header(13, tag, po | pvo << 16 | pio << 32, pos, user)),
    ]
    ctl = []
    for i, (name, word) in enumerate(values):
        row = 480 + 4*i
        for k in range(4):
            body = row+k | 15 << 10 | ((word >> (128*k)) & (2**128-1)) << 14
            ctl.append(dict(cycle=32+4*i+k, target=5, body=body,
                            payload=_payload(1 << sid, 5, 1 << leaf, body), kind='config_row'))
        # First two configuration headers deliberately share one continuous
        # four-pair RDOUT. Real SEND-B emits them two edges apart, not one.
        if i == 1:
            continue
        # Separate each command from all writes and neighbouring lo streams.
        t = 90 + i*50
        for cycle, target, body, kind in [
            (t, 4, send_cfg('B', 4, 0, 1 << sid, leaf, row, 2), 'send_b'),
            (t+2, 0, _vp(6, a0=row, n=4 if i == 0 else 2), 'rdout'),
        ]:
            ctl.append(dict(cycle=cycle,target=target,body=body,
                            payload=_payload(1 << sid,target,1 << leaf,body),kind=kind))
    return dict(schema='opentallas.s81.qf_config_source.v1', enabled_by_default=False,
                tag=tag,sid=sid,leaf=leaf,register_delta=0,macro_delta=0,
                reserved_existing_sram_bits=1536, reserved_rows=[480,491],
                ctls=sorted(ctl,key=lambda x:x['cycle']),
                frames=[dict(name=n,word=f'{w:0128x}') for n,w in values],
                runtime_payloads_lowered=False,production_calendar_admitted=False)


def model():
    # One 512-bit q word consumes two 256-bit lo pairs. pk_go is observed on
    # the following edge, overlapping next packet's first pair: rate1/2.
    # Existing consumer schedule has 128 consecutive payload words per Q half.
    return dict(schema='opentallas.s81.qf_source_model.v1',
        source_shape=dict(heads=16,dimensions=512,q_bf16_bits=131072,
                          own_row_code_scale_bits=4224),
        q_half_payload_words=128,q_half_existing_span=128,
        xr_pairs_per_q_word=2,xr_minimum_edges_per_word=2,
        q_half_lower_bound_span=255,minimum_added_edges_per_half=127,
        whole_q_contiguous_lower_bound_added_edges=254,
        serialized_startup_and_ctl_contention_included=False,
        schedule_mutation_permitted=False,
        hardware_added=False,whole_token_delta=None,
        storage=[dict(use='configuration header rows',bits=1536,new_hardware=False),
                 dict(use='complete Q BF16 staging',bits=131072,macro_required=True,
                      actual_macro_count=None,area_um2=None,producer_mapping=None)],
        unresolved=['actual projection output producer placement',
                    'non-RoPE Q 448 dimensions per head runtime rows',
                    'RoPE tail rows gather from 16 head leaves',
                    'FP32-in-row BF16 compaction before 512-bit Q word packing',
                    'actual FP8 own-row encoder and scale producer',
                    'header/SMJ parameter source state and user-slot lifetime',
                    'two central SEND-B calendars plus actual route/reset phase',
                    'burst serializer or consumer-calendar recompilation pricing'],
        qualification='CONFIGURATION_COMPONENT_ONLY; runtime QF producer blocked')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    plans=[]
    for tag in (0, 1, 53, 127, 128, 213, 254, 255):
        p=compile_headers(tag);plans.append(p)
        (out/f'ctl_{tag}.hex').write_text(''.join(f'{c["cycle"]:08x} {c["payload"]:046x}\n' for c in p['ctls']))
        (out/f'gold_{tag}.hex').write_text(''.join(x['word']+'\n' for x in p['frames']))
    (out/'plans.json').write_text(json.dumps(plans,indent=2)+'\n')
    (out/'model.json').write_text(json.dumps(model(),indent=2)+'\n')
    print('COMPILED_CONFIG_HEADERS tags=8 frames=24 actual_target5_rdout_send_b=1 runtime_payloads=0')

if __name__=='__main__':main()
