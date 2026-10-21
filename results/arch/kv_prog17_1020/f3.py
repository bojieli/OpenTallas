import sys, pickle, os
sys.path.insert(0, '/home/ubuntu/wt/kv-prog17-1020')
from tools.qwen_static_schedule import mu_calendar as MC
from tools.qwen_static_schedule import mu_opcal as O
MC.KV_PHASE['groups'] = int(os.environ.get('GROUPS', '68'))
rows = pickle.load(open(sys.argv[2], 'rb')); MC.KV_ATT_END = int(sys.argv[1]); F = int(sys.argv[3])
fp = MC.kv_frame_params(rows); P = fp['layer_period']
T = 258048 if 'r16' in sys.argv[2] else 250368
for st in ([round(P/4), T + round(P/2), 2*T + round(3*P/4)], [0, T, 2*T], [1764, T + 3528, 2*T + 5293]):
    try:
        cal = O.compile_frame(F, p=fp, starts=st, filler_tokens=1)
        gaps, _ = MC.kv_gap_table(cal)
        chk = MC.check_kv_programme(rows, gaps, MC.kv_frame_starts(cal), cal['H'])
        print('OK', st, cal['tokens_per_frame'], round(cal['aggregate_tok_s'], 1), [round(u['tok_s'], 1) for u in cal['users']]); break
    except MC.ScheduleError as e:
        print('FAIL', st, str(e)[:150])
