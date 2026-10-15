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
