"""Explicit opt-in generator hook for NEW cases only; modeled PHY access v1."""
import hashlib
import json
import os
from pathlib import Path
import re
try:
    from .assumed_access import build
except ImportError:
    from assumed_access import build

NAMES=r'ot_q(?:fd_serdes_112g_x12|fd_ucie_x64|kvd_ucie_x64)_phy(?:_s\d+)?'

def patch_pdn(text, phy_instances):
    # Remove exact instance ownership from old generic M8 grids. The PHY now
    # belongs solely to its declared M4/M5/M8 grid.
    lines=text.splitlines();out=[];skip_grid=None
    for line in lines:
        if line.startswith('define_pdn_grid -macro'):
            match=re.search(r'-instances \{([^}]*)\}',line)
            if match:
                pats=match[1].split();kept=[]
                for p in pats:
                    matched=[n for n in phy_instances if re.fullmatch(p,n)]
                    if matched:
                        if len(matched)!=1 or p not in [matched[0],'^'+matched[0]+'$']:
                            raise ValueError('broad PHY instance grid requires explicit partition: '+p)
                    else:kept.append(p)
                if not kept:
                    skip_grid=re.search(r'-name \{?([^\s}]+)',line)[1];continue
                line=line[:match.start(1)]+' '.join(kept)+line[match.end(1):]
        if skip_grid and re.match(r'add_pdn_\w+ -grid \{?'+re.escape(skip_grid)+r'\}?(?: |$)',line):continue
        # KV's class-selected HBM PHY grid must keep only the HBM masters.
        line=re.sub(r'(?:OT_PDN_BBOX_)?'+NAMES+r'\*? ?', '', line)
        out.append(line)
    out+=['# Explicit ASSUMED PHY PG access contract v1; source-pinned candidate LEFs required.',
          'source /work/assumed_phy_pg_access.tcl','ot_assumed_phy_pg_grids']
    return '\n'.join(out)+'\n'

def apply(case):
    case=Path(case)
    if any(case.glob('*.odb')):raise ValueError('PHY access revision must precede any ODB generation; preserve frozen cases')
    if (case/'assumed_phy_pg_access.json').exists():raise ValueError('PHY access already applied')
    plans=[];receipts=[];masters=[]
    for path in case.glob('*.lef'):
        text=path.read_text()
        def revised(match):
            out,rec=build(match[0]);rec['master']=match[1];rec['lef']=path.name
            receipts.append(rec);masters.append(match[1]);return out
        candidate=re.sub(r'(?ms)^MACRO ('+NAMES+r')\n.*?^END \1\s*$',revised,text)
        if candidate!=text:plans.append((path,text,candidate))
    if not plans:raise ValueError('no source PHY abstracts found in new case')
    netlist=(case/'die.v').read_text()
    insts=[]
    for master in masters:insts+=re.findall(r'\b'+re.escape(master)+r'\s+(\w+)\s*\(',netlist)
    if not insts:raise ValueError('no actual modeled PHY instances in die.v')
    pdn=case/'pdn.tcl';old_pdn=pdn.read_text();new_pdn=patch_pdn(old_pdn,insts)
    for p,old,new in plans:
        p.with_suffix('.historical-original.lef.txt').write_text(old);p.write_text(new)
    pdn.with_suffix('.historical-original.tcl.txt').write_text(old_pdn);pdn.write_text(new_pdn)
    helper=Path(__file__).with_name('assumed_access.tcl')
    (case/'assumed_phy_pg_access.tcl').write_text(helper.read_text())
    record=dict(schema='opentallas.assumed-phy-pg-case.v1',status='ASSUMED_UNQUALIFIED',instances=insts,masters=receipts,
      helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),area_delta_um2=0,
      qualification='Fixture proves declared geometry only; full die connectivity/short/routing/IR checks still required; no foundry IP claim.')
    (case/'assumed_phy_pg_access.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

def maybe_apply(case):
    if os.environ.get('OT_ASSUMED_PHY_PG_ACCESS')=='1':return apply(case)
    return None

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('case',type=Path)
    ap.add_argument('--ack-assumed-phy-contract',action='store_true',required=True)
    args=ap.parse_args()
    print(json.dumps(apply(args.case),indent=2))
