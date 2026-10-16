#!/usr/bin/env python3
"""View plan of the v16 full HBM die case (H-DIE-V16CASE 2026-10-16): for every master/port-variant of the v16 source
contract (results/arch/hbm_die_v16/contract.json) pick the view a die GRT/STA binds:
  REAL  = closed routed view on main (physical/**/views/<m>/<m>.lef + <m>_{tt,ff}.lib) whose pins equal the contract ports
  SYNTH = current-source mapped netlist ETM (synth_master.sh HIER=1 + synth_etm.sh): an estimate, never a sign-off view.
One representative instance per (master, port signature); per-instance parameter differences that do not change ports
(pgslice G, cmd target TARGET, PC P ...) share that representative's ETM (recorded in views.json).
Writes OUT/views.json, OUT/jobs.tsv and OUT/wrap/<cell>.sv (parameter wrappers: the wrapper module binds every SV
parameter value literally, arrays and wide hex included; ports identical to the master's).

    v16_views.py --out DIR
"""
import argparse, glob, json, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'results/arch/hbm_die_v16/contract.json'
BIG = {  # measured --mem (tools/fleet/die_trial_mem.json 2026-10-16: typical synth 48, small 23, largest 154, ETM 48)
    'hfd_hgi_vms_static': 154, 'ot_hfd_coll_q3_static_host_v4': 154, 'ot_hfd_coll_q2_static_host_v4': 154,
    'ot_hgi_sfu_scheduled_engine': 154, 'ot_hbm_idx_client_static_sw': 154, 'ot_hbm_accel_smh_static': 128,
}
ENV = {'ot_hbm_accel_smh_static': 'DEFINES=OT_SMH_FC_HIER LIBCELLS=1', 'hfd_ckgen': 'DROP=rtl/hbm_accel/control/tb_hfd_ckgen.sv'}
PRE = {'hfd_ckgen': '(* blackbox *) module ot_hbm_pll_bb(input wire refclk, input wire reset_n, output wire clk_stream, '
       'output wire clk_serial, output wire clk_hbm, output wire clk_link, output wire locked); endmodule'}
BB = {}   # the PLL (allowed analog model, die_port_bind --allow-model) is declared blackbox in the ckgen wrapper (PRE)


def lef_ports(lef):
    out = defaultdict(int)
    for m in re.finditer(r'^\s*PIN\s+(\S+)', Path(lef).read_text(), re.M):
        p = m.group(1)
        if p in ('VDD', 'VSS'):
            continue
        out[re.sub(r'\[\d+\]$', '', p)] += 1
    return dict(out)


def real_view(m):
    for lef in sorted(glob.glob(str(ROOT / f'physical/**/views/{m}/{m}.lef'), recursive=True)) + \
            sorted(glob.glob(str(ROOT / f'physical/asap7*/{m}/{m}.lef'))):
        d = Path(lef).parent
        tt = [x for x in d.glob(f'{m}*tt*.lib')]
        ff = [x for x in d.glob(f'{m}*ff*.lib')]
        if tt and ff:
            return d, lef, tt[0], ff[0]
        if tt and '/asap7' in str(d):   # modelled off-die PHY macro with a TT-only abstract (SerDes/UCIe): FF uses TT
            return d, lef, tt[0], tt[0]
    return None


def sv_val(v):
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    return str(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--contract', type=Path, default=CONTRACT, help='source contract (default: main); freeze it to the synthesis snapshot')
    a = ap.parse_args()
    C = json.loads(a.contract.read_text())
    (a.out / 'wrap').mkdir(parents=True, exist_ok=True)
    groups = defaultdict(list)
    for n, i in C['instances'].items():
        groups[(i['master'], json.dumps(i['ports'], sort_keys=True))].append(n)
    nvar = defaultdict(int)
    for (m, _) in groups:
        nvar[m] += 1
    views, jobs, k_of = {}, [], defaultdict(int)
    for (m, sig), insts in sorted(groups.items()):
        rep = C['instances'][insts[0]]
        k = k_of[m]; k_of[m] += 1
        cell = m if nvar[m] == 1 else f'{m}__pv{k}'
        ports = {p: v['bits'] for p, v in rep['ports'].items()}
        rv = real_view(m)
        ent = dict(master=m, cell=cell, instances=insts, representative=insts[0], params=rep['params'],
                   source=rep['source'], ports=len(ports), port_bits=sum(ports.values()))
        if rv:
            lp = lef_ports(rv[1])
            mism = {p: (lp.get(p), w) for p, w in ports.items() if lp.get(p) != w}
            extra = sorted(set(lp) - set(ports))
            ent.update(kind='REAL' if not mism else 'REAL_PORT_MISMATCH', view_dir=str(Path(rv[0]).relative_to(ROOT)),
                       lef=str(Path(rv[1]).relative_to(ROOT)), tt=str(Path(rv[2]).relative_to(ROOT)),
                       ff=str(Path(rv[3]).relative_to(ROOT)), mismatch=mism, view_extra_pins=extra)
            if not mism:
                views[cell] = ent
                continue
        # SYNTH: wrapper binding the representative's parameters
        w = 'v16w_' + cell
        decl = []
        for p, v in rep['ports'].items():
            rng = f'[{v["bits"] - 1}:0] ' if v['bits'] > 1 else ''
            decl.append(f'  {v["direction"]} wire {rng}{p}')
        prm = ''
        # yosys cannot bind unpacked-array parameter values ('{...}): the module default is synthesised and recorded
        keep = {k: v for k, v in rep['params'].items() if not str(v).startswith("'{")}
        dropped = sorted(set(rep['params']) - set(keep))
        if keep:
            prm = ' #(' + ', '.join(f'.{k}({sv_val(v)})' for k, v in keep.items()) + ')'
        body = [f'// generated by tools/hbm_die_v15/v16_views.py: {m} with the parameters of v16 instance {insts[0]}', PRE.get(m, ''),
                f'module {w} (', ',\n'.join(decl), ');',
                f'  {m}{prm} u (' + ', '.join(f'.{p}({p})' for p in rep['ports']) + ');', 'endmodule', '']
        (a.out / 'wrap' / f'{w}.sv').write_text('\n'.join(body))
        base = re.sub(r'_(SW|SE|NW|NE)$', '', m)
        mem = BIG.get(m, BIG.get(base, 48))
        ent.update(kind='SYNTH', params_dropped_yosys=dropped, wrapper=w, mem_gb=mem, env=ENV.get(m, ''), blackbox=BB.get(m, '-'))
        views[cell] = ent
        jobs.append((cell, m, w, mem, BB.get(m, '-'), ENV.get(m, '')))
    (a.out / 'views.json').write_text(json.dumps(views, indent=1))
    with open(a.out / 'jobs.tsv', 'w') as f:
        for j in jobs:
            f.write('\t'.join(map(str, j)) + '\n')
    cnt = defaultdict(int)
    for v in views.values():
        cnt[v['kind']] += 1
    print(json.dumps(dict(cells=len(views), by_kind=cnt, synth_jobs=len(jobs))))
    for c, v in views.items():
        if v['kind'] == 'REAL_PORT_MISMATCH':
            print('MISMATCH', c, list(v['mismatch'].items())[:5])


if __name__ == '__main__':
    main()
