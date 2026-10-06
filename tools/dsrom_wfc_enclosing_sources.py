#!/usr/bin/env python3
"""Expose existing WFC owner/accept nodes without changing its exact body.

Only module names, two observation ports/assignments and their parent forwarding
change. The full866-exact controller remains byte-identical in its pinned file.
"""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def one(s,a,b):
    if s.count(a)!=1:raise ValueError('ambiguous source node '+a)
    return s.replace(a,b,1)
def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    paths=['rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv','rtl/rom/wavefront/context/ot_dsrom_wfc_parent_cut.sv']
    c=(ROOT/paths[0]).read_text();p=(ROOT/paths[1]).read_text()
    c=one(c,'module ot_rom_pkg_ctrl_wfc #(','module ot_rom_pkg_ctrl_wfc_enclosed #(')
    c=one(c,'    output reg                wf_squash','    output wire core_done_accepted,\n    output wire [USER_W-1:0] core_owner_user,\n    output reg                wf_squash')
    c=one(c,'    assign core_busy = running;','    assign core_busy = running;\n    // Literal current owner and original native acceptance event. No new state.\n    assign core_owner_user = cur_user;\n    assign core_done_accepted = WAVE && job_done;')
    p=one(p,'module ot_dsrom_wfc_parent_cut #(','module ot_dsrom_wfc_parent_enclosed #(')
    p=one(p,'    output reg                wf_squash','    output wire core_done_accepted,\n    output wire [USER_W-1:0] core_owner_user,\n    output reg                wf_squash')
    p=one(p,'    ot_rom_pkg_ctrl_wfc #(','    ot_rom_pkg_ctrl_wfc_enclosed #(')
    p=one(p,'        .core_busy(core_busy),','        .core_busy(core_busy),\n        .core_done_accepted(core_done_accepted),.core_owner_user(core_owner_user),')
    for name,body in [('ot_rom_pkg_ctrl_wfc_enclosed.sv',c),('ot_dsrom_wfc_parent_enclosed.sv',p)]:
        (out/name).write_text(body)
    record=dict(canonical_sha256={f:sha((ROOT/f).read_bytes())for f in paths},
      derived_sha256={f.name:sha(f.read_bytes())for f in out.glob('*.sv')},
      changes='module names, two existing observation ports/assignments and exact parent forwarding only',
      producer='core_owner_user=literal cur_user, core_done_accepted=WAVE&&literal job_done',
      controller_state_or_calendar_changed=False,whole_stage_authority_created=False,
      retained_full866_gate='results/rtl/dsrom_wfc_decoded_read_20261005/structural_full/record.json')
    (out/'source_binding.json').write_text(json.dumps(record,indent=2)+'\n')
    return record
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);args=a.parse_args()
    print(json.dumps(prepare(args.out),indent=2))
