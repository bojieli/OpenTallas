"""Recover the retained SFU cut boundary edges and parameterize its VM bridge.

This operates on the native composed cut, not LG_PATH (whose removed external
flops are already accounted for by the die lane table). No plan is adopted.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def contract(text):
    top = text.split('endmodule', 1)[0]
    rows = {}
    assignments = dict(re.findall(r'assign\s+(\w+\[\d+\])\s*=\s*(\w+);', top))
    for port, regnum, boundary, width, outgoing in [
        ('local_rq', 21, 'u_core_procdff_66916__Q', 136, True),
        ('local_wq', 22, 'u_core_procdff_66921__Q', 2248, True),
        ('local_rr', 23, 'u_core_procdff_66926__D', 2056, False),
        ('local_w_done', 24, 'u_core_procdff_66931__D', 8, False),
    ]:
        reg = f'g_compose_m{regnum}_q'
        q = re.search(r'assign\s*\{([^}]+)\}\s*=\s*'+reg+r';', top)
        d = re.search(r'else\s+'+reg+r'\s*<=\s*\{([^}]+)\};', top)
        bridge = re.search(r'\.'+port+r'\(\{([^}]+)\}\)', top)
        if not all((q, d, bridge)):
            raise ValueError(f'{port}: native FF/bridge structure absent')
        bits = lambda x: [b.strip() for b in x.split(',')]
        qb, db, bb = bits(q[1]), bits(d[1]), bits(bridge[1])
        expected = [f'{boundary}[{i}]' for i in reversed(range(width))]
        if len(qb) != width or len(db) != width or len(bb) != width:
            raise ValueError(f'{port}: width changed')
        if outgoing:
            if db != bb or [assignments.get(p) for p in expected] != qb:
                raise ValueError(f'{port}: output FF wiring changed')
        elif qb != bb or db != expected:
            raise ValueError(f'{port}: input FF wiring changed')
        rows[port] = {'bits': width, 'boundary_port': boundary, 'register': reg, 'retained_edges': 1}
    return {'read_k': 2, 'write_k': 2, 'paths': rows,
            'law': 'bridge_return = external_tap_plus_cut_boundary_loop + intrinsic_k'}


def parameterize(text):
    contract(text)
    old = 'module ot_hgi_sfu_sp2_ctl (' if 'module ot_hgi_sfu_sp2_ctl (' in text else 'module ot_hgi_sfu_core_split3__ctl ('
    if text.count(old) != 1:
        raise ValueError('expected one native ctl module')
    text = text.replace(old, 'module ot_hgi_sfu_sp2_ctl #(\n parameter integer SFU_READ_RETURN=145, SFU_WRITE_RETURN=142\n) (', 1)
    old = 'ot_hgi_sfu_vm_static_bridge #(.LWB(15), .READ_RETURN(145), .WRITE_RETURN(142)) m56'
    if old not in text:
        old = 'ot_hgi_sfu_vm_static_bridge #(.LWB(15), .READ_RETURN(88), .WRITE_RETURN(85)) m56'
    if text.count(old) != 1:
        raise ValueError('expected exact m56 bridge')
    return text.replace(old, 'ot_hgi_sfu_vm_static_bridge #(.LWB(15), .READ_RETURN(SFU_READ_RETURN), .WRITE_RETURN(SFU_WRITE_RETURN)) m56', 1)



def parameterize_fr(text):
    """Thread one native front read-tag delay without changing default91 form."""
    mods=re.findall(r'^module (\w+)',text,re.M)
    expected=['ot_hgi_sfu_split3_lane_core_fr_r91','ot_hdc_v41x_vec_lane_sp2_fr_r91',
              'ot_su12_lane_sp2_fr_r91','ot_su12_sfu_sp2_fr_r91']
    if set(mods)!=set(expected):
        raise ValueError('unexpected native front module set')
    for mod in mods:
        text=re.sub(r'\b'+mod+r'\b',mod.removesuffix('_r91')+'_param',text)
    changes=[
        ('module ot_hgi_sfu_split3_lane_core_fr_param #(parameter integer MUT = 0)',
         'module ot_hgi_sfu_split3_lane_core_fr_param #(parameter integer MUT = 0, SFU_RDX = 91)'),
        ('ot_su12_sfu_sp2_fr_param #(.MUT(MUT),',
         'ot_su12_sfu_sp2_fr_param #(.RDX(SFU_RDX), .MUT(MUT),'),
        ('module ot_su12_sfu_sp2_fr_param #(parameter integer MUT = 0,',
         'module ot_su12_sfu_sp2_fr_param #(parameter integer RDX = 91, parameter integer MUT = 0,'),
        ('ot_su12_lane_sp2_fr_param #(.MUT(MUT),',
         'ot_su12_lane_sp2_fr_param #(.RDX(RDX), .MUT(MUT),')]
    for old,new in changes:
        if text.count(old)!=1:
            raise ValueError('native front parameter path changed: '+old)
        text=text.replace(old,new,1)
    return text


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    text = a.source.read_text()
    receipt = contract(text)
    receipt.update(source=str(a.source), source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                   default_read_return=145, default_write_return=142,
                   parameter_names=['SFU_READ_RETURN', 'SFU_WRITE_RETURN'])
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out/'ot_hgi_sfu_sp2_ctl.sv').write_text(parameterize(text))
    (a.out/'bridge_contract.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
