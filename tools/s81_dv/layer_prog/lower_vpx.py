"""LB2-S81/CC fork VPX (10-18): lowering of the vp NORM / hc_post coefficient path and the end-slice lep collectives.

Plugin of tools/s81_dv/dv_layer_compile.py (family hook): OPS + lower(die, op, ctx).  Every ABI below is read from the
BUILT RTL of record (origin/main 711fb3da3+; byte-identical files on claude/lb2-s81-cc-1018):

  CTL beat payload  ot_s81sl_xr.sv:5-12 / 119-125     [15:0] slice mask (bit = sid strap), [20:16] target, [25:21] leaf
                                                     mask, [185:26] body 160 (dv_layer_compile.ctl_payload)
  target 0 vp cmd   ot_s81sl_xr.sv:223, ot_s81sl_vp.sv:17-27 / 82   op [3:0], a0 [13:4], a1 [23:14], n [31:24], imm [159:32]
                    RDOUT (op 6): n row pairs (a0 + 2i, a0 + 2i + 1) -> lo, one pair a cycle (vp.sv:100-103, 289)
  target 4 send cfg ot_s81sl_xr.sv:131-145            body [3:0] dir {B, V, W, E}, [6:4] kind, [11:7] hops, [27:12] dst
                                                     slice mask, [30:28] dst leaf, [40:31] dst row, [42:41] pairs - 1,
                                                     [43] SC relay.  The config is latched once (xr.sv:137-141): every
                                                     beat packed under it carries the SAME dst row -> one config per beat;
                                                     a config landing in a cycle with a lo pair drops that pair from the
                                                     pack count (else-if, xr.sv:141) -> configs only in lo-free cycles.
  line RD beat      ot_s81sl_xr.sv:146-151            [0] 1, [3:1] kind (4 RD), [8:4] hops, [12:9] src, [21 +: 16] dst
                                                     mask, [37 +: 3] leaf, [40 +: 10] row, [50 +: 2] pairs - 1,
                                                     [52 +: 1024] up to 4 row pairs (pair i -> rows row + 2i, + 1)
  RD receive        ot_s81sl_xr.sv:179-215            mask bit [sid] at ANY stop the beat passes (rstop delivers every
                                                     beat, rstop.sv:153-155), one pair a cycle into the leaf's row-pair
                                                     write port; a second RD to a busy leaf = sticky fault
  ring stop         ot_s81sl_rstop.sv:129-141         a control-plane beat with hops != 0 leaves unchanged; a beat with
                                                     hops > 1 is forwarded (hops - 1): an end slice's outward port is the
                                                     lep (ot_s81sl_slice_lep.sv header), so hops 1 = delivered at the
                                                     peer die's end slice
  lep / lanes       ot_s81sl_slice_lep.sv:6-35        off-die rate <= 0.764 beats / cycle (landing FIFO DT 512); flow
                                                     control only inside the lane tiles

hc coefficient path (FIXED 10-18 by vp op 7 NORMR + POST row order, S81-SLICE 5043d6876; history below): the G-unit HC tail writes its 24 coefficients as six leaf-store rows (dsdv_gunit_l5.sv:7,
82, 101; order = dsdv_gunit_tail.sv:173-174: row R pre 0..3, R + 1 post 0..3, R + 2..R + 5 comb row-major), but
  * vp NORM takes hc_pre ONLY from the command immediate (ot_s81sl_vp.sv:285 n_pre <= cd_c[159:32]; vn.sv:69): the
    command body is a boot-loaded CTL template (seq_host 0x13) and no unit writes a CTL target-0 body at run time, so
    the runtime pre coefficients in row R cannot reach vn;
  * vp POST reads comb from rows a0..a0 + 3 and post from row a0 + 4 (vp.sv:18, 96, 196, 219) while L5 puts post at
    R + 1 BEFORE comb (R + 2..R + 5): no single a0 matches (comb orientation word 4j + k = comb[j][k] DOES match the
    golden: fixture L0 attn.hc_post == BF16(y post[k] + sum_j r_j comb[j][k]) with comb = attn.hc.sinkhorn row-major,
    max |err| 0 after BF16 rounding).
  Proposed RTL fix (owner S81-SLICE / RTL-BUILD-S81; s81dv_leaf is a critical prefix -> re-gate + visual review):
    vp op 7 NORMR: a0 = coefficient row; read row a0 (one bank), n_pre <= that row 2 edges later, n_go / m_* as NORM
    (a1 = global beat index stays in the template); and POST step 0 reads the post row a0, steps 1..4 comb rows
    a0 + 1..a0 + 4 (L5 order) -> NORMR a0 = R, POST a0 = R + 1, both static templates.
"""
import math
import json
import re

