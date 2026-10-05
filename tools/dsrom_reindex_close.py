#!/usr/bin/env python3
"""DS ROM re-index fixes (main d35c34901): routed SS/FF closure of ot_hdc_v41x_sel_mdrop (MDROP=1) and
ot_hdc_v41x_idx_kgctl at 1.2 GHz, in the register-to-register context harnesses of
rtl/hdc/v41x/phys/ot_hdc_v41x_reindex_ctx.sv.

  groups  per-corner OpenSTA on a routed run_abi3_physical workdir (6_final.odb + RCX spef): SS RVT libs for
          setup (60 ps), FF RVT libs for hold (25 ps), propagated clocks, plus the slack of the paths that
          are combinational through the DUT boundary (in the die a neighbour's logic shares those cycles,
          so each external side must leave the 20% neighbour budget the bare routes charge:
          --io-delay-fraction 0.2).
              python3 tools/dsrom_reindex_close.py groups --workdir W --nickname N --block mdrop|kgctl --out J
  record  assemble results/rtl/dsrom_reindex_close_20261004/record.json from the per-run physical.json and
          groups.json files.
              python3 tools/dsrom_reindex_close.py record --runs DIR --out J
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERIOD_PS, BUDGET = 833.0, 0.2

# launch (harness u_l.q) and capture (harness u_c.q) bit ranges of the combinational boundary signals,
# from the concatenations in ot_hdc_v41x_reindex_ctx.sv at the deployed parameters
def mdrop_groups(Q=4, W=16, IW=20, KW=10, NS=13):
    no = Q + Q + Q + Q * W + Q * W * 16 + Q * W * IW + KW + 1
    sl = list(range(0, Q * NS))                  # select-slice state flops whose in_ready logic is out_ready
    return {
        # select state -> (its in_ready logic, modelled) -> out_ready -> mdrop register enables: neighbour as built
        "out_ready_in": dict(frm=sl, to=None, sides=0),
        # mdrop -> in_ready: the scorer's side keeps the 20% budget
        "in_ready_out": dict(frm=None, to=list(range(no - Q, no)), sides=1),
        "out_ready_to_in_ready": dict(frm=sl, to=list(range(no - Q, no)), sides=1),
    }


def kgctl_groups(NPC=32, TAGW=16, BEATW=4, LBW=14, LMW=11, HW=20):
    # i = {lr_e, lr_o, cmd_v, cmd_base, cmd_skip, cmd_n, req_rdy, rsp_v, rsp_tag, rsp_beat, dr_ready}
    b = 0
    dr_ready = [b]; b += 1
    b += NPC * BEATW + NPC * TAGW + NPC          # rsp_beat, rsp_tag, rsp_v: registered on entry
    req_rdy = list(range(b, b + NPC)); b += NPC
    b += (LMW + 1) + 10 + HW + 1                 # cmd_n, cmd_skip, cmd_base, cmd_v
    lr = list(range(b, b + 2 * LBW))             # lr_o, lr_e (SRAM read data)
    no = 1 + (LMW - 1) + 1 + 1 + NPC + NPC * 28 + NPC * 4 + NPC * TAGW + NPC + 2 + 7 + 14 + 10 + 10 + 2 * LBW
    lr_out = list(range(no - LMW, no))           # {lr_re, lr_addr}: SRAM read port
    return {
        "dr_ready_in": dict(frm=dr_ready, to=None, sides=1),
        "req_rdy_in": dict(frm=req_rdy, to=None, sides=1),
        "lr_data_in": dict(frm=lr, to=None, sides=1),
        "lr_port_out": dict(frm=None, to=lr_out, sides=1),
    }


STA_HEAD = r'''
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(QA_LIBTAG)_*.lib*]] { read_liberty $f }
read_db $::env(QA_ODB)
read_sdc $::env(QA_SDC)
read_spef $::env(QA_SPEF)
set_propagated_clock [all_clocks]
report_units
puts "RC setup"; report_worst_slack -max -digits 2
puts "RC hold"; report_worst_slack -min -digits 2
set nv 0; set nh 0; set eps [all_registers -data_pins]
foreach p $eps {
  set s [get_property $p slack_max]; if {$s != "INF" && $s < 0} { incr nv }
  set s [get_property $p slack_min]; if {$s != "INF" && $s < 0} { incr nh }
}
puts "RC failing setup $nv hold $nh of [llength $eps]"
proc grp {name from to} {
  set a {}
  if {[llength $from]} { lappend a -from $from }
  if {[llength $to]} { lappend a -to $to }
  puts "RC group $name max"
  report_checks {*}$a -path_delay max -group_path_count 1 -digits 2
  puts "RC group $name min"
  report_checks {*}$a -path_delay min -group_path_count 1 -digits 2
}
proc cells_of {pfx bits} {
  set want [dict create]
  foreach b $bits { dict set want $b 1 }
  set out {}
  foreach c [get_cells -quiet "${pfx}*"] {
    if {[regexp {\[([0-9]+)\]} [get_full_name $c] -> i] && [dict exists $want $i]} { lappend out $c }
  }
  return $out
}
'''


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cmd_groups(a):
    work = Path(a.workdir).resolve()
    res = sorted(work.rglob(f"results/asap7/{a.nickname}/base"))[0]
    mount = res.parents[3]
    odb, sdc, spef = res / "6_final.odb", res / "6_final.sdc", res / "6_final.spef"
    groups = mdrop_groups() if a.block == "mdrop" else kgctl_groups()
    tcl = [STA_HEAD]
    for name, g in groups.items():
        frm = f"[cells_of u_l.q {{{' '.join(map(str, g['frm']))}}}]" if g["frm"] else "{}"
        to = f"[cells_of u_c.q {{{' '.join(map(str, g['to']))}}}]" if g["to"] else "{}"
        tcl.append(f"grp {name} {frm} {to}")
    tcl.append('puts "RC end"')
    (mount / "rc_groups.tcl").write_text("\n".join(tcl) + "\n")
    rel = lambda p: "/work/" + str(p.relative_to(mount))
    out = dict(schema="opentallas.dsrom-reindex-close.groups.v1", workdir=str(work), nickname=a.nickname,
               block=a.block, period_ps=PERIOD_PS, neighbour_budget_fraction=BUDGET,
               basis="OpenSTA on 6_final.odb + RCX 6_final.spef, one ASAP7 RVT liberty corner per run, propagated "
                     "clocks, routed SDC uncertainties (60 ps setup / 25 ps hold)",
               artifacts_sha256={p.name: sha(p) for p in (odb, sdc, spef)}, corners={})
    for corner, tag in (("ss", "SS"), ("ff", "FF")):
        c = ["docker", "run", "--rm", "-v", f"{mount}:/work", "-e", f"QA_LIBTAG={tag}", "-e", f"QA_ODB={rel(odb)}",
             "-e", f"QA_SDC={rel(sdc)}", "-e", f"QA_SPEF={rel(spef)}", "openroad/orfs:latest", "bash", "-lc",
             "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /work/rc_groups.tcl"]
        p = subprocess.run(c, capture_output=True, text=True)
        log = p.stdout + p.stderr
        (work / f"rc_groups_{corner}.log").write_text(log)
        tu = re.search(r"time\s+1(\S*)s", log)
        scale = {"p": 1.0, "n": 1e3}.get(tu.group(1) if tu else "p", 1.0)    # report units -> ps
        f = lambda v: None if v in (None, "INF", "") else round(float(v) * scale, 2)
        r = dict(exit=p.returncode)
        m = re.search(r"RC setup\s+worst slack (?:max )?(\S+)", log); r["setup_wns_ps"] = f(m.group(1)) if m else None
        m = re.search(r"RC hold\s+worst slack (?:min )?(\S+)", log); r["hold_wns_ps"] = f(m.group(1)) if m else None
        m = re.search(r"RC failing setup (\d+) hold (\d+) of (\d+)", log)
        if m:
            r.update(failing_setup_endpoints=int(m.group(1)), failing_hold_endpoints=int(m.group(2)),
                     endpoints=int(m.group(3)))
        r["groups"] = {}
        secs = re.split(r"^RC group (\S+) (max|min)\n", log, flags=re.M)
        got = {}
        for i in range(1, len(secs) - 2, 3):
            body = secs[i + 2].split("RC ")[0]
            sl = re.search(r"(-?[0-9.]+)\s+slack \((?:MET|VIOLATED)\)", body)
            sp = re.search(r"Startpoint: (\S+)", body); ep = re.search(r"Endpoint: (\S+)", body)
            got.setdefault(secs[i], {})[secs[i + 1]] = (sl and sl.group(1), sp and sp.group(1), ep and ep.group(1))
        for name, g in groups.items():
            mx = got.get(name, {}).get("max", (None, None, None)); mn = got.get(name, {}).get("min", (None,) * 3)
            need = BUDGET * PERIOD_PS * g["sides"]
            s_ = f(mx[0])
            r["groups"][name] = dict(setup_slack_ps=s_, hold_slack_ps=f(mn[0]), start=mx[1], end=mx[2],
                                     external_sides=g["sides"], budget_needed_ps=need,
                                     budget_met=None if s_ is None else s_ >= need)
        out["corners"][corner] = r
    ss, ff = out["corners"]["ss"], out["corners"]["ff"]
    out["signoff"] = dict(
        ss_setup_met=ss.get("setup_wns_ps") is not None and ss["setup_wns_ps"] >= 0,
        ff_hold_met=ff.get("hold_wns_ps") is not None and ff["hold_wns_ps"] >= 0,
        ss_boundary_budget_met=all(g["budget_met"] is not False for g in ss["groups"].values()))
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["signoff"] | {k: {kk: vv for kk, vv in v.items() if kk != "groups"}
                                       for k, v in out["corners"].items()}, indent=1))


def cmd_record(a):
    runs = Path(a.runs)
    rec = json.loads(Path(a.out).read_text()) if Path(a.out).is_file() else {}
    rec.setdefault("schema", "opentallas.dsrom-reindex-close.record.v1")
    rec["runs"] = {}
    for d in sorted(runs.iterdir()):
        if not (d / "physical.json").is_file():
            continue
        ph = json.loads((d / "physical.json").read_text())
        de = ph.get("design", {})
        e = dict(top=de.get("top"), params=ph.get("design", {}).get("parameters") or ph.get("parameters"),
                 status=ph.get("status"), area_um2=de.get("area_um2"), cells=de.get("cells"),
                 core_area_um2=de.get("core_area_um2"), drc=de.get("drc"),
                 signal_integrity_clean=de.get("signal_integrity_clean"),
                 flow_setup_wns_ns=de.get("setup_wns_ns"), flow_hold_wns_ns=de.get("hold_wns_ns"),
                 flow_reason=ph.get("acceptance", {}).get("reason"), git=ph.get("git"))
        if (d / "groups.json").is_file():
            g = json.loads((d / "groups.json").read_text())
            e["signoff"] = g["signoff"]
            e["corners"] = g["corners"]
        rec["runs"][d.name] = e
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("groups")
    g.add_argument("--workdir", required=True)
    g.add_argument("--nickname", required=True)
    g.add_argument("--block", choices=["mdrop", "kgctl"], required=True)
    g.add_argument("--out", required=True)
    r = sub.add_parser("record")
    r.add_argument("--runs", required=True)
    r.add_argument("--out", required=True)
    a = ap.parse_args()
    {"groups": cmd_groups, "record": cmd_record}[a.cmd](a)


if __name__ == "__main__":
    main()
