"""TOK-FUNC2-S81-L0B (10-21): KV RMSNorm (D 512) -> RoPE tail -> FP8 QDQ of the layer's own KV row.

Plugin of tools/s81_dv/dv_layer_compile.py (family hook): OPS + lower(die, op, ctx).

Why the slice units cannot do it (verified on the built RTL, main == claude/tokfunc2-s81-1021 for vn / vq / vs / vp):
  * the rstd finish: ot_s81dv_xfin -> ot_s81dv_norm_finish #(.D(64 * NVL * NS)) = D 5120 (ot_s81dv_norm.sv, xfin
    u_f), divider ot_dsrom_divc #(.F(DF), .K(DK)) constant F 5 K 10; ot_s81sl_eg asserts D == 5120.  No D 512 (nor
    D 1280, q_norm) rstd exists in a slice: rsqrt(ss / 512 + eps) is not reachable bit-exactly from / 5120.
  * the order: golden kv = qdq_fp8(rope_tail(rmsnorm(kraw))) (tools/s81_dv/dv_layer_fixtures.py attention()).  vn's
    normed y goes ONLY to vq (ot_s81sl_slice.sv ot_s81sl_leaf: u_vn .y -> u_vq .y); no vp / vs path writes y into the
    leaf store, so vs QR (the rope) cannot run between the norm and vq's act-quant.
The structural fix exists as RTL: ot_s81sl_kv_leaf / ot_s81sl_kv_bank (the production D 512 KV masters of
rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_kv.sv behind a vp opcode-15 bridge), opt-in KV_ENABLE = 1 on u_s_3N leaf 0
(codex/s81-kvq-bind-1021, ABI = layer_prog/kv_bank_contract.py), consumer component bench PASS with the exponent-write
negative rejected (results/token_pass/s81_kv_real_vp_1021/r3/result.json).  The die of record must bind it: this
lowering emits the KV programme only when die.v instantiates u_s_3N with KV_ENABLE (else GAP, programme recorded in
prog/kv/ for the bind, NO calendar rows -- op 15 on an unbound leaf is a vs sticky fault).
"""
import json
import re

from layer_prog import kv_bank_contract as KB

OPS = [r'^attn\.kv_norm\.(sumsq|rsqrt|scale)$', r'^attn\.kv_rope_qdq$']
BENCH = 'results/token_pass/s81_kv_real_vp_1021/r3'
UNIT = 'ot_s81sl_kv_leaf / ot_s81sl_kv_bank (production D512 KV masters) on u_s_3N leaf 0, vp opcode 15'
EPS = 0x358637BD                                  # 1e-6 (rms_norm_eps), as lower_norm_smoke
GK_LEAD = 1200                                    # GK job before the KV job: measured gain finish 1025 (+ guard)
JID_GK, JID_KV = 1, 2

GAP_BIND = dict(
    module='die.v u_s_3N (ot_s81sl_slice) -- S81 die bind (S81-DIE9 / S81-ELEM)',
    port='KV_ENABLE (ot_s81sl_kv_leaf on leaf 0, vp opcode 15)',
    missing='REAL HARDWARE GAP on the die of record: no unit computes D 512 KV RMSNorm -> RoPE -> FP8 QDQ (xfin rstd '
            'finish is D 5120 only: ot_s81dv_norm_finish D = 64 NVL NS, ot_dsrom_divc F 5 K 10; vn y feeds only vq, so '
            'no rope can sit between norm and quant).  Fix RTL exists (codex/s81-kvq-bind-1021: ot_s81sl_kv_leaf + '
            'KV_ENABLE on u_s_3N leaf 0; component bench PASS + exponent-drop negative, '
            'results/token_pass/s81_kv_real_vp_1021/r3) but die.v instantiates u_s_3N without it.  Programme '
            'recorded in prog/kv/ (dispatch words, kv_bank_contract ABI); no calendar rows emitted')
GAP_FEED = dict(
    module='a_allgather consumer placement / kv_bank_contract operand rows 692..819',
    port='kv operand rows (32 spine rows -> 128 leaf rows) + 5 parameter rows (descriptor, cos lo/hi, sin lo/hi)',
    missing='dispatch words emitted; the kv part of the gathered a_proj vector must land at the adapter operand rows of '
            'u_s_3N leaf 0 (a_allgather consumer placement not compiled) and the position cos / sin parameter rows '
            'have no lowered producer; OWN_ROW handoff of the 25 result rows to svc not lowered')


def kv_bound(die):
    i = die.inst.get(KB.SLICE) or {}
    return bool(re.search(r'\bKV_ENABLE\s*\(\s*1\s*\)', i.get('params', ''))) or 'kv' in i.get('master', '')


def programme(t_kv):
    t_gk = t_kv - GK_LEAD
    gk = KB.dispatch(7, 0, JID_GK, 1024)
    kv = KB.dispatch(1, 0, JID_KV, 1024)
    return dict(schema='opentallas.s81.kv_programme.v1', slice=KB.SLICE, leaf=KB.LEAF,
                commands=[dict(job='GK', issue=t_gk, word=f'{gk:040x}', finish_after=1025),
                          dict(job='KV', issue=t_kv, word=f'{kv:040x}', finish_after=1130)],
                descriptor=f'{KB.descriptor(EPS):0128x}', contract=KB.contract())


def lower(die, op, ctx):
    name = op['op']
    first = name == 'attn.kv_norm.sumsq'
    t_kv = int(ctx.get('t_issue', 0))
    p = programme(t_kv)
    files = {f'prog/kv/{op["id"]}.json': json.dumps(p, indent=1) + '\n'} if first else {}
    base = dict(unit=UNIT, insts=[KB.SLICE], files=files, bench=BENCH, fused_into=None if first else 'attn.kv_norm.sumsq')
    if not kv_bound(die):
        return dict(base, status='GAP', rows=[], templates=[], events=[], gap=GAP_BIND)
    if not first:
        return dict(base, status='PARTIAL', rows=[], templates=[], events=[], gap=GAP_FEED)
    from layer_prog.lower_vs import ctl_payload
    sid = die.slices()[KB.SLICE]['sid']
    eng = 0 if KB.SLICE.endswith('N') else 1
    tpl, rows = [], []
    for c in p['commands']:
        tpl.append((f'kv.{c["job"]}', ctl_payload(1 << sid, 0, 1 << KB.LEAF, int(c['word'], 16))))
        rows.append(dict(eng=eng, issue=c['issue'], arg=len(tpl) - 1, what=f'kv {c["job"]} job (vp op 15)'))
    return dict(base, status='PARTIAL', rows=rows, templates=tpl, events=[], gap=GAP_FEED)