OPS = [
    r'(^|\.)(attn|ffn)\.hc_pre$',
    r'(^|\.)(attn|ffn)\.norm\.(sumsq|rsqrt|scale)$',
    r'(^|\.)(attn|ffn)\.hc_post$',
    r'(^|\.)attn\.a_allgather$',
    r'(^|\.)eng\.rows_allgather$',      # TOK-S81-GAPS/IDX: same endpoint ABI (Engram rows, L14)
    r'(^|\.)ffn\.router_allgather$',
    r'(^|\.)attn\.out_allreduce$',
    r'(^|\.)ffn\.combine_allreduce$',
    r'(^|\.)substage_hop\d+$',
]

BENCH = 'results/rtl/s81_layer_tput_1018/compiler/bench_vpx'

# ---------------------------------------------------------------------------------------------------------------- ABI
K_RD = 4
DIR = dict(E=1, W=2, V=4, B=8)
VP_RDOUT = 6


def send_cfg(dir_, kind, hops, dst_mask, dst_leaf, dst_row, pairs):
    """CTL target 4 body (ot_s81sl_xr.sv:131-141)"""
    assert 1 <= pairs <= 4 and 0 <= dst_row < 1024 and 0 <= dst_leaf < 5
    return (DIR[dir_] | (kind & 7) << 4 | (hops & 0x1F) << 7 | (dst_mask & 0xFFFF) << 12 | (dst_leaf & 7) << 28
            | (dst_row & 0x3FF) << 31 | (pairs - 1) << 41)


def rd_beat(src, hops, dst_mask, leaf, row, pairs, data, kind=K_RD):
    """line RD beat as the xr send packer builds it (ot_s81sl_xr.sv:146-151); data = up to 4 x 256-b row pairs"""
    return (1 | (kind & 7) << 1 | (hops & 0x1F) << 4 | (src & 0xF) << 9 | (dst_mask & 0xFFFF) << 21 | (leaf & 7) << 37
            | (row & 0x3FF) << 40 | ((pairs - 1) & 3) << 50 | (data & ((1 << 1024) - 1)) << 52)


# Edge constants of the send / receive path, from the RTL edge chain below; bench_vpx asserts every one of them on
# every run (send edges, read-back edges and the receive latency must match exactly); edge chain (inward port = the edge the beat is on the slice pin):
#   CTL beat on the slice pin -> rstop pin flop + delivery flop (2) -> xr pin flop (1) -> XR7 stage-1 register (1,
#   ot_s81sl_xr.sv:181-204, "every CTL / RD / lo / V / SC consequence moves +1 cycle") -> cvld / tg: CFG_AT = 4
#   cvld (target 0) -> c_d flop (1) -> leaf relay DL 4 -> vp pin flop (1) -> sequencer step 0 (1) -> macro + output
#   register + dv (2) -> lo flop (1) -> relay DL 4 -> xr lo pin flop (1) = lov: first lo pair at xr = CFG_AT + LO_AFTER_CTL
#   XR7 (TOK-DS-9 10-27): the packer reads lov1 = lov one edge later (ot_s81sl_xr.sv:204, 250-251), and a send config
#   (tg[4]) in a cycle with |lov1 is a sticky fault (xr.sv:558): the config slot is the lov1-free edge = LO_PACK after lov
#   pk_go the edge after the 4th lov1 pair; snd -> ci flop -> rstop ci flop -> ro flop: beat on the outward port SEND_AFTER_GO
# Measured TOK-DS-9 on tb_vpx_ag (current main RTL, the TOK-DS-8 binary; sources sha-identical to main 0f9789993e):
# RDOUT pin 8136 -> cvld 8140 (CFG_AT 4), lov 8155 (LO_AFTER_CTL 15); 10-18 values were CFG_AT 3, no LO_PACK, RX 5.
CFG_AT = 4
LO_AFTER_CTL = 15
LO_PACK = 1
SEND_AFTER_GO = 3
RX_WR_AFTER_PIN = 6          # RD beat on the slice pin -> rstop pin + delivery flops (2) -> xr pin flop (1) -> XR7 stage 1
                             # (1) -> unpacker busy flop (1) -> sw row-pair write flop (1); pair j one edge later each
