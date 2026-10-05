#!/usr/bin/env python3
"""Actual SU adapter: QK score -> exp score, sink denominator, post-PV divide.

H16, D512, T128/T640; bounded N16/M8 ports, synchronous one-cycle VM.
PV itself is outside this gate. Its accumulator input is a deterministic fixture.
No probability reference is injected into RTL. Whole VM compares bit for bit.
"""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
import rtl_hdc_v41x_vec_campaign as C
import hdc_golden as G
import hdc_golden_v41 as V
import hdc_isa_v41 as I

ROOT = Path(__file__).resolve().parents[1]


def fixture(tokens, scores_hex=None, pv_acc_hex=None):
    h, d = 16, 512
    score, maximum, total, den, acc = 0, 16384, 16400, 16416, 17408
    vm = np.zeros(1 << 15, dtype=np.uint32)
    # Finite, signed scores with cancellation and unequal maxima across heads.
    x = np.arange(h * tokens, dtype=np.int64).reshape(h, tokens)
    scores = (((x * 37 + x // tokens * 19) % 1021) - 510).astype(np.float32) / np.float32(32)
    if scores_hex is not None:
        scores = C.ffrom(C.read_hex(scores_hex).astype(np.uint32)).reshape(h, tokens)
    vm[:h*tokens] = C.fbits(scores).reshape(-1)
    accumulator = (((np.arange(h*d) * 23) % 509) - 254).astype(np.float32) / np.float32(17)
    if pv_acc_hex is not None:
        accumulator = C.ffrom(C.read_hex(pv_acc_hex).astype(np.uint32)).reshape(h*d)
    vm[acc:acc+h*d] = C.fbits(accumulator)
    cr = np.zeros((16, 2), dtype=np.uint32)
    cr[:, 0] = C.fbits(np.arange(h, dtype=np.float32) / 16 - 0.5)
    mem = C.Mem(vm, np.zeros(16, np.uint32), cr, np.zeros(16, np.uint16))
    def op(**kw):
        return dict(C.op_defaults(), w_idle=1, **kw)
    common = dict(nout=h, nin=tokens, abase=score, aso=tokens, asi=1,
                  dst=I.DST_VM, obase=score, oso=tokens, osi=1)
    ops = [op(**common, m1=I.M1_AIMM, imm1=C.f32u(512 ** -0.5), red=I.RED_MAX, rbase=maximum, rso=1),
           op(**common, bbase=maximum, bso=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, red=I.RED_SUM, rbase=total, rso=1),
           op(nout=1, nin=h, asrc=I.SRC_CLO, asi=1, bbase=maximum, bsi=1,
              ad=I.AD_NEGB, sfu=I.SFU_EXP, cbase=total, csi=1, e1=I.E1_ADDC,
              dst=I.DST_VM, obase=den, osi=1),
           op(nout=h, nin=d, abase=acc, aso=d, asi=1, bbase=den, bso=1,
              m1=I.M1_DIVB, rnd=1, dst=I.DST_VM, obase=acc, oso=d, osi=1)]
    # Direct golden arithmetic follows Builder.attention and Machine.su1.
    expected = mem.copy()
    scaled = G.mul(scores, np.float32(512 ** -0.5))
    maxima = scaled.max(axis=1)
    exps = G.exp(G.add(scaled, G.neg(maxima[:, None])))
    sums = V.csum(exps)
    denominator = G.add(G.exp(G.add(C.ffrom(cr[:, 0]), G.neg(maxima))), sums)
    result = G.to_bf16(V.div(accumulator.reshape(h,d), denominator[:,None]))
    for base, data in ((score,exps), (maximum,maxima), (total,sums), (den,denominator), (acc,result)):
        expected.vm[base:base+data.size] = C.fbits(data).reshape(-1)
    regions = dict(exp_scores=(score,h*tokens), maximum=(maximum,h), exp_sum=(total,h), denominator=(den,h), output_bf16=(acc,h*d))
    return mem, ops, expected, regions


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--build-dir', type=Path, default=ROOT/'build/v41x_su_softmax')
    ap.add_argument('--output', type=Path, default=ROOT/'results/rtl/v41x_su_softmax.json')
    ap.add_argument('--reuse', action='store_true')
    ap.add_argument('--tokens', type=int, choices=(128,640), nargs='+', default=[128,640])
    ap.add_argument('--scores-hex', type=Path, help='actual QK FP32 words, head major; requires one token count')
    ap.add_argument('--pv-acc-hex', type=Path, help='actual PV FP32 accumulator words, head major')
    args=ap.parse_args()
    if args.scores_hex or args.pv_acc_hex:
        assert len(args.tokens)==1, 'external operands require one token count'
    obj=args.build_dir.resolve(); obj.mkdir(parents=True,exist_ok=True)
    C.write_fields_svh()
    if not args.reuse:
        cmd=[C.VERILATOR,'--cc','--exe','--build','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNOPTFLAT',
             '--top-module','tb_hdc_v41x_su_softmax','--prefix','Vtb','-Mdir',str(obj),
             '-GN=16','-GM=8','-GLV=7','-GVMA=15','-GKVA=4','-GCRA=4','-GWRA=4','-GXBA=4','-GPMAX=8',
             f'-I{ROOT / "rtl/test"}',*map(str,C.LIB),*map(str,C.RTL),
             str(ROOT/'rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv'),str(ROOT/'rtl/test/tb_hdc_v41x_su_softmax.sv'),
             str(C.HARNESS),'-CFLAGS','-O1','-j','4']
        with (obj/'build.log').open('w') as log:
            subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    records=[]
    for tokens in args.tokens:
        mem,ops,expected,regions=fixture(tokens,args.scores_hex,args.pv_acc_hex)
        case=obj/f't{tokens}'; C.write_case(case,mem,ops)
        tr=C.run_case(obj/'Vtb',case,len(ops))
        mismatches={name:int(np.count_nonzero(tr['vm'][base:base+n] != expected.vm[base:base+n])) for name,(base,n) in regions.items()}
        # Export chronological two-token x sixteen-head BF16 beats for actual PV.
        p=G.to_bf16(C.ffrom(tr['vm'][:16*tokens]).reshape(16,tokens)).view(np.uint32) >> 16
        C.write_hex(case/'pv_exp_bf16.hex',p.T.reshape(-1),16)
        records.append(dict(heads=16,tokens=tokens,head_dim=512,mismatches=mismatches,
             whole_vm_mismatches=int(np.count_nonzero(tr['vm'] != expected.vm)),
             accepted=tr['acc'],end_cycle=tr['end'],completed=tr['end'] is not None and tr['end'][1]=='ok',faults=tr['faults'],order_faults=tr['orders'],
             emits={k:[min(v),max(v),len(v)] for k,v in tr['emits'].items()},
             results={k:[min(v),max(v),len(v)] for k,v in tr['ress'].items()}))
    report=dict(contract='unnormalized FP32 exp scores; BF16 at PV operand boundary; sink DEN; post-PV divide then BF16',
                score_source=str(args.scores_hex) if args.scores_hex else 'deterministic fixture',
                pv_acc_source=str(args.pv_acc_hex) if args.pv_acc_hex else 'deterministic fixture',
                lanes=16,sfu_lanes=8,reducer_levels=8,pv_included=False,cases=records)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    assert all(r['completed'] and r['whole_vm_mismatches']==0 and r['faults']==0 and r['order_faults']==0 for r in records)

if __name__=='__main__': main()
