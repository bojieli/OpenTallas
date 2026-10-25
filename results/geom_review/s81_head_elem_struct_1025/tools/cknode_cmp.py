# per clock node: GRT-est minus RCX arrival (FF min); split buffer (in->out) vs wire (driver out->load in) contributions
import sys, statistics as st, json
def rd(fn):
    r = {}
    for l in open(fn):
        f = l.rstrip('\n').split('\t')
        try: r[f[0]] = (f[1], float(f[2]), float(f[3]))
        except: pass
    return r
d = sys.argv[1]
R = rd(f'{d}/cknodes_rcx_FF.tsv'); G = rd(f'{d}/cknodes_grt_FF.tsv')
gap = {k: G[k][1] - R[k][1] for k in R if k in G}
# leaf sinks = CLK pins of registers; buffers: A (input), Y (output)
cellA = {k.rsplit('/',1)[0]: k for k in gap if k.endswith('/A')}
cellY = {k.rsplit('/',1)[0]: k for k in gap if k.endswith('/Y')}
buf_d = [gap[cellY[c]] - gap[cellA[c]] for c in cellA if c in cellY]
sinks = [k for k in gap if k.endswith('/CLK')]
out = dict(n_nodes=len(gap), sink_gap_median=round(st.median(gap[k] for k in sinks),2),
           buffer_stage_gap_sum_contrib_median=round(st.median(buf_d),2), n_buffers=len(buf_d),
           slew_sinks_rcx_median=round(st.median(R[k][2] for k in sinks)*1,2), slew_sinks_grt_median=round(st.median(G[k][2] for k in sinks),2))
# depth decomposition along the worst-depth: total sink gap = sum(wire gaps)+sum(buffer gaps); estimate wire share
# wire gap for each buffer input = gap(A) - gap(driver Y) unknown w/o topology; approximate by sink gap - sum of buffer deltas on typical path depth
out['buffer_gaps_p10_p90'] = [round(sorted(buf_d)[len(buf_d)//10],2), round(sorted(buf_d)[len(buf_d)*9//10],2)]
print(json.dumps(out, indent=1))
