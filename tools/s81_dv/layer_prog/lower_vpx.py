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
import re

OPS = [
    r'(^|\.)(attn|ffn)\.hc_pre$',
    r'(^|\.)(attn|ffn)\.norm\.(sumsq|rsqrt|scale)$',
    r'(^|\.)(attn|ffn)\.hc_post$',
    r'(^|\.)attn\.a_allgather$',
    r'(^|\.)attn\.rows_allgather$',
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
#   CTL beat on the slice pin -> rstop pin flop + delivery flop (2) -> xr pin flop (1) -> XR2 classify flop (1) -> cvld/tg: CFG_AT = 4
#   cvld (target 0) -> c_d flop (1) -> leaf relay DL 4 -> vp pin flop (1) -> sequencer step 0 (1) -> macro + output
#   register + dv (2) -> lo flop (1) -> relay DL 4 -> xr lo pin flop (1) -> XR2 lov1 flop (1): first lo pair at xr = CFG_AT + LO_AFTER_CTL
#   pk_go the edge after the 4th pair; snd -> ci flop -> rstop ci flop -> ro flop: beat on the outward port SEND_AFTER_GO
CFG_AT = 4
LO_AFTER_CTL = 16
SEND_AFTER_GO = 3
RX_WR_AFTER_PIN = 6          # RD beat on the slice pin -> rstop pin + delivery flops (2) -> xr pin flop (1) -> unpacker
                             # XR2 classify flop (1) -> busy flop (1) -> sw row-pair write flop (1); pair j one edge later each
PAIRS = 4                    # row pairs per RD beat (the 1,024-b payload)


def beat_period():
    """issue period of one 4-pair beat: 4 lo cycles + the one lo-free cycle that takes the next config (= pk_go of the
    previous beat; xr.sv:137-143), with the config CTL and the RDOUT CTL on distinct pin cycles"""
    p = PAIRS + 1
    while (LO_AFTER_CTL - 1) % p == 0:        # config of beat i (pin t_i + LO_AFTER_CTL - 1) vs RDOUT of beat j (t0 + p j)
        p += 1
    return p


def leg_program(sid, dir_, peer_sid, rows, leaf=0, t0=0, mut=None):
    """one end slice's send leg: own rows (even base row list of 2-row pairs, grouped 4 pairs a beat) out of the outward
    port (dir W at a W end, E at an E end) to the peer die's end slice (hops 1, dst mask = peer sid bit, same rows).
    Returns CTL arrivals at the slice pin (relative cycles), and the expected outward beats (cycle, rows).
    Per beat i (period P): RDOUT CTL at t0 + P i; its 4 pairs reach xr at + CFG_AT + LO_AFTER_CTL .. + 3; the config for
    beat i lands on xr the lo-free edge before (the previous beat's pk_go edge)."""
    P = beat_period()
    pairs = [rows[i:i + 2] for i in range(0, len(rows), 2)]
    assert all(len(p) == 2 and p[0] % 2 == 0 and p[1] == p[0] + 1 for p in pairs), 'rows must be even-based pairs'
    beats = [pairs[i:i + PAIRS] for i in range(0, len(pairs), PAIRS)]
    ctl, sends = [], []
    for i, bp in enumerate(beats):
        base = bp[0][0]
        assert all(bp[j][0] == base + 2 * j for j in range(len(bp))), 'beat rows must be consecutive'
        tr = t0 + P * i
        lo0 = tr + CFG_AT + LO_AFTER_CTL
        tc = lo0 - 1 - CFG_AT
        dst = base
        if mut == 'row' and i == 2:
            dst = base + 2                      # mutant: wrong dst row field in beat 2's config
        if mut == 'shift' and i == 2:
            tr += 1                             # mutant: beat 2's RDOUT CTL one edge late (collides with the next config)
        ctl.append(dict(cycle=tc, target=4, body=send_cfg(dir_, K_RD, 1, 1 << peer_sid, leaf, dst, len(bp)),
                        tag=f'cfg{i}', leaf_mask=0))
        ctl.append(dict(cycle=tr, target=0, body=_vp(VP_RDOUT, a0=base, n=len(bp)), tag=f'rdout{i}', leaf_mask=1 << leaf))
        sends.append(dict(cycle=lo0 + len(bp) - 1 + 1 + SEND_AFTER_GO, rows=[r for p in bp for r in p], dst_row=base,
                          dst_mask=1 << peer_sid, leaf=leaf, pairs=len(bp), src=sid))
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


# TP4 circuits (TOKEN-XDIE-S81 vehicle / p4l plan): d.ES <-> (d+1).WS, d.EN <-> (d+2).WN -> each die sends its own part
# out of s_0S (W, to d-1's s_7S), s_7S (E, to d+1's s_0S) and s_7N (E, to d+2's s_0N); parts land at s_0S (rank d-1),
# s_7S (rank d+1), s_0N (rank d+2).
LEGS = [('u_s_0S', 'W', 'u_s_7S'), ('u_s_7S', 'E', 'u_s_0S'), ('u_s_7N', 'E', 'u_s_0N')]

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


# ------------------------------------------------------------------------------------------------ stage h hop (XB)
# MU-DIE-S81/HOP (10-19, parent decision after MUWIN 2244fc3c0): the end-slice stage hop (substage_hop<i>) is lowered as
# XB beats, the only kind the MU lep TX window stamps / lands (ot_s81sl_lep_core K_XB / K_XQ; MU tag in the spare bits
# [1077:1045], MU-S81/LINK 258c9894b).  RTL as is: the only path that sends a beat out of an end slice's OUTWARD port
# (the lep ro) with an explicit hop count is the xr send packer (rstop: a control-plane beat with hops != 0 leaves
# unchanged; vq's own XB beats take the line default hops, which never cross the end slice).  Per end slice:
#   send config (CTL target 4) {dir outward (E at s_7*, W at s_0*), kind 2 XB, hops 1 (delivered at the peer die's end
#   slice), dst mask / leaf / row 0 (unused by an XB receive), pairs 3}, then two vp RDOUTs of 120 row pairs each (vp
#   steps rows by si[6:0]: <= 128 pairs per command; the 2nd command one edge after the 1st completes, no busy hit).
#   The packer emits a beat every 3 lo pairs -> HOP_NB = 80 beats a hop, one every 3 cycles (1 gap cycle at beat 40),
#   rate 1/3 < the lep lane rate 0.764.
# Why 3 pairs: the packer places the pairs at beat [52 +: 1024] (RD layout).  With 4 pairs, pair 3 bits [1023:993] sit
# on the MU tag field [1077:1045]: a window stamp overwrites them, the RX strip zeroes them, and an UNstamped data bit
# 1045 = 1 is taken as a tag (tagd) -- a single-user beat would be landed / stripped.  3 pairs (768 b at [819:52])
# leave [1103:820] zero, so the beat is a clean XB beat for the window logic.
HOP_LEGS = [('u_s_7N', 'E'), ('u_s_7S', 'E'), ('u_s_0N', 'W'), ('u_s_0S', 'W')]   # hwin ep order 0..3 (dv_mu_win EPS)
K_XB = 2
HOP_NB = 80                 # beats per end-slice h share per hop (ot_s81sl_lep_core NB, dsdv_mu_land NB)
HOP_PAIRS = 3               # row pairs per beat: tag field [1077:1045] clear
HOP_RD_N = 120              # row pairs per RDOUT (vp rr0 = a0 + {si[6:0], 0}: <= 128)
HOP_LEAF = 0
HOP_ROW0 = 0                # stand-in rows (GAP_HOP (1)): leaf 0 rows 0 .. 479
GAP_HOP = dict(module='tools/s81_dv/frame_return_plan.py / hc_post h store + ot_s81sl_xr send pack (XB layout)',
               port='h share rows at the end slices; XB payload layout',
               missing='TX timing is lowered (cfg + 2 RDOUT a slice, 80 XB beats on the lep ro at fixed edges, the MU '
                       'window anchors on them); NOT compiled: (1) the on-die move of the 16 slices\' h to the 4 end '
                       'slices and the leaf rows it occupies (leaf 0 rows 0..479 stand in); (2) payload: the xr packer '
                       'puts the pairs at beat [1075:52], so a kind-2 beat keeps the MU tag field [1077:1045] clear only '
                       'with <= 3 pairs (768 b): NB 80 beats carry 7,680 B of the 10,240-B share, and the peer gather '
                       'reads an XB beat in the vq layout (gidx [20:13], bf [1044:21]) -> the hop beat arrives 31 b '
                       'shifted with gidx 0.  Exact h transport needs an xr XB-layout pack mode (RTL) or NB 107 + a '
                       're-laid receive (parent / RTL decision)')


def hop_leg(sid, dir_, leaf=HOP_LEAF, row0=HOP_ROW0, nb=HOP_NB, pairs=HOP_PAIRS, rd_n=HOP_RD_N):
    """one end slice's hop leg, pin-relative cycles (cycle 0 = the first RDOUT CTL on the slice pin): CTL arrivals and
    the beats on the outward port (the rstop ro register edge, SEND edge of bench_vpx)"""
    npairs = nb * pairs
    assert rd_n % pairs == 0 and npairs % rd_n == 0 and rd_n <= 128 and row0 + 2 * npairs <= 1024
    ctl, lo = [], []
    tr = 0
    for j in range(npairs // rd_n):
        ctl.append(dict(cycle=tr, target=0, body=_vp(VP_RDOUT, a0=row0 + 2 * rd_n * j, n=rd_n), tag=f'hrd{j}',
                        leaf_mask=1 << leaf))
        lo += [tr + CFG_AT + LO_AFTER_CTL + i for i in range(rd_n)]
        tr += rd_n + 1                              # vp: next command one edge after the running one completes
    tc = lo[0] - 1 - CFG_AT                        # config on xr the lo-free edge before the first pair
    ctl.append(dict(cycle=tc, target=4, body=send_cfg(dir_, K_XB, 1, 0, 0, 0, pairs), tag='hcfg', leaf_mask=0))
    assert len({c['cycle'] for c in ctl}) == len(ctl)
    sends = []
    for k in range(nb):
        last = lo[pairs * k + pairs - 1]
        sends.append(dict(cycle=last + 1 + SEND_AFTER_GO, beat=k, rows=[row0 + 2 * p + r for p in
                                                                          range(pairs * k, pairs * k + pairs) for r in (0, 1)]))
    return dict(ctl=sorted(ctl, key=lambda c: c['cycle']), sends=sends, lo=lo)


def lower_hop(die, op, t0):
    """8 V rows a hop: per tier (engine vo_n / vo_s) the two RDOUT commands are ONE CTL beat each, slice-masked to both
    end slices of the tier (the column-4 re-injection carries it both ways; each end slice runs it on its own arrival
    edge), plus one send config per end slice (pin cycle 14 at the E end, 13 at the W end: distinct V edges, both on xr
    before the first lo pair).  Fewer rows keep the layer's hop inside issuer job 0 (NOPS 128: 12 rows split the L0
    calendar at the hop and moved the job-0 KIT before the replay edges)."""
    from dv_layer_compile import ctl_path   # noqa: E402 (plugin runs inside the compiler)
    name = op['op']
    sl = die.slices()
    rows, templates, events, insts = [], [], [], []
    for eng, tier in ((0, 'N'), (1, 'S')):
        legs = [(src, d) for src, d in HOP_LEGS if src.endswith(tier) and src in sl]
        if not legs:
            continue
        progs = {src: hop_leg(sl[src]['sid'], d) for src, d in legs}
        mask = 0
        for src, _ in legs:
            mask |= 1 << sl[src]['sid']
        ref = progs[legs[0][0]]
        first = min(c['cycle'] for c in ref['ctl'] if c['target'] == 0)
        shared = []
        for c in ref['ctl']:
            if c['target'] != 0:
                continue
            ti = len(templates)
            templates.append((f'{tier}.{name}.{c["tag"]}', _payload(mask, 0, c['leaf_mask'], c['body'])))
            rows.append(dict(eng=eng, issue=t0 + c['cycle'] - first, arg=ti,
                             what=f'{"+".join(s for s, _ in legs)} {c["tag"]}'))
            shared.append((c, ti))
        for j, (src, d) in enumerate(legs):
            sid = sl[src]['sid']
            lat = ctl_path(die, src)['edges']
            cfg = next(c for c in progs[src]['ctl'] if c['target'] == 4)
            cc = cfg['cycle'] - j                     # W end one edge earlier: one V row per engine per edge
            ti = len(templates)
            templates.append((f'{src}.{name}.hcfg', _payload(1 << sid, 4, 0, cfg['body'])))
            rows.append(dict(eng=eng, issue=t0 + cc - first, arg=ti, what=f'{src} hcfg'))
            for c, tj in shared + [(dict(cfg, cycle=cc), ti)]:
                events.append(dict(cycle=t0 + c['cycle'] - first + lat, inst=src, port='ri_e' if d == 'W' else 'ri_w',
                                   dir='in', kind='CTL', tag=f'{name}.{c["tag"]}', payload=f'template {tj}'))
            hdr = rd_beat(sid, 1, 0, 0, 0, HOP_PAIRS, 0, kind=K_XB)
            for s_ in progs[src]['sends']:
                ce = t0 + s_['cycle'] - first + lat
                events.append(dict(cycle=ce, inst=src, port='lep (outward line port)', dir='out', kind='XB',
                                   tag=f'{name} h beat {s_["beat"]} rows {s_["rows"][0]}..{s_["rows"][-1]}', hop=name,
                                   beat=s_['beat'], payload='h share (stand-in leaf rows)', boundary='offdie',
                                   observe=f'{src} outward ring port ({"ro_w" if d == "W" else "ro_e"} inside the lep '
                                           f'master) -> lep core frame mux (MU tag stamp) -> lt_lk link lanes',
                                   words=[[ce, f'{hdr:x}', f'{(1 << 52) - 1:x}']],
                                   data_masked='row pairs [819:52] = leaf rows (stand-in); [1103:820] = 0 (MU tag field)'))
            insts.append(src)
        assert len({r['issue'] for r in rows if r['eng'] == eng}) == sum(r['eng'] == eng for r in rows)
    return dict(status='PARTIAL' if insts else 'GAP', unit='end-slice send cfg (XB, hops 1) + 2 x vp RDOUT 120 -> lep '
                'ro (MU TX window) -> peer end slice', insts=insts, gap=GAP_HOP, rows=rows, templates=templates,
                events=events, bench=BENCH, atomic=True, hop=dict(nb=HOP_NB, pairs=HOP_PAIRS, rd_n=HOP_RD_N, leaf=HOP_LEAF,
                                                     row0=HOP_ROW0))


def lower(die, op, ctx):
    name = op['op']
    t0 = int(ctx.get('t_issue', 0))
    if re.search(r'(^|\.)substage_hop\d+$', name):
        return lower_hop(die, op, t0)
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
        return dict(status='PARTIAL', unit='slice vp POST (a0 = R + 1: post row, comb R+2..R+5) -> vn h store',
                    insts=[ctx.get('slice')], gap=GAP_POST, bench=BENCH_VP)
    if name.endswith('a_allgather') or name.endswith('rows_allgather') or name.endswith('router_allgather'):
        rank = int(ctx.get('rank', 0))
        sl = die.slices()
        rows, templates, events, insts = [], [], [], []
        own = a_rows(rank) if name.endswith('a_allgather') else []
        used = set()
        for src, d, peer in LEGS:
            if src not in sl or not own:
                continue
            sid, psid = sl[src]['sid'], sl[peer]['sid']
            leg = leg_program(sid, d, psid, own, t0=0)
            eng = 0 if src.endswith('N') else 1
            # the calendar issues each CTL so that it is on the slice pin at its leg cycle: issue = t0 + cycle - lat
            from dv_layer_compile import ctl_path   # noqa: E402 (plugin runs inside the compiler)
            lat = ctl_path(die, src)['edges']
            first = min(c['cycle'] for c in leg['ctl'])
            # one V row per engine per edge (vo_n / vo_s): the legs of one tier are staggered whole (the pin-relative
            # programme of each slice is unchanged)
            sh = 0
            while any((eng, t0 + c['cycle'] - first + sh) in used for c in leg['ctl']):
                sh += 1
            first -= sh
            used |= {(eng, t0 + c['cycle'] - first) for c in leg['ctl']}
            for c in leg['ctl']:
                ti = len(templates)
                templates.append((f'{src}.{c["tag"]}', _payload(1 << sid, c['target'], c['leaf_mask'], c['body'])))
                issue = t0 + c['cycle'] - first
                rows.append(dict(eng=eng, issue=issue, arg=ti, what=f'{src} {c["tag"]}'))
                events.append(dict(cycle=issue + lat, inst=src, port='ri_e' if d == 'W' else 'ri_w', dir='in',
                                   kind='CTL', tag=c['tag'], payload=f'template {ti}'))
            for s in leg['sends']:
                # LB2-S81/EVENTS: the beat as it leaves the outward port (bench_vpx SEND edge): header bits [51:0]
                # exact, the 4 row pairs are leaf-store data (fixture rows; their producer is not compiled: GAP_PLACE).
                # The outward port is INSIDE the end-slice lep master: at the die cut it continues as the reliable
                # link lanes lt_lk_* (seq / CRC / credits: flow control at the off-die boundary, owner 10-14), so no
                # cut sees this word at a fixed cycle -> boundary 'offdie' (bench_vpx checks it through the real lep)
                ce = t0 + s['cycle'] - first + lat
                hdr = rd_beat(s['src'], 1, s['dst_mask'], s['leaf'], s['dst_row'], s['pairs'], 0)
                events.append(dict(cycle=ce, inst=src, port='lep (outward line port)', dir='out', kind='RD',
                                   tag=f'rows {s["rows"][0]}..{s["rows"][-1]} -> sid {psid}',
                                   payload='fixture a_allgather words', boundary='offdie',
                                   observe=f'{src} outward ring port ({"ro_w" if d == "W" else "ro_e"} of the slice '
                                           f'inside the lep master) -> lt_lk link lanes',
                                   words=[[ce, f'{hdr:x}', f'{(1 << 52) - 1:x}']],
                                   data_masked='row pairs [1075:52] = leaf rows (fixture)'))
            insts.append(src)
        st = 'PARTIAL' if own else 'GAP'
        gap = GAP_PLACE if own else dict(GAP_PLACE, missing='same endpoint ABI as attn.a_allgather (bench_vpx); the '
                                         'production rows of this op are not placed')
        return dict(status=st, unit='end-slice send cfg + vp RDOUT -> lep -> peer end-slice RD receive', insts=insts,
                    gap=gap, rows=rows, templates=templates, events=events, bench=BENCH)
    if name.endswith('allreduce'):
        return dict(status='GAP', unit='RS + AG over the end-slice endpoints + owner fold', insts=[], gap=GAP_FOLD,
                    bench=BENCH)
    return dict(status='GAP', unit='vpx', insts=[], gap=dict(module='lower_vpx', port='-', missing=f'{name} not lowered'))