PAIRS = 4                    # row pairs per RD beat (the 1,024-b payload)


def beat_period():
    """issue period of one 4-pair beat: 4 lo cycles + the one lo-free cycle that takes the next config (= pk_go of the
    previous beat; xr.sv:137-143), with the config CTL and the RDOUT CTL on distinct pin cycles"""
    p = PAIRS + 1
    while (LO_AFTER_CTL + LO_PACK - 1) % p == 0:   # config of beat i (pin t_i + LO_AFTER_CTL + LO_PACK - 1) vs RDOUT j (t0 + p j)
        p += 1
    return p


def leg_program(sid, dir_, peer_sid, rows, leaf=0, t0=0, mut=None, dst_leaf=None, dst_off=0):
    """one end slice's send leg: own rows (even base row list of 2-row pairs, grouped 4 pairs a beat) out of the outward
    port (dir W at a W end, E at an E end) to the peer die's end slice (hops 1, dst mask = peer sid bit, same rows).
    Returns CTL arrivals at the slice pin (relative cycles), and the expected outward beats (cycle, rows).
    Per beat i (period P): RDOUT CTL at t0 + P i; its 4 pairs reach xr at + CFG_AT + LO_AFTER_CTL .. + 3; the config for
    beat i lands on xr the lo-free edge before (the previous beat's pk_go edge).
    TOK-DS-8: dst_leaf / dst_off = the peer's leaf / row offset (reduce-scatter scratch); default = the same leaf and rows."""
    P = beat_period()
    dleaf = leaf if dst_leaf is None else dst_leaf
    pairs = [rows[i:i + 2] for i in range(0, len(rows), 2)]
    assert all(len(p) == 2 and p[0] % 2 == 0 and p[1] == p[0] + 1 for p in pairs), 'rows must be even-based pairs'
    beats = [pairs[i:i + PAIRS] for i in range(0, len(pairs), PAIRS)]
    ctl, sends = [], []
    for i, bp in enumerate(beats):
        base = bp[0][0]
        assert all(bp[j][0] == base + 2 * j for j in range(len(bp))), 'beat rows must be consecutive'
        tr = t0 + P * i
        lo0 = tr + CFG_AT + LO_AFTER_CTL + LO_PACK      # first pair at the packer (lov1)
        tc = lo0 - 1 - CFG_AT
        dst = base + dst_off
        if mut == 'row' and i == 2:
            dst = base + dst_off + 2            # mutant: wrong dst row field in beat 2's config
        if mut == 'shift' and i == 2:
            tr += 1                             # mutant: beat 2's RDOUT CTL one edge late (collides with the next config)
        ctl.append(dict(cycle=tc, target=4, body=send_cfg(dir_, K_RD, 1, 1 << peer_sid, dleaf, dst, len(bp)),
                        tag=f'cfg{i}', leaf_mask=0))
        ctl.append(dict(cycle=tr, target=0, body=_vp(VP_RDOUT, a0=base, n=len(bp)), tag=f'rdout{i}', leaf_mask=1 << leaf))
        sends.append(dict(cycle=lo0 + len(bp) - 1 + 1 + SEND_AFTER_GO, rows=[r for p in bp for r in p], dst_row=base + dst_off,
                          dst_mask=1 << peer_sid, leaf=dleaf, src_leaf=leaf, pairs=len(bp), src=sid))
    return dict(period=P, ctl=sorted(ctl, key=lambda c: c['cycle']), sends=sends)


def _vp(op, a0=0, a1=0, n=0, imm=0):
    return (op & 0xF) | (a0 & 0x3FF) << 4 | (a1 & 0x3FF) << 14 | (n & 0xFF) << 24 | (imm & ((1 << 128) - 1)) << 32


def _payload(smask, target, lmask, body):
    return (smask & 0xFFFF) | (target & 0x1F) << 16 | (lmask & 0x1F) << 21 | (body & ((1 << 160) - 1)) << 26


