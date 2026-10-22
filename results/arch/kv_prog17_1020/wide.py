import os, sys, pickle, random
sys.path.insert(0, '/home/ubuntu/wt/kv-prog17-1020')
from tools.qwen_static_schedule import mu_calendar as MC
from tools.qwen_static_schedule import mu_opcal as O
MC.KV_PHASE['groups'] = 68
rows = pickle.load(open('rows_r16.pkl', 'rb')); MC.KV_ATT_END = int(sys.argv[1]); seed = int(sys.argv[2]); N = int(sys.argv[3])
fp = MC.kv_frame_params(rows); T = 258048; H = 2 * T
rnd = random.Random(seed); fails = {}
for i in range(N):
    st = sorted(rnd.randrange(0, H) for _ in range(3)) if seed % 2 else [rnd.randrange(0, 7057) for _ in range(3)]
    try:
        cal = O.compile_frame(2, p=fp, starts=st)
        gaps, _ = MC.kv_gap_table(cal)
        MC.check_kv_programme(rows, gaps, MC.kv_frame_starts(cal), cal['H'])
        print('OK', st, cal['tokens_per_frame'], round(cal['aggregate_tok_s'], 1), flush=True); sys.exit(0)
    except MC.ScheduleError as e:
        k = str(e)[:60]; fails[k] = fails.get(k, 0) + 1
print('NONE', seed, fails, flush=True)
