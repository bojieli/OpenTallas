"""Analyze optimistic complete-word service traces; never certify hardware safety."""
import argparse,bisect,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def analyze(path,words,window=1024):
    rows=[tuple(map(int,s.split(','))) for s in Path(path).read_text().splitlines()]
    ready=dict(rows)
    if len(rows)!=words or set(ready)!=set(range(words)):raise ValueError('missing or duplicate words')
    prefix=[];t=0
    for i in range(words):
        if ready[i]<0:raise ValueError('negative cycle')
        t=max(t,ready[i]);prefix.append(t)
    start=prefix[window-1]
    misses=[i for i in range(words) if prefix[i]>start+i+1]
    earliest=max(prefix[i]-i-1 for i in range(words))
    return dict(word_count=words,window_words=window,initial_window_ready_cycle=start,
        first_missing_word=misses[0] if misses else None,
        available_words_at_consume_end=bisect.bisect_right(prefix,start+words),
        end_deficit_words=words-bisect.bisect_right(prefix,start+words),
        earliest_optimistic_unstalled_start=earliest,
        words_already_resident_at_that_start=bisect.bisect_right(prefix,earliest),
        final_word_cycle=prefix[-1],fixed_rate_window_pass=not misses)

def main():
    a=argparse.ArgumentParser();a.add_argument('--alone',required=True);a.add_argument('--mixed',required=True);a.add_argument('--output',required=True);args=a.parse_args()
    bind=ROOT/'results/rtl/hdc_v41x_fullshape_program_bind_rope_hbm.json'
    trace=json.loads(bind.read_text())['qe_address_trace'];q=next(x for x in trace if x['matrix']=='wq_a')
    words=q['end_word_exclusive']-q['start_word'];assert words==3840
    sources=['rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv','rtl/chip/ot_chip_v41x_weight_pc_adapter.sv','rtl/chip/ot_chip_v41x_shared_hbm_model.sv','rtl/test/tb_v41_shared_qe_admission.sv','tools/v41_shared_qe_admission.py',str(bind.relative_to(ROOT))]
    result={'status':'measured_fixed_rate_admission_failure','logical_matrix':'L0.wq_a','sectors':words*17,
        'alone':analyze(args.alone,words),'mixed':analyze(args.mixed,words),
        'scope':'Real descriptor shape; synthetic weight payload and sustained K traffic; optimistic unlimited completion capture; one stack',
        'limits':['No actual QE numeric consumption','No complete production index/WINDOW trace','Service can change when consumer scheduling changes; this is a rejected prototype operating point, not universal impossibility'],
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
        'trace_sha256':{k:hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in [('alone',args.alone),('mixed',args.mixed)]}}
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