# Vehicle placement of the gathered a_proj vector in a slice's leaf 0 (global element order, 4 FP32 words a row):
# q (wq_a out 1280) rank r at rows 80 r .. 80 r + 79, kv (wkv out 512) rank r at rows 320 + 32 r .. + 31.  The production
# placement is the xs return plan's (where the frames' capture writes the a_proj rows) -- not yet compiled (GAP below).
def a_rows(rank):
    return list(range(80 * rank, 80 * rank + 80)) + list(range(320 + 32 * rank, 320 + 32 * rank + 32))


# TOK-DS-8 (10-27): vehicle placements of the other shared collectives on the SAME endpoint ABI (leaf rows of 4 FP32
# words; a beat = 4 consecutive row pairs of ONE leaf; a leaf has 1024 rows).  As for a_rows, these are where the
# compiler puts the rows, not yet where the producers' capture writes them (GAP_PLACE stays: status PARTIAL).
#   ffn.router_allgather  384 router logits = 96 rows; rank r owns experts 96 r .. 96 r + 95 = leaf 0 rows 448 + 24 r ..
#   substage_hop0        [4, 5120] HC residual; rank r carries stream r (5120 words = 1280 rows) to the next stage's
#                        rank r: rows 0..639 of leaf 1 then of leaf 2 (priced 1033.5 = 160 beats x 5 + edges)
#   attn.out_allreduce   rank partial 1280 rows; quarter q (owner rank q) = leaf 3 + q // 2 rows 320 (q % 2) ..; RS:
#                        each rank sends quarter p to owner p into scratch slot k = (src - p) % 4 - 1 = leaf 1 + k rows
#                        640..959; owner fold ((p0+p1)+(p2+p3), owner_fold.py / run_owner_fold.sh) in place; AG: the
#                        folded own quarter to the 3 peers at the same leaf / rows (their partial quarter is dead)
def router_rows(rank):
    return list(range(448 + 24 * rank, 472 + 24 * rank))


STAGE_SEGS = [(1, 0, 640), (2, 640, 640)]        # (leaf, first stream row, rows): leaf rows 0..639


def ar_quarter(q):
    """(leaf, first leaf row) of quarter q of a rank partial / the folded result"""
    return 3 + q // 2, 320 * (q % 2)


def rs_slot(src_rank, owner_rank):
    k = (src_rank - owner_rank) % 4 - 1
    assert 0 <= k < 3
    return 1 + k, 640


# TP4 circuits (S81-LINK5, owner 10-21; dv_mu_calendar.CIRCUITS): d.ES <-> (d+1).WS, d.EN <-> (d+2).EN (ONE
# bidirectional d+2 circuit; was d.EN -> (d+2).WN) -> each die sends its own part out of s_0S (W, to d-1's s_7S), s_7S
# (E, to d+1's s_0S) and s_7N (E, to d+2's s_7N); parts land at s_0S (rank d-1), s_7S (rank d+1), s_7N (rank d+2: the
# E end, so the d+2 part enters the N ring at slice 7 and runs westward; its on-die leg is the E-end leg).
LEGS = [('u_s_0S', 'W', 'u_s_7S'), ('u_s_7S', 'E', 'u_s_0S'), ('u_s_7N', 'E', 'u_s_7N')]
# Stage hop (S81-LINK5): h out of s_0N pair A (W, every window ab 0) to the NEXT stage's rank-r s_0N, where it arrives
# on pair B (merged into ri).  Never on a TP endpoint.
STAGE_LEG = ('u_s_0N', 'W', 'u_s_0N')

BENCH_VP = 'results/rtl/s81_layer_tput_1018/compiler/bench_vp'
# (10-18: the former GAP_PRE / old GAP_POST RTL gaps are fixed by vp op 7 NORMR + the G-unit POST row order, bench_vp)
GAP_NORM16 = dict(module='ot_s81sl_xr / ot_s81sl_rstop (xfin NX snake, XQ all-gather)', port='16-slice norm composition',
                  missing='the per-leaf NORMR / norm / act-quant programme is emitted on ONE slice (lower_norm_smoke); '
                          'the xfin NX snake (partial roots -> rstd) and the XQ all-gather of all 16 slices are not composed')
