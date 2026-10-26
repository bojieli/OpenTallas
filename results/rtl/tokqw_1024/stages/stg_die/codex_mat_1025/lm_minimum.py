import copy, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent / 'tree/rtl/test/qwen_dv'))
import dv_lower_mat_bench as B
original_ownership = B.D.ownership

def one_round(*a, **kw):
    own = copy.deepcopy(original_ownership(*a, **kw))
    own['lm_head']['blocks'] = own['lm_head']['blocks'][:6]
    own['lm_head']['rounds'] = 1
    return own

B.D.ownership = one_round
name = sys.argv[1]
work = Path(__file__).parent / name
work.mkdir(exist_ok=True)
ages = B.M.load_ages('/srv/opentallas-scratch2/claude/tok-qw/s8exp_wf3/die/cal_mat/stn_ages.json')
B.ARF['on'] = True
ok, n, errs, info = B.run_lm(work, ages, np.random.default_rng(1), 'amnb5' if name.endswith('mut') else None)
print('LM_MINIMUM', 'PASS' if ok == n and not errs else 'FAIL', f'{ok}/{n}', json.dumps(info), 'errors', errs[:12])
sys.exit(0 if ok == n and not errs else 1)
