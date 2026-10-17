#!/usr/bin/env python3
"""Equivalence of the SOFT IDX client composition against the die master (H-NETLIST/IDXP 2026-10-16).

    idx_soft_equiv_1016.py OUT_DIR [--mutant N]

gold = ot_hbm_idx_client_static_sw (rtl/hbm_accel/index), gate = ot_hbm_idx_client_static_soft (soft_1016). The eight
leaf masters (calendar, topk, vm_share, vm_query, query, score x4, selector, topk_link) are read as blackboxes from their
real sources, renamed to one canonical instance name in both designs, and EVERTED (yosys expose -evert): every leaf
input becomes a compared output, every leaf output a shared free input. The miter then compares all client outputs and
all leaf input pins over all states (sat -tempinduct, async resets as sync), so every glue gate, constant, slice and the
parent calendar_fault register is proven identical. --mutant N edits the gate RTL in a scratch copy (must FAIL).
"""
import argparse, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IDX = 'rtl/hbm_accel/index/'
LEAVES = [IDX + f for f in ('ot_hbm_idx_calendar_static.sv', 'ot_hbm_idx_topk_static.sv', 'ot_hbm_idx_vm_share_static.sv',
                            'ot_hbm_idx_vm_query_static.sv', 'ot_hbm_idx_query_static.sv', 'ot_hbm_idx_score_static.sv',
                            'ot_hbm_idx_selector_static.sv', 'ot_hbm_idx_topk_link_static.sv')]
GOLD = [IDX + f for f in ('ot_hbm_idx_client_static_sw.sv', 'ot_hbm_idx_client_static.sv', 'ot_hbm_idx_scheduled_static.sv',
                          'ot_hbm_idx_parent_static.sv')]
GATE = [IDX + 'soft_1016/ot_hbm_idx_client_static_soft.sv', IDX + 'soft_1016/ot_hbm_idx_ctl_static.sv']
LEAF_MASTERS = ('ot_hbm_idx_calendar_static', 'ot_hbm_idx_topk_static', 'ot_hbm_idx_vm_share_static',
                'ot_hbm_idx_vm_query_static', 'ot_hbm_idx_query_static', 'ot_hbm_idx_score_static',
                'ot_hbm_idx_selector_static', 'ot_hbm_idx_topk_link_static')
GLUE_REG = {'gold': 'implementation.index.parent.calendar_fault', 'gate': 'ctl.parent_calendar_fault'}
MUTANTS = {  # gate-side edits that change glue behaviour (each must make the proof FAIL)
    1: (IDX + 'soft_1016/ot_hbm_idx_ctl_static.sv', 'assign ingest_v=&selected_v;', 'assign ingest_v=|selected_v;'),
    2: (IDX + 'soft_1016/ot_hbm_idx_client_static_soft.sv', ".key_lines(key_lines[q*8792+:8792])",
        ".key_lines(key_lines[(N_Q-1-q)*8792+:8792])"),   # scorer slots swapped
    3: (IDX + 'soft_1016/ot_hbm_idx_ctl_static.sv', 'assign query_emit=issue_v&&ins[29];', 'assign query_emit=ins[29];'),
}


def canon(name):
    n = name.lstrip('\\')
    m = re.search(r'gscore\[(\d)\]\.scorer$', n) or re.search(r'(?:^|\.)scorer(\d)$', n)
    if m:
        return f'u_scorer{m.group(1)}'
    for leaf in ('calendar', 'topk', 'share', 'operands', 'query', 'selector', 'link'):
        if re.search(rf'(?:^|\.){leaf}$', n):
            return f'u_{leaf}'
    raise SystemExit(f'unmapped leaf cell {name}')


