import os
import sys, pickle, random, collections
sys.path.insert(0, '/home/ubuntu/wt/kv-prog17-1020')
from tools.qwen_static_schedule import mu_calendar as MC
from tools.qwen_static_schedule import mu_opcal as O
MC.KV_PHASE['groups'] = int(os.environ.get('GROUPS', '68'))
rows = pickle.load(open(__import__('os').environ.get('ROWS','/tmp/kvprog17/rows.pkl'),'rb'))
MC.KV_ATT_END = int(sys.argv[1]); F = int(sys.argv[2]); N = int(sys.argv[3]); spread = int(sys.argv[4])
fp = MC.kv_frame_params(rows)
base = [round(k * fp['layer_period'] / MC.KV_USERS) for k in range(1, MC.KV_USERS)]
rnd = random.Random(1); why = collections.Counter()
for i in range(N):
    st = base if i == 0 else [b + rnd.randint(-spread, spread) for b in base]
    stage = 'compile'
    try:
        cal = O.compile_frame(F, p=fp, starts=st); stage='gap'
        gaps, _ = MC.kv_gap_table(cal); stage='check'
        MC.check_kv_programme(rows, gaps, MC.kv_frame_starts(cal), cal['H'])
        print('OK', i, st, cal['tokens_per_frame'], round(cal['aggregate_tok_s'],1)); break
    except MC.ScheduleError as e:
        why[(stage, str(e)[:100])] += 1
for k, v in why.most_common(6): print(v, k)
