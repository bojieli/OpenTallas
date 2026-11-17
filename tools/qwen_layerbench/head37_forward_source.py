#!/usr/bin/env python3
"""Prepare default-off forwarding overlays for the actual selected QC STM sources.

Only the two native STM module bodies change. Existing source files and binding
recipes are never modified. Review and select the emitted complete sources as
one tuple with the paired CTLM event; no global HEAD_STAGE37 adoption is made.
"""
import argparse,hashlib,json,re
from pathlib import Path

TARGETS=[('rtl/qwen_dv/s5/s6/qfd_dv_s6_leaves.sv','qfd_dv_s6_stm'),
         ('rtl/qwen_dv/s5/s8/qfd_dv_s8_ce.sv','qfd_dv_s6_stm_se0')]
def digest(data):return hashlib.sha256(data).hexdigest()

def forward(text,master):
    match=re.search(r'^module '+re.escape(master)+r'\b.*?^endmodule\b',text,re.M|re.S)
    if not match:raise ValueError(f'actual selected module absent {master}')
    old=match[0]
    if 'HEAD_STAGE37' in old:raise ValueError('HEAD37 forwarding already present; inspect selected source')
    if old.count('parameter integer TSLICE = 0')!=1:raise ValueError('actual TSLICE declaration changed')
    new=old.replace('parameter integer TSLICE = 0','parameter integer TSLICE = 0, parameter integer HEAD_STAGE37 = 0',1)
    t=re.search(r'    qfd_dv_slice_tload\n.*?        u_tload\(',new,re.S)
    if not t:raise ValueError('actual loader instance changed')
    before=t[0]
    if before.count('.LOCAL_JOIN(1))')!=2 or '`elsif OT_QC_TLOADCAP' not in before:
        raise ValueError('actual selected J loader profile branches changed')
    after=before.replace('.LOCAL_JOIN(1))','.LOCAL_JOIN(1),.HEAD_STAGE37(HEAD_STAGE37))')
    after=after.replace('`endif\n        u_tload(', '`else\n        #(.HEAD_STAGE37(HEAD_STAGE37))\n`endif\n        u_tload(',1)
    new=new[:t.start()]+after+new[t.end():]
    # Ports, publication registers, reset and stream path are preserved verbatim.
    if old.split(') (',1)[1].split(');',1)[0]!=new.split(') (',1)[1].split(');',1)[0]:
        raise AssertionError('native wrapper port ABI changed')
    restored=new.replace(', parameter integer HEAD_STAGE37 = 0','').replace(',.HEAD_STAGE37(HEAD_STAGE37)','')
    restored=restored.replace('`else\n        #(.HEAD_STAGE37(HEAD_STAGE37))\n`endif\n        u_tload(', '`endif\n        u_tload(')
    if restored!=old:raise AssertionError('forwarding overlay changed unrelated actual source')
    output=text[:match.start()]+new+text[match.end():]
    return output,dict(master=master,HEAD_STAGE37_default=0,added_cycles=0,
        before_module_sha256=digest(old.encode()),after_module_sha256=digest(new.encode()),
        unchanged_ports=True,unchanged_reset_and_publication=True,default_off_source_normalization_exact=True,
        branches=['OT_S6_SIM C1/LOCAL1','OT_QC_TLOADCAP C1/LOCAL1','production-default C0/LOCAL0'],
        enable_profile='C0/LOCAL0 only: existing native HEAD37 guard rejects C1/LOCAL1')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    rows=[]
    for rel,master in TARGETS:
        p=a.source_root/rel;raw=p.read_bytes();modified,info=forward(raw.decode(),master)
        out=a.out/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(modified)
        rows.append(dict(info,source=str(p),relative_path=rel,before_sha256=digest(raw),after_sha256=digest(out.read_bytes())))
    result=dict(schema='opentallas.qc-head37-stm-forwarding.v1',status='DEFAULT_OFF_SOURCE_PROPOSAL',
        selected_bindings_changed=False,global_HEAD_STAGE37_enabled=False,modules=rows,
        paired_CTLM='qfd_dv_cmd_cal_mu_head37 HEAD_STAGE37 must match all selected loader flags',
        mask_identity='exact48 per-instance mask hashes required on enable; numeric TSLICE unchanged',
        scope='Actual selected-source forwarding only. Physical closure and complete TT source-parent selection remain separate.')
    (a.out/'forwarding.json').write_text(json.dumps(result,indent=2)+'\n')
    print('HEAD37_FORWARD_SOURCE_READY defaults0 modules2 binding_unchanged')
if __name__=='__main__':main()
