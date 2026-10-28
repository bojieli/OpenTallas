#!/usr/bin/env python3
"""TOK-ALL-17: KV boot / REOPEN phase calendar emitter for the HHP c708 OWN phase, gated by hhp_phase_guard (fail closed).

For every one of the 128 PCs it emits the boot-phase calendar in GATEWAY edges (qkd_embgw_boot_s, kv_static_die.BOOT_GW:
HOLD / GAP) and checks it with tools/qwen_kv_die/hhp_phase_guard.check at the kit's PHASE_DELAY (c708 = 1):
  W  first writer word   >= BOOT_END + 1 + d    (c708: >= BOOT_END + 2)
  S  first re-load slice >= REOPEN + d          (c708: >= REOPEN + 1)
  E  embedding issue -> return >= 1 + d         (c708: >= 2)
Scenario (one PC, gateway edges):  cold boot -> BOOT_END word taken at gateway edge G -> emb_ready rises HOLD + 1 edges
later (Er = G + HOLD + 1) -> run window -> a re-load BOOT_WR at the skid head at edge E0 drops emb_ready (REOPEN) and
the first new boot word leaves the gateway HOLD + 1 edges later -> second BOOT_END.
Ages (edges from the gateway register to the es-merge input) are composed from the as-built die relay table
(results/token_pass/hhp_boot_calendar_1027/asbuilt_boot_bus_ages.json: est trunk + group fork, bw -> kvs_ctl, ctl ->
hroot trunk, hroot -> PC31, chain hop) plus element constants:
  est      : st_q (+1, pin flop of embgw) + est trunk + EST_PINS (slg pin, slg y register, kvpc pin; WORST = max) + fork
  boot word: bw register (+1) + bw->kvs_ctl + BW_PIN + ROOT (kvjc3 2) + ctl->hroot + hroot->PC31 + HOP (31 - slot)
             + FACE (kvjc3 hop pin flop + PC face register 2) + SLICE (land_es -> HOST slice -> ctrl_es; WORST = min 0)
  writer   : HOST sees est (+1 st_q + est->host relays + 1 pin) + HOST_LAUNCH (WORST = min 0) + ROOT + ctl->hroot +
             hroot->PC31 + HOP (31 - slot) + FACE  (kvjc3_pc_chain.writer_ages form)
  emb      : issue no earlier than the first writer word; return = issue + MERGE (2) + CTRL_LAT (kvjc3 92)
WORST corner: longest est arrival (BOOT_END / REOPEN late at the PC), shortest boot-word / writer arrival.  Constants
not read from a netlist are named in UNCHECKED_CONSTANTS of the report.  Exit 1 (FAIL) when any PC violates.

    python3 tools/qwen_kv_die/hhp_boot_calendar.py --ages AGES.json --phase-delay 1 --out REPORT.json
"""
from __future__ import annotations

import argparse, hashlib, json, sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hhp_phase_guard as G  # noqa: E402
import kvjc3_pc_chain as KJ  # noqa: E402

AGES = ROOT_DIR / 'results/token_pass/hhp_boot_calendar_1027/asbuilt_boot_bus_ages.json'
GW = dict(HOLD=64, GAP=1)        # kv_static_die.BOOT_GW (qkd_embgw_boot_s parameters); asserted below
CTRL_LAT = 92                    # kvjc3_pc_chain default --ctrl-lat (controller es -> er, exact)
FACE = 2                         # kvjc3 writer_ages: hop pin flop + PC face register
UNCHECKED_CONSTANTS = dict(EST_PINS_MAX=3, BW_PIN=1, SLICE_MIN=0, HOST_LAUNCH_MIN=0, HOST_PIN=1)


def gw_params():
    src = (ROOT_DIR / 'tools/qwen_kv_die/kv_static_die.py').read_text()
    for k, v in GW.items():
        assert f"{k}={v}" in src.split("BOOT_GW = ")[1].splitlines()[0], f'BOOT_GW {k} changed'
    return dict(GW)