GAP_POST = dict(module='tools/s81_dv/frame_return_plan.py / lower_xs (wo_b / down return rows)', port='POST a1 (y rows)',
                missing='POST a0 = R + 1 matches the G-unit rows (bench_vp g_b37 PASS, old order g_mpl FAIL); its a1 = the '
                        'y rows of the sublayer output (attn wo_b / ffn down + combine all-reduce result) whose leaf-store '
                        'placement is not compiled (GAP_XS_ROM / GAP_FOLD), so no POST command can be issued yet')
GAP_PLACE = dict(module='tools/s81_dv/frame_return_plan.py / xs fork (lower_xs)', port='a_proj capture rows -> end slices',
                 missing='the endpoint send / receive ABI is lowered and benched (bench_vpx: s_0S <-> peer s_7S through '
                         'the real lep + lane tiles); the production rows of the own part at the 3 end slices (the '
                         'capture rows of the a_proj return + the on-die move to s_0S / s_7S / s_7N) and the consumer '
                         'placement of the 3 received parts are not compiled yet')
GAP_FOLD = dict(module='ot_s81sl_vs (SU add) / TOKEN-PASS-S81', port='owner fold ((p0+p1)+(p2+p3))',
                missing='RS + AG transport uses the benched RD endpoint ABI; the owning slice fold (an SU op on vs) has '
                        'no encoder yet (vs fork) and the RS row ownership is not placed')
GAP_FFN_COMBINE = dict(module='final_ffn.py / xs_calendar --final-ffn-placement',
                       port='output-row-owned VS13 then result allgather',
                       missing='actual VS13/POST words and capture/move map exist; bind VPX lifetimes, current RD paths '
                               'and allgather arrivals on all four ranks before issuing the production calendar')


