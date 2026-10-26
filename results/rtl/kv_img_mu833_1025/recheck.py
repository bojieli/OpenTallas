# independent re-check of a compiled MU bundle: rebuild the frame from the bundle's own SU rows + the compile's phase
# profile, require the MU target1/target3 words to match, and re-run the KV programme's static checks on the frame
import json, pickle, sys
sys.path.insert(0, sys.argv[1])
from tools.qwen_static_schedule import mu_calendar as MC, mu_opcal as O
fs = pickle.load(open(sys.argv[2], 'rb')); bmu, bsu = sys.argv[3], sys.argv[4]
rd = lambda p: [int(x, 16) for x in open(p).read().split()]
su, mu, own = rd(bsu + '/target1.hex'), rd(bmu + '/target1.hex'), rd(bmu + '/target3.hex')
MC.KV_PHASE.update(fs['PHASE']); MC.KV_ATT_END = fs['ATT_END']
rows = MC.kv_rows_from_image(su)
assert rows == fs['rows'], 'SU rows differ from the compile input'
ft = 1 if fs['F'] > MC.KV_FRAME_F else None
st, cal = MC.kv_frame_search(rows, fs['F'], filler_tokens=ft)
gaps, per = MC.kv_gap_table(cal)
starts = MC.kv_frame_starts(cal)
chk = MC.check_kv_programme(rows, gaps, starts, cal['H'])
img = MC.kv_layer_image_mu(su, gaps)
o, _ = MC.kv_ownership_roots_mu(rows, gaps)
gaps_img = [mu[326 + 36 * u: 326 + 36 * (u + 1)] for u in range(4)]
legal = all(MC.kv_launch_legal(rows[s - 1], b) for u, k, s, b in MC.kv_programme_events(rows, gaps, starts, cal['H'], detail=True)[4])
print(json.dumps(dict(F=fs['F'], ticks=MC.kv_phase_ticks(), beat_cycle=MC.kv_beat_cycle(), filler_first_starts=st,
                      mu_words=len(mu), mu_image_equal=img == mu, gaps_equal=gaps_img == gaps, user0_gaps_zero=not any(gaps[0]),
                      ownership_bundle=own, ownership_recomputed_no_lead=o, patterns=per, checks=chk, all_launches_legal=legal,
                      tokens_per_frame=cal['tokens_per_frame'], aggregate_tok_s=round(cal['aggregate_tok_s'], 1))))
