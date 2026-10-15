#!/usr/bin/env python3
"""Lower one contiguous elementwise SFU operation to fixed control words.

The accepted instruction class is explicit: independent vector elements with
four contiguous/scalar operands and contiguous VM output. Gather, reductions, scalar
side operations and overlap are refused. Those need their own real lowering;
this routine never silently changes their memory or arithmetic contract.
Each of the four arithmetic opcode groups remains stable through a full drain,
so there are no data-dependent controller decisions or in-flight op conflicts.
"""
from __future__ import annotations
from sfu_control_image import pack

SFU_DEPTH = {0: 0, 1: 94, 4: 122, 5: 122} # MLAT6 ALAT6 DDIV21 DENR1


def compile_vector(*, words: int, bases: tuple[int, int, int, int, int],
                   m1: int=0, m2: int=0, ad: int=0, sfu: int=0,
                   e1: int=0, e2: int=0, imm1: int=0x3f800000,
                   imm2: int=0x3f800000, imm3: int=0x3f800000,
                   arnd: int=0, arelu: int=0, amin: int=0, cclip: int=0,
                   rnd: int=0, strides: tuple[int,int,int,int,int]=(1,1,1,1,1)) -> dict:
    if not isinstance(words, int) or not 1 <= words < 1 << 24:
        raise ValueError('vector length must fit 24-bit nonzero lane count')
    if len(bases) != 5 or any(not 0 <= base <= (1 << 24)-words for base in bases):
        raise ValueError('five contiguous regions must fit the 24-bit address space')
    if any(not isinstance(value, int) or not 0 <= value < 1 << 32 for value in (imm1, imm2, imm3)):
        raise ValueError('immediates must be exact unsigned FP32 bit patterns')
    if sfu not in SFU_DEPTH:
        raise ValueError('scalar side operations require actual side-unit lowering')
    if not 0 <= m1 <= 6 or not 0 <= m2 <= 2 or not 0 <= ad <= 5 or not 0 <= e1 <= 4 or not 0 <= e2 <= 2:
        raise ValueError('reserved arithmetic opcode')
    if len(strides)!=5 or any(stride not in (0,1) for stride in strides) or strides[4]!=1:
        raise ValueError('operand strides are contiguous1 or actual scalar-broadcast0; output must be contiguous')
    # 5 stream offsets, ten hardware term positions per stream. Only four
    # positions are used by sixteen lanes. Offsets are loaded before emitting.
    terms = sum((strides[stream] << bit) << (24*(stream*10+bit)) for stream in range(5) for bit in range(4))
    imm3_key = (~imm3 & 0xffffffff) if imm3 >> 31 else imm3 | 0x80000000
    fields = dict(ld_bank=0, bank=0, no=1, ni=words, ls=4, lvw=4, ld_c=terms,
                  dst=1, cx_arnd=arnd, cx_arelu=arelu, cx_amin=amin, cx_cclip=cclip,
                  cx_imm3=imm3_key, cp_m1=m1, cp_imm1=imm1, cm_m1=m1,
                  cm_m2=m2, cm_imm1=imm1, ca_ad=ad, ca_imm2=imm2,
                  ci_sfu=sfu, cs_sfu=sfu, cs_e1=e1, cs_imm2=imm2,
                  ce_e2=e2, ce_imm1=imm1, co_rnd=rnd, co_dst=1)
    beats = (words+15)//16
    # All controls stay stable through the exact arithmetic horizon. The load
    # lead exceeds the actual three-edge offset-bank load (no ready polling).
    lead = 8
    # Base pipeline: pin1 + map4 + physical input1 + leaf/fetch5 + pre1 +
    # M1(7 or22) + M2 6 + AD7 + E1 7 + E2 6 + output1 =46/61.
    horizon = 46 + (15 if m1 in (4,5) else 0) + SFU_DEPTH[sfu]
    rows = []
    for cycle in range(lead+beats+horizon):
        beat = max(0, min(cycle-lead, beats-1))
        bases_now = sum((base+16*beat*strides[i]) << (24*i) for i,base in enumerate(bases))
        row = dict(fields, ld=int(cycle == 0), emit=int(lead <= cycle < lead+beats),
                   i_v=16*beat, vb=bases_now)
        rows.append(dict(cycle=cycle, fields=row))
        pack(row) # Fail on any accidentally overflowing control field.
    return dict(cycles=len(rows), rows=rows, vector_words=words,
                vector_beats=beats, load_lead=lead, drain_horizon=horizon,
                production_qualification=False)
