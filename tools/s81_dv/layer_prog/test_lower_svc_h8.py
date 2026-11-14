"""S81-SVCC-1 (11-08) R5: the H8 slice's two-pass svc job (lower_svc OT_SVC_H / heads=8) against the H16 job.

Fixture-free: a synthetic layer job (random BF16 q / P, random window codes, random FP32 P.V, sinks) runs through the
real Job._frames / schedule / finish code.  Checks:
  * H16 (heads=16, the default) is byte-identical to origin/main c477959f3c: the digest of every q word + cycle, the
    SOT booking and the done / span edges equals the one the unmodified module gives (H16_DIGEST, made by
    svc/h8_digest.py on the base module);
  * H8: landing frames once; pass j's ATTN_Q / SMJ / SO frames are today's words for heads 8 j .. 8 j + 7; the fold-root
    PV frame of each pass and the P.V entry words decode per head per row / dim to the H16 values; GO MORE; the passes
    never share a cycle (pass 1 starts after pass 0 retired, GO 1 after pass 0's drain); one SOT per job books all 16 heads after the final pass; the compiler mutants change exactly what they name.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lower_svc as L  # noqa: E402

AG = dict(j_w=6, j_e=12, jd_w=32, jd_e=25, q_w=20, q_e=23, pv_w=4, pv_e=4)


def bf16(a):
    return (np.asarray(a, np.float32).view(np.uint32) & np.uint32(0xFFFF0000)).view(np.float32)


def synth(heads=16, mutant=None, T=128, so=True, mod=L):
    import rtl_hdc_v41x_attn_campaign as C
    mod.rope_cs_u32 = lambda fx: ([0x3F800000 + i for i in range(32)], [0x3F000000 + i for i in range(32)])
    j = mod.Job.__new__(mod.Job)
    rng = np.random.default_rng(1108)
    j.pio_extra, j.timing_profile = 0, 'closing_allq'
    j.timing = mod.SERVICE_TIMING['closing_allq']
    if hasattr(mod, 'SVC_H'):
        j.hs, j.npass = heads, 16 // heads
    j.C, j.meta, j.compressed = C, {'kind': 'sliding'}, T != 128
    j.h0, j.pos = 0, 1000
    j.wfirst = j.pos - (mod.WIN - 1)
    j.codes = rng.integers(0, 256, (mod.WIN, mod.D))
    j.e8 = rng.integers(0, 256, (mod.WIN, 16))
    j.sel, j.held = np.zeros(0, np.int64), np.zeros(0, bool)
    j.T = T
    j.q = bf16(rng.standard_normal((16, mod.D)))
    j.p = bf16(rng.random((16, T)))
    j.scale = np.float32(mod.D ** -0.5)
    j.sinkw = rng.standard_normal(16).astype(np.float32)
    j.pv = rng.standard_normal((16, mod.D)).astype(np.float32)
    j.tag, j.mutant, j.allq, j.fx, j.so, j.owner = 0x21, mutant, True, None, so, None
    j.ik, j.t_ik = None, 0
    j.frames = j._frames()
    return j


def run(job, mod=L):
    s = job.schedule(1805, 3001, 3763, AG['j_w'], AG['j_e'])
    s['issue'] = s['s_j'] - 2
    if hasattr(mod, 'finish'):
        s = mod.finish(job, s, dict(AG))
    else:                                    # origin/main c477959f3c build() tail, verbatim
        dw = de = s['done']
        if job.so and 'SOT' in s['at']:
            rec = mod.sot_booking_for(job, s)
            i = [k for k, (n_, _) in enumerate(job.frames) if n_ == 'SOT'][0]
            job.frames[i] = ('SOT', list(rec['words']))
            c0 = s['at']['SOT']
            s['frame_words']['SOT'] = [(c0 + k, w) for k, w in enumerate(rec['words'])]
            pos = {c: k for k, (c, _) in enumerate(s['words'])}
            for k, w in enumerate(rec['words']):
                s['words'][pos[c0 + k]] = (c0 + k, w)
            s['sot'] = rec
            dw, de = rec['done']['W'], rec['done']['E']
        s['done_w'], s['done_e'] = dw, de
        s['ls'] = max(dw + AG['jd_w'], de + AG['jd_e']) - s['s_j']
    return s


def digest(job, s, mod=L):
    pv = [mod.pv_words(job, s, e) for e in ('u_rsv_11', 'u_rsv_05')]
    rec = dict(words=[[c, f'{w:x}'] for c, w in s['words']], at=s['at'],
               edges={k: s[k] for k in ('s_j', 'go', 'pvs', 'po', 'pvo', 'pv_first', 'pv_last', 'done_w', 'done_e', 'ls')},
               sot=[f'{w:x}' for w in s['sot']['words']] if 'sot' in s else None,
               pexp=[f'{w:x}' for w in job.p_words], pv=pv, nframes=s['nframes'])
    return hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()


# ------------------------------------------------------------------------------------------------------- H16 identity
@pytest.mark.parametrize('T', [128, 256])
def test_h16_default_is_byte_identical(T):
    exp = json.loads((HERE / 'svc/h8_digest_base.json').read_text())
    j = synth(16, T=T)
    assert j.hs == 16 and j.npass == 1
    assert digest(j, run(j)) == exp[str(T)]


def test_h16_is_the_default():
    assert L.SVC_H == 16 or 'OT_SVC_H' in __import__('os').environ
    j = synth(16)
    assert 'GO.1' not in dict(j.frames) and not hasattr(j, 'fpass')


# ------------------------------------------------------------------------------------------------------------ H8 frames
def frames(j):
    return dict(j.frames)


def test_h8_landing_once_and_pass_frames_are_todays_words():
    a, b = synth(16), synth(8)
    fa, fb = frames(a), frames(b)
    names = [n for n, _ in b.frames]
    for n in ('CFG', 'OWN_ROW', 'WIN_LOAD', 'SOT'):
        assert names.count(n) == 1
    for n in ('CFG', 'OWN_ROW', 'WIN_LOAD'):
        assert fa[n] == fb[n]
    assert fa['ATTN_Q0'] == fb['ATTN_Q0'] and fa['ATTN_Q1'] == fb['ATTN_Q1']
    assert fa['SMJ'] == fb['SMJ'] == fb['SMJ.1']
    assert fa['SMJ_SO'] == fb['SMJ_SO']
    for g in range(16):
        assert fa[f'SMJ_OP{g}'] == fb[f'SMJ_OP{g}']
    assert names == (['CFG', 'OWN_ROW', 'WIN_LOAD', 'SOT', 'ATTN_Q0', 'SMJ', 'GO', 'ATTN_Q1', 'SMJ.1', 'GO.1', 'SMJ_SO']
                     + [f'SMJ_OP{g}' for g in L.SO_ORDER])
    assert [n for n, _ in a.frames] == [n for n in names if n not in ('SMJ.1', 'GO.1')][:4] + \
        ['ATTN_Q0', 'ATTN_Q1', 'SMJ', 'GO', 'SMJ_SO'] + [f'SMJ_OP{g}' for g in L.SO_ORDER]
    assert len(b.frames) == len(a.frames) + 2      # + SMJ.1, GO.1


def unpack_h16_p(words, T):
    out = np.zeros((16, T), np.int64)
    for w, x in enumerate(words[1:]):
        for jj in range(2):
            t = 2 * w + jj
            if t < T:
                for h in range(16):
                    out[h, t] = (x >> (16 * (jj * 16 + h))) & 0xFFFF
    return out


@pytest.mark.parametrize('T', [128, 130, 640])
def test_h8_fold_root_p_words_per_head_per_row(T):
    a, b = synth(16, T=T), synth(8, T=T)
    ref = unpack_h16_p(a.p_words, T)
    assert b.p_words == a.p_words
    for k, pw in enumerate(b.p_words_pass):
        assert pw[0] >> 508 == 5 and (pw[0] >> 480) & 4095 == -(-T // 4) == len(pw) - 1
        for w, x in enumerate(pw[1:]):
            for r in range(4):
                t = 4 * w + r
                for h in range(8):
                    v = (x >> (16 * (8 * r + h))) & 0xFFFF
                    assert v == (ref[8 * k + h, t] if t < T else 0)


# --------------------------------------------------------------------------------------------------------- H8 schedule
def test_h8_schedule_passes_never_share_a_cycle():
    b = synth(8)
    s = run(b)
    cyc = [c for c, _ in s['words']]
    assert cyc == sorted(cyc) and len(set(cyc)) == len(cyc)
    p0, p1 = s['passes']
    at = s['at']
    assert p0['more'] == 1 and p1['more'] == 0 and p0['heads'] == list(range(8)) and p1['heads'] == list(range(8, 16))
    go0, go1 = s['frame_words']['GO'][0][1], s['frame_words']['GO.1'][0][1]
    assert (go0 >> L.GO_MORE) & 1 == 1 and (go1 >> L.GO_MORE) & 1 == 0
    for w, p in ((go0, p0), (go1, p1)):
        assert w & 0xFFFF == p['po'] and (w >> 16) & 0xFFFF == p['pvo'] and (w >> 32) & 0xFFFF == p['pio']
        assert w >> 49 & ((1 << 400) - 1) == 0
    # pass 1's q replaces the slice's 8-head q memory only after pass 0's last P.V word; its GO after pass 0's drain
    assert at['ATTN_Q1'] >= p0['pv_last'] + L.JD_LAT + L.PASS_GAP and p1['go'] >= p0['pv_last'] + L.PASS_GAP
    assert p1['pv_first'] > p0['pv_last']
    # the SO programme after the last drain; the SO gather window opens after every P.V word of the job
    assert at['SMJ_SO'] >= p1['pv_last'] + L.SO_GAP
    assert s['sot']['entry_window'][0] > p1['pv_last']
    # done = today's rule: each half's booked retires, after the job's last q word
    assert (s['done_w'], s['done_e']) == (s['sot']['done']['W'], s['sot']['done']['E'])
    assert min(s['done_w'], s['done_e']) > s['words'][-1][0] + 1
    assert s['ls'] == max(s['done_w'] + AG['jd_w'], s['done_e'] + AG['jd_e']) - s['s_j']


def test_h8_pass0_matches_h16_up_to_go():
    a, b = synth(16), synth(8)
    sa, sb = run(a), run(b)
    for n in ('CFG', 'OWN_ROW', 'WIN_LOAD', 'SOT', 'ATTN_Q0'):
        assert sa['at'][n] == sb['at'][n]
    # pass 0 sends one ATTN_Q frame (129 words) less before its SMJ / GO (GO bound by the q stream, not W_SLACK)
    assert sb['at']['SMJ'] == sa['at']['SMJ'] - 129 and sb['go'] == sa['go'] - 129
    assert sb['pvo'] - sb['po'] == sa['pvo'] - sa['po']
    assert sb['passes'][0]['po'] == sa['po']  # H8 static feed every two cycles needs the same T128 frame lag


def test_h8_sot_is_todays_booking_of_all_heads():
    from smwire_cal import sot_decode
    b = synth(8)
    s = run(b)
    rec = s['sot']
    assert set(rec['heads']) == set(range(16))
    assert {hf for _, _, _, hf in rec['arrival'].values()} == {'E', 'W'}
    h, p0, p1 = rec['words']
    for t in range(16):
        d = sot_decode(h, p0, p1, t)
        assert d['last'] > d['first'] and d['retire'] > d['read'] + 34
    assert dict(b.frames)['SOT'] == list(rec['words'])


def test_h8_pv_words_decode_per_head_per_dim():
    b = synth(8)
    s = run(b)
    vals = np.asarray(b.pv, np.float32).view(np.uint32)
    for k in range(2):
        for e, t0 in (('u_rsv_11', 0), ('u_rsv_05', 8)):
            ws = L.pv_words(b, s, e, pass_k=k)
            assert ws[0][0] == s['passes'][k]['pv_first'] - 1 and len(ws) == 2 * L.NPVQ + 1
            for w, (_, dh, _) in enumerate(ws[:-1]):
                d = int(dh, 16) >> 1
                t, bb, wi = t0 + w // 40, (w % 40) // 5, w % 5
                if wi == 0:
                    assert d >> 512 & 1 and (d >> 64) & 255 == bb
                    assert (d >> 32) & 1 == k and (d >> 33) & ((1 << 31)-1) == 0
                else:
                    assert d >> 256 == 0
                    dim = 32 * t + 8 * (wi - 1) + bb
                    for h in range(8):
                        assert (d >> (32 * h)) & 0xFFFFFFFF == vals[8 * k + h, dim]
    # every (head, dim) of the rank leaves exactly once over both passes and both entries
    seen = set()
    for k in range(2):
        for e, t0 in (('u_rsv_11', 0), ('u_rsv_05', 8)):
            for w in range(2 * L.NPVQ):
                t, bb, wi = t0 + w // 40, (w % 40) // 5, w % 5
                if wi:
                    for h in range(8):
                        seen.add((8 * k + h, 32 * t + 8 * (wi - 1) + bb))
    assert len(seen) == 16 * 512


# ---------------------------------------------------------------------------------------------------------- mutants
def test_h8_mutants_change_what_they_name():
    base = synth(8)
    fb = frames(base)
    hs = frames(synth(8, 'hb_swap'))
    assert (hs['ATTN_Q0'][0] >> 448) & 1 == 1 and (hs['ATTN_Q1'][0] >> 448) & 1 == 0
    assert hs['ATTN_Q0'][1:] == fb['ATTN_Q0'][1:]
    pd = synth(8, 'pass_drop')
    assert not any(n.endswith('.1') or n == 'ATTN_Q1' for n, _ in pd.frames)
    sp = run(pd)
    assert sp['passes'][0]['more'] == 0 and len(sp['passes']) == 1
    ps = [n for n, _ in synth(8, 'pass_swap').frames]
    assert ps.index('ATTN_Q1') < ps.index('ATTN_Q0')
    sm = run(synth(8, 'more_off'))
    assert all((sm['frame_words'][g][0][1] >> L.GO_MORE) & 1 == 0 for g in ('GO', 'GO.1'))
    assert (run(synth(8))['frame_words']['GO'][0][1] >> L.GO_MORE) & 1 == 1


def test_h8_frame_count_fits_the_job_word():
    b = synth(8)
    s = run(b)
    arg, jw = L.job_word(s['nframes'], b.tag)
    assert (arg >> 7) & 255 == len(b.frames) < 256


def test_h8_requires_on_die_p(monkeypatch):
    monkeypatch.setattr(L, 'PPATH', False)
    j = L.Job.__new__(L.Job)
    with pytest.raises(ValueError):
        L.Job.__init__(j, '/nonexistent', heads=8)
    with pytest.raises(ValueError):
        L.Job.__init__(j, '/nonexistent', heads=4)


@pytest.mark.parametrize('T', [1, 4, 5, 128, 130, 640])
def test_h8_p_feed_never_reads_a_word_before_its_arrival(T):
    npw = -(-T // 4)
    lag = L.h8_p_feed_lag(npw)
    assert all(lag + 2 * (j // 2) >= 2 * j for j in range(npw))
    if npw > 1:
        assert any(lag - 1 + 2 * (j // 2) < 2 * j for j in range(npw))
    if T == 128:
        assert lag == 32
    j = synth(8, T=max(T, 128))
    _, rec = j.pass_go(0, 0)
    assert rec['po'] == rec['pio'] + L.P_ARR + L.h8_p_feed_lag(rec['npw']) + L.P_PO_M


def test_h8_folded_sm_operand_rows_and_booking_follow_two_cycle_cadence():
    b = synth(8)
    s = run(b)
    for g in range(16):
        at = s['at'][f'SMJ_OP{g}']
        fw = s['frame_words'][f'SMJ_OP{g}']
        assert [c for c, _ in fw] == [at] + [at + 1 + 2*r for r in range(32)]
        # The booking covers the last physical input row; a one-cycle-per-row
        # window would close 31 cycles before the final row reached the target.
        rec = s['sot']
        assert rec['heads'][g]['last'] + rec['install_edge'] == fw[-1][0] + L.SOT_W_LAT + L.SOT_SLACK + L.SOT_INST
    cyc = {c for c,_ in s['words']}
    first = s['at']['SMJ_OP0']
    assert first + 2 not in cyc


@pytest.mark.parametrize("selected", [False, True])
def test_native_rt2_optin_record_does_not_change_go(selected):
    job = synth(heads=8, T=32, so=False)
    old_word, old_record = job.pass_go(0, 100)
    job.native_rt2_prospective = selected
    word, record = job.pass_go(0, 100)
    assert word == old_word
    if selected:
        calendars = record.pop("native_rt2_calendar")
        assert [item["go_phase"] for item in calendars] == [0, 1]
        assert all("OT_SVC_NATIVE_RT2_CALENDAR" in item["build_defines"] for item in calendars)
        assert all(item["h8_calibrated"] is False for item in calendars)
    else:
        assert "native_rt2_calendar" not in record
    assert record == old_record
