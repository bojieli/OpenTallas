"""Plan explicit ROM interface clock groups from an actual head ODB site dump.

This emits a proposal only: no CTS, legal-placement or timing approval is implied.
Register clock capacitances come from the exact native TT liberty used by the kit.
"""
import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sites", type=Path)
    ap.add_argument("seq_lib", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--occupancy", type=Path)
    ap.add_argument("--rows", type=Path)
    ap.add_argument("--buf-lib", type=Path)
    args = ap.parse_args()
    rows = list(csv.DictReader(args.sites.open(), delimiter="\t"))
    lib = args.seq_lib.read_text()
    caps = {}
    for match in re.finditer(r"\bcell\s*\(([^)]+)\)", lib):
        end = lib.find("\n  cell (", match.end())
        body = lib[match.end():end if end >= 0 else len(lib)]
        pin = re.search(r"\bpin\s*\(CLK\)\s*\{", body)
        if pin:
            cap = re.search(r"\bcapacitance\s*:\s*([0-9.eE+-]+)", body[pin.end():])
            if cap:
                caps[match.group(1)] = float(cap.group(1))
    banks = []
    for bank in (0, 1):
        clean = lambda r: r["name"].replace("\\", "")
        macro = [r for r in rows if clean(r) == f"u_m.u_rom{bank}"]
        capture = [r for r in rows if re.search(rf"u_m.cap{bank}\[", clean(r))]
        addr = [r for r in rows if f"u_m.u_rom_addr{bank}/addr[" in clean(r)]
        ce = [r for r in rows if clean(r).startswith(f"u_m.ce{bank}_q$")]
        assert (len(macro), len(capture), len(addr), len(ce)) == (1, 256, 12, 1)
        m = macro[0]
        cx = (float(m["x0"]) + float(m["x1"])) / 2
        base_y = float(m["y0"]) - 8
        leaves = []
        for side in ("left", "right"):
            sinks = sorted([r for r in capture if (float(r["ckx"]) < cx) == (side == "left")],
                           key=lambda r: (float(r["cky"]), float(r["ckx"])))
            count = math.ceil(len(sinks)/16)
            for group in range(count):
                ss = sinks[len(sinks)*group//count:len(sinks)*(group+1)//count]
                leaves.append(dict(name=f"rom{bank}_{side}_cap{group}", side=side,
                    kind="capture", sinks=[r["name"] for r in ss],
                    load_ff=sum(caps[r["master"]] for r in ss),
                    desired_xy=[sum(float(r[k]) for r in ss)/len(ss) for k in ("ckx", "cky")]))
        ss = addr + ce
        leaves.append(dict(name=f"rom{bank}_right_launch", side="right", kind="address_CE",
            sinks=[r["name"] for r in ss], load_ff=sum(caps[r["master"]] for r in ss),
            desired_xy=[sum(float(r[k]) for r in ss)/len(ss) for k in ("ckx", "cky")]))
        leaves.append(dict(name=f"rom{bank}_right_macro", side="right", kind="macro",
            sinks=[m["name"]], load_ff=9.3458,
            desired_xy=[float(m["x1"])+7, float(m["cky"])],
            load_source="ot_rom_4096x274_m8_tt.lib pin(clk) capacitance=9.3458fF"))
        banks.append(dict(bank=bank, common_root_name=f"ot_hrom{bank}_root",
            shallow_trunk_target=f"ot_hrom{bank}_root/A",
            triton_local_cts=False,
            local_cts_exclusion="All explicit ROM subtree root/branch/leaf output nets; synthesize only ordinary density-tap outputs",
            macro_box=[float(m[k]) for k in ("x0","y0","x1","y1")],
            root_desired_xy=[cx,base_y],
            side_roots={"left":[float(m["x0"])-7,base_y],"right":[float(m["x1"])+7,base_y]},
            sink_counts=dict(capture=256,address=12,CE=1,macro=1), leaves=leaves))
    legal_summary = None
    if args.occupancy and args.rows:
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
        from tools.die_trial.legal_sites import RowAllocator
        rowdata=[line.split("\t") for line in args.rows.read_text().splitlines()]
        box=[min(float(r[1]) for r in rowdata),min(float(r[2]) for r in rowdata),
             max(float(r[3]) for r in rowdata),max(float(r[4]) for r in rowdata)]
        blocks=[list(map(float,line.split("\t")[1:5])) for line in args.occupancy.read_text().splitlines()]
        for bank in banks:
            x0,y0,x1,y1=bank["macro_box"]
            blocks.append([x0-6,y0-6,x1+6,y1+6])
        allocator=RowAllocator(box,blocks,cell_size=(1.62,.27),column_pitch=1.62,
            row_pitch=.27,origin=(box[0],box[1]),bucket_um=10)
        nodes=[]
        for bank in banks:
            nodes.append((bank,"root_legal_xy",bank["root_desired_xy"]))
            for side,xy in bank["side_roots"].items():
                nodes.append((bank,f"{side}_legal_xy",xy))
            for leaf in bank["leaves"]:
                nodes.append((leaf,"legal_xy",leaf["desired_xy"]))
        rowmap={}
        for row in rowdata: rowmap.setdefault(round(float(row[2]),6),[]).append(row)
        largest=0
        for obj,key,xy in nodes:
            site,stats=allocator.allocate(xy,1,max_radius_um=12)
            obj[key]=site[0].tolist()
            lower_y=round(float(site[0][1])-.135,6)
            matching=[r for r in rowmap[lower_y] if float(r[1])-1e-7 <= site[0][0]-.81 and site[0][0]+.81 <= float(r[3])+1e-7]
            assert len(matching)==1, (key,site,matching)
            row=matching[0]
            obj[key.replace("_xy","_row")]=dict(name=row[0],orient=row[5],site_pitch_um=float(row[6])/1000,
                lower_left_xy=[float(site[0][0]-.81),lower_y])
            largest=max(largest,stats["max_distance_um"])
        legal_summary=dict(node_count=len(nodes),max_shift_um=largest,
            reserved_footprint_um=[1.62,.27],column_pitch_um=1.62,row_pitch_um=.27,
            macro_halo_um=6,existing_occupancy_preserved=True,
            limitation="Candidate rectangle check only; confirm actual site class/orientation and buffer master before CTS")
    immediate_loads=None
    if args.buf_lib:
        blib=args.buf_lib.read_text()
        part=blib[blib.index("cell (BUFx24_ASAP7_75t_R)"):]
        part=part[:part.index("\n  cell (",1)]
        pin=part[part.index("pin (A)"):]
        cin=float(re.search(r"\bcapacitance\s*:\s*([0-9.eE+-]+)",pin).group(1))
        immediate_loads=dict(master="BUFx24_ASAP7_75t_R",input_capacitance_ff=cin,
            root_children_ff=2*cin,source=str(args.buf_lib),wire_load="Not measured; actual branch RC required before sizing approval")
        for bank in banks:
            bank["immediate_side_loads_ff"]={side:sum(1 for n in bank["leaves"] if n["side"]==side)*cin for side in ("left","right")}
    args.out.write_text(json.dumps(dict(immediate_loads=immediate_loads,legal_candidate_summary=legal_summary,status="PROPOSED_NOT_LEGALIZED_NOT_TIMED", domain="clk",
        topology="common ROM root -> left/right buffered branches -> <=16-register or dedicated macro leaves",
        source_sites=str(args.sites), banks=banks,
        requirements=["Legalize all proposed buffer sites against actual rows and full current cell occupancy before review",
            "Keep all data/macro sites and all538 F6 relationships",
            "Size branch drivers against real input capacitance; left/right loads and branch counts differ; no symmetric-count assumption",
            "Integrate only with qualified shallow root; no independent deep macro tree",
            "Preserve short-chain unit groups and reset/other domains",
            "Actual TT/FF guide RC, macro-vs-bank skew, related pairs and boundary insertion arbitrate"]),indent=2)+"\n")


if __name__ == "__main__":
    main()
