#!/usr/bin/env python3
"""S81 die SIM filelist with the kit-inserted pin / reset landings of every hardened (CLOSED) view.

Why (STW-S81c-RTLGAP NOTICE 10-22): a CLOSED view is synthesised from its RTL *plus* the kit wrapper that
physical/common_flow/ot_pin_regs.tcl generates when the kit sets OT_RST_LAND=1 (reset ports land in N registered
stages, ot_rst_land_wrapper.v) or OT_PIN_REGS=1 (data pins registered, ot_pin_regs_wrapper.v).  The die calendar
(bind table landing_reset_stages) prices those stages, but a die.v RTL simulation that reads only the master RTL lacks
them, so token sims fault on every landing.  This tool emits, for one die case, a filelist that simulates the silicon
netlist structure:

  * for every CLOSED master whose kit enables OT_RST_LAND / OT_PIN_REGS: a wrapper module <M> generated with exactly
    the ot_pin_regs.tcl rules (port list from the view LEF, first OT_PIN_REGS_CLOCK as the landing clock), and the
    master RTL module renamed to <M>__ot_pr_core (as `yosys rename` does in the flow);
  * the die RTL filelist (port_bind.json rtl_files) with each source file that defines a wrapped master replaced by a
    patched copy in which only those module names are renamed.

Kit settings come from the view's own kit (physical/ref_tile/<kit>/kit.env at the view ref) or, when the view was
imported without its kit, from the CLOSED closure-daemon job of that master (its source commit's kit.env).  A master
whose kit cannot be resolved fails closed unless --allow-unresolved lists it.  The wrapped reset stages are checked
against the bind table's landing_reset_stages (mismatch = error).  Replicated KEPT copies (OT_RST_LAND_COPIES /
_FIRST_COPIES) are functionally identical to the single chain and are not modelled.

    python3 tools/s81_dv/die_sim_wrappers.py --case CASE_DIR --bind-dir BIND_DIR --table table.json --out OUT_DIR
Outputs OUT_DIR/{wrappers/*.v, patched/*.sv, sim_filelist.f, defines.f, manifest.json}.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ['OT_REPO']) if os.environ.get('OT_REPO') else Path(__file__).resolve().parents[2]
JOBS = Path(os.path.expanduser('~/.local/state/closure_loop/jobs'))


def git_show(ref, path):
    r = subprocess.run(['git', '-C', str(REPO), 'show', f'{ref}:{path}'], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def kit_vars(text):
    """kit.env -> dict of the flow variables that select the wrapper (EXTRA --orfs-var K=V and plain exports)."""
    v = dict(re.findall(r"'(OT_[A-Z0-9_]+)=([^']*)'", text))
    v.update(re.findall(r'^export (OT_[A-Z0-9_]+)=(\S*)', text, re.M))
    top = re.search(r'^TOP=(\S+)', text, re.M)
    v['TOP'] = top.group(1) if top else None
    return v


KIT_MAP = {}


def resolve_kit(master, view):
    """(vars, source) for a CLOSED view 'ref:physical/ref_tile/<kit>/views/<M>'."""
    if master in KIT_MAP:          # explicit 'commit:physical/ref_tile/<kit>/kit.env' (e.g. resolved on the daemon host)
        c, p = KIT_MAP[master].split(':', 1)
        t = git_show(c, p)
        if t is None:
            raise SystemExit(f'die_sim_wrappers: --kit-map {master}: {KIT_MAP[master]} not readable')
        return kit_vars(t), f'{c[:12]}:{p} (kit map)'
    ref, path = view.split(':', 1)
    kit = path.split('/views/')[0]
    t = git_show(ref, f'{kit}/kit.env')
    if t is not None:
        return kit_vars(t), f'{ref[:12]}:{kit}/kit.env'
    # View imported without its kit: the CLOSED daemon job of this master names the source commit + kit dir.
    cands = []
    for f in JOBS.glob('*.json'):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        sp = d.get('spec') or {}
        if d.get('status') == 'CLOSED' and sp.get('block') == master and sp.get('ref_tile'):
            cands.append((d.get('updated') or '', (sp.get('source') or {}).get('commit'), d.get('name')))
    for _, commit, name in sorted(cands, reverse=True):
        if not commit:
            continue
        if subprocess.run(['git', '-C', str(REPO), 'cat-file', '-e', commit], capture_output=True).returncode:
            subprocess.run(['git', '-C', str(REPO), 'fetch', '-q', 'origin', commit], capture_output=True)
        ls = subprocess.run(['git', '-C', str(REPO), 'grep', '-l', f'^TOP={master}$', commit, '--', 'physical/ref_tile/*/kit.env'],
                            capture_output=True, text=True).stdout.split()
        for hit in ls:
            p = hit.split(':', 1)[1]
            t = git_show(commit, p)
            if t is not None:
                return kit_vars(t), f'{commit[:12]}:{p} (daemon job {name})'
    return None, None


def lef_ports(ref, path, master):
    """[(dir, msb, lsb, name)] from the view LEF (exact hardened ports)."""
    t = git_show(ref, f'{path}/{master}.lef')
    if t is None:
        raise SystemExit(f'die_sim_wrappers: no LEF for {master} at {ref}:{path}')
    ports = {}
    order = []
    for m in re.finditer(r'^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$', t, re.M | re.S):
        pin, body = m.group(1), m.group(2)
        d = re.search(r'DIRECTION\s+(\w+)', body)
        use = re.search(r'USE\s+(\w+)', body)
        if use and use.group(1).upper() in ('POWER', 'GROUND'):
            continue
        d = (d.group(1).lower() if d else 'input')
        b = re.fullmatch(r'(.+?)\[(\d+)\]', pin)
        name, idx = (b.group(1), int(b.group(2))) if b else (pin, None)
        if name not in ports:
            ports[name] = [d, set()]
            order.append(name)
        if idx is not None:
            ports[name][1].add(idx)
    out = []
    for n in order:
        d, idxs = ports[n]
        out.append((d, max(idxs) if idxs else 0, 0, n))
    return out


def wrapper(master, ports, v):
    """ot_pin_regs.tcl wrapper text (same rules: reset landing chain, pin registers when OT_PIN_REGS=1)."""
    rl_on = v.get('OT_RST_LAND') == '1'
    regs = (not rl_on) or v.get('OT_PIN_REGS') == '1'
    n_rl = int(v.get('OT_RST_LAND_STAGES') or 2)
    clocks = [c for c in (v.get('OT_PIN_REGS_CLOCK') or '').split(',') if c]
    if not clocks:
        raise SystemExit(f'die_sim_wrappers: {master}: OT_PIN_REGS_CLOCK not set')
    ck = clocks[0]
    resets = [r for r in (v.get('OT_PIN_REGS_RESET_PORTS') or '').split(',') if r]
    exc = v.get('OT_PIN_REGS_EXCLUDE') or ''
    names = {p[3] for p in ports}
    for r in resets + clocks:
        if re.sub(r'\[\d+\]$', '', r) not in names:
            raise SystemExit(f'die_sim_wrappers: {master}: declared port {r} not in view ports')
    core = f'{master}__ot_pr_core'
    s = [f'// generated by tools/s81_dv/die_sim_wrappers.py = physical/common_flow/ot_pin_regs.tcl rules '
         f'({"OT_PIN_REGS=1" if regs else "OT_RST_LAND=1"}) for SIMULATION of the hardened view',
         f'module {master} ({", ".join(p[3] for p in ports)});']
    conn, landed, registered = [], [], 0
    for d, a, b, n in ports:
        rng = '' if (a == 0 and b == 0) else f' [{a}:{b}]'
        s.append(f'  {d}{rng} {n};')
        why = ''
        if n in clocks:
            why = 'clock'
        elif d == 'inout':
            why = 'inout'
        elif n in resets:
            why = 'reset'
        elif exc and re.search(exc, n):
            why = 'excluded'
        elif not regs:
            why = 'excluded'
        if why == 'reset' and rl_on and d == 'input':
            prev = n
            for k in range(n_rl):
                s.append(f'  (* keep *) reg{rng} {n}__ot_rl{k};')
                s.append(f'  always @(posedge {ck}) {n}__ot_rl{k} <= {prev};')
                prev = f'{n}__ot_rl{k}'
            conn.append(f'.{n}({prev})')
            landed.append(n)
            continue
        if why:
            conn.append(f'.{n}({n})')
            continue
        s.append(f'  wire{rng} {n}__ot_pr;')
        s.append(f'  (* keep *) reg{rng} {n}__ot_q;')
        if d == 'input':
            s.append(f'  always @(posedge {ck}) {n}__ot_q <= {n};')
            s.append(f'  assign {n}__ot_pr = {n}__ot_q;')
        else:
            s.append(f'  always @(posedge {ck}) {n}__ot_q <= {n}__ot_pr;')
            s.append(f'  assign {n} = {n}__ot_q;')
        conn.append(f'.{n}({n}__ot_pr)')
        registered += 1
    if rl_on and not landed:
        raise SystemExit(f'die_sim_wrappers: {master}: OT_RST_LAND=1 but no reset port landed')
    s.append(f'  {core} u_ot_pr_core ({", ".join(conn)});')
    s.append('endmodule')
    return '\n'.join(s) + '\n', dict(clock=ck, reset_ports=landed, reset_stages=n_rl if rl_on else 0,
                                    pin_registers=registered, mode='OT_PIN_REGS' if regs else 'OT_RST_LAND')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', type=Path, required=True, help='die case dir (case.json closed_views)')
    ap.add_argument('--bind-dir', type=Path, required=True, help='bind/bind dir (port_bind.json rtl_files/defines)')
    ap.add_argument('--table', type=Path, help='bind table json (landing_reset_stages cross-check)')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--kit-map', type=Path, help='json {master: "commit:physical/ref_tile/<kit>/kit.env"}')
    ap.add_argument('--allow-unresolved', nargs='*', default=[], help='CLOSED masters allowed without a resolvable kit')
    a = ap.parse_args()
    if a.kit_map:
        KIT_MAP.update({k: v for k, v in json.load(open(a.kit_map)).items() if not k.startswith('_')})
    case = json.load(open(a.case / 'case.json'))
    pb = json.load(open(a.bind_dir / 'port_bind.json'))
    lrs = json.load(open(a.table)).get('landing_reset_stages', {}) if a.table else {}
    (a.out / 'wrappers').mkdir(parents=True, exist_ok=True)
    (a.out / 'patched').mkdir(parents=True, exist_ok=True)
    roots = [Path(r) for r in pb.get('rtl_roots', [])]
    man = dict(schema='opentallas.s81.die_sim_wrappers.v1', case=str(a.case), die_v_sha256=pb.get('die_sha256'),
               masters={}, unresolved=[], unwrapped=[])
    wrapped = {}
    for master, view in sorted(case['closed_views'].items()):
        v, src = resolve_kit(master, view)
        if v is None:
            if master not in a.allow_unresolved:
                raise SystemExit(f'die_sim_wrappers: no kit for CLOSED view {master} ({view}); '
                                 '--allow-unresolved only after checking the view has no flow wrapper')
            man['unresolved'].append(master)
            continue
        if not (v.get('OT_RST_LAND') == '1' or v.get('OT_PIN_REGS') == '1'):
            man['unwrapped'].append(master)
            if lrs.get(master):
                raise SystemExit(f'die_sim_wrappers: table prices {lrs[master]} reset stages for {master}, kit has none ({src})')
            continue
        ref, path = view.split(':', 1)
        text, info = wrapper(master, lef_ports(ref, path, master), v)
        if master in lrs and lrs[master] != info['reset_stages']:
            raise SystemExit(f'die_sim_wrappers: {master}: kit {info["reset_stages"]} reset stages != table {lrs[master]}')
        (a.out / 'wrappers' / f'{master}.v').write_text(text)
        info.update(kit=src, view=view, table_reset_stages=lrs.get(master))
        man['masters'][master] = info
        wrapped[master] = info
    # rename the wrapped masters' RTL definitions (only those names) in patched copies of their source files
    files = list(pb['rtl_files'])
    pat = {m: re.compile(r'(^\s*module\s+)' + re.escape(m) + r'(\b)', re.M) for m in wrapped}
    out_files, done = [], set()
    for f in files:
        p = Path(f)
        if not p.is_absolute():
            p = next((r / f for r in roots if (r / f).exists()), REPO / f)
        try:
            t = p.read_text()
        except Exception:
            out_files.append(str(p))
            continue
        hit = [m for m, r in pat.items() if r.search(t)]
        if hit:
            for m in hit:
                t = pat[m].sub(lambda mo, m=m: f'{mo.group(1)}{m}__ot_pr_core{mo.group(2)}', t)
                done.add(m)
            q = a.out / 'patched' / (re.sub(r'[^\w.-]+', '_', str(p).strip('/')))
            q.write_text(f'// die_sim_wrappers.py: {p} with {", ".join(sorted(hit))} renamed to *__ot_pr_core\n' + t)
            out_files.append(str(q))
        else:
            out_files.append(str(p))
    missing = sorted(set(wrapped) - done)
    if missing:
        raise SystemExit(f'die_sim_wrappers: RTL definition not found for wrapped masters {missing}')
    out_files += [str(a.out / 'wrappers' / f'{m}.v') for m in sorted(wrapped)]
    (a.out / 'sim_filelist.f').write_text('\n'.join(out_files) + '\n')
    (a.out / 'defines.f').write_text(''.join(f'+define+{d}\n' for d in pb.get('defines', [])))
    (a.out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f'DIE_SIM_WRAPPERS wrapped={len(wrapped)} unwrapped={len(man["unwrapped"])} '
          f'unresolved={len(man["unresolved"])} files={len(out_files)} -> {a.out}')


if __name__ == '__main__':
    main()
