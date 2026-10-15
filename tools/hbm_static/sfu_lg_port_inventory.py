#!/usr/bin/env python3
"""Source/LEF inventory for the current scheduled SFU; no physical grant implied."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PEER = ROOT / "rtl/hbm_accel/generic/peers"

def inventory():
    macro_dir = ROOT / "physical/asap7_memory_macros"
    macros = []
    for shape, count, owner in [("256x256_m2_r2c2", 80, "five local groups x16 banks, RB=LWB-log2(16)=11"),
                                ("1024x256_m2_r2c2", 22, "arithmetic eight stripes x2 pages + IO three stripes x2 pages")]:
        name = "ot_sram_1r1w_" + shape
        lef = macro_dir / name / (name + ".lef")
        w, h = map(float, re.search(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)", lef.read_text()).groups())
        macros.append(dict(master=name, count=count, width_um=w, height_um=h,
                           area_um2=count*w*h, owner=owner,
                           lef_sha256=hashlib.sha256(lef.read_bytes()).hexdigest()))
    group = []
    for g in range(4):
        group.append(dict(group=g, banks=[2*g,2*g+1], state=f"u_vm.g_lg[{g}]",
                          clock=f"clk_lg[{g}]", reset=f"rst_lg_n[{g}]",
                          ports={"local_rq":[34*g,34],"local_wq":[562*g,562],
                                 "local_rr":[514*g,514],"local_w_done":[2*g,2]},
                          granted_outline=None, granted_pin_rectangles=None))
    files = sorted(PEER.glob("ot_hgi_sfu_*static*.sv")) + [PEER / "ot_hgi_sfu_scheduled_engine.sv",PEER / "ot_hgi_sfu_programmed_engine.sv",PEER / "ot_hgi_su_unit.sv"]
    lower = sum(m["area_um2"] for m in macros)
    return dict(top="ot_hgi_sfu_scheduled_engine",parameters=dict(PAGE_AW=1,AW=11,LWB=15),
                lanes=16, lane_clocks=16, mapper_clocks=16, lg_clocks=4, total_clock_pins=37,
                arithmetic_broadcast_tree=0,
                broadcast_tree_note="static_engine does not override static_quarter BTREE=0; the separate BTREE=1 proof is not this master.",
                common_clock="clk (programme, operand/output store, scalar publication and fault aggregation)",
                clock_relationship="Same-frequency related roots; no asynchronous CDC contract. Die STA must cover group-to-store and programme-to-group crossings.",
                groups=group, logical_widths=dict(local_rq=136,local_wq=2248,local_rr=2056,local_w_done=8),
                read_response_update=14, read_store_sample=15, write_completion_update=11,
                added_service_edges=0, macros=macros, macro_count=102,
                macro_only_area_um2=lower, old_engine_outline_um=[552.96,723.6],
                old_outline_area_um2=552.96*723.6, macro_to_old_outline=lower/(552.96*723.6),
                mapped_logic_area_um2=None, placed_area_um2=None, physical_qualified=False,
                source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                preserved_synthesis=[dict(host="ot-epyc1tb",pid=3876234,path="/srv/opentallas-scratch/claude/hdie-v15c/out/sfu",scope="pre-LG-split exact fullshape; progressing Yosys flat SHARE SAT"),
                                     dict(host="ot-epyc4",pid=639281,path="/srv/opentallas-scratch/claude/hdie-v15c/out/sfu_c",scope="pre-LG-split coarse synthesis")],
                blockers=["Macro-only footprint already exceeds old engine grant before 16 arithmetic lanes, mappers, logic, halos or utilization.",
                          "All four port-group outlines and full RTL pin rectangles remain ungranted.",
                          "local_rq remains direct programme-to-pin wiring; pin registration/reach must be resolved with the actual slot and calendar, not waived.",
                          "Operand store and programme are central: related-root group/store crossings have no measured physical reach proof.",
                          "No fresh mapped area/CTS/route for the four-root successor; preserved synthesis measures predecessor.",
                          "Existing canonical 3072-word Qwen GLU diagnostic is 432 IO edges /120 priced=3.6; whole-layer production qualification remains open."])

if __name__ == "__main__":
    print(json.dumps(inventory(), indent=2))
