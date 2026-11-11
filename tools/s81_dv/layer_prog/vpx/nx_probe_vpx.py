#!/usr/bin/env python3
"""S81-XTIER-FIX 11-11: measure NX_AFTER_LAST_NORMR on the current RTL with the tb_vpx_ag vehicle (die A = the u_s_0S
end-slice master, real vp / vn / xr(t) / xfin / rstop).

    nx_probe_vpx.py gen --out DIR [--shift 0]     stim.txt: the compiler's lower_norm_smoke CTL beats on A's inward pin
                                                   (HLOAD, GAIN +40, NORMR leaf k at +60 + k, XFIN_GO +65; payloads from
                                                   dv_layer_compile.ctl_payload / vp_cmd / xfin_go)
    nx_probe_vpx.py check --dir DIR               first K_NX beat on A's inward output (OUT A = ro_e, the eo flit of sid 0)
                                                   -> NX edge - last NORMR pin edge, vs norm_nx.NX_AFTER_LAST_NORMR

Edge convention = tb_vpx_ag / check_vpx_ag: a stim line's cycle is the CTL beat's slice-pin edge (the compiler's CTL event
cycle) and an OUT record's cycle is the compiler's outward-beat event cycle (the vpx read-back beats are checked on it).
Data: zero leaf rows (the NX emission edge is data-independent: inj when leaf NVL-1's partial lands)."""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]
import dv_layer_compile as D  # noqa: E402

T0 = 8100           # after the link lanes are live (tb WAIT 8000)
SID = 0             # tb_vpx_ag SA
R_PRE = 1008        # GU_FFN delayed-pre row (norm_nx header)
K_NX = 3


def beat(p):
    return 1 | (1 << 4) | (4 << 9) | p << 21            # CTL, hops 1 (this end slice), src 4 (as gen_vpx_ag.ctl_beat)


def gen(out, shift=0):
    out.mkdir(parents=True, exist_ok=True)
    sm = 1 << SID
    cmds = [(T0, 'HLOAD', D.ctl_payload(sm, 0, 0x1F, D.vp_cmd(D.VP['HLOAD'], a0=0))),
            (T0 + D.BEAT['hload_slot'], 'GAIN', D.ctl_payload(sm, 0, 0x1F, D.vp_cmd(D.VP['GAIN'], a0=64)))]
    tn = T0 + D.BEAT['hload_slot'] + D.BEAT['gain_slot'] + shift
    for k in range(5):
        cmds.append((tn + k, f'NORMR.k{k}', D.ctl_payload(sm, 0, 1 << k, D.vp_cmd(D.VP['NORMR'], a0=R_PRE, a1=5 * SID + k, n=3))))
    cmds.append((tn + 5, 'XFIN_GO', D.ctl_payload(sm, 1, 0, D.xfin_go(D.norm_eps_bits()))))
    end = tn + 900
    (out / 'stim.txt').write_text(f'END {end}\n' + ''.join(f'{c} 0 {beat(p):0276x}\n' for c, _, p in cmds))
    (out / 'nx_probe.json').write_text(json.dumps(dict(cmds=[dict(cycle=c, tag=t) for c, t, _ in cmds], last_normr=tn + 4,
                                                       shift=shift, end=end), indent=1) + '\n')


def check(d):
    meta = json.loads((d / 'nx_probe.json').read_text())
    nx, faults, done, outs = [], {}, None, 0
    for ln in (d / 'run.log').read_text(errors='replace').splitlines():
        t = ln.split()
        if len(t) >= 4 and t[0] == 'OUT' and t[1] == 'A':
            outs += 1
            v = int(t[3], 16)
            if v & 1 and (v >> 1) & 7 == K_NX:
                nx.append(dict(cycle=int(t[2]), hops=(v >> 4) & 0x1F, sid=(v >> 9) & 0xF, b=(v >> 13) & 0xFF))
        elif t and t[0] == 'FAULT':
            faults[t[1]] = int(t[2])
        elif t and t[0] == 'DONE':
            done = int(t[1])
    sys.path.insert(0, str(HERE.parent))
    import norm_nx as N
    res = dict(done=done, faults=faults, out_beats_A=outs, nx=nx[:4], last_normr_pin=meta['last_normr'],
               compiled=N.NX_AFTER_LAST_NORMR)
    if nx:
        res['measured'] = nx[0]['cycle'] - meta['last_normr']
        res['verdict'] = 'MATCH' if res['measured'] == N.NX_AFTER_LAST_NORMR else 'DIFFER'
    else:
        res['verdict'] = 'NO_NX_FLIT'
    (d / 'nx_check.json').write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(res))
    return 0 if res['verdict'] == 'MATCH' else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('gen', 'check'))
    ap.add_argument('--out')
    ap.add_argument('--dir')
    ap.add_argument('--shift', type=int, default=0)
    a = ap.parse_args()
    if a.cmd == 'gen':
        gen(Path(a.out), a.shift)
    else:
        sys.exit(check(Path(a.dir)))
