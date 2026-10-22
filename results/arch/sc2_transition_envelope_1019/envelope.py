#!/usr/bin/env python3
"""Standalone finite-rectangle NLDM envelope; deliberately no flow integration.

Coordinates and values use native SI. This proves extrema of the pinned native
piecewise bilinear mathematical lookup, including its first/last-segment linear
extrapolation. It does not extend the physical characterization domain.
"""
import bisect,math

PAIRS={('input_net_transition','total_output_net_capacitance'),
       ('constrained_pin_transition','related_pin_transition'),
       ('related_pin_transition','constrained_pin_transition')}

def admit(t,domain):
    if (t['axis1_kind'],t['axis2_kind']) not in PAIRS:
        raise ValueError('unsupported axes/model; no role/axis fallback')
    for k in ('axis1','axis2'):
        a=t[k]
        if len(a)<2 or any(not math.isfinite(v) for v in a) or any(x>=y for x,y in zip(a,a[1:])):
            raise ValueError('strict finite multi-point axes required')
    if len(t['values'])!=len(t['axis1']) or any(len(r)!=len(t['axis2']) for r in t['values']):
        raise ValueError('table shape')
    if any(not math.isfinite(v) for r in t['values'] for v in r):raise ValueError('nonfinite table')
    if len(domain)!=2 or any(len(d)!=2 or any(not math.isfinite(v) for v in d) or d[0]<0 or d[0]>d[1] for d in domain):
        raise ValueError('finite nonnegative explicit rectangle required')

def evaluate(t,x,y):
    a,b=t['axis1'],t['axis2']
    i=max(0,min(len(a)-2,bisect.bisect_right(a,x)-1))
    j=max(0,min(len(b)-2,bisect.bisect_right(b,y)-1))
    u=(x-a[i])/(a[i+1]-a[i]);v=(y-b[j])/(b[j+1]-b[j])
    terms=[(1-u)*(1-v)*t['values'][i][j],u*(1-v)*t['values'][i+1][j],
           u*v*t['values'][i+1][j+1],(1-u)*v*t['values'][i][j+1]]
    return math.fsum(terms),sum(abs(q) for q in terms)

def envelope(t,domain,*,output_transition=False):
    admit(t,domain)
    grids=[[d[0],*[v for v in t['axis'+str(i+1)] if d[0]<v<d[1]],d[1]] for i,d in enumerate(domain)]
    observations=[(evaluate(t,x,y),x,y) for x in grids[0] for y in grids[1]]
    lo=min(observations,key=lambda r:r[0][0]);hi=max(observations,key=lambda r:r[0][0])
    # Explicit conservative float32 cushion for this research probe. Formal
    # numerical certification/derate support remains outside this prototype.
    pad=64*2**-23*max(abs(v) for r in t['values'] for v in r)
    pad+=64*2**-23*sum(max(evaluate(t,x,y)[1] for x in grids[0] for y in grids[1]) for _ in range(4))
    lower=math.nextafter(lo[0][0]-pad,-math.inf);upper=math.nextafter(hi[0][0]+pad,math.inf)
    if output_transition:lower=max(0,lower);upper=max(0,upper)
    return dict(lower=lower,upper=upper,raw_lower=lo[0][0],raw_upper=hi[0][0],
                lower_witness=[lo[1],lo[2]],upper_witness=[hi[1],hi[2]],
                knot_vertices=len(observations),float32_research_cushion=pad,
                extrapolated=any(d[0]<t['axis'+str(i+1)][0] or d[1]>t['axis'+str(i+1)][-1] for i,d in enumerate(domain)),
                physical_domain_qualified=False)

def witnesses():
    t=dict(axis1_kind='input_net_transition',axis2_kind='total_output_net_capacitance',axis1=[5,10,20],axis2=[1,2],values=[[5,6],[-8,-7],[20,21]])
    e=envelope(t,[[0,20],[1,2]])
    assert e['raw_lower']==-8 and e['lower_witness'][0]==10 # interior knot, not endpoint-only
    assert evaluate(t,0,1)[0]==18 and evaluate(t,5,1)[0]==5 # extrapolate, never clamp
    assert envelope(t,[[0,20],[1,2]],output_transition=True)['lower']==0
    h={**t,'axis1_kind':'constrained_pin_transition','axis2_kind':'related_pin_transition','values':[[2,9],[30,4],[1,3]]}
    assert envelope(h,[[0,20],[1,2]])['raw_upper']==30 # check maximum, not minimum
    refused=0
    for bad,domain in (({**t,'axis1_kind':'unsupported_ccs'},[[0,20],[1,2]]),(t,[[-1,20],[1,2]]),({**t,'axis1':[5,5,20]},[[0,20],[1,2]]),(t,[[0,math.inf],[1,2]])):
        try:envelope(bad,domain)
        except ValueError:refused+=1
    assert refused==4
    return {'nonmonotone_interior_min':True,'zero_is_extrapolated_not_clamped':True,'transition_only_zero_clip':True,'constraint_uses_upper':True,'unsupported_refusals':refused}

if __name__=='__main__':print(witnesses())
