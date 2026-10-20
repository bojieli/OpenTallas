"""HBM-H9BIND 10-20: renewed semantic delta review (CANDIDATE, LEAD digest admission owed) of the e4->fallback unread review.
The 309 entries / 65066 bits / instances / ports / nets / ranges are copied unchanged; ONLY the four source pins that
a6572c814 (HBM-DIE10 r10: l24 XSLOT/OPEN_IL + QINT8 checker view + INT8 hard tile) changed are re-pinned, after review
of the exact diffs (recorded below). source_commit stays the transfer's 59576ab0f, where all four equal the die src bytes.
Run from the ep6 codex-hbm-die11-1020 dir:  python3 make_review_h9bind.py"""
import hashlib, json
from pathlib import Path
SN = 'rtl/hbm_accel/loader/service_native/'
REPIN = {
 SN + 'ot_hbm_svc_sm_feed_programmed_rel_id.sv': ('7b303c847', 'XSLOT/CTXW/OPEN_IL params (die contract: defaults 0 -> CTXW 46, block_ready=producer_ready unchanged); '
   'xaddr add c_xit+c_xb (c_xb=0 at XSLOT 0); QINT8 S1 checker copy now sees the SM-front INT8 view (s1_packet) and adds sticky i8_f to fault. '
   'Reviewed unread ports (via group lt0/lt1/lb0/lb1/fm/expected_request) remain checker-copy observations of ot_smh_static_feed, same widths; '
   'the change only makes the checker mirror the SM front more exactly; fault (read) gains i8_f. Classification duplicate_checker_feed holds.'),
 SN + 'ot_hbm_svc_sm_group_rel_id.sv': ('c3852a6f8', 'adds XSLOT/CTXW/OPEN_IL pass-through params only (die contract: defaults); ctx width param; '
   'no port added/removed; reviewed outputs lt0/lt1/lb0/lb1/fm/expected_request unchanged in width and source.'),
 SN + 'ot_hbm_svc_sm_xcal_rel_t.sv': ('dddedcec9', 'XSLOT pass-through parameter only (default 0); no port or logic change; no reviewed entry on this master.'),
 'rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv': ('51fdb4368', 'ENABLE_INT8=1 (die value) now instantiates the hard SAFE tile ot_smh_int8_tile '
   '(cycle-exact with the soft glue, LH-SMATT/INT8) with kept select copies; INT8W param default 0 passed to u_front. Reviewed unread port '
   'request (43 b) is still u_front.request = command[82:40] observation (front unchanged at INT8W 0); classification checked_request_observation holds.'),
}
r = json.loads(Path('fallback_unread/review.json').read_text())
pred = hashlib.sha256(Path('fallback_unread/review.json').read_bytes()).hexdigest()
rec = []
for p, (old_commit, why) in REPIN.items():
    cur = hashlib.sha256(Path('src/' + p).read_bytes()).hexdigest()
    assert p in r['source_sha256'] and r['source_sha256'][p] != cur, p
    rec.append({'path': p, 'old_sha256': r['source_sha256'][p], 'old_commit': old_commit, 'new_sha256': cur,
                'new_commit': 'a6572c814', 'review': why})
    r['source_sha256'][p] = cur
for p, s in r['source_sha256'].items():
    assert hashlib.sha256(Path('src/' + p).read_bytes()).hexdigest() == s, ('unreviewed drift', p)
r['delta_review_h9bind'] = {'predecessor_review_sha256': pred, 'repinned_sources': rec, 'entries_changed': 0,
    'approved_bits': r['approved_bits'], 'scope': 'functional source intent of unread observation ports only; '
    'h9c fallback controller has no reviewed entry; no physical/native/token qualification granted'}
r['reviewer'] = ('HBM-H9BIND (LEAD9-HBM sub-lane, Claude): renewed semantic delta review of 4 a6572c814 source changes '
                 'on the h9c-fallback die; CANDIDATE pending LEAD digest admission')
r['time'] = '2026-10-20T13:50:00-07:00'
Path('fallback_unread/review_h9bind.json').write_text(json.dumps(r, indent=1) + '\n')
print('REVIEW_H9BIND repinned', len(rec), 'entries', len(r['approved_entries']), 'bits', r['approved_bits'],
      'sha', hashlib.sha256(Path('fallback_unread/review_h9bind.json').read_bytes()).hexdigest())
