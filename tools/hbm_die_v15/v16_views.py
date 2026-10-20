#!/usr/bin/env python3
"""View plan of the v16 full HBM die case (H-DIE-V16CASE 2026-10-16): for every master/port-variant of the v16 source
contract (results/arch/hbm_die_v16/contract.json) pick the view a die GRT/STA binds:
  ROUTED_UNBOUND = routed library candidate on main (source/native qualification unverified) (physical/**/views/<m>/<m>.lef + <m>_{tt,ff}.lib) whose pins equal the contract ports
  SYNTH = current-source mapped netlist ETM (synth_master.sh HIER=1 + synth_etm.sh): an estimate, never a sign-off view.
One representative instance per exact (master, port signature, parameter set). Equal ports with different parameters
never alias the representative ETM.
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
    'ot_hbm_accel_smh_attn': 128, 'ot_hbm_hc_eng_static': 96, 'ot_hgi_sfu_core_split': 96,
}
ENV = {'ot_hbm_accel_smh_static': 'DEFINES=OT_SMH_FC_HIER LIBCELLS=1', 'ot_hbm_accel_smh_attn': 'DEFINES=OT_SMH_FC_HIER,OT_SMH_HIER,OT_SMH_XLK,OT_FP_DATA_NORST,OT_SMH_DRST0,OT_SMH_RSTRELAY LIBCELLS=1', 'hfd_ckgen': 'DROP=rtl/hbm_accel/control/tb_hfd_ckgen.sv',
       # L2H-GEN2E 10-19: l21 hfd_ckgen_nolink has the same PLL model child (GEN2e4 S2 failed: tb file picked as its definer)
       'hfd_ckgen_nolink': 'DROP=rtl/hbm_accel/control/tb_hfd_ckgen.sv'}
PRE = {'hfd_ckgen': '(* blackbox *) module ot_hbm_pll_bb(input wire refclk, input wire reset_n, output wire clk_stream, '
       'output wire clk_serial, output wire clk_hbm, output wire clk_link, output wire locked); endmodule'}
PRE['hfd_ckgen_nolink'] = PRE['hfd_ckgen']
# DIE-HBM-LEAD 10-19: hop-0 / 0-station landing masters (hbfd_lh0_*, hbfd_land0_*) instantiate the ASAP7 ICG (ot_hdc_cg) directly:
# read lib cells as boxes (the behavioural retention_cell_models.sv ICG became a 'reg IQ = 0' netlist that OpenSTA cannot parse).
def env_of(m):
    return ENV.get(m, 'LIBCELLS=1' if re.match(r'hbfd_(lh0|land0)_', m) else '')


BB = {}   # the PLL (allowed analog model, die_port_bind --allow-model) is declared blackbox in the ckgen wrapper (PRE)


def lef_ports(lef):
    out = defaultdict(int)
    for m in re.finditer(r'^\s*PIN\s+(\S+)', Path(lef).read_text(), re.M):
        p = m.group(1)
        if p in ('VDD', 'VSS'):
            continue
        out[re.sub(r'\[\d+\]$', '', p)] += 1
    return dict(out)


# routed views that must not bind (native qualification FAIL): H-DIE-R8 10-17 h9b view fails native capture 213.7 ->
# the CLOSED successor hdie_pc_ctrl_cfg_h9c (same master, RTL unchanged, 155.52^2) binds instead
NOT_BINDABLE = ('physical/ref_tile/hdie_pc_ctrl_cfg_h9b/',)


def real_views(m):
    """every routed library candidate of master m: (dir, lef, tt, ff)."""
    out = []
    for lef in sorted(glob.glob(str(ROOT / f'physical/**/views/{m}/{m}.lef'), recursive=True)) + \
            sorted(glob.glob(str(ROOT / f'physical/asap7*/{m}/{m}.lef'))):
        if '/provenance/' in lef or any(x in lef for x in NOT_BINDABLE):
            continue
        d = Path(lef).parent
        tt = [x for x in d.glob(f'{m}*tt*.lib')]
        ff = [x for x in d.glob(f'{m}*ff*.lib')]
        if tt and ff:
            out.append((d, lef, tt[0], ff[0]))
        elif tt and '/asap7' in str(d):   # modelled off-die PHY macro with a TT-only abstract (SerDes/UCIe): FF uses TT
            out.append((d, lef, tt[0], tt[0]))
    return out


def spec_params(view_dir):
    """the hardened tile's parameters (physical/ref_tile/<tile>/spec.json 'params'), None if unknown."""
    sp = Path(view_dir).parent.parent / 'spec.json'
    if not sp.is_file():
        return None
    try:
        return json.loads(sp.read_text()).get('params')
    except ValueError:
        return None


def real_view(m, ports=None, params=None):
    """H-DIE-R8b 10-17: a master with several hardened parameter variants (ot_hbm_static_cfg_collar = col_sfu / col_su /
    col_idx) has one routed view per variant tile; pick the candidate whose LEF pins equal this variant's ports and whose
    tile spec params (when recorded) agree with the instance's.  The first sorted candidate used to win for every
    variant (col_su and col_sfu were planned against col_idx's view and fell back to SYNTH)."""
    cands = real_views(m)
    if not cands or ports is None:
        return cands[0] if cands else None
    param_miss = False
    for rv in cands:
        lp = lef_ports(rv[1])
        if any(lp.get(p) != w for p, w in ports.items()):
            continue
        sp = spec_params(rv[0])
        if sp and params is not None and any(str(params.get(k, v)) != str(v) for k, v in sp.items()):
            param_miss = True
            continue
        return rv
    # DIE-HBM-LEAD 10-19: a view hardened for OTHER parameter values (equal pins) must never bind (it fell back to
    # cands[0] and bound e.g. the QID 2 / G 0 cxport dl_s view on all 16 lanes) -> SYNTH of this variant
    return None if param_miss else cands[0]


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
        groups[(i['master'], json.dumps(i['ports'], sort_keys=True),
                json.dumps(i.get('params', {}), sort_keys=True))].append(n)
    nvar = defaultdict(int)
    for (m, _, _) in groups:
        nvar[m] += 1
    views, jobs, k_of = {}, [], defaultdict(int)
    for (m, sig, _params), insts in sorted(groups.items()):
        rep = C['instances'][insts[0]]
        k = k_of[m]; k_of[m] += 1
        cell = m if nvar[m] == 1 else f'{m}__pv{k}'
        ports = {p: v['bits'] for p, v in rep['ports'].items()}
        rv = real_view(m, ports, rep['params'])
        ent = dict(master=m, cell=cell, instances=insts, representative=insts[0], params=rep['params'],
                   source=rep['source'], ports=len(ports), port_bits=sum(ports.values()))
        if rv:
            lp = lef_ports(rv[1])
            mism = {p: (lp.get(p), w) for p, w in ports.items() if lp.get(p) != w}
            extra = sorted(set(lp) - set(ports))
            ent.update(kind='ROUTED_UNBOUND' if not mism else 'REAL_PORT_MISMATCH',
                       source_lineage_verified=False, native_qualified=False,
                       qualification_gap='Port signature alone does not prove source/dependency/parameter lineage or native qualification.', view_dir=str(Path(rv[0]).relative_to(ROOT)),
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
        ent.update(kind='SYNTH', params_dropped_yosys=dropped, wrapper=w, mem_gb=mem, env=env_of(m), blackbox=BB.get(m, '-'))
        views[cell] = ent
        jobs.append((cell, m, w, mem, BB.get(m, '-'), env_of(m)))
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
