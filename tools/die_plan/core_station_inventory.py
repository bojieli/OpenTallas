"""Actual native CS FF inventory for physical banks; no guessed or receipt-only flops."""
import argparse
import fnmatch
import hashlib
import json
import re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import kit_istations as KI

REG = re.compile(r"\breg\s+(?:\[(\d+)\s*:\s*(\d+)\]\s+)?([A-Za-z_$][\w$]*)\s*;")
NODE = re.compile(r"^g_(?P<leaf>u_lf\d*_)?(?:u_cst_(?P<cls>[a-z]+)|u_vp_g_h(?P<hdir>[io])g_(?P<group>\d+)_u_cst|u_vp_g_ln_(?P<lane>\d+)_u_cst_(?P<lcls>hi|ho))_gd_s_(?P<stage>\d+)_u_")


def native_banks(txt):
    """One record per actual driven native CS class/stage/group, including valid flops.

    Count reg declarations with procedural nonblocking drivers, not Q aliases or
    source-level dimensions that a flattened body does not realize.
    """
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", txt, flags=re.S)
    declarations = list(REG.finditer(code))
    groups = {}
    for index, declaration in enumerate(declarations):
        name = declaration.group(3)
        node = NODE.match(name)
        if not node:
            continue
        end = declarations[index+1].start() if index+1 < len(declarations) else len(code)
        body = code[declaration.end():end]
        if not re.search(r"\b"+re.escape(name)+r"\s*<=", body):
            raise ValueError("native CS register has no adjacent procedural driver: " + name)
        clock = re.search(r"always\s*@\(([^)]*)\)", body)
        if not clock or "posedge clk" not in clock.group(1):
            raise ValueError("native CS register is not on the released core clock: " + name)
        hi,lo = (int(declaration.group(1)),int(declaration.group(2))) if declaration.group(1) else (0,0)
        width=abs(hi-lo)+1
        prefix=node.group(0)
        cls=node.group("cls") or node.group("lcls") or "h"+node.group("hdir")
        bank=groups.setdefault(prefix,dict(id=prefix.rstrip("_"),cls=cls,stage=int(node.group("stage")),
            leaf=node.group("leaf"),lane=int(node.group("lane")) if node.group("lane") else None,
            group=int(node.group("group")) if node.group("group") else None,
            cell_glob="*"+prefix+"*",registers=[],rtl_scalars=[],flops=0,resettable_flops=0))
        resettable="negedge" in clock.group(1)
        bank["registers"].append(dict(name=name,msb=hi,lsb=lo,width=width,resettable=resettable))
        bank["rtl_scalars"] += [name+f"[{bit}]" for bit in range(min(hi,lo),max(hi,lo)+1)]
        bank["flops"] += width
        bank["resettable_flops"] += width if resettable else 0
    return sorted(groups.values(), key=lambda b:b["id"])


def inventory(tn,t,txt):
    """Add existing plan-centroid/glob and link endpoints to actual native banks.

    Missing planned stages remain explicit (never fabricated). Derived M stages
    may be unsited: geometry must give them an actual bank before adoption.
    """
    banks=native_banks(txt)
    native_depths=KI.native_params(txt)
    group_size=native_depths.get("CS_H_G",4)
    lines=[];receipt=[]
    # Inventory generation never consumes the geometry it is preparing.
    clean=json.loads(json.dumps(t));clean.get("clock",{}).pop("soft_reg_banks",None)
    KI.core_stations(clean,txt,False,(4,0,0),lines,receipt)
    sites=[]
    for line in lines:
        m=re.fullmatch(r"is_place \{([^}]+)\} ([\d.eE+-]+) ([\d.eE+-]+) cst:(\w+)",line)
        if m:sites.append((m.group(1),[float(m.group(2)),float(m.group(3))],m.group(4)))
    for bank in banks:
        cls = bank["cls"]
        total = native_depths.get("CS_"+cls.upper()+"_D")
        if total is None:
            total = max(b["stage"] for b in banks if b["cls"] == cls)+1
        shared = native_depths.get("CS_"+cls.upper()+"_GS", 0)
        # HI: shared source stages then lane stages; HO: lane stages then shared.
        # These are physical pipeline ordinals, while stage remains local generate index.
        offset = shared if cls == "hi" and bank["lane"] is not None else 0
        if cls == "ho" and bank["group"] is not None:
            offset = total-shared
        bank["pipeline_stage"] = offset+bank["stage"]
        bank["total_depth"] = total
        bank["shared_stages"] = shared if cls in {"hi", "ho"} else None
        matches=[(pat,xy) for pat,xy,_ in sites if all(fnmatch.fnmatchcase(r["name"],pat) for r in bank["registers"])]
        if len(matches)>1:raise ValueError("ambiguous planned CS bank site: "+bank["id"])
        bank["centroid_um"]=matches[0][1] if matches else None
        if matches:bank["cell_glob"]=matches[0][0]
        links=[]
        for row in t.get("internal_stations",[]):
            if str(row.get("conn","")).startswith("bus:"):continue
            cls,fwd,lane=KI.core_class(row)
            if cls!=bank["cls"]:continue
            if bank["lane"] is not None and lane!=bank["lane"]:continue
            if bank["group"] is not None and (lane is None or lane//group_size!=bank["group"]):continue
            links.append(dict(launch=row.get("launch"),capture=row.get("capture"),rtl_forward=fwd,
                              bits=row.get("bits",1),planned_stages=len(row.get("regs_um",[]))))
        bank["links"]=links
        bank["realization"]="native_driven"
    missing=[dict(cell_glob=pat,centroid_um=xy,cls=cls,realization="planned_without_native")
             for pat,xy,cls in sites if not any(any(fnmatch.fnmatchcase(r["name"],pat) for r in b["registers"]) for b in banks)]
    sha=hashlib.sha256(txt.encode()).hexdigest()
    for bank in banks:bank["source"]="nativeRTL:"+sha+"#"+bank["id"]
    return dict(schema="opentallas.native_cs_inventory.v1",type=tn,source_rtl_sha256=sha,
                native_depths=native_depths,banks=banks,missing_planned=missing,
                total_flops=sum(b["flops"] for b in banks),receipt=receipt)


def main():
    p=argparse.ArgumentParser();p.add_argument("plan",type=Path);p.add_argument("type");p.add_argument("rtl",type=Path);p.add_argument("out",type=Path);a=p.parse_args()
    t=json.loads(a.plan.read_text())["partition_types"][a.type]
    out=inventory(a.type,t,a.rtl.read_text());a.out.write_text(json.dumps(out,indent=1)+"\n")
    print("CS inventory",a.type,"banks",len(out["banks"]),"flops",out["total_flops"],"unrealized planned banks",len(out["missing_planned"]))

if __name__=="__main__":main()
