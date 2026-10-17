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
MUTANTS = {  # gate-side edits that change glue behaviour (each must make the proof FAIL)
    1: (IDX + 'soft_1016/ot_hbm_idx_ctl_static.sv', 'assign ingest_v=&selected_v;', 'assign ingest_v=|selected_v;'),
    2: (IDX + 'soft_1016/ot_hbm_idx_client_static_soft.sv', ".first_ord(11'(2*342))", ".first_ord(11'(1*342))"),
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
    rd = lambda files: f"read_verilog -sv -lib {lib}; read_verilog -sv {' '.join(str(src / f) for f in files)}"
    sel = ' '.join(f't:{m}' for m in LEAF_MASTERS)
    names = {}
    for tag, files, top in (('gold', GOLD, 'ot_hbm_idx_client_static_sw'), ('gate', GATE, 'ot_hbm_idx_client_static_soft')):
        rc, o = yosys(f"{rd(files)}; hierarchy -top {top}; proc; flatten; select -write {out}/{tag}.cells {sel}", out / f'{tag}_list.log')
        if rc:
            print(o[-3000:]); raise SystemExit(f'{tag}: yosys list failed')
        cells = [l.split('/', 1)[1] for l in (out / f'{tag}.cells').read_text().split() if '/' in l]
        names[tag] = {c: canon(c) for c in cells}
        assert sorted(names[tag].values()) == sorted({*names[tag].values()}) and len(cells) == 11, (tag, cells)
    assert sorted(names['gold'].values()) == sorted(names['gate'].values())
    steps = []
    for tag, files, top in (('gold', GOLD, 'ot_hbm_idx_client_static_sw'), ('gate', GATE, 'ot_hbm_idx_client_static_soft')):
        ren = '; '.join(f'cd {top}; rename {c} {n}; cd' for c, n in names[tag].items())
        steps.append(f"design -reset; {rd(files)}; hierarchy -top {top}; proc; flatten; {ren}; "
                     f"expose -evert {top}/c:u_*; opt_clean; async2sync; rename {top} {tag}; design -stash {tag}")
    script = '; '.join(steps) + ("; design -reset; design -copy-from gold -as gold gold; design -copy-from gate -as gate gate; "
                                  "miter -equiv -flatten -make_assert -ignore_gold_x gold gate miter; hierarchy -top miter; "
                                  "sat -verify -prove-asserts -tempinduct -set-init-zero -seq 1 -maxsteps 8 -show-ports miter")
    (out / 'equiv.ys').write_text(script.replace('; ', '\n') + '\n')
    rc, o = yosys(script, out / 'equiv.log')
    log = (out / 'equiv.log').read_text()
    ok = rc == 0 and 'SUCCESS!' in log
    verdict = 'EQUIVALENT' if ok else 'NOT_EQUIVALENT'
    print(f"IDX_SOFT_EQUIV mutant={a.mutant} {verdict} rc={rc} leaves={len(names['gold'])}")
    if not ok:
        print(o[-2000:])
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