def yosys(script, log):
    r = subprocess.run(['yosys', '-q', '-l', str(log), '-p', script], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    ap.add_argument('--mutant', type=int, default=0)
    ap.add_argument('--nq', type=int, default=4, help='N_Q of both designs (A2P half die: 2)')
    ap.add_argument('--method', choices=('sat', 'equiv'), default='sat',
                    help='sat: miter + sat -tempinduct; equiv: equiv_make/equiv_simple/equiv_induct/equiv_status -assert '
                         '(same everted designs; matches gold/gate signals by name, proves every equiv cell by induction)')
    ap.add_argument('--gold-root', type=Path, help='read the gold client (GOLD files) from this tree, no N_Q parameter '
                    '(regression: the pre-N_Q client); default: this tree with N_Q=--nq')
    ap.add_argument('--gate', choices=('soft', 'client'), default='soft',
                    help='soft: ot_hbm_idx_client_static_soft; client: ot_hbm_idx_client_static_sw of this tree')
    a = ap.parse_args()
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    src = ROOT
    if a.mutant:
        src = out / 'mut_src'
        shutil.rmtree(src, ignore_errors=True)
        for f in LEAVES + GOLD + GATE:
            (src / f).parent.mkdir(parents=True, exist_ok=True); shutil.copy(ROOT / f, src / f)
        f, old, new = MUTANTS[a.mutant]
        t = (src / f).read_text(); assert t.count(old) == 1, (f, old); (src / f).write_text(t.replace(old, new))
    lib = ' '.join(str(src / f) for f in LEAVES)
    rd = lambda files, root=None: f"read_verilog -sv -lib {lib}; read_verilog -sv {' '.join(str((root or src) / f) for f in files)}"
    gate_files, gate_top = (GATE, 'ot_hbm_idx_client_static_soft') if a.gate == 'soft' else (GOLD, 'ot_hbm_idx_client_static_sw')
    groot = a.gold_root.resolve() if a.gold_root else None
    chp = lambda tag, top: '' if (tag == 'gold' and groot) else f'chparam -set N_Q {a.nq} {top}; '
    glue = dict(GLUE_REG, gate=GLUE_REG['gold'] if a.gate == 'client' else GLUE_REG['gate'])
    sel = ' '.join(f't:{m}' for m in LEAF_MASTERS)
    names = {}
    for tag, files, top in (('gold', GOLD, 'ot_hbm_idx_client_static_sw'), ('gate', gate_files, gate_top)):
        rc, o = yosys(f"{rd(files, groot if tag == 'gold' else None)}; {chp(tag, top)}hierarchy -top {top}; proc; flatten; select -write {out}/{tag}.cells {sel}", out / f'{tag}_list.log')
        if rc:
            print(o[-3000:]); raise SystemExit(f'{tag}: yosys list failed')
        cells = [l.split('/', 1)[1] for l in (out / f'{tag}.cells').read_text().split() if '/' in l]
        names[tag] = {c: canon(c) for c in cells}
        assert sorted(names[tag].values()) == sorted({*names[tag].values()}) and len(cells) == 7 + a.nq, (tag, cells)
    assert sorted(names['gold'].values()) == sorted(names['gate'].values())
    steps = []
    for tag, files, top in (('gold', GOLD, 'ot_hbm_idx_client_static_sw'), ('gate', gate_files, gate_top)):
        ren = '; '.join(f'cd {top}; rename {c} {n}; cd' for c, n in names[tag].items())
        # the one glue register (parent calendar_fault, sticky): same canonical name in both so equiv_induct pairs the states
        ren += f'; cd {top}; rename {glue[tag]} glue_calendar_fault_q; cd'
        steps.append(f"design -reset; {rd(files, groot if tag == 'gold' else None)}; {chp(tag, top)}hierarchy -top {top}; proc; flatten; {ren}; "
                     f"expose -evert {top}/c:u_*; opt_clean; async2sync; rename {top} {tag}; design -stash {tag}")
    tail = ("miter -equiv -flatten -make_assert -ignore_gold_x gold gate miter; hierarchy -top miter; "
            "sat -verify -prove-asserts -tempinduct -set-init-zero -seq 1 -maxsteps 8 miter") if a.method == 'sat' else (
            "equiv_make gold gate eq; hierarchy -top eq; equiv_simple -seq 2; equiv_induct -seq 2; equiv_status -assert")
    script = '; '.join(steps) + ("; design -reset; design -copy-from gold -as gold gold; design -copy-from gate -as gate gate; " + tail)
    (out / 'equiv.ys').write_text(script.replace('; ', '\n') + '\n')
    rc, o = yosys(script, out / 'equiv.log')
    log = (out / 'equiv.log').read_text()
    ok = rc == 0 and ('SUCCESS!' in log if a.method == 'sat' else 'Equivalence successfully proven!' in log)
    verdict = 'EQUIVALENT' if ok else 'NOT_EQUIVALENT'
    print(f"IDX_SOFT_EQUIV method={a.method} gate={a.gate} gold_root={a.gold_root} nq={a.nq} mutant={a.mutant} {verdict} rc={rc} leaves={len(names['gold'])}")
    if not ok:
        print(o[-2000:])
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
