#!/usr/bin/env python3
"""New SOURCE/STG physical masters using retained full-shape r24/r11 budgets.

Run remotely through measured admission. No old source/view is changed.
"""
import argparse,json,subprocess,os
from pathlib import Path
import dsrom_wfc_split_physical as L
ROOT=Path(__file__).resolve().parents[1]

def corner_sta(work: Path, nick: str, out: Path):
    res = next(work.rglob(f"results/asap7/{nick}/base"))
    mount = res.parents[3]
    (mount / "wf_sta.tcl").write_text(L.WF.STA_TCL)
    rel = lambda q: "/work/" + str(q.relative_to(mount))
    rec = dict(basis="OpenSTA on 6_final.odb + RCX 6_final.spef, one ASAP7 RVT liberty corner per run, propagated "
                     "clock. block = the routed SDC (IO at 20 % of the period vs an ideal clock); incontext = IO at "
                     "20 % vs a virtual clock carrying the block's own min/max insertion delay (same die tree as "
                     "the neighbours); reg2reg = IO false-pathed. 60 ps setup / 25 ps hold uncertainty.",
               artifacts_sha256={q.name: L.WF.sha(res / q) for q in (Path("6_final.odb"), Path("6_final.sdc"),
                                                                 Path("6_final.spef"))}, corners={})
    import re
    for lib in ("SS", "TT", "FF"):
        c = ["docker", "run", "--rm", "-v", f"{mount}:/work", "-e", f"WF_LIB={lib}",
             "-e", f"WF_ODB={rel(res / '6_final.odb')}", "-e", f"WF_SDC={rel(res / '6_final.sdc')}",
             "-e", f"WF_SPEF={rel(res / '6_final.spef')}", "-e", "WF_CLK=clk", "-e", "WF_USETUP=60",
             "-e", "WF_UHOLD=25", "openroad/orfs:latest", "bash", "-lc",
             "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /work/wf_sta.tcl"]
        p = subprocess.run(c, capture_output=True, text=True)
        log = p.stdout + p.stderr
        (out / f"wf_sta_{lib}.log").write_text(log)
        r = dict(exit=p.returncode, done="WFDONE" in log)
        m = re.search(r"WFLAT (\S+) (\S+)", log)
        if m:
            r["insertion_ps"] = [round(float(m.group(1)), 1), round(float(m.group(2)), 1)]
        for m in re.finditer(r"WFSTA (\w+) setup (\S+) hold (\S+) fails (\d+) (\d+)", log):
            r[m.group(1)] = dict(setup_wns_ps=round(float(m.group(2)) * 1e12, 1),
                                 hold_wns_ps=round(float(m.group(3)) * 1e12, 1),
                                 failing_setup=int(m.group(4)), failing_hold=int(m.group(5)))
        for m in re.finditer(r"WFPATH (\w+) (max|min)\n(.*?)(?=WFPATH|WFEND)", log, re.S):
            # report_checks emits one path per group. The first may be a
            # passing recovery path; select the least slack across all groups.
            paths = []
            for text in re.split(r"(?=Startpoint:)", m.group(3)):
                sp = re.search(r"Startpoint: (\S+)", text)
                ep = re.search(r"Endpoint: (\S+)", text)
                sl = re.search(r"([-+]?\d+(?:\.\d+)?)\s+slack \((?:MET|VIOLATED)\)", text)
                group = re.search(r"Path Group: (\S+)", text)
                if sp and ep and sl:
                    paths.append((float(sl.group(1)), sp.group(1), ep.group(1), group and group.group(1)))
            if paths:
                slack, sp, ep, group = min(paths)
                mode = r.setdefault(m.group(1), {})
                mode[f"worst_{m.group(2)}_path"] = [sp, ep]
                mode[f"worst_{m.group(2)}_path_slack_ps"] = slack
                mode[f"worst_{m.group(2)}_path_group"] = group
        rec["corners"][lib] = r
    ss, ff = rec["corners"]["SS"], rec["corners"]["FF"]
    def met(mode):
        try:
            return ss[mode]["setup_wns_ps"] >= 0 and ff[mode]["hold_wns_ps"] >= 0 and ss[mode]["hold_wns_ps"] >= 0
        except (KeyError, TypeError):
            return None
    rec["signoff"] = {m: met(m) for m in ("block", "incontext", "reg2reg")}
    (out / "wf_sta.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def main():
 p=argparse.ArgumentParser();p.add_argument('cmd',choices=['prep','sta','check']);p.add_argument('--inst',choices=['src','stg'],required=True)
 p.add_argument('--case',type=Path,required=True);p.add_argument('--src',type=Path,default=ROOT);p.add_argument('--cores',type=int,default=12);p.add_argument('--need',type=int,default=32)
 a=p.parse_args();basis=json.loads((ROOT/f'physical/dsrom_wfc_tokpipe/{a.inst}_basis.json').read_text())
 L.CTRL='rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc_tokpipe.sv'
 if a.cmd=='sta':
  L.WF.corner_sta=corner_sta
  return L.cmd_sta(argparse.Namespace(case=a.case,macros=a.inst=='src'))
 if a.cmd=='check':return L.cmd_check(argparse.Namespace(case=a.case))
 # Size before route: retained full-shape basis, same macro count and registered
 # interfaces; SOURCE metadata +1cycle, current-user STAGE tuple +0cycles.
 L.cmd_prep(argparse.Namespace(inst=a.inst,case=a.case,src=a.src,knob=[f'{k}={v}' for k,v in basis['params'].items()],util=50,density=.50,lb_addon=.20,orfs_var=basis['orfs_var'],die_skew=150,link_hold_pad=0,link_hold_abs_min=basis.get('link_hold_abs_min_ps'),route_period=770,ideal_io=False,io_lat=None,cores=a.cores,need=a.need))
 cfg=a.case/'config.mk';s=cfg.read_text().replace('export DESIGN_NAME = ot_rom_pkg_ctrl_wfc\n',f'export DESIGN_NAME = ot_dsrom_wfc_tokpipe_{a.inst}\n')
 s=s.replace('export VERILOG_FILES = ',f'export VERILOG_FILES = /src/rtl/dsrom_sys/mtp/ot_dsrom_wfc_tokpipe_{a.inst}.sv ')
 if os.environ.get('OT_ORFS_CORNER_OVERRIDE')=='TC':
  # ORFS accepts WC/BC named corners; WC reads actual TT libraries here.
  s=s.replace('export WC_LIB_FILES = $(WC_NLDM_LIB_FILES)', 'export WC_LIB_FILES = $(TC_NLDM_LIB_FILES)')
  s=s.replace('_ss.lib', '_tt.lib')
  s+='\n# TC route: WC alias reads TC stdcell and TT macro liberties\n'
 cfg.write_text(s)
 run=a.case/'run.sh';s=run.read_text().replace('tools/dsrom_wfc_split_physical.py sta',f'tools/dsrom_wfc_tokpipe_physical.py sta --inst {a.inst}').replace('tools/dsrom_wfc_split_physical.py check',f'tools/dsrom_wfc_tokpipe_physical.py check --inst {a.inst}')
 # Wrapper infers SRAM macro STA from --inst src; the base generator's --macros
 # option belongs to dsrom_wfc_split_physical and is redundant/invalid here.
 s=s.replace(' --case $W --macros', ' --case $W')
 # Calibrate stops atCTS; subsequent route keeps the same pinned source and recipe.
 s=s.replace('finish\" > $W/flow.log','${WFC_TARGET:-finish}\" > $W/flow.log')
 s=s.replace('cd $S && python3', 'if [[ "${WFC_TARGET:-finish}" != "finish" ]]; then exit 0; fi\ncd $S && python3',1)
 run.write_text(s)
 print(json.dumps(dict(master=f'ot_dsrom_wfc_tokpipe_{a.inst}',basis=f'physical/dsrom_wfc_tokpipe/{a.inst}_basis.json',source_cycles_added=1 if a.inst=='src' else 0,registered_boundary_unchanged=True)))
if __name__=='__main__':main()
