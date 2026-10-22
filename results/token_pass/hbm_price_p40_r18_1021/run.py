"""Conditional incremental P40/R18 price; existing census and scheduling law unchanged.

HC delta 512 = existing k4 495 + P23->P39 first capture 16 + QCHX 1.
QDQ delta 120 = read75 + done45, replaces former read-only47.
141 is a separate RL54->75 sensitivity, not selected geometry.
"""
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
rows = {}
for name, base, extra in [
    ('release', 'results/token_pass/hbm_price_qdq54_hc17_1021/base_h9b.json', []),
    ('next', 'results/rtl/hbm_rate7_1020/census/m_xl_i8.json', ['--bw','98','--bridge','1']),
]:
    rows[name] = {}
    for label, hc, qdq in [('previous',495,47), ('p40_r18',512,120), ('rl75_sensitivity',512,141)]:
        m = json.loads((ROOT/base).read_text())
        for cls, delta in [('HC.HC_MIX',hc), ('FUSED.QDQ_FP8',qdq)]:
            for shape in m['designs']['ds_ar'][cls]['shapes'].values():
                if shape.get('cycles') is not None:
                    shape['cycles'] += delta
        stem = OUT/f'{name}_{label}'
        inp = stem.with_suffix('.json')
        inp.write_text(json.dumps(m))
        code = 'from hgi_sim import toksim_hbm_census_1019 as C; C.main()'
        with stem.with_suffix('.log').open('w') as log:
            subprocess.run([sys.executable,'-c',code,'--measured',str(inp),'--out',str(stem)+'_census.json']+extra,
                           cwd=ROOT, env=dict(os.environ,PYTHONPATH='tools'),stdout=log,stderr=subprocess.STDOUT,check=True)
        row = {}
        for design, suffix in [('ds','AR'),('qwen','qwen')]:
            j = json.loads((OUT/f'{stem.name}_census_jobs/info_banklat_all__{suffix}.json').read_text())
            row[design] = dict(schedule_total=j['schedule_total'],
                classes={c:{k:v[k] for k in ('n','used_sum','crit_n','crit_cycles')} for c,v in j['classes'].items() if c in ('HC.HC_MIX','FUSED.QDQ_FP8')})
        rows[name][label] = row
        (OUT/'sweeps.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(name,label,row,flush=True)
