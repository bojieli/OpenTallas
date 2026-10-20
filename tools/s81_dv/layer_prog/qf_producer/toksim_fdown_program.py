#!/usr/bin/env python3
"""TOKSIM-S81B/FDOWN 10-19: ffn.down full-slice vehicle programme on the fullsix sid6 slice (6 real frames).

The rows one slice owns (xs_place.op_groups('ffn.down'): per expert -- shared + the 6 routed experts of the fixture --
the rank's 1,280 output rows dealt 80 / slice; slice 6 = rows 480..559), dealt over the slice's 6 frames (14/14/13/13/13/13),
real K 2304 (shared FP8 32x32-block scales, routed FP4 per-row scales), real rows of the released checkpoint fixture
(layerbench-s81 L0, meta sha d7f2eb61 = the sid6 fixture's), x = bf16(route_w) of each expert (bf16(shared.swiglu)),
quantised FP8 (q family) exactly as golden_vals.  Epoch = one field phase per frame: 4 rows / frame (10 q pairs, nseg 5),
4 epochs / expert, 28 epochs.  Every epoch is legalised by frame_return_plan.plan_phase (xs_place.phase_plan, MEASURED
ELEM_SEG fp4/fp8 K2304 nseg5), placed in ONE multi-phase Field per frame, serialised to the fullsix ROM image names;
the xs calendar per epoch is xs_calendar.compile_phase (same as retained_xs_program.py), epoch i issued at
1100 + P i + G e(i) (e = expert index; the gap G lets the single-parity x buffer reload the next expert's x after the
previous expert's last stream read).  Each expert's first epoch opens a gather window (is_d gw, parity 0); the TB
(toksim_fdown_tb.py) then delivers that expert's 36 FP8 beats at the xs g pins.
Row tags are retagged unique per (epoch, row): tag row = 8 epoch + r (the CAP is not the measured scope).
Outputs: model/ (xs ROMs, source_ctl.txt, contract.json with every row's golden segment sums / acc / bf16 and the
fixture tie), images/ (1012 frame images + xs ROMs), expected_xq.mem, expected_reads.mem, rows.json.
"""
import argparse, hashlib, json, os, shutil, sys
from pathlib import Path
os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
from head_local_contract import ROOT
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
sys.path.insert(0, str(ROOT / 'tools/s81_suhc'))
sys.path.insert(0, str(ROOT / 'tools/s81_slice'))
import numpy as np
import xs_place as XP
import lower_xs as LX
import xs_calendar as XC
import frame_return_plan as P
import frame_bench as B
import v41_die_images_w17w10 as I
from pq_calendar import viamap
from lower_vs import ctl_payload
from field_cfg7_image import encode_bank, decode_bank
from cap_model import golden_row
import hc_gate as HG
import hdc_golden_v41 as G

NB = 36  # 64-element beats of K 2304


def issue(epochs, P, Gp):
    issuers = {}
    for e in epochs:
        i, gi, c = e['epoch'], e['expert_index'], e['chunk']
        shift = 1100 + P * i + Gp * gi
        for t, v in e['iss'].items():
            t, v = int(t), int(v, 16)
            if t == XC.GW_IT and c:
                continue
            if t == XC.T_OFFCFG and i:
                continue
            if t in (XC.TS - 20, XC.TS):
                v = XC.isd(**({'prime': 1} if t == XC.TS - 20 else {'start': 1}), base=e['calendar_base'], length=e['calendar_rows'])
            assert shift + t not in issuers, ('issuer edge collision', i, t)
            issuers[shift + t] = v
    its = sorted(issuers)
    for t in its:
        assert len([j for j in its if j <= t < j + XC.OFF + 2]) <= XC.ND, ('issuer delay line over-full', t)
    return issuers