def lower(die, op, ctx):
    name = op['op']
    t0 = int(ctx.get('t_issue', 0))
    if name.endswith('hc_pre'):
        # The arithmetic bench proves row reads, not the layer's row producer.
        # run_layer uses entry pre for attn and attn pre for ffn. Current-block
        # coefficients are a different value even when their arrival is exact.
        source = 'attn HC row 1000' if name.startswith('ffn.') else 'entry previous-ffn HC row 1008'
        return dict(status='PARTIAL', unit='slice vp NORMR (previous-sublayer pre row) -> vn n_pre',
                    insts=[ctx.get('slice')], bench=BENCH_VP,
                    gap=dict(module='dv_layer_compile / previous-sublayer pre transfer', port='NORMR a0',
                             missing=f'{source}: arithmetic is benched, but the full producer/transfer/row-lifetime '
                                     'binding is absent; current-block hc.coef_row0 is not the pre operand'))
    if re.search(r'\.norm\.(sumsq|rsqrt|scale)$', name):
        return dict(status='PARTIAL', unit='slice vp NORMR + vn / vq / xr / xfin', insts=[ctx.get('slice')], gap=GAP_NORM16,
                    bench=BENCH_VP)
    if name.endswith('hc_post'):
        if name == 'ffn.hc_post' and 'final_ffn' in ctx:
            from layer_prog.final_ffn import local_program
            sl = ctx['slice'] if ctx['slice'].startswith('u_') else 'u_' + ctx['slice']
            sid = die.slices()[sl]['sid']
            program = local_program(sid, int(ctx['leaf']), ctx['final_ffn'])
            return dict(status='PARTIAL', unit='production FFN POST binding', insts=[sl],
                        rows=[], templates=[program['templates'][1]], events=[], bench=BENCH_VP,
                        pending_leaf_program=program['rows'][1],
                        gap=dict(module='final FFN production composition', port='RD paths/reservations + VP/VN',
                                 missing='actual source paths and all-leaf calendars; actual POST/native timing'))
        return dict(status='PARTIAL', unit='slice vp POST (a0 = R + 1: post row, comb R+2..R+5) -> vn h store',
                    insts=[ctx.get('slice')], gap=GAP_POST, bench=BENCH_VP)
    if name.endswith('a_allgather') or name.endswith('rows_allgather') or name.endswith('router_allgather') \
            or re.search(r'substage_hop\d+$', name):
        rank = int(ctx.get('rank', 0))
        sl = die.slices()
        rows, templates, events, insts = [], [], [], []
        own = a_rows(rank) if name.endswith('a_allgather') else []
        # TOK-DS-8: (src, dir, peer, rows, leaf, dst_leaf, dst_off, tier) legs; a_allgather unchanged (3 TP legs, leaf 0)
        specs = [(src, d, peer, own, 0, None, 0, 0) for src, d, peer in LEGS] if own else []
        if name.endswith('ffn.router_allgather'):
            own = router_rows(rank)
            specs = [(src, d, peer, own, 0, None, 0, 0) for src, d, peer in LEGS]
        if re.search(r'substage_hop\d+$', name):
            own = [r for lf, _, n in STAGE_SEGS for r in range(n)]
            # one xr send packer on s_0N: segment k starts after segment k-1's beats (n / 8 beats a segment)
            specs = [(STAGE_LEG[0], STAGE_LEG[1], STAGE_LEG[2], list(range(n)), lf, None, 0,
                      sum(m // 8 for _, _, m in STAGE_SEGS[:k]) * beat_period()) for k, (lf, _, n) in enumerate(STAGE_SEGS)]
        _emit(die, sl, specs, t0, rows, templates, events, insts)
        st = 'PARTIAL' if own else 'GAP'
        gap = GAP_PLACE if own else dict(GAP_PLACE, missing='same endpoint ABI as attn.a_allgather (bench_vpx); the '
                                         'production rows of this op are not placed')
        if name.endswith('attn.rows_allgather'):
            # TOK-DS-CMP2 (10-26, 877 die audit): the compressed-row attention ROWS (q frame type 6) have NO producer
            gap = dict(module='877: no held-row export (dsdv_svc_att reads its held rows by SEL_IDS id into its own '
                              'attention tile only; outputs qrq / l_d / pv_od / sm_* carry no row data) + no ROWS frame '
                              'builder on the entry q path (u_s_3S / u_s_4S bo -> u_rsv_05 / u_rsv_11 q)',
                       port='u_rsv_05 / u_rsv_11 q: ROWS words {scales [290 +: 32], nibbles [34 +: 256], pair [33:31], '
                            'rank [9:0]} for every non-held selected row (L14: 476 of 512, 3808 words)',
                       missing='the other (die, stack) owners of the selected compressed rows (g[5:4] die, g[7:6] stack) '
                               'have no RTL path from their HBM row region (SB + 9 (g >> 9)) to a link / ring; the '
                               'L14 bench_cmp drives ROWS at the compiled q cycles.  Owner-level design item; measured '
                               'ingress lower bound 3809 q cycles vs price 1032.9 (ledger SVC.ROWS_INGRESS)')
        if re.search(r'substage_hop\d+$', name):
            gap = dict(gap, port=f'{STAGE_LEG[0]} pair A -> next stage {STAGE_LEG[2]} pair B (S81-LINK5 stage NEXT; '
                                 'TX window ab 0)')
        return dict(status=st, unit='end-slice send cfg + vp RDOUT -> lep -> peer end-slice RD receive', insts=insts,
                    gap=gap, rows=rows, templates=templates, events=events, bench=BENCH)
    if name.endswith('allreduce'):
        if name == 'attn.out_allreduce' and 'owner_fold_binding' in ctx:
            from layer_prog.owner_fold import program
            from layer_prog.lower_vs import ctl_payload
            b = ctx['owner_fold_binding']
            p = program(b['pair01'], b['pair23'], b['scratch'], b['output'],
                        start=b['start'])
            sl = ctx['slice']
            sid = die.slices()[sl]['sid']
            leaf = int(ctx['leaf'])
            templates = [(f'{name}.RB{k}', ctl_payload(1 << sid, 0, 1 << leaf,
                           int(c['word'], 16))) for k, c in enumerate(p['commands'])]
            return dict(status='PARTIAL', unit='VS11 canonical TP4 owner pair tree',
                        insts=[sl], templates=templates,
                        rows=[dict(eng=0 if sl.endswith('N') else 1, issue=c['issue'], arg=k,
                                   what=f'owner fold {c["expression"]}')
                              for k, c in enumerate(p['commands'])], events=[],
                        files={f'prog/owner_fold/{op["id"]}.json': json.dumps(p, indent=2) + '\n'},
                        gap=dict(module='owner-fold producer and collective transport binding',
                                 port='four real rank-partial rows -> two adjacent source pairs',
                                 missing='bind actual producer captures, RD gather paths and lifetimes; '
                                         'the emitted arithmetic commands alone do not qualify the collective'),
                        bench='tools/s81_dv/tokfunc/run_owner_fold.sh')
        if name == 'ffn.combine_allreduce' and 'final_ffn' in ctx:
            from layer_prog.final_ffn import local_program
            sl = ctx['slice'] if ctx['slice'].startswith('u_') else 'u_' + ctx['slice']
            sid = die.slices()[sl]['sid']
            program = local_program(sid, int(ctx['leaf']), ctx['final_ffn'])
            return dict(status='PARTIAL', unit='VS13 routed-ID-order + shared combine; output-sharded down',
                        insts=[sl], rows=[], templates=[program['templates'][0]], events=[], bench=BENCH,
                        pending_leaf_program=program['rows'][0],
                        gap=dict(module='final FFN production composition', port='RD paths/reservations',
                                 missing='place actual4480 RD pairs on current die paths; qualify all leaf calendars'))
        if name == 'ffn.combine_allreduce':
            return dict(status='PARTIAL', unit='output-row-owned VS13 then combined-result allgather',
                        insts=[], rows=[], templates=[], events=[], gap=GAP_FFN_COMBINE, bench=BENCH)
        if name == 'attn.out_allreduce':
            return lower_ar(die, ctx, t0)
        return dict(status='GAP', unit='RS + AG over the end-slice endpoints + owner fold', insts=[], gap=GAP_FOLD,
                    bench=BENCH)
    return dict(status='GAP', unit='vpx', insts=[], gap=dict(module='lower_vpx', port='-', missing=f'{name} not lowered'))


# ------------------------------------------------------------------------------------- TOK-DS-8 generic leg emission
def _emit(die, sl, specs, t0, rows, templates, events, insts, used=None):
    """CTL rows / templates / events of leg specs (src, dir, peer, leaf rows, leaf, dst leaf, dst row offset, t_rel);
    the a_allgather emission of 10-18 generalised (identical output for its 3 leaf-0 legs).  Returns the last outward
    beat edge (relative to t0, CTL latency included) so a following phase can start after it."""
    from dv_layer_compile import ctl_path   # noqa: E402 (plugin runs inside the compiler)
    used = set() if used is None else used
    last = 0
    for src, d, peer, own, leaf, dleaf, doff, trel in specs:
        if src not in sl or peer not in sl or not own:
            continue
        sid, psid = sl[src]['sid'], sl[peer]['sid']
        leg = leg_program(sid, d, psid, own, leaf=leaf, t0=0, dst_leaf=dleaf, dst_off=doff)
        eng = 0 if src.endswith('N') else 1
        lat = ctl_path(die, src)['edges']
        first = min(c['cycle'] for c in leg['ctl']) - trel
        sh = 0
        while any((eng, t0 + c['cycle'] - first + sh) in used for c in leg['ctl']):
            sh += 1
        first -= sh
        used |= {(eng, t0 + c['cycle'] - first) for c in leg['ctl']}
        for c in leg['ctl']:
            ti = len(templates)
            templates.append((f'{src}.{c["tag"]}', _payload(1 << sid, c['target'], c['leaf_mask'], c['body'])))
            issue = t0 + c['cycle'] - first
            # template_index: the family index may exceed arg[6:0] (RS + AG of out_allreduce = 240 beats); absorb()
            # re-points arg to the shared table from it (arg & 0x7F would alias index 128+ onto 0+)
            rows.append(dict(eng=eng, issue=issue, arg=ti & 0x7F, template_index=ti, what=f'{src} {c["tag"]}'))
            events.append(dict(cycle=issue + lat, inst=src, port='ri_e' if d == 'W' else 'ri_w', dir='in',
                               kind='CTL', tag=c['tag'], payload=f'template {ti}'))
        for s in leg['sends']:
            ce = t0 + s['cycle'] - first + lat
            last = max(last, ce - t0)
            hdr = rd_beat(s['src'], 1, s['dst_mask'], s['leaf'], s['dst_row'], s['pairs'], 0)
            events.append(dict(cycle=ce, inst=src, port='lep (outward line port)', dir='out', kind='RD',
                               tag=f'leaf {s["src_leaf"]} rows {s["rows"][0]}..{s["rows"][-1]} -> sid {psid} leaf '
                                   f'{s["leaf"]} row {s["dst_row"]}',
                               payload='vehicle-placed collective words', boundary='offdie',
                               observe=f'{src} outward ring port ({"ro_w" if d == "W" else "ro_e"} of the slice '
                                       f'inside the lep master) -> lt_lk link lanes',
                               words=[[ce, f'{hdr:x}', f'{(1 << 52) - 1:x}']],
                               data_masked='row pairs [1075:52] = leaf rows (vehicle placement)'))
        if src not in insts:
            insts.append(src)
    return last


# TP4 rank of the die reached by each leg (S81-LINK5: s_0S W -> d-1, s_7S E -> d+1, s_7N E -> d+2)
LEG_PEER_RANK = {'u_s_0S': -1, 'u_s_7S': 1, 'u_s_7N': 2}
# owner fold VS11 pair tree after the last RS write.  TOK-DS-9 (10-27) replaces the 10-27 FOLD_GAP 64 placeholder:
#   RS_LAND_TAIL  MEASURED (CHECKED) on bench_vpx out_allreduce_rs_none (current main RTL): last outward RS beat edge ->
#                 the owner's last RS row-pair write = 50 edges (send -> lep -> lane -> peer lep 41 / 42 + RX_WR_AFTER_PIN 6
#                 + pairs 1..3); the same 50 on a_allgather / router / out_allreduce_ag.
#   owner_fold_span(rows)  DERIVED, UNCHECKED: the fold is NOT bound to these rows (RS slots sit on leaves 1..3, the own
#                 quarter on leaf 3 / 4, and VS RB is leaf-local), so its span is the owner_fold.py law for one leaf: three
#                 serial RB commands of n = rows pairs, VS_DUR RB n + 19 (measured at n = 1 / 6 only) + guard 8 between.
RS_LAND_TAIL = 50
FOLD_GUARD = 8


def owner_fold_span(rows):
    return 3 * (rows + 19) + 2 * FOLD_GUARD


FOLD_GAP = RS_LAND_TAIL + owner_fold_span(320)      # = 50 + 1033 = 1083 edges


def lower_ar(die, ctx, t0):
    """attn.out_allreduce transport: RS (quarter p of the own partial -> owner p's scratch slot) then AG (folded own
    quarter -> the 3 peers, same leaf / rows), both on the 3 TP legs of the endpoint ABI."""
    rank = int(ctx.get('rank', 0))
    sl = die.slices()
    rows, templates, events, insts = [], [], [], []
    used = set()
    rs, ag = [], []
    for src, d, peer in LEGS:
        p = (rank + LEG_PEER_RANK[src]) % 4
        lf, r0 = ar_quarter(p)
        dl, dr = rs_slot(rank, p)
        rs.append((src, d, peer, list(range(r0, r0 + 320)), lf, dl, dr - r0, 0))
    last = _emit(die, sl, rs, t0, rows, templates, events, insts, used)
    lf, r0 = ar_quarter(rank)
    # last carries the CTL path age, which can hold half-edge link ages (ctl_path edges, e.g. 11.5): the AG legs
    # start on the next whole issue edge (ceil = the conservative later edge), never a fractional calendar row
    ag = [(src, d, peer, list(range(r0, r0 + 320)), lf, None, 0, math.ceil(last) + FOLD_GAP) for src, d, peer in LEGS]
    _emit(die, sl, ag, t0, rows, templates, events, insts, used)
    return dict(status='PARTIAL', unit='RS (3 TP legs, quarter -> owner scratch) + owner fold + AG (3 TP legs) on the '
                'end-slice endpoint ABI', insts=insts, rows=rows, templates=templates, events=events, bench=BENCH,
                gap=dict(GAP_FOLD, missing='RS + AG transport is lowered on the benched endpoint ABI (bench_vpx op '
                         'out_allreduce_rs / _ag); the owner fold between them is not bound to these rows (FOLD_GAP '
                         f'{FOLD_GAP} = RS landing tail {RS_LAND_TAIL} CHECKED + fold law {owner_fold_span(320)} UNCHECKED) and the partial rows\' producer capture is not placed'))
