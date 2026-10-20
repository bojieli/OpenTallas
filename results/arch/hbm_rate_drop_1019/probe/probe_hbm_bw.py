"""HBM-RATE-DROP probe: per-record hbm_bw floor attribution for the LH-REPRICE3 current scenario (read-only wrapper)."""
import json, os, sys, collections
from hgi_sim import d4g_reprice_1019 as R
from hgi_sim import d4g_reprice3b_1019 as R3b
from hgi_sim import timing as T
OUT = os.environ['PROBE_OUT']
CUR = {}
_INNER_JOB = R._job
def _probe_job(j):
    CUR['name'] = j[1]; CUR['rows'] = collections.defaultdict(lambda: dict(n=0, cost=0.0, bw=0.0, bytes16=0.0, bytes32=0.0))
    res = _INNER_JOB(j)
    with open(f"{OUT}/{j[1].replace('|','_')}.json", 'w') as f:
        json.dump(dict(CUR['rows']), f, indent=0)
    return res
orig_main = R.main
def main_hook():
    R._job = _probe_job
    inner = R.rp_added
    def rp(r, c, kn):
        before = dict(R.PER_RUN)
        add = inner(r, c, kn)
        d = R.PER_RUN.get('hbm_bw', 0.0) - before.get('hbm_bw', 0.0)
        if r.unit in ('SM', 'ATT', 'DMA'):
            b = r.desc.get('B') or r.desc.get('A')
            key = f"{r.unit}.{r.op}.{getattr(b,'fmt',None)}.{getattr(b,'space',None)}.p{r.param & 3}"
            row = CUR['rows'][key]; row['n'] += 1; row['cost'] += c; row['bw'] += d
            try:
                L = r.layer if isinstance(getattr(r, 'layer', 0), int) else 0
                _, n, m, _, _ = T.eff(b, T.Dyn(8191), L)
                es = T.ESZ[b.fmt]
                row['bytes16'] += n * (-(-m // 16)) * es if r.unit == 'SM' else 0
                row['bytes32'] += n * (-(-m // 32)) * es if r.unit == 'SM' else 0
                row['total_bytes'] = row.get('total_bytes', 0) + n * m * es
            except Exception as e:
                row['err'] = str(e)
        return add
    R.rp_added = rp
    return orig_main()
# R3b wraps R.main itself; install ours underneath it
R.main = main_hook
sys.argv = [sys.argv[0]] + sys.argv[1:]
R3b.main()
