"""Carry production frame images into the exact runtime names selected by one bound die."""
from pathlib import Path
import re
import tempfile
import frame_cfg_identity as C
import frame_qx_identity as Q


def alias_material(material,master,frame,active_pairs,selectors,root):
    match=re.fullmatch(r'(col_h(?:9|10))_l4_lp_asb_(x|nx)',master)
    if not match:raise ValueError('bound image aliases need an exact as-built frame master: '+master)
    if not re.fullmatch(r'[A-Za-z_]\w*',frame):raise ValueError('unsafe frame image identity')
    if len(active_pairs)!=len(set(active_pairs)) or any(type(i)is not int or i<0 for i in active_pairs):
        raise ValueError('invalid active frame QX pairs')
    root=Path(root);base,var=match.groups()
    parent=C.bind_elab.module_body(root/f'rtl/dsrom_sys/s81_dv/frame_lp/{base}_l4_lp.sv',base+'_l4_lp')
    bands=[];known=set()
    for b in range(3):
        module=f'{base}_l4_lp_r{b}'+('_nx'if b==0 and var=='nx'else'')
        body=C.bind_elab.module_body(root/f'rtl/dsrom_sys/s81_dv/frame_lp/plan/{base}_l4_lp_plan_kit.sv',module)
        known.update(Q.prove(parent,body));bands.append((f'u_r{b}',body))
    active={'u_e'+str(i)for i in active_pairs}
    if not active<=known:raise ValueError('active QX pair absent from exact split frame: '+str(sorted(active-known)))
    report={'instance_path_params':selectors}
    with tempfile.TemporaryDirectory(prefix='ot-bound-frame-images-')as tmp:
        tmp=Path(tmp)
        for name,text in material.items():
            if Path(name).name!=name:raise ValueError('frame material must use flat image names')
            (tmp/name).write_text(text)
        aliases=[]
        for band,body in bands:
            aliases+=C.emit_bound_aliases(parent,body,frame,band,report,tmp)
            aliases+=Q.emit_bound_aliases(parent,body,frame,band,report,tmp,active_names=active)
        out=dict(material)
        for row in aliases:
            name=row['alias'];text=(tmp/name).read_text()
            if name in out and out[name]!=text:raise ValueError('conflicting bound frame image material: '+name)
            out[name]=text
    return out
