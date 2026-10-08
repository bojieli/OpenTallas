#!/usr/bin/env python3
"""TT timing models for hardened HBM views (OWNER OPTION B 2026-10-07: setup signs off at TT, hold at FF).

Each view's SS / FF Liberty was written by write_timing_model from its routed 6_final odb / sdc / spef
(tools/hbm_fmax_attn_abstract.py).  This writes <name>_tt.lib the same way with the ASAP7 TT NLDM libraries (+ the
LVT / SLVT TT libraries when the odb uses them, as tools/w18/corner_sta.py) and the TT Liberty of every hardened
sub-macro (which must exist first: leaves before parents).  It runs on the host that holds the route (docker
openroad/orfs:asap7lock) and copies the Liberty back into the repo view directory.

    python3 tools/hbm_view_tt.py --jobs jobs.json [--par 6]
jobs.json: [{"name", "view_dir" (repo), "host", "orfs" (candidate dirs), "macro_views": [repo dirs]}]
"""
import argparse
import json
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'
TT = ['asap7sc7p5t_AO_{v}_TT_nldm_211120.lib.gz', 'asap7sc7p5t_INVBUF_{v}_TT_nldm_220122.lib.gz',
      'asap7sc7p5t_OA_{v}_TT_nldm_211120.lib.gz', 'asap7sc7p5t_SEQ_{v}_TT_nldm_220123.lib',
      'asap7sc7p5t_SIMPLE_{v}_TT_nldm_211120.lib.gz']
SCR = {'ot-epyc1tb': '/srv/opentallas-scratch/claude/hbm-die/tt', 'ot-agidock128': '/srv/opentallas-scratch/claude/hbm-die/tt',
       'ot-pve1': '/srv/opentallas-scratch/claude/hbm-die/tt'}
SCR_DEF = '/srv/opentallas-scratch2/scratch/claude/hbm-die/tt'


def sh(host, cmd, **kw):
    return subprocess.run(['ssh', host, cmd], capture_output=True, text=True, **kw)


def one(j):
    name, host = j['name'], j['host']
    w = f"{SCR.get(host, SCR_DEF)}/{name}"
    # resolve the ORFS dir holding results/asap7/*/base/6_final.{odb,spef,sdc}
    cands = ' '.join(shlex.quote(c) for c in j['orfs'])
    r = sh(host, f"for d in {cands}; do for b in $d/results/asap7/*/base; do "
                 f"[ -f $b/6_final.odb ] && [ -f $b/6_final.spef ] && [ -f $b/6_final.sdc ] && echo $b && exit 0; done; done; exit 1")
    if r.returncode:
        return dict(name=name, ok=False, error='no routed 6_final odb/spef/sdc at ' + ' '.join(j['orfs']))
    base = r.stdout.split()[0]
    vts = sh(host, f"for t in L SL; do grep -c -a -m1 -E \"_ASAP7_75t_$t([^A-Za-z0-9_]|$)\" {base}/6_final.odb >/dev/null && echo $t; done").stdout.split()
    vtn = {'L': 'LVT', 'SL': 'SLVT'}
    sh(host, f'mkdir -p {w}/mv')
    mv_lef, mv_lib = '', ''
    for d in j.get('macro_views', []):
        d = ROOT / d
        n = d.name
        if not (d / f'{n}_tt.lib').exists():
            return dict(name=name, ok=False, error=f'sub-macro {n} has no TT Liberty yet')
        subprocess.run(['scp', '-q', str(d / f'{n}.lef'), str(d / f'{n}_tt.lib'), f'{host}:{w}/mv/'], check=True)
        mv_lef += f'read_lef /w/mv/{n}.lef\n'
        mv_lib += f'read_liberty /w/mv/{n}_tt.lib\n'
    libs = '\n'.join(f'read_liberty {PLAT}/lib/NLDM/{x.format(v=v)}' for v in ['RVT'] + [vtn[t] for t in vts] for x in TT)
    lefs = ''.join(f'\nread_lef {PLAT}/lef/asap7sc7p5t_28_{t}_1x_220121a.lef' for t in vts)
    tcl = f"""read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef{lefs}
{libs}
{mv_lib}{mv_lef}read_db /in/6_final.odb
read_sdc /in/6_final.sdc
read_spef /in/6_final.spef
set_propagated_clock [all_clocks]
puts "OT_TT_WS setup_ns=[sta::worst_slack_cmd max] hold_ns=[sta::worst_slack_cmd min]"
write_timing_model -library_name {name}_tt /w/{name}_tt.lib
puts OT_EXPORT_DONE
"""
    p = subprocess.run(['ssh', host, f'cat > {w}/export_tt.tcl'], input=tcl, text=True)
    r = sh(host, f"cd {w} && docker run --rm --memory=64g -v {base}:/in:ro -v {w}:/w openroad/orfs:asap7lock "
                 f"/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /w/export_tt.tcl > {w}/export_tt.log 2>&1; "
                 f"grep -E 'OT_TT_WS|OT_EXPORT_DONE|ERROR|Error' {w}/export_tt.log | tail -5")
    if 'OT_EXPORT_DONE' not in r.stdout:
        return dict(name=name, ok=False, error=r.stdout[-400:], base=base)
    out = ROOT / j['view_dir']
    subprocess.run(['scp', '-q', f'{host}:{w}/{name}_tt.lib', f'{host}:{w}/export_tt.tcl', str(out) + '/'], check=True)
    (out / 'export_tt.tcl').rename(out / f'export_{name}_tt.tcl')
    ws = [l for l in r.stdout.splitlines() if 'OT_TT_WS' in l]
    return dict(name=name, ok=True, host=host, base=base, vts=vts, ws=ws[0] if ws else None,
                lib=str((out / f'{name}_tt.lib').relative_to(ROOT)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--jobs', required=True)
    ap.add_argument('--par', type=int, default=6)
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    jobs = json.loads(Path(a.jobs).read_text())
    with ThreadPoolExecutor(a.par) as ex:
        res = list(ex.map(one, jobs))
    for r_ in res:
        print(json.dumps(r_))
        sys.stdout.flush()
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + '\n')


if __name__ == '__main__':
    main()
