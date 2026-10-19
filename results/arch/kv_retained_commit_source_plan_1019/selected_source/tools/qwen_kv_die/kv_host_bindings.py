"""Real compact embedding endpoint binding; no unqualified view substitution."""
def land_emb_ifw_binding():
    return dict(module='qkd_land_emb_ifw', file='rtl/qwen_sys/split_20261014/qkd_land_emb_ifw.sv',
                ports=dict(ck=['ck'], rst_n=['rst_n'], emf=['emf','emf_cr'], emr=['emr','emr_cr'],
                           dno=['dno'], upi=['upi'], cri=['cri'], fi=['fi'], gfi=['gfi'], mf=['mf']),
                classed={'st':'by_design: stack strap, match gateway WS/WN/ES/EN index'})


def host_splitboot_binding(root):
    """All actual ports are mandatory; consumers must wire each named net.

    This is a source mapping, not permission to treat missing endpoint state
    as constants. Slot/root/pin qualification remains a separate requirement.
    """
    import re
    from pathlib import Path
    file='rtl/qwen_sys/host_20261013/qkd_host_splitboot_service.sv'
    text=re.sub(r'//[^\n]*', '', (Path(root)/file).read_text())
    header=text[text.index(' input wire[7:0]ck_phy'):text.index(');',text.index(' input wire[7:0]ck_phy'))]
    names=[]
    for part in header.split(','):
        names.append(re.findall(r'[A-Za-z_][A-Za-z_0-9]*',part.strip())[-1])
    ports={name:[name] for name in names}
    for physical,rtl in [('tk','local_tk'),('kst','local_kst')]:
        ports[physical]=ports.pop(rtl)
    return dict(module='qkd_host_splitboot_service',file=file,ports=ports,
                parameters=dict(ENABLE_SERVICE=1,ENABLE_TOKEN=1,ENABLE_NATIVE=1),classed={})


def pll_analog_binding():
    names=['refclk','por_n','locked','pll_WS','pll_WN','pll_ES','pll_EN','pll_c','pll_fwd',
           'pll_hbm_WS','pll_hbm_WN','pll_hbm_ES','pll_hbm_EN','pll_host','pll_ingest','pll_phy']
    return dict(module='qkd_pll_analog_model',file='rtl/qwen_sys/split_20261014/qkd_pll_analog_model.sv',
                ports={name:[name] for name in names},classed={},hard_phy_analog=True)


def gateway_splitboot_binding(base):
    import copy
    binding=copy.deepcopy(base)
    binding.update(module='qkd_embgw_splitboot',file='rtl/qwen_sys/split_20261014/qkd_embgw_splitboot.sv')
    return binding


def host_rank_services_binding(root):
    """Actual draft rank ABI, preserving every child clock entry separately.

    This deliberately does not replace the production die's HOST until the
    composed coordinator/peer transport and physical child placement exist.
    New inputs remain mandatory; no classed constants or missing-port aliases.
    """
    import json
    import sys
    from pathlib import Path
    root=Path(root)
    sys.path.insert(0,str(root/'tools/qwen_kv_die'))
    from die_port_bind_kv import header,evalw
    file='rtl/qwen_sys/host_integrated_20261014/qkd_host_rank_services.sv'
    params,raw=header((root/file).read_text(),'qkd_host_rank_services')
    if raw is None:
        raise ValueError('actual qkd_host_rank_services header is missing')
    inventory=json.loads((root/'results/arch/qwen_split_1014/host_bind_request_1014/die_wiring.json').read_text())['host_ports']
    new_core={'ck_program_rx','ck_program_loader','ck_boot','ck_boot_test'}
    families={'CORE833':'stream','CORE833.334':'stream','HOST1000':'host','INGEST1666.668':'ingest','PHY1043':'phy'}
    periods={'stream':833.334,'host':1000.,'ingest':1666.668,'phy':1043.}
    ports={p:[p] for p in raw};sliced={};clocks={}
    for p,(direction,width_expr) in raw.items():
        width=evalw(width_expr,params)
        if width is None:
            raise ValueError(f'actual HOST width unresolved: {p} {width_expr}')
        if not p.startswith('ck_'):
            continue
        label='CORE833.334' if p in new_core else inventory.get(p,{}).get('clock_family')
        if label not in families or direction!='input':
            raise ValueError(f'HOST clock lacks actual source family: {p} {label}')
        family=families[label]
        if width==1:
            clocks[p]=dict(rtl_port=p,bit=0,family=family,period_ps=periods[family])
        else:
            del ports[p]
            ports[p+'0']=[p]
            for bit in range(width):
                physical=p+str(bit)
                if bit:
                    sliced[physical]=p+'0'
                clocks[physical]=dict(rtl_port=p,bit=bit,family=family,period_ps=periods[family])
    # Full actual1043 FDI, with the same declared field order as the real PHY
    # binder. The HOST wire word is distinct from the548 KV/static payload.
    fdi=['phy_up','phy_tx_v','phy_tx_flit','phy_rx_v','phy_rx_flit']
    for p in fdi:
        if p not in ports:
            raise ValueError(f'missing actual HOST FDI pin {p}')
        del ports[p]
    ports['fdi']=fdi
    for physical,rtl in [('tk','local_tk'),('kst','local_kst')]:
        ports[physical]=ports.pop(rtl)
    return dict(module='qkd_host_rank_services',file=file,ports=ports,sliced=sliced,
                parameters=dict(ENABLE_SERVICE=1,ENABLE_TOKEN=1,ENABLE_NATIVE=1),classed={},clock_domains=clocks,
                integration_status='ACTUAL_DRAFT_RANK_SOURCE; full coordinator/peer transport and physical placement still required')
