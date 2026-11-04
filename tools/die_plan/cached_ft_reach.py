"""Opt-in FT reach geometry cache; row reservations are never inputs or outputs.

Backward sets cover an immutable bundle of actual output sites conservatively:
the last stage reaches EVERY member within the original budget. All stages,
RowAllocator reservations, and the final actual per-bit 405um check remain.
"""
from collections import OrderedDict
import numpy as np


def l1_distance(mask, pitch):
    """Separable Manhattan distance transform, equivalent to _l1_dt recurrence."""
    d = np.where(mask, 0.0, 1e9)
    for axis in (0, 1):
        shape = [1] * d.ndim; shape[axis] = d.shape[axis]
        q = np.arange(d.shape[axis]).reshape(shape) * pitch
        a = np.minimum.accumulate(d-q, axis=axis)+q
        b = np.flip(np.minimum.accumulate(np.flip(d+q, axis=axis), axis=axis), axis=axis)-q
        d = np.minimum(a, b)
    return d


class CachedReach:
    def __init__(self, frame, blocked, pitch=2.16, clearance=8.64, slack=1.5, entries=4):
        if pitch <= 0 or clearance < 0 or slack < 0 or entries < 1:
            raise ValueError('invalid reach geometry')
        self.frame = tuple(map(float, frame))
        self.blocked = tuple(tuple(map(float, b)) for b in blocked)
        self.pitch, self.slack, self.entries = float(pitch), float(slack), int(entries)
        self.xs = np.arange(clearance, self.frame[0]-clearance, pitch)
        self.ys = np.arange(clearance, self.frame[1]-clearance, pitch)
        self.x, self.y = self.xs[:, None], self.ys[None, :]
        self.free = np.ones((len(self.xs), len(self.ys)), dtype=bool)
        for a,b,c,d in self.blocked:
            self.free &= ~((self.x>a)&(self.x<c)&(self.y>b)&(self.y<d))
        self.cache, self.goals = OrderedDict(), {}
        self.hits = self.misses = 0

    def set_goals(self, outputs, bundle=64):
        if bundle < 1: raise ValueError('nonpositive bundle')
        ordered = sorted(outputs); self.goals = {}
        for start in range(0, len(ordered), bundle):
            members = ordered[start:start+bundle]; points = [outputs[b] for b in members]
            u = [x+y for x,y in points]; v = [x-y for x,y in points]
            envelope = (min(u), max(u), min(v), max(v))
            for bit in members: self.goals[bit] = envelope

    def _backward(self, envelope, k, budget, use_cache):
        # Geometry/grid/clearance are immutable for this cache object.
        key = (envelope, int(k), float(budget), self.slack)
        if use_cache and key in self.cache:
            self.hits += 1; self.cache.move_to_end(key); return self.cache[key]
        self.misses += 1; bound = budget-self.slack
        u,v = self.x+self.y, self.x-self.y
        distance = np.maximum(np.maximum(abs(u-envelope[0]),abs(u-envelope[1])),
                              np.maximum(abs(v-envelope[2]),abs(v-envelope[3])))
        backward = [None]*(k-1); backward[-1] = self.free & (distance<=bound)
        for stage in range(k-3,-1,-1):
            backward[stage] = self.free & (l1_distance(backward[stage+1],self.pitch)<=bound)
        if use_cache:
            self.cache[key] = backward
            while len(self.cache)>self.entries: self.cache.popitem(last=False)
        return backward

    def solve(self, ia, ib, ps, k, budget, bit, use_cache=True):
        if k<2 or len(ps)!=k-1 or budget<=self.slack: raise ValueError('invalid fixed stage count/budget')
        envelope = self.goals.get(bit,(ib[0]+ib[1],ib[0]+ib[1],ib[0]-ib[1],ib[0]-ib[1]))
        u,v = ib[0]+ib[1], ib[0]-ib[1]
        if not (envelope[0]-1e-8<=u<=envelope[1]+1e-8 and envelope[2]-1e-8<=v<=envelope[3]+1e-8):
            raise ValueError('actual output is outside immutable goal envelope')
        backward = self._backward(envelope,k,budget,use_cache); bound=budget-self.slack; out=[];prev=ia
        for stage in range(k-1):
            lo,hi=np.searchsorted(self.xs,[prev[0]-bound,prev[0]+bound],side='left')
            bot,top=np.searchsorted(self.ys,[prev[1]-bound,prev[1]+bound],side='left')
            # Both endpoints are included when exactly on a track.
            hi=int(np.searchsorted(self.xs,prev[0]+bound,side='right'))
            top=int(np.searchsorted(self.ys,prev[1]+bound,side='right'))
            x,y=self.xs[lo:hi,None],self.ys[None,bot:top]
            ok=backward[stage][lo:hi,bot:top] & (abs(x-prev[0])+abs(y-prev[1])<=bound)
            if not ok.any(): raise ValueError(f'no conservative fixed-{k}-hop chain at stage {stage+1}')
            cost=np.where(ok,abs(x-ps[stage][0])+abs(y-ps[stage][1]),np.inf)
            ix,iy=np.unravel_index(np.argmin(cost),cost.shape)
            prev=(float(self.xs[lo+ix]),float(self.ys[bot+iy]));out.append(prev)
        chain=[ia,*out,ib]
        if any(abs(a[0]-b[0])+abs(a[1]-b[1])>bound+1e-6 for a,b in zip(chain,chain[1:])):
            raise AssertionError('computed chain violates its original reach budget')
        return out

    def __call__(self,ia,ib,ps,k,grow,budget,tn,name,bit):
        if tuple(tuple(map(float,b)) for b in grow)!=self.blocked: raise ValueError('stale reach geometry')
        return self.solve(ia,ib,ps,k,budget,bit)
