#!/usr/bin/env python3
"""Executable F2 reduction-order contract; not an RTL/performance qualification.

Transfer the partial chunk and binary-tree frontier at each quarter boundary.
Four independently padded quarter totals do not preserve the global tree.
The RTL implementation must compute the same additions at the same rounding
points; this program specifies required state, not an alternative CPU datapath.
"""
from dataclasses import dataclass, field
import numpy as np
from hdc_golden_v41 import add, csum


def bits(x):
    return int(np.float32(x).view(np.uint32))


def value(x):
    return np.uint32(x).view(np.float32)


@dataclass
class Frontier:
    chunks: int = 0
    partial_n: int = 0
    partial_bits: int = 0
    levels: list = field(default_factory=list)

    def _chunk(self, x):
        level = 0
        occupied = self.chunks
        while occupied & 1:
            x = add(value(self.levels[level]), x)
            self.levels[level] = None
            occupied >>= 1
            level += 1
        if level == len(self.levels):
            self.levels.append(bits(x))
        else:
            self.levels[level] = bits(x)
        self.chunks += 1

    def feed(self, values):
        for x in values:
            self.partial_bits = bits(add(value(self.partial_bits), np.float32(x)))
            self.partial_n += 1
            if self.partial_n == 8:
                self._chunk(value(self.partial_bits))
                self.partial_bits = 0
                self.partial_n = 0

    def export(self):
        return dict(chunks=self.chunks, partial_n=self.partial_n,
                    partial_bits=self.partial_bits, levels=list(self.levels))

    @classmethod
    def restore(cls, state):
        return cls(state['chunks'], state['partial_n'], state['partial_bits'], list(state['levels']))

    def finish(self):
        # This is the only padding operation, after the whole global row.
        if self.partial_n or not self.chunks:
            self.feed([np.float32(0)] * (8-self.partial_n))
        target = 1 << (self.chunks-1).bit_length()
        while self.chunks < target:
            self._chunk(np.float32(0))
        return value(self.levels[target.bit_length()-1])


def f2_reduce(values, cuts=None):
    if cuts is None:
        cuts = [len(values)*q//4 for q in range(5)]
    if cuts[0] != 0 or cuts[-1] != len(values) or any(a>b for a,b in zip(cuts,cuts[1:])):
        raise ValueError('quarter cuts must cover the complete row in order')
    state = Frontier()
    transfers = []
    for a,b in zip(cuts,cuts[1:]):
        state.feed(values[a:b])
        transfers.append(state.export())
        state = Frontier.restore(transfers[-1])
    return state.finish(), transfers


def selftest():
    rng = np.random.default_rng(1014)
    tested = mismatches = max_state_bits = 0
    witness = None
    mismatch_by_length = {}
    for n in [0,1,7,8,9,31,32,33,127,128,129,512,640,1280,4096,4100,5120,8192]:
        for trial in range(12):
            # Broad exponents and cancellation expose changed rounding trees.
            x = (rng.integers(-4096,4097,n).astype(np.float32) *
                 np.exp2(rng.integers(-14,15,n)).astype(np.float32))
            y, transfers = f2_reduce(x)
            expected = csum(x)
            if bits(y) != bits(expected):
                raise AssertionError((n, trial, bits(y), bits(expected)))
            tested += 1
            for state in transfers:
                occupied = sum(v is not None for v in state['levels'])
                max_state_bits = max(max_state_bits, occupied*32+32+3+32)
            if n:
                totals = np.array([csum(x[n*q//4:n*(q+1)//4]) for q in range(4)],dtype=np.float32)
                naive = add(add(totals[0],totals[1]),add(totals[2],totals[3]))
                if bits(naive) != bits(expected):
                    mismatches += 1
                    mismatch_by_length[n] = mismatch_by_length.get(n, 0)+1
                    witness = witness or dict(n=n,trial=trial,golden=bits(expected),naive=bits(naive))
    assert mismatches, 'naive-quarter mutant was not killed'
    return dict(status='PASS',golden_vectors=tested,quarter_total_mutant_failures=mismatches,
                first_witness=witness,quarter_total_failures_by_length=mismatch_by_length,
                max_observed_transfer_bits=max_state_bits,
                qualification='model arithmetic-order proof only; no RTL/throughput claim')


if __name__ == '__main__':
    import json
    print(json.dumps(selftest(),indent=2))
