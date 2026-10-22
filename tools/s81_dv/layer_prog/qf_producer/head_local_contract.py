#!/usr/bin/env python3
"""Private source contract: retag genuine wq_b returns into the unchanged QR layout.

No value generation, hardware or production image/binding installation. A caller
must supply the real semantic row identity and install both image tags and CAP
cfg atomically after actual return-calendar/port/lifetime proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools/s81_slice'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cap_model import decode
from lower_vpx import _vp


def storage_offset(dimension):
    if not 0<=dimension<512:raise ValueError('not a real512-dimension head')
    if dimension<448:return dimension
    s=dimension-448
    word=64+8*(s//4)+(s%4)
    return 64*(2+5*(word//64))+(word%64)


def retag_return(tag, *, head, dimension):
    """Retag only an actual rank-local semantic wq_b row, preserving tree/pos."""
    if not 0<=head<16 or not 0<=dimension<512:raise ValueError('identity out of range')
    old=(tag>>13)&65535
    if old&0x8000:raise ValueError('SENT/padding cannot become a real wq_b value')
    if (old&0x3fff) != 512*head+dimension:
        raise ValueError('foreign semantic row; phase-local tags cannot be passed as rank-local')
    row=(old&0xc000)|1024*head|storage_offset(dimension)
    return (tag&~(65535<<13))|(row<<13)


def config(head, *, row_flags):
    if row_flags not in (0,1):raise ValueError('unknown/SENT source flags')
    return dict(obase=0,ops=0,np=0,fmt=2,rbase=(row_flags<<14)+1024*head,rcnt=828,
                rsplit=0,lo32=0,hi32=0)


def capword(c):
    return c['obase']|c['ops']<<12|c['np']<<24|c['fmt']<<27|c['rbase']<<29|c['rcnt']<<45


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    heads=[];total=0;bad_flag_rejects=0;wrong_stride=0;source_identity_rejects=0
    for h in range(16):
        cfg=config(h,row_flags=1);values=[];seen=set()
        for d in range(512):
            # All partials of each real semantic row share this storage tag;
            # lower13 golden-tree bits are preserved verbatim by the adapter.
            old=(0x4000+512*h+d)<<13|0x3ff
            t=retag_return(old,head=h,dimension=d)
            assert t&8191==old&8191 and t>>29==old>>29
            assert ((t>>27)&3)==((old>>27)&3)
            bad,leaf,port,word,_=decode(t,0,cfg)
            assert not bad and (leaf,word) not in seen
            assert decode(t,0,config(h,row_flags=0))[0]
            bad_flag_rejects+=1
            seen.add((leaf,word))
            if d<448:
                assert leaf==(d//64)%5 and word==64*((d//64)//5)+d%64
            else:
                s=d-448
                assert leaf==2 and word==64+8*(s//4)+s%4
                wrong_stride+=int(word != 64+s)
            values.append(dict(semantic_dimension=d,reference_eight_frame=d//64,reference_eight_frame_local_row=d%64,
                semantic_rank_row=512*h+d,storage_rank_row=(t>>13)&65535,
                leaf=leaf,word=word,row=word//4,word_in_row=word%4,bank=port))
            total+=1
            # Flags0 also preserve exact address/class; flags2/3 are SENT and
            # are refused, never relabeled as real payload.
            t0=retag_return((512*h+d)<<13|0x3ff,head=h,dimension=d)
            assert decode(t0,0,config(h,row_flags=0))[1:4]==(leaf,port,word)
            try:retag_return(old|(1<<28),head=h,dimension=d)
            except ValueError:pass
            else:raise AssertionError('SENT accepted')
            try:retag_return(old,head=h,dimension=(d+1)%512)
            except ValueError:source_identity_rejects+=1
            else:raise AssertionError('foreign source identity accepted')
        coeff={(2,4*r+k) for r in range(17,48,2) for k in range(4)}
        qrout={(2,4*r+k) for r in range(544,560) for k in range(4)}
        assert seen.isdisjoint(coeff) and seen.isdisjoint(qrout) and coeff.isdisjoint(qrout)
        # Foreign head windows must be rejected by the unchanged CAP decoder.
        for other in range(16):
            if other!=h:
                t=retag_return((0x4000+512*other)<<13,head=other,dimension=0)
                assert decode(t,0,cfg)[0]
        sends=[]
        for i in range(16):
            d=32*i
            if d<448:
                leaf=(d//64)%5;word=64*((d//64)//5)+d%64;row=word//4
            else:leaf=2;row=544+(d-448)//4
            # Four genuine row-pair reads, no final-Q payload materialization.
            sends.append(dict(q_word=i,dimension_first=d,dimension_last=d+31,
                source_slice=h,source_leaf=leaf,first_row=row,last_row=row+7,
                rdout_pairs=4,rdout_body=f'{_vp(6,a0=row,n=4):040x}',
                read_ready_edge=None,central_gather_route=None,
                needs_actual_qr=d>=448))
        # Source shape: actual wq_b K1280/nseg3/10pairs =>6 rows/frame/phase.
        # These are alias CANDIDATES only; real partial live intervals/ports
        # have not been derived. No slots are certified free here.
        candidates=[]
        for p in range(11):
            byslot={}
            for f in range(8):
                for k in range(6):
                    s=6*p+k
                    if s>=64:continue
                    d=64*f+s;slot=storage_offset(d)&63
                    byslot.setdefault(slot,[]).append(d)
            candidates.append(dict(phase_chunk=p,
                slot_alias_candidates={str(s):ds for s,ds in byslot.items() if len(ds)>1},
                actual_partial_lifetimes=None,actual_write_port_calendar=None))
        heads.append(dict(head=h,source_slice=h,rope_leaf=2,capture_cfg=cfg,
            capture_cfg_body=f'{capword(cfg):040x}',
            coefficient_rows=list(range(17,48,2)),
            qr_command=dict(target=0,leaf_mask=4,body=f'{_vp(12,a0=16,n=16,imm=544):040x}',
                            measured_existing_duration=57,new_duration_claimed=False),
            values=values,source_word_reads=sends,reference_eight_frame_return_slot_candidates=candidates))
    rec=dict(schema='opentallas.s81.head_local_qf_source_contract.v1',
        default_enabled=False,production_installed=False,hardware_added=False,
        new_ff=0,new_macro=0,new_pins=0,added_stage_edges=0,
        source_value_format='original CAP fmt2 and VS QR bf16: canonical BF16-in-FP32',
        actual_row_flags=1,padding_sent_rejected=True,
        real_values_mapped=total,logical_values_per_head=512,
        causal_guard_model=dict(wrong_source_identity_rejected=source_identity_rejects,
            wrong_row_flag_capture_rejected=bad_flag_rejects,
            old_uninterleaved_tail_wrong_addresses=wrong_stride),
        minimum_reserved_bits_per_head=dict(captured_projection=16384,coefficients=2048,qr_output=2048),
        source_files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
            'tools/s81_dv/layer_prog/xs_place.py','tools/s81_dv/layer_prog/xs_calendar.py',
            'tools/s81_dv/layer_prog/lower_vs.py','tools/s81_slice/cap_model.py',
            'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_rt.sv',
            'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vs.sv']},
        heads=heads,
        blockers=['actual imagewriter must install semantic-row-to-storage-tag map, not only bench tags',
                  'all real partial live intervals and both CAP write ports must pass',
                  'actual selected 6/7/8-frame wq_b calendar/RETIRE and fixed row lifetime not emitted',
                  'head-local leaf2 QR/coeff cmd placement requires exact new compiler profile',
                  'actual 16head-to-central6/8 gather incl tier crossings/local reads unproved',
                  'full runtime source/consumer originalgold/deadlines/mutants not run',
                  'native parent and MU context lifetime not qualified'],
        qualification='ADDRESS_SOURCE_MODEL_ONLY; no token/gather/return-calendar closure')
    (out/'contract.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('HEAD_LOCAL_ADDRESS_MODEL_PASS values=8192 headwindows=16 tailcoeffoutput_disjoint=1 native_calendar=UNPROVED')
    print('SOURCE_GUARDS wrong_identity_rejected',source_identity_rejects,
          'wrong_flag_rejected',bad_flag_rejects,'old_tail_stride_wrong',wrong_stride)

if __name__=='__main__':main()
