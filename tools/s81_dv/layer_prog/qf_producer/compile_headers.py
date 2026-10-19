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
    owners=[]
    for h in range(16):
        owners.append(dict(head=h,wqb_slice=h,
            capture_chunks=[dict(dim_first=64*c,dim_last=64*c+63,
                leaf=c%5,word_first=64*(c//5),word_last=64*(c//5)+63)
                for c in range(8)],
            original_rope=dict(slice=h//5,leaf=h%5),
            head_local_rope_candidate=dict(slice=h,leaf=2),
            raw_tail_source=dict(leaf=2,word_first=64,word_last=127),
            interleaved_tail_target=dict(first_row=512,last_row=542,stride=2),
            coefficient_target=dict(first_row=513,last_row=543,stride=2),
            output_target=dict(first_row=544,last_row=559)))
    return dict(schema='opentallas.s81.qf_source_model.v1',
        ownership=owners,
        preferred_model_only='head-local RoPE on actual projection owner leaf2',
        ownership_choices=[
            dict(name='head_local',remote_tail_transfers=0,
                 local_tail_row_permutations=256,static_coefficient_writes=256,
                 q_tail_raw_bits=32768,
                 reserved_existing_qr_sram_bits=98304,
                 new_sram_count=0,extra_state_ff=None,extra_logic_area_um2=None,
                 minimum_tail_copy_write_edges_per_head=16,
                 copy_pipeline_edges=None,
                 new_mechanism='source-dependent row scatter/permutation or separate coefficient read',
                 available_in_current_rtl=False),
            dict(name='keep_original_rope_ownership',remote_head_tails=15,
                 same_slice_cross_leaf_tails=1,
                 cross_tier_head_tails=sum((h%2)!=(h//5%2) for h in range(16)),
                 q_tail_raw_bits=32768,
                 local_tail_row_permutations=256,
                 minimum_tail_copy_write_edges_per_head=16,
                 route_edges=None,extra_state_ff=None,extra_logic_area_um2=None,
                 available_in_current_rtl=False)],
        source_shape=dict(heads=16,dimensions=512,q_bf16_bits=131072,
                          own_row_code_scale_bits=4224),
        q_half_payload_words=128,q_half_existing_span=128,
        xr_pairs_per_q_word=2,xr_minimum_edges_per_word=2,
        q_half_lower_bound_span=255,minimum_added_edges_per_half=127,
        two_half_payload_span_only_added_edges=254,
        combined_q_frames_words=258,combined_q_frames_existing_span=258,
        combined_q_frames_lower_bound_span=515,
        combined_q_frames_lower_bound_added_edges=257,
        serialized_startup_and_ctl_contention_included=False,
        schedule_mutation_permitted=False,
        hardware_added=False,whole_token_delta=None,
        source_contract=dict(
            wqb='xs_place.op_groups(attn.wq_b): head h slice h; 8 frames/head',
            capture='xs_calendar.cmd_cap first wqb allocation obase0, e>>6 mod5, word64*(chunk//5)+e%64',
            qrope='lower_vs.shares uses G=5sid+leaf; QR needs interleaved q/coefficient row pairs',
            current_sends='XR lo accepts raw256-bit FP32 row pairs; no BF16 compacting B mode',
            vq='existing QB/VQ produces XB1024 in four fragments; no VQ→XR lo/B binding',
            ownrow='lower_svc fixture fp8_row_codes is reference construction, not runtime RTL producer'),
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
