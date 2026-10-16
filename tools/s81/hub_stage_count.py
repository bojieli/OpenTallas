"""Pin-to-pin register stages of every hub-slab bus of a generated S81 die (ds-1010 lat-audit, 2026-10-10).

A slab master that sizes a receiver / a fixed latency for its die-level buses must use the PIN-TO-PIN stage count:
the hub-bus chain stations (_hub_bus_chain, the floorplan's 'chains' / 'hub_stations' records) PLUS the stations
--hop-fix / --pin-relay add on a chain's first and last segment (g_hb_* dsfd_hstn).  The chain record alone
under-counts: on head631 capture -> mtp is 6 stages (chain 5), mtp -> capture 7 (6), vm -> mtp 11 (9), mtp -> vm 11 (10).

Walk: from every hub slab output pin through the single-lane relay kinds (dsfd_hstn di -> dq, dsfd_rly i -> o, hop-fix
forwarded dsfd_stn di0 -> do0) to the first non-relay load; one cycle per relay.

  python3 tools/s81/hub_stage_count.py OPTS_FILE --output OUT.json [--check-mtp-rtt]

--check-mtp-rtt compares the head-die chains with dsfd_mtp_seq_rtt's FWD_R / RET_R / FWD_V / RET_V defaults (exit 1
on a mismatch).  The q-element LEF follows OT_S81_Q_LEF as for the generator.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTP = {'di': 'dq', 'i': 'o', 'di0': 'do0'}


def count(model):
    kind = {it.name: it.kind for it in model['insts']}
    relay = {n for n, k in kind.items() if k in ('rly', 'hstn') or (k == 'stn' and n.startswith('g_'))}
    outs = {}
    for bid, cls, bits, eps in model['buses']:
        outs.setdefault(tuple(eps[0]), []).append((bid, cls, [tuple(e) for e in eps[1:]]))
    res = {}
    for it in model['insts']:
        if it.kind != 'hub':
            continue
        for (inst, port), lst in list(outs.items()):
            if inst != it.name:
                continue
            stack = [((inst, port), 0)]
            while stack:
                ep, n = stack.pop()
                for bid, cls, loads in outs.get(ep, []):
                    if cls in ('clock', 'reset'):
                        continue
                    for l_ in loads:
                        if l_[0] in relay and l_[1] in OUTP:
                            stack.append(((l_[0], OUTP[l_[1]]), n + 1))
                        elif l_[0] not in relay:
                            res.setdefault(f'{inst}.{port}->{l_[0]}.{l_[1]}', set()).add(n)
    # one value per pin pair (a pair reached over two different stage counts would be its own finding: kept as min..max)
    return {k: (min(v) if len(v) == 1 else f'{min(v)}..{max(v)}') for k, v in res.items()}


def rtt_params():
    s = (ROOT / 'rtl/dsrom_sys/mtp/dsfd_mtp_seq_rtt.sv').read_text()
    return {k: int(re.search(rf'parameter integer {k} = (\d+)', s).group(1)) for k in ('FWD_R', 'RET_R', 'FWD_V', 'RET_V')}


def main():
    sys.path.insert(0, str(ROOT / 'tools'))
    import dsrom_s81_fulldie as F
    ap = argparse.ArgumentParser()
    ap.add_argument('options', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--check-mtp-rtt', action='store_true')
    own = ap.parse_args()
    args = F.die_options(argparse.ArgumentParser()).parse_args(own.options.read_text().split())
    F.apply_options(args)
    model = F.build()
    F.finalize_r8(model)
    res = count(model)
    out = dict(tool='tools/s81/hub_stage_count.py', options=own.options.read_text(), stages=dict(sorted(res.items())),
               chain_record=model.get('hub_stations'))
    rc = 0
    if own.check_mtp_rtt:
        need = dict(FWD_R=res.get('sp_capture.t_mtp->sp_mtp.f_capture'), RET_R=res.get('sp_mtp.t_capture->sp_capture.f_mtp'),
                    FWD_V=res.get('sp_vm.t_mtp->sp_mtp.f_vm'), RET_V=res.get('sp_mtp.t_vm->sp_vm.f_mtp'))
        have = rtt_params()
        ok = all(need[k] is not None and have[k] == need[k] for k in need)
        out['mtp_rtt_check'] = dict(die=need, rtl=have, verdict='PASS' if ok else 'FAIL',
                                    other_receivers=dict(mtp_to_collective=res.get('sp_mtp.t_collective->sp_collective.f_mtp'),
                                                         collective_to_mtp=res.get('sp_collective.t_mtp->sp_mtp.f_collective')))
        # mtp-colllane-1011: with --coll-mtp-lane the collective end is dsfd_coll_mtp_lane's dsfd_coll_mtp_ep (FWD_C / RET_C)
        if F.COLL_MTP_LANE:
            lt = (ROOT / 'rtl/dsrom_sys/s81_ph/coll/dsfd_coll_mtp_lane.sv').read_text().split('`else', 1)[1]
            cp = {k: int(re.search(rf'parameter integer {k} = (\d+)', lt).group(1)) for k in ('FWD_C', 'RET_C')}
            cd = dict(FWD_C=res.get('sp_mtp.t_collective->sp_collective.f_mtp'), RET_C=res.get('sp_collective.t_mtp->sp_mtp.f_collective'))
            cok = all(cd[k] is not None and cd[k] == cp[k] for k in cd)
            out['mtp_rtt_check']['collective_lane'] = dict(die=cd, rtl=cp, verdict='PASS' if cok else 'FAIL')
            ok = ok and cok
            out['mtp_rtt_check']['verdict'] = 'PASS' if ok else 'FAIL'
        print('MTP_RTT_CHECK', out['mtp_rtt_check'])
        rc = 0 if ok else 1
    own.output.write_text(json.dumps(out, indent=1) + '\n')
    for k, v in out['stages'].items():
        print(f'{v!s:>6}  {k}')
    sys.exit(rc)


if __name__ == '__main__':
    main()