def ctl_only(a):
    base, out = Path(a.ctl_only), Path(a.out)
    rec = json.loads((base / 'model/contract.json').read_text())
    iss = issue(rec['epochs_rec'], a.epoch_period, a.expert_gap)
    out.mkdir(parents=True)
    for f in ('expected_xq.mem', 'expected_reads.mem', 'rows.json'):
        shutil.copyfile(base / f, out / f)
    (out / 'images').symlink_to((base / 'images').resolve())
    (out / 'source_ctl.txt').write_text(''.join(f'{t} {ctl_payload(1 << 6, 2, 0, v):047x}\n' for t, v in sorted(iss.items())))
    print('FDOWN_CTL_ONLY base', base.name, 'P', a.epoch_period, 'G', a.expert_gap, 'issuers', len(iss))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', required=True); p.add_argument('--contract', required=True); p.add_argument('--out', required=True)
    p.add_argument('--epoch-period', type=int, default=600); p.add_argument('--expert-gap', type=int, default=0)
    p.add_argument('--slice', type=int, default=6); p.add_argument('--experts', type=int, default=7)
    p.add_argument('--ctl-only', default=None, help='BASE run dir: reuse its images / plans, recompute only source_ctl.txt')
    a = p.parse_args()
    out = Path(a.out)
    if a.ctl_only:
        return ctl_only(a)
    if out.exists():
        raise SystemExit('REFUSE_EXISTING_RUN_DIR')
    fx = XP.Fix(a.fixture); m = fx.meta
    assert hashlib.sha256((Path(a.fixture) / 'meta.json').read_bytes()).hexdigest() == \
        'd7f2eb6175bec6a21f2ccede5a103842d7d03e36c54b4859b967a6e04ba44b28', 'not the sid6 / released-checkpoint fixture'
    frames = json.loads(Path(a.contract).read_text())['phase_contracts'][0]['frames']
    assert len(frames) == 6
    r0 = m['tp_split']['expert_down_rows'][m['rank']][0]
    groups = []
    for e in (['shared'] + [f'exp{x}' for x in m['experts']])[:a.experts]:
        n2 = f'{e}.w2'
        for nm in (f'weights/{n2}.bin', f'weights/{n2}.scale.bin'):
            assert hashlib.sha256((Path(a.fixture) / nm).read_bytes()).hexdigest() == fx.files[nm]['sha256'], nm
        xop = 'ffn.shared.swiglu' if e == 'shared' else f'ffn.experts.{e[3:]}.route_w'
        tie_op = 'ffn.shared.down' if e == 'shared' else f'ffn.experts.{e[3:]}.down'
        nrow = fx.w(n2).shape[0]; assert nrow == 1280
        srows = XP.deal(nrow, XP.NSLICE)[a.slice]
        per = XP.deal_into(srows, len(frames))
        fmt = XP.fmt_of(fx, n2)
        K = fx.w(n2).shape[1] * (2 if fmt == 'fp4' else 1); assert K == 2304
        nseg, _ = XP.nseg_for(fmt, K, 12)
        groups.append(dict(e=e, mat=n2, fmt=fmt, K=K, nseg=nseg, R=2 * (12 // nseg), per=per,
                           x=G.to_bf16(fx.op(xop)).astype(np.float32), xop=xop, tie_op=tie_op))
    # epochs
    eps = []
    for gi, g in enumerate(groups):
        for c in range(-(-max(len(f) for f in g['per']) // g['R'])):
            eps.append((gi, c))
    NE = len(eps); assert NE <= 64
    fields, common, plans, rowrec, gold = {}, [], [], [], []
    tie_bad = 0
    for i, (gi, c) in enumerate(eps):
        g = groups[gi]
        for fi, f in enumerate(frames):
            rows = g['per'][fi][c * g['R']:(c + 1) * g['R']]
            if not rows:
                continue
            name = f['frame']; master = LX.base_master(f['master'])
            q, _ = B.frame_pairs(master); npq = (12 // g['nseg']) * g['nseg']; qa = q[:npq]; assert len(qa) == npq
            mat = XP.FMat(g['mat'], g['fmt'], fx.w(g['mat']), fx.sc(g['mat']), rows, 'ffn.down')
            plan = XP.phase_plan(f['master'], f['lk'], qa, 0, mat, g['x'], g['nseg'], 4000)
            assert plan['faults'] == 0, (name, i, plan['faults'])
            assert plan['calendar'] == 'measured_class', plan['calendar']
            field = fields.setdefault(name, dict(field=I.Field(16, 1, 0, depth=8192, active=npq, pp=True, fast=True),
                                                 q=q, master=f['master'], pairs=qa, phases=[]))
            ph = XP.add_planned(field['field'], plan, mat, g['nseg'])
            field['phases'].append(i)
            assert len(field['field'].cfg) == i + 1, ('every frame holds every epoch as its phase i', name, i)
            words = field['field'].stream[ph['sbase']:ph['sbase'] + ph['nbeat']]
            if len(common) <= i:
                common.append(words)
            assert words == common[i], ('stream differs across frames', name, i)
            vals = P.golden_vals(mat, g['x'], g['nseg'])
            fix = fx.op(g['tie_op']).reshape(-1)
            for r, row in enumerate(rows):
                acc, err = golden_row(vals[r]); assert not err
                bf = int(G.bits(G.to_bf16(G.from_bits(acc)))) >> 16   # 10-19 fix: bits() of the bf16-valued fp32 is 32 bits (was compared with fb >> 16 -> all 560 rows 'golden != fixture')
                fb = int(G.bits(G.F(fix[r0 + row])))
                tie = (fb >> 16 == bf and not fb & 0xFFFF)
                tie_bad += not tie
                rowrec.append(dict(epoch=i, frame=name, lane=fi, tag=r, uid=8 * i + r, expert=g['e'], fmt=g['fmt'],
                                   rank_row=r0 + row, slice_row=row, vals=vals[r], acc=acc, bf16=bf, fixture_fp32=fb,
                                   fixture_tie=tie))
            plans.append(dict(epoch=i, frame=name, expert=g['e'], rows=rows, phase=ph, ret=plan['ret'],
                              emission=plan['emission'], placement=plan['placement']))
    assert tie_bad == 0, ('golden != fixture', tie_bad)
    # x beats (FP8 q family) of each expert, quantised as golden_vals (G.quant_fp8 == HG.g_quant, asserted)
    for g in groups:
        x = g['x']; qf, qe = G.quant_fp8(x)
        for b in range(NB):
            qq = HG.g_quant(x[64 * b:64 * b + 64]); packed = 0
            for h, (e, codes) in enumerate(qq):
                assert (int(qe[2 * b + h]) & 1023) == int(e)
                assert np.array_equal(G.E4M3[np.asarray(codes, np.uint8)], qf[64 * b + 32 * h:64 * b + 32 * h + 32])
                packed |= int.from_bytes(bytes(np.asarray(codes, np.uint8)), 'little') << (266 * h)
                packed |= int(e) << (256 + 266 * h)
            gold.append(packed)
    # phase / stream ROMs
    phase, stream = [], []
    for i, w in enumerate(common):
        g = groups[eps[i][0]]
        nrows = max(len(g['per'][fi][eps[i][1] * g['R']:(eps[i][1] + 1) * g['R']]) for fi in range(6))
        phase.extend([g['K'] << 1 | len(w) << 14 | len(stream) << 30 | nrows << 46, 0]); stream.extend(w)
    cals, issuers, epochrec = [], {}, []
    for i in range(NE):
        gi, c = eps[i]
        cc = XC.compile_phase(phase, stream, i, a.slice); base = len(cals); cals.extend(cc['packed'])
        shift = 1100 + a.epoch_period * i + a.expert_gap * gi
        for t, v in cc['iss'].items():
            if t == XC.GW_IT and c:
                continue      # one gather window per expert (its first epoch); later epochs reuse the buffer
            if t == XC.T_OFFCFG and i:
                continue
            if t in (XC.TS - 20, XC.TS):
                v = XC.isd(**({'prime': 1} if t == XC.TS - 20 else {'start': 1}), base=base, length=cc['cal_rows'])
            assert shift + t not in issuers, ('issuer edge collision', i, t)
            issuers[shift + t] = v
        reads = sorted(cc['ts'])
        epochrec.append(dict(epoch=i, expert=groups[gi]['e'], expert_index=gi, chunk=c, calendar_base=base, calendar_rows=cc['cal_rows'],
                             is_d_shift=shift, stream_words=cc['nb'], data_reads=sum(bool(w & 1) for w in common[i]),
                             stall_edges=cc['stall_edges'], gather_slack=cc['slack'], stream_rows=[reads[0], reads[-1]],
                             iss={str(t): f'{v:040x}' for t, v in cc['iss'].items()}))
    assert len(cals) <= 4096 and len(stream) <= 16384 and len(phase) <= 4096, (len(cals), len(stream))
    its = sorted(issuers)
    for t in its:
        assert len([j for j in its if j <= t < j + XC.OFF + 2]) <= XC.ND, ('issuer delay line over-full', t)
    commands = {t: ctl_payload(1 << 6, 2, 0, v) for t, v in issuers.items()}
    md = out / 'model'; md.mkdir(parents=True)
    (md / 'source_ctl.txt').write_text(''.join(f'{t} {v:047x}\n' for t, v in sorted(commands.items())))
    roms = {'pq_calendar_action': viamap([w & ((1 << 72) - 1) for w in cals] + [0] * (4096 - len(cals))),
            'pq_calendar_time': viamap([w >> 72 for w in cals] + [0] * (4096 - len(cals))),
            'pq_phase0': viamap(phase + [0] * (4096 - len(phase)))}
    sp = stream + [0] * (16384 - len(stream))
    for b in range(4):
        roms[f'pq_stream{b}'] = viamap(sp[b * 4096:(b + 1) * 4096])
    for k, v in roms.items():
        (md / f'{k}.viamap.hex').write_text(v)
    # serialisation (serialize_selected_vehicle.py, generalised: NE phases, unique row tags)
    images = out / 'images'; images.mkdir(); blank = out / 'blank_weight.hex'
    I.viamap({}, blank); blank.write_text(''.join(blank.read_text().splitlines(keepends=True)[:512]))
    retags = 0
    for name, f in fields.items():
        field = f['field']
        for i in range(NE):
            for slot in range(len(f['pairs'])):
                cfg = field.cfg[i][slot]
                for wi in list(range(8)) + list(range(17, 25)):
                    v = cfg[wi]
                    if not v:
                        continue
                    tag = v & 65535
                    if tag & 0x8000:
                        continue
                    assert tag < 8
                    cfg[wi] = (v & ~65535) | (tag & 0xc000) | (8 * i + (tag & 0x3fff)); retags += 1
        tmp = out / (name + '_field'); I.write_field(field, tmp, 10, flat_viamaps=True)
        words = field.stream + [0] * (16384 - len(field.stream))
        for b in range(4):
            assert viamap(words[4096 * b:4096 * (b + 1)]) == roms[f'pq_stream{b}']
        base = f['master'].replace('_MX', '').removesuffix('_l4'); q, bfp = B.frame_pairs(base)
        smap = {k: i for i, k in enumerate(f['pairs'])}
        for k in q:
            for mb in ('', 'b'):
                for par in (0, 1):
                    src = tmp / f'e{smap[k]}{mb}_{par}.viamap.hex' if k in smap else blank
                    shutil.copyfile(src, images / f'{name}_e{k}{mb}_{par}.viamap.hex')
        for k in bfp:
            for side in ('e', 'w'):
                for par in (0, 1):
                    shutil.copyfile(blank, images / f'{name}_e{k}{side}_{par}.viamap.hex')
        for k in q + bfp:
            banks = [[0] * 4096 for _ in range(7)]
            for ph in range(NE):
                ws = field.cfg[ph][smap[k]] if k in smap else [0] * 25
                for wi, v in enumerate(ws):
                    banks[wi % 7][4 * ph + wi // 7] = v
            for bank in range(7):
                enc = encode_bank(banks[bank]); assert decode_bank(enc) == banks[bank]
                (images / f'{name}_c{k}_{bank}.viamap.hex').write_text(''.join(f'{w:0144x}\n' for w in enc))
        shutil.rmtree(tmp)
    nimg = len(list(images.glob('*'))); assert nimg == 1012, nimg
    for k, v in roms.items():
        (images / f'{k}.viamap.hex').write_text(v)
    (out / 'source_ctl.txt').write_text((md / 'source_ctl.txt').read_text())
    (out / 'expected_xq.mem').write_text(''.join(f'{w:0133x}\n' for w in gold))
    (out / 'expected_reads.mem').write_text(''.join(f'{e["data_reads"]:08x}\n' for e in epochrec))
    (out / 'rows.json').write_text(json.dumps(rowrec) + '\n')
    rec = dict(schema='opentallas.toksim_s81b.fdown_vehicle.v1', slice=a.slice, frames=[f['frame'] for f in frames],
               experts=[g['e'] for g in groups], rows=len(rowrec), rows_per_expert=80, K=2304, epochs=NE,
               epoch_period=a.epoch_period, expert_gap=a.expert_gap, tie_bad=tie_bad, retags=retags,
               groups=[{k: v for k, v in g.items() if k != 'x'} for g in groups], epochs_rec=epochrec, plans=plans,
               fixture=str(a.fixture), fixture_meta_sha256='d7f2eb6175bec6a21f2ccede5a103842d7d03e36c54b4859b967a6e04ba44b28',
               checkpoint=m.get('checkpoint'), calendar_rows=len(cals), stream_words=len(stream))
    (md / 'contract.json').write_text(json.dumps(rec, indent=1) + '\n')
    print('FDOWN_PROGRAM_PASS rows', len(rowrec), 'epochs', NE, 'tie_bad', tie_bad, 'retags', retags, 'cal', len(cals),
          'stream', len(stream), 'P', a.epoch_period, 'G', a.expert_gap,
          'stream_rows', [e['stream_rows'] for e in epochrec[:2]], 'stall', epochrec[0]['stall_edges'])


if __name__ == '__main__':
    main()
