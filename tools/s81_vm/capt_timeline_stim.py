#!/usr/bin/env python3
"""S-VM-CAPT-TIMELINE (claude 2026-10-16): gather->capture stimuli for capt_timeline_bench.sh, made legal for the VM
static capture lanes (ALIGNMENT CONTRACT of dsfd_vm_static_capl: obase and the per-position stride ops are multiples
of 256 words, so root r's words carry addr[7:1] == r).  Cases: the gen_stim.py cases with obase/ops aligned, plus
'lock' / 'lockmix' (every root starts on the same stream cycle, one partial a cycle: the compiled lockstep shape).
usage: capt_timeline_stim.py <case> <out>"""
import random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'rtl/dsrom_sys/s81_ph/test'))
import gen_stim

class Lock(random.Random):
    def randint(self, a, b):
        return 0 if (a, b) == (0, 8) else super().randint(a, b)

def align(path):
    out = []
    for l in Path(path).read_text().splitlines():
        if l.startswith('P '):
            f = l.split()
            ob = int(f[3], 16) & ~0xff
            ops = (int(f[4], 16) + 255) // 256 * 256
            f[3], f[4] = f'{ob:x}', f'{ops:x}'
            l = ' '.join(f)
        out.append(l)
    Path(path).write_text('\n'.join(out) + '\n')

def main():
    case, out = sys.argv[1], sys.argv[2]
    if case in ('lock', 'lockmix'):
        rng = Lock(5)
        with open(out, 'w') as f:
            if case == 'lock':
                gen_stim.phase(rng, f, 0, 576, 0, 2, burst=True, maxseg=1)
                gen_stim.phase(rng, f, 1, 7168, 0, 0, burst=True, maxseg=1)
            else:
                ph = 0
                for fmt in (0, 1, 2):
                    for np_ in (0, 3):
                        gen_stim.phase(rng, f, ph, rng.choice([256, 300, 576, 1000]), np_, fmt, burst=True, maxseg=1); ph += 1
    else:
        seed = {'mix': 7, 'mix11': 11, 'mix12': 12, 'mix13': 13}.get(case, 7)
        sys.argv = ['gen_stim.py', 'mix' if case.startswith('mix') else case, str(seed), out]
        gen_stim.main()
    align(out)

if __name__ == '__main__':
    main()