def pc_calendar(a: dict, pc: dict, c: dict, gw: dict, d: int, mutate: str = '') -> tuple[G.PhaseSchedule, dict]:
    st, p = pc['stack'], pc['pc']
    tr = a['trunk'][st]
    hop = KJ.HOP * (31 - p) + (31 - p) * max(a['chain_hop_relays'])
    est = 1 + pc['est_trunk'] + c['EST_PINS_MAX'] + pc['est_fork']
    bw = 1 + a['bw_to_ctl'] + c['BW_PIN'] + KJ.ROOT + tr['ctl_hroot'] + tr['hroot_pc31'] + hop + FACE + c['SLICE_MIN']
    wr = 1 + a['est_to_host'] + c['HOST_PIN'] + c['HOST_LAUNCH_MIN'] + KJ.ROOT + tr['ctl_hroot'] + tr['hroot_pc31'] + hop + FACE
    hold = gw['HOLD'] - (1 if mutate == 'hold' else 0) * gw['HOLD']
    g_end = 1000                                   # gateway edge that takes the BOOT_END word
    er = g_end + hold + 1                          # emb_ready register = 1 after this edge
    boot_end = er + est + 1                        # first PC edge that samples emb_boot_ready = 1
    first_wr = er + wr + (-(wr - est) - 1 if mutate == 'writer' else 0)
    e0 = er + 20000                                # re-load BOOT_WR at the skid head (emb_ready drops after e0)
    reopen = e0 + est + 1
    first_sl = e0 + hold + 1 + bw
    if mutate == 'slice':
        first_sl = reopen - 1 + d                  # one edge too early (d = 1: at REOPEN)
    emb_i = first_wr
    emb_r = emb_i + KJ.MERGE + CTRL_LAT if mutate != 'emb' else emb_i + d
    boot_end2 = e0 + 30000
    ev = (G.Event('writer', first_wr), G.Event('slice', first_sl), G.Event('emb_return', emb_r, issue=emb_i))
    s = G.PhaseSchedule(windows=(G.PhaseWindow(boot_end, reopen), G.PhaseWindow(boot_end2, None)), events=ev, phase_delay=d)
    row = dict(est_age=est, bw_age=bw, writer_age=wr, W_margin=first_wr - (boot_end + 1 + d),
               S_margin=first_sl - (reopen + d), E_margin=(emb_r - emb_i) - (1 + d))
    return s, row


def emit(ages: Path, d: int, mutate: str = '', consts: dict | None = None) -> dict:
    a = json.loads(ages.read_text())
    c = dict(UNCHECKED_CONSTANTS, **(consts or {}))
    gw = gw_params()
    rows, viol = {}, {}
    for name, pc in a['pcs'].items():
        s, row = pc_calendar(a, pc, c, gw, d, mutate)
        v = G.check(s)
        rows[name] = row
        if v:
            viol[name] = v
    mins = {k: min((r[k], n) for n, r in rows.items()) for k in ('W_margin', 'S_margin', 'E_margin')}
    return dict(schema='opentallas.qwen_kv.hhp_boot_calendar.v1', phase_delay=d, mutate=mutate or None,
                admitted=not viol, violations=viol, pcs=len(rows), min_margin={k: dict(edges=v[0], pc=v[1]) for k, v in mins.items()},
                gateway=gw, ctrl_lat=CTRL_LAT, kvjc3=dict(root=KJ.ROOT, hop=KJ.HOP, merge=KJ.MERGE, face=FACE),
                unchecked_constants=c, ages=str(ages.relative_to(ROOT_DIR)) if ages.is_relative_to(ROOT_DIR) else str(ages),
                ages_sha256=hashlib.sha256(ages.read_bytes()).hexdigest(),
                guard_sha256=hashlib.sha256((ROOT_DIR / 'tools/qwen_kv_die/hhp_phase_guard.py').read_bytes()).hexdigest(),
                rows=rows)


def require_admitted(report: Path | str | None, d: int = 1) -> dict:
    """Kit hook: a phase-delivery kit must carry an admitted calendar report at its PHASE_DELAY under the current guard."""
    if report is None:
        raise SystemExit('HHP_PHASE_CALENDAR_MISSING: kvspc phase delivery needs an admitted hhp_boot_calendar report')
    r = json.loads(Path(report).read_text())
    cur = hashlib.sha256((ROOT_DIR / 'tools/qwen_kv_die/hhp_phase_guard.py').read_bytes()).hexdigest()
    if r.get('schema') != 'opentallas.qwen_kv.hhp_boot_calendar.v1' or r.get('mutate'):
        raise SystemExit('HHP_PHASE_CALENDAR_BAD: not an unmutated hhp_boot_calendar report')
    if r.get('phase_delay') != d or not r.get('admitted') or r.get('violations'):
        raise SystemExit(f'HHP_PHASE_CALENDAR_FAIL: report not admitted at phase_delay {d}: {list(r.get("violations", {}))[:4]}')
    if r.get('guard_sha256') != cur:
        raise SystemExit('HHP_PHASE_CALENDAR_STALE: guard changed since the report; re-emit')
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ages', type=Path, default=AGES)
    ap.add_argument('--phase-delay', type=int, default=1)
    ap.add_argument('--mutate', choices=['', 'writer', 'slice', 'emb', 'hold'], default='')
    ap.add_argument('--out', type=Path, required=True)
    x = ap.parse_args()
    r = emit(x.ages.resolve(), x.phase_delay, x.mutate)
    x.out.parent.mkdir(parents=True, exist_ok=True)
    x.out.write_text(json.dumps(r, indent=1) + '\n')
    print(('ADMITTED' if r['admitted'] else 'FAIL'), 'pcs', r['pcs'], 'violating', len(r['violations']), 'min', r['min_margin'])
    sys.exit(0 if r['admitted'] else 1)


if __name__ == '__main__':
    main()
