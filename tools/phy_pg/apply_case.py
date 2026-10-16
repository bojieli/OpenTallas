"""Explicit opt-in generator hook for NEW cases only; modeled PHY access v1."""
import hashlib
import json
import os
from pathlib import Path
import re
try:
    from .assumed_access import build,m4_profile
    from .hbm_assumed_pg import add_hbm_pg
except ImportError:
    from assumed_access import build,m4_profile
    from hbm_assumed_pg import add_hbm_pg

NAMES=r'ot_q(?:fd_serdes_112g_x12|fd_ucie_x64|kvd_ucie_x64)_phy(?:_s\d+)?'

def patch_pdn(text, phy_instances, hbm_pg=False):
    # Remove exact instance ownership from old generic M8 grids. The PHY now
    # belongs solely to its declared M4/M5/M8 grid.
    lines=text.splitlines();out=['source /work/hbm_pg_interface.tcl','ot_hbm_pg::check'] if hbm_pg else [];skip_grid=None
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
        # Only rewrite the generated literal glob list. Never delete tokens
        # from arbitrary Tcl regexp expressions: an empty alternative or a
        # remaining anchor would broaden matching and could claim every cell.
        def class_globs(match):
            kept=[p for p in match[1].split()
                  if not re.fullmatch(r'(?:OT_PDN_BBOX_)?'+NAMES+r'\*?',p)]
            if hbm_pg and 'ot_hbm3e_phy*' in kept:
                kept+=['qkd_hbm3e_phy_pc','OT_PDN_BBOX_qkd_hbm3e_phy_pc']
            return 'foreach pp {'+' '.join(kept)+'}'
        line=re.sub(r'foreach pp \{([^}]*)\}',class_globs,line)
        if not line.lstrip().startswith('#') and re.search(NAMES,line):
            raise ValueError('unsupported PHY selector; explicit partition required: '+line)
        out.append(line)
    out+=['# Explicit ASSUMED PHY PG access contract v1; source-pinned candidate LEFs required.',
          'source /work/assumed_phy_pg_access.tcl','ot_assumed_phy_pg_grids']
    return '\n'.join(out)+'\n'

def apply(case):
    case=Path(case)
    if any(case.glob('*.odb')):raise ValueError('PHY access revision must precede any ODB generation; preserve frozen cases')
    if (case/'assumed_phy_pg_access.json').exists():raise ValueError('PHY access already applied')
    plans=[];receipts=[];masters=[];hbm_receipts=[]
    source_hbm=(case/'phy_ew.lef').read_text() if (case/'phy_ew.lef').exists() else ''
    for path in case.glob('*.lef'):
        text=path.read_text()
        def revised(match):
            if not m4_profile(match[0]):return match[0]
            out,rec=build(match[0]);rec['master']=match[1];rec['lef']=path.name
            receipts.append(rec);masters.append(match[1]);return out
        candidate=re.sub(r'(?ms)^MACRO ('+NAMES+r')\n.*?^END \1\s*$',revised,text)
        def hbm_revised(match):
            source=re.search(r'(?ms)^MACRO ot_hbm3e_phy\n.*?^END ot_hbm3e_phy\s*$',source_hbm)
            if not source:raise ValueError('missing source ot_hbm3e_phy power interface')
            out,rec=add_hbm_pg(match[0],source[0]);rec['master']='qkd_hbm3e_phy_pc';rec['lef']=path.name
            hbm_receipts.append(rec);return out
        candidate=re.sub(r'(?ms)^MACRO qkd_hbm3e_phy_pc\n.*?^END qkd_hbm3e_phy_pc\s*$',hbm_revised,candidate)
        if candidate!=text:plans.append((path,text,candidate))
    if not plans:raise ValueError('no source PHY abstracts found in new case')
    netlist=(case/'die.v').read_text()
    insts=[]
    for master in masters:insts+=re.findall(r'\b'+re.escape(master)+r'\s+(\w+)\s*\(',netlist)
    if not insts:raise ValueError('no actual modeled PHY instances in die.v')
    pdn=case/'pdn.tcl';old_pdn=pdn.read_text();new_pdn=patch_pdn(old_pdn,insts,bool(hbm_receipts))
    for p,old,new in plans:
        p.with_suffix('.historical-original.lef.txt').write_text(old);p.write_text(new)
    pdn.with_suffix('.historical-original.tcl.txt').write_text(old_pdn);pdn.write_text(new_pdn)
    if hbm_receipts:
        (case/'hbm_pg_interface.tcl').write_text(Path(__file__).with_name('hbm_pg_interface.tcl').read_text())
    # Manual fresh-case adoption must also update the conservative-OBS helper;
    # old snapshots would otherwise close the newly reserved access columns.
    bbox_source=Path(__file__).resolve().parents[1]/'qwen_kv_die/chain'
    for name in ['pdn_bbox_obs.py','pdn_bbox_obs.tcl']:
        dest=case/name
        if dest.exists():dest.with_suffix(dest.suffix+'.historical-original.txt').write_bytes(dest.read_bytes())
        dest.write_bytes((bbox_source/name).read_bytes())
    helper=Path(__file__).with_name('assumed_access.tcl')
    (case/'assumed_phy_pg_access.tcl').write_text(helper.read_text())
    hbm_insts=re.findall(r'\bqkd_hbm3e_phy_pc\s+(\w+)\s*\(',netlist) if hbm_receipts else []
    record=dict(hbm_pg=hbm_receipts,hbm_instances=hbm_insts,schema='opentallas.assumed-phy-pg-case.v1',status='ASSUMED_UNQUALIFIED',instances=insts,masters=receipts,
      helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),
      bbox_helper_sha256=hashlib.sha256((case/'pdn_bbox_obs.tcl').read_bytes()).hexdigest(),
      hbm_helper_sha256=hashlib.sha256((case/'hbm_pg_interface.tcl').read_bytes()).hexdigest() if hbm_receipts else None,area_delta_um2=0,
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
