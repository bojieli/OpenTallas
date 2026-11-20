"""Exact declared form-A path projection for the two PVSO bound cuts.

The original svc_formA_sites.py generator omitted one `u` in these cuts.
Only physical identities change; the plan's logical names and geometry remain.
This declares 31 sites, including the eight source-unused sites: it does not waive
missing live macros or extend the separate r369 optimized-bank policy.
"""
import re

CASES = {'svc_hi_dsdv_svc_pvso_entry__t1': '05',
         'svc_hi_dsdv_svc_pvso_entry__t2': '11'}
SMALL = 'ot_sram_1r1w_32x128_m1_r0c0'
BIG = 'ot_sram_1r1w_160x256_m1_r0c0'

def specifications(type_name, heads=16, scan_read_pipe=False):
    r = CASES[type_name]
    old = f'u_bound.u_u_rsv_{r}_u_u_'
    actual = f'u_u_rsv_{r}_u_u_u_'
    ab = f'u_rsv_{r}.u.u.u_'
    specs = []
    for a in range(3):
        for c in range(2):
            suffix = f'att_g_wqm_{a}_g_pc_{c}_u_wq_mem'
            for g in range(3):
                specs.append((old+suffix+f'.g_m[{g}].g_32.u_mem', actual+suffix,
                              ab+f'att.g_wqm[{a}].g_pc[{c}].u_wq_mem',
                              'dsdv_svc_mem_ar', {'AW':3,'DEPTH':8,'W':341},
                              f'.g_m[{g}].g_32.u_mem', SMALL))
    for g in range(4):
        specs.append((old+f'att_u_qmem_mem.g_m[{g}].g_32.u_mem', actual+'att_u_qmem_mem',
                      ab+'att.u_qmem_mem', 'dsdv_svc_mem_ar', {'AW':4,'DEPTH':heads,'W':512},
                      f'.g_m[{g}].g_32.u_mem', SMALL))
    scan_module = 'dsdv_svc_mem_lr' if scan_read_pipe else 'dsdv_svc_mem_la'
    for b in range(2):
        for g in range(4):
            specs.append((old+f'att_u_sw_mem.g_b[{b}].g_m[{g}].u_mem', actual+'att_u_sw_mem',
                          ab+'att.u_sw_mem', scan_module, {'AW':5,'W':512},
                          f'.g_b[{b}].g_m[{g}].u_mem', SMALL))
    specs.append((old+'pbuf_mem.g_m[0].g_160.u_mem', actual+'pbuf_mem', ab+'pbuf_mem',
                  'dsdv_svc_mem_ar', {'AW':6,'DEPTH':40,'W':256}, '.g_m[0].g_160.u_mem', BIG))
    return specs


def resolve(type_name, t, bound_text):
    """Return all 31 exact declared path rows, or fail before projecting any.

    Evidence is the canonical bound netlist's unique as-built leaf declaration,
    its actual instance/module and dimensions. No guessed prefix, alternate cut,
    missing leaf, duplicate declaration or partial 31-site contract is accepted.
    """
    if type_name not in CASES:
        return []
    defines = {d.removeprefix("-D").partition("=")[0] for d in t.get("verilog_defines", [])}
    specs = specifications(type_name, heads=8 if "OT_SVC_H8" in defines else 16,
                           scan_read_pipe="OT_SVC_ATT_RDPIPE" in defines)
    by = {}
    for c in t.get('contents', []):
        by.setdefault(c['inst'], []).append(c)
    rows = []
    for old, actual, ab, module, params, tail, master in specs:
        entries = by.get(old, [])
        if len(entries) != 1 or entries[0].get('module') != master:
            raise ValueError(f'PVSO form-A requires unique declared site/master: {old}')
        c = entries[0]
        physical = 'u_bound.'+actual+tail
        if c.get('physical_inst', physical) != physical or c.get('physical_master', master) != master:
            raise ValueError(f'PVSO form-A conflicts with existing physical identity: {old}')
        # Match the exact comment and declaration together; duplicate same-path
        # comments remain ambiguous even if their strings happen to agree.
        pat = (r'(?m)^[ \t]*// as-built '+re.escape(ab)+r'[ \t]*\n[ \t]*'
               r'(\w+)[ \t]*#\(([^;]*?)\)[ \t]+(\w+)[ \t]*\(')
        hits = list(re.finditer(pat, bound_text))
        if len(hits) != 1 or hits[0].group(1) != module or hits[0].group(3) != actual:
            raise ValueError(f'PVSO form-A missing/ambiguous actual bound leaf: {ab}')
        text = hits[0].group(2)
        for key, value in params.items():
            values = re.findall(r'\.'+key+r'\s*\(\s*(\d+)\s*\)', text)
            if values != [str(value)]:
                raise ValueError(f'PVSO form-A actual shape mismatch: {ab}.{key}')
        rows.append(dict(inst=old, physical_inst=physical, physical_master=master,
                         asbuilt=ab, rule='exact PVSO canonical bound leaf + dimensions',
                         source_physical_inst=c.get('physical_inst')))
    return rows
