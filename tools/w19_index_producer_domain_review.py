#!/usr/bin/env python3
"""Pinned source-only golden domain audit. No checkpoint or correction implementation."""
import argparse, hashlib, importlib, io, json, pathlib, subprocess, sys, tarfile, tempfile
import numpy as np
PIN="bb38a691ee3e67f3a9faf175c842b94df8b247a8"
FAIL="f036610959c14aeb4d75504c6a26a08bd477bb3f"
ROOT=pathlib.Path(__file__).resolve().parents[1]
PATHS=["tools/hdc_golden.py","tools/hdc_golden_v41.py","tools/w19_hbm_tp96_isa.py","tools/deepseek_hbm_complete_index_ingress.py","tools/deepseek_hbm_complete_index_producer_scope.py"]
def build(out):
    out.mkdir(parents=True,exist_ok=False)
    blobs={p:subprocess.check_output(["git","show",PIN+":"+p],cwd=ROOT) for p in PATHS}
    with tempfile.TemporaryDirectory(prefix="w19-source-domain-") as d:
        for p in PATHS[:2]: pathlib.Path(d,pathlib.Path(p).name).write_bytes(blobs[p])
        sys.path.insert(0,d)
        G=importlib.import_module("hdc_golden"); V=importlib.import_module("hdc_golden_v41")
        def bits(v): return int(np.asarray(v,np.float32).view(np.uint32))
        def observe(name,row):
            row=np.asarray(row,np.float32)
            with np.errstate(all="ignore"):
                am=np.maximum(np.max(np.abs(row)),V.FP4_AMAX_FLOOR_E8M0).astype(np.float32)
                e=int(V._ceil_log2(G.mul(am,V.FP4_MAX_INV)))
                y=V.qdq_fp4_e8m0(row)
            return dict(name=name,input_bits=[bits(x) for x in row],exponent=e,scale_candidate_integer=e+127,output_bits=[bits(x) for x in y],finite_output=bool(np.all(np.isfinite(y))))
        reachable=[]
        for s in range(1,253):
            row=np.full(32,np.float32(6*np.exp2(s-127)))
            r=observe("scale"+str(s),row)
            assert r["scale_candidate_integer"]==s
            reachable.append(s)
        r=observe("finite_scale253",np.full(32,np.float32(6.1*2.0**125)))
        assert r["scale_candidate_integer"]==253 and r["finite_output"]
        reachable.append(253)
        producers=[r]
        values=[("positive_zero",0), ("negative_zero",0x80000000), ("smallest_F32_subnormal",1), ("largest_F32_subnormal",0x007fffff), ("smallest_normal",0x00800000), ("maximum_finite_F32",0x7f7fffff), ("maximum_finite_BF16",0x7f7f0000), ("positive_inf",0x7f800000), ("negative_inf",0xff800000), ("quiet_nan",0x7fc00000), ("signaling_nan",0x7f800001)]
        for name,b in values: producers.append(observe(name,np.full(32,np.array(b,np.uint32).view(np.float32))))
        # Arbitrary encoded scale inputs are a transport domain, not all producer-reachable.
        encoded=[]
        for s in range(256):
            with np.errstate(all="ignore"):
                pre=(V.E2M1*np.exp2(s-127)).astype(np.float32)
                rounded=G.to_bf16(pre)
            encoded.append(dict(scale=s,source_raw_exponent=s-127,pre_BF16_bits=[bits(x) for x in pre],post_BF16_bits=[bits(x) for x in rounded]))
        # Fixed block maximum6 yields scale127; exercise every E2M1 midpoint at F32 neighbors.
        ties=[]
        for mid in V.E2M1_MIDPOINTS:
            for sign in [1,-1]:
                for direction in [-1,0,1]:
                    x=np.float32(sign*mid)
                    if direction:x=np.nextafter(x,np.float32(-np.inf if direction<0 else np.inf))
                    row=np.zeros(32,np.float32);row[0]=6;row[1]=x
                    ties.append(observe("midpoint_"+str(mid)+"_sign"+str(sign)+"_neighbor"+str(direction),row))
        bf=[]
        for b in [0,0x80000000,1,0x00007fff,0x00008000,0x00008001,0x00018000,0x007f8000,0x00800000,0x3f808000,0x3f818000,0x7f7f7fff,0x7f7f8000,0x7f7fffff,0x7f800000,0x7fc00000,0x7fffffff]:
            for sign in [0,0x80000000]:
                x=np.array(b|sign,np.uint32).view(np.float32);bf.append(dict(input_bits=bits(x),output_bits=bits(G.to_bf16(x))))
    report=dict(schema="opentallas.w19.index_full_producer_domain_review.v1",producer_pin=PIN,failure_pin=FAIL,source_pins={p:hashlib.sha256(b).hexdigest() for p,b in blobs.items()},checkpoint_reads=0,correction_implemented=False,
        finite_F32_producer_scale_codes=reachable,finite_F32_producer_scale_range=[1,253],finite_input_always_finite_output=False,
        producer_fixtures=producers,raw_encoded_scale_table=encoded,E2M1_midpoint_fixtures=ties,BF16_RNE_boundaries=bf,
        scale_semantics={"0":"Excluded by producer amax floor; raw checkpoint decoder subtracts127 and does not reject. Explicit transport reject/accept policy required.","1..252":"Finite producer-reachable; still preserve producer rounding, subnormal and sign semantics.","253":"Finite producer-reachable. Some decoded outputs finite; E2M1 magnitude4/6 at exponent126 overflow F32 to Inf. Must not blanket reject reachable253 or silently saturate.","254":"Unreachable from finite F32 producer. Raw source exponent127 produces finite small codes and Inf large codes. Explicit foreign-wire validity policy required.","255":"Raw checkpoint scale decoder treats as exponent128, not special NaN. Inf producer input yields candidate255. Source golden behavior is separate from any UE8M0 NaN convention; do not invent or promote a wire convention.","256":"NaN amax can yield exponent129/candidate256; no uint8 code. Never silently mask to0; explicitly reject unsupported producer domain or preserve pinned nonfinite semantics under a separately authorized contract."},
        producer_rounding_order="F32 amax floor; F32 multiply by rounded1/6; bit-based ceil_log2; F64 scale/clamp/grid nearest-even; F32 cast; BF16 bit-add RNE. No fused/reordered quantizer allowed.",
        required_correction_gates=[
            "Finite full-domain positive: all reachable scale1..253, both signs and all E2M1 values, query32/key128 four32-element blocks; compare exact producer output bits at every rounding boundary, not an approximate unpacked value.",
            "Scale transition: below/equal/above each rounded amax*(F32 1/6) power-of-two threshold; preserve F32 multiply BEFORE bit-based ceil_log2. Include 252-to253 finite witness6.1*2**125 and both signs.",
            "E2M1: all seven midpoints (.25,.75,1.25,1.75,2.5,3.5,5), exact tie and adjacent representable inputs, both signs, fixed block maximum to avoid moving scale; nearest-even code, saturation6 and signed-zero behavior. Producer exact -0 canonicalizes+0 while negative nonzero rounding down can produce-0; transport code8 is a distinct raw-0.",
            "Subnormal/BF16: F32 min/max subnormals and normal boundary, producer amax floor and first nonzero quantized value; BF16 discarded-bit half ties with retained even/odd LSB, signed underflow and normal carry. No FTZ unless golden does it.",
            "Overflow: scale253 finite magnitudes0..3 and Inf magnitudes4/6, both signs; largest finite F32 and BF16 producer inputs; BF16 overflow threshold0x7f7f8000 and neighbors. Do not clamp, reject all253, substitute real-number integer score or hide Inf under finite-only equality.",
            "Foreign scale negative: full encoded0..255 x16 E2M1 table. Scale0/254 are finite-producer unreachable; record explicit actual transport validity policy. At255 raw source exponent128 has both finite and Inf code results, not universal NaN. Do not confuse raw decoder behavior with a standards convention.",
            "Nonfinite producer: +/-Inf, quiet/signalingNaN and mixed finite+nonfinite block with exact retained output policy. Candidate integer256 must never uint8-wrap to0; reject unsupported source input explicitly or obtain authorized changed numerical contract before admission.",
            "Packed producer binding: actual retained producer stores decoded BF16-valued F32, not68B bytes. Require explicit code/scale output and low-nibble-first order, four block scales, partial-row masks and publication visibility from producer through actual ingress; no fixture packer credited as production endpoint.",
            "Downstream closure: decode currently requires finite alreadyBF16 QDQ blocks. Bind overflow/nonfinite handling through actual score/reduction/select boundary; a finite-input producer that outputs Inf is not covered by ingress scale extension alone.",
            "Negative preservation: keep historical eef/de0 partial and bb38/f036 DOMAINFAIL immutable, compare correction only after full domain declared. OrdinaryGPU integer/round/pack costs and finite RF/shared publication priced before RTL; no physical/adoption credit from this source oracle."
        ],
        original_partial_candidate="1..252 only, not full production domain; historical partial evidence remains unchanged",hardware_admission=False,adopt=False)
    (out/"review_r1.json").write_text(json.dumps(report,indent=2)+"\n")
    manifest={"historical/"+PIN+"/"+p:hashlib.sha256(b).hexdigest() for p,b in blobs.items()}
    with tarfile.open(out/"source_snapshot.tar.gz","w:gz") as t:
        for p,b in blobs.items():
            i=tarfile.TarInfo("historical/"+PIN+"/"+p);i.size=len(b);i.mtime=0;t.addfile(i,io.BytesIO(b))
    (out/"snapshot_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(dict(reachable=[1,253],encoded_scale_cases=256,encoded_code_cases=4096,midpoint_cases=len(ties),BF16_boundaries=len(bf),checkpoint_reads=0,admission=False)))
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--out",type=pathlib.Path,required=True);build(a.parse_args().out)
