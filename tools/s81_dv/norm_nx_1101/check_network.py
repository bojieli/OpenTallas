"""Check current source-relative NX transport, exact partials and finish order."""
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from layer_prog.norm_nx_candidate import events
from layer_prog.norm_q import finish_root


def check(book,transport,partials,log):
    sid=lambda s:2*int(s[4])+(s[-1]=='N')
    expected=set();expected_dl=set();anchors={}
    for c in book['commands']:
        if c['kind']=='NORMR':anchors[c['slice']]=c['partial_cohort_offset_excluding_common_local_age']
    # Public partial0 -> own XG output is ten registered source edges in this
    # component epoch: five serial partials then actual collector/XSTOP/rstop.
    for p,e in zip(transport['snake_peer_paths'],events(book,transport,6)):
        origin=sid(p['origin']);payload=sum(partials[5*origin+k]<<(32*k)for k in range(5))
        hops=(8 if p['side']=='e'else 7)-p['prior_XG_XFIN_forward_count']
        expected.add((sid(e['slice']),e['port'],e['relative_output_edge']+10,5*origin,hops,payload))
        expected_dl.add((sid(e['destination']),e['relative_landing_edge']+13,5*origin))
    for sl,a in anchors.items():expected_dl.add((sid(sl),a+7,5*sid(sl)))
    actual_words=[(int(s),port,int(c),int(b),int(h),int(d,16))for s,port,c,b,h,d in re.findall(r'NX_NET_WORD sid(\d+) (\w+) cycle(\d+) base(\d+) hops(\d+) data([0-9a-f]+)',log)]
    actual_dl=[(int(s),int(c),int(b))for s,port,c,b in re.findall(r'NX_NET_DL sid(\d+) port(\d+) cycle(\d+) base(\d+)',log)]
    problems=[]
    if len(actual_words)!=240 or set(actual_words)!=expected:problems.append(dict(kind='NX_WORD',missing=list(expected-set(actual_words))[:3],extra=list(set(actual_words)-expected)[:3],count=len(actual_words)))
    if len(actual_dl)!=256 or set(actual_dl)!=expected_dl:problems.append(dict(kind='XSTOP_DELIVERY',missing=list(expected_dl-set(actual_dl))[:3],extra=list(set(actual_dl)-expected_dl)[:3],count=len(actual_dl)))
    roots={int(s):int(c)for s,c in re.findall(r'NX_NET_ROOT sid(\d+) cycle(\d+)',log)}
    predicted={}
    for s in range(16):
        arrivals={b:c for ss,c,b in expected_dl if ss==s}
        if len(arrivals)!=16:raise ValueError('missing actual composed normalization peer')
        predicted[s]=finish_root(arrivals)
    if roots!=predicted:problems.append(dict(kind='GOLDEN_TREE_ISSUE_DATE',actual=roots,predicted=predicted))
    rstd={int(s):(int(c),d)for s,c,d in re.findall(r'NX_NET_RSTD sid(\d+) cycle(\d+) word([0-9a-f]+)',log)}
    if len(rstd)!=16 or any(d!='40ca3c85'for c,d in rstd.values())or'NX_NET_PASS'not in log:problems.append(dict(kind='ACTUAL_RSTD_MATH_OR_FAULT'))
    return dict(status='PASS_CURRENT_NX_COMPONENT_NETWORK'if not problems else'FAIL_CURRENT_NX_COMPONENT_NETWORK',
        errors=problems,NX_words=len(actual_words),deliveries=len(actual_dl),source_local_forward_edges=6,peer_delivery_edges=3,
        legacy_C_IN_edges=2,peer_delivery_delta_edges=1,clock_ps=833,
        source_top_sha256=book['source_top_sha256'],root_writeback_edges=roots,predicted_root_writeback_edges=predicted,
        actual_RSTD=rstd,RSTD_after_root_edges={s:rstd[s][0]-roots[s]for s in roots if s in rstd},
        component_epoch='partial0 dates equal candidate aligned-cohort offsets; unknown common native producer term set to0 in this component',
        absolute_native_producer_dates_qualified=False,physical_phases_qualified=False,HEAD_final_input_values=False,full_token=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--book',type=Path,required=True);p.add_argument('--transport',type=Path,required=True)
    p.add_argument('--partials',type=Path,required=True);p.add_argument('--log',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=check(json.loads(a.book.read_text()),json.loads(a.transport.read_text()),[int(x,16)for x in a.partials.read_text().split()],a.log.read_text())
    a.out.write_text(json.dumps(r,indent=1)+'\n');print(r['status'],r['errors']);sys.exit(bool(r['errors']))
