#!/usr/bin/env python3
"""SMH r5 only: partition each writer's reset by slot at the same capture edge.
Run after rp5_gen.py and lp.py gen; shared landing primitives stay unchanged.
"""
from pathlib import Path
import json
import re
ROOT=Path(__file__).resolve().parents[2]
RTL="rtl/hbm_accel/sm/repack/h2a5/ot_rp5_land_reset_split.sv"

def main():
    original=(ROOT/"rtl/common/landed_parent/ot_pl_land.sv").read_text()
    start=original.index("module ot_pl_land_local_w #(")
    local=original[start:original.index("endmodule",start)+len("endmodule")]
    local=local.replace("module ot_pl_land_local_w", "module ot_rp5_land_local_w")
    local=local.replace("    reg rq;", "    reg rq;\n    wire [D-1:0] rq_slot;")
    local=local.replace("    generate for (s=0;s<D;s=s+1) begin:g_slot", """    generate for (s=0;s<D;s=s+1) begin:g_slot
        // Identical reset capture edge; kept per-slot flop prevents ABC from
        // redistributing one control rq to every data/epoch mux in D slots.
        (* keep_hierarchy="yes" *) ot_pl_land_field_copy_bit #(.ID(8192+s)) u_reset(
            .ck(ck), .d(rsi), .q(rq_slot[s]));""")
    local=local.replace("if (rq && write_oh[s])", "if (rq_slot[s] && write_oh[s])")
    original=(ROOT/"rtl/common/landed_parent/ot_pl_land_reset_forest.sv").read_text()
    start=original.index("module ot_pl_land_vector_reset_w #(")
    vector=original[start:original.index("endmodule",start)+len("endmodule")]
    vector=vector.replace("ot_pl_land_local_w #(", "ot_rp5_land_local_w #(")
    header="""`timescale 1ns/1ps
`default_nettype none
// SMH r5 source-local native reset repair. Original rq/control and per-slot
// data write guards remain at the same edge; reader, ring D/K, data/epoch
// storage, reset run, valid masks and static calendars are unchanged.
// Each rq_slot flop drives one W24 + epoch/selector slice (~30 mapped loads),
// replacing the original D4-wide rq fanout120. Reset forest leaves drive five
// same-edge reset captures. No new latency, no global primitive replacement.
"""
    # Source-local replacement file: keep the public primitive identities for
    # the existing LP topology audit. Reader/reset-forest definitions are
    # copied byte-exact; only the writer's internal local module changes.
    end=original.index("endmodule",start)+len("endmodule")
    scoped=original[:start]+vector+original[end:]
    (ROOT/RTL).write_text(header+local+"\n\n"+scoped)
    for h in "ns":
        for v in "mf":
            base=ROOT/f"rtl/hbm_accel/sm/repack/h2a5/lp_{h}_{v}"
            p=base/f"ot_hbm_smh_rp5{h}_{v}.sv"
            s=p.read_text().replace("ot_rp5_land_vector_reset_w #(", "ot_pl_land_vector_reset_w #(")
            # Existing reset mutant previously vanished before the bench's
            # warm30 compare window. Use lp.py's documented mut4_stages knob;
            # MUT0 remains identical, no positive latency/reset changes.
            s,n=re.subn(r"(\.N\(\(MUT == 4\) \? )\d+( : 0\)\))",r"\g<1>64\2",s)
            if n != 1: raise RuntimeError(f"Expected one reset mutant in {p}, found {n}")
            s=s.replace("one stage long", "64 stage(s) long")
            p.write_text(s)
            spec=ROOT/f"results/arch/hbm_smh_r5_1021/lp_spec_{h}_{v}.json"
            d=json.loads(spec.read_text());d["mut4_stages"]=64
            spec.write_text(json.dumps(d,indent=1)+"\n")
            for p in [base/f"ot_hbm_smh_rp5{h}_{v}_bench.sh"]:
                s=p.read_text()
                s=s.replace("rtl/common/landed_parent/ot_pl_land_reset_forest.sv",RTL)
                s=s.replace(f'SRCS="{RTL} ', 'SRCS="',1) if s.count(RTL)>1 else s
                p.write_text(s)
            p=ROOT/f"physical/ref_tile/smh_rp5{h}_{v}/spec.json"
            d=json.loads(p.read_text())
            d['sources']=list(dict.fromkeys(RTL if x=='rtl/common/landed_parent/ot_pl_land_reset_forest.sv' else x for x in d['sources']))
            p.write_text(json.dumps(d,indent=1)+"\n")
    p=ROOT/"rtl/hbm_accel/sm/repack/h2a5/run_rp5_2_one.sh"
    s=p.read_text()
    s=s.replace("rtl/common/landed_parent/ot_pl_land_reset_forest.sv",RTL)
    s=s.replace(f'SRCS="{RTL} ', 'SRCS="',1) if s.count(RTL)>1 else s
    p.write_text(s)

if __name__=="__main__":main()
