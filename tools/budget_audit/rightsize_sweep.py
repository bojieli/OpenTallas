"""Right-size sweep: token cycles (S2) of Qwen P8191 TP4 and DS 1M TP96 rank 0 vs SM count and SU lane count.
SM: R = ceil(m / N_SM) rows a SM (timing.cost; DS walk WC.N_SM).  SU: VC.layout(f, N_SU, 256)."""
import json, math, sys, copy
from pathlib import Path
ROOT = Path('/home/ubuntu/OpenTallas'); sys.path.insert(0, str(ROOT / 'tools'))
from hgi_sim import timing as T, qwen_compiler as QC
which = sys.argv[1]
SMS = [8, 12, 16, 20, 24, 28, 32, 40, 48]
SUS = [256, 512, 768, 1024]
state = dict(nsm=32, nsu=1024)
VC = T._su_model(); _lay = VC.layout
VC.layout = lambda f, N, M: _lay(f, state['nsu'], M)
_cost = T.cost
def cost_q(r, dyn, L, cfg=None):
    if r.unit == 'SM' and 'SM.bf16_lines_per_row_k' in T.MEAS:
        b = r.desc['B']; _, n, m, st, _ = T.eff(b, dyn, L)
        tr = T.TRANSPORT if (r.param & 3) == 3 else 1.0
        stream = n * m * T.ESZ[b.fmt] * tr / T.cv('hbm', 'bytes_per_cycle')
        R = -(-m // state['nsm'])
        lines = math.ceil(T.MEAS['SM.bf16_lines_per_row_k']['value'] * R * n * T.SM_RATE)
        comp = lines + T.MEAS['SM.drain']['value']
        return T.MEAS['hbm.first_access']['value'] + T.MEAS['SM.overhead']['value'] + max(comp, stream), 'm', ''
    return _cost(r, dyn, L, cfg)
out = {}
if which == 'qwen':
    cfg = json.loads((ROOT / 'compiler/models/qwen3-8b/config.json').read_text())
    md = QC.qwen_params(cfg); g = QC.Geometry(cfg, 8192)
    recs = QC.program(g, md, cfg['num_hidden_layers'])
    for n in SMS:
        state.update(nsm=n, nsu=1024)
        out[f'sm{n}'] = T.schedule(recs, 8191, 'S2', cost_fn=cost_q)['total_cycles']; print('sm', n, out[f'sm{n}'], flush=True)
    for n in SUS:
        state.update(nsm=32, nsu=n)
        out[f'su{n}'] = T.schedule(recs, 8191, 'S2', cost_fn=cost_q)['total_cycles']; print('su', n, out[f'su{n}'], flush=True)
else:
    from hgi_sim import ds_native_timing as DN
    d, recs = DN.load(ROOT / 'results/arch/hgi_programs_20261010/inputs/ds_rank0_program.json')
    recs = T.rebuild_waits(recs)
    import dshbm_1m_allmeasured as DA
    for n in SMS:
        state.update(nsu=1024); DA.WC.N_SM = n
        cf = DN.NativeCost(d['ops'], recs)
        out[f'sm{n}'] = T.schedule(recs, DN.POS, 'S2', cost_fn=cf)['total_cycles']; print('sm', n, out[f'sm{n}'], flush=True)
    DA.WC.N_SM = 32
    for n in SUS:
        state.update(nsu=n); cf = DN.NativeCost(d['ops'], recs)
        out[f'su{n}'] = T.schedule(recs, DN.POS, 'S2', cost_fn=cf)['total_cycles']; print('su', n, out[f'su{n}'], flush=True)
json.dump(out, open(f'/home/ubuntu/claude-takeover-20261007/budget-audit-1010/rightsize_{which}.json', 'w'), indent=1)
