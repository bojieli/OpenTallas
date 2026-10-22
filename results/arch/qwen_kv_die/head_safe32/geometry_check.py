"""KV-BIND12 head safe32: geometry-only die build (no relays) + kv_expand-style leaf placement of both heads."""
import json, os, sys, itertools
sys.path.insert(0, 'tools'); sys.path.insert(0, 'tools/qwen_kv_die')
import kv_die as K
K.HOST_V14.update(on=True, north=True, trees=True); K.V143['on'] = True
K._set_geometry(True, reserve_native_astk=True)
K._relays = lambda m: None      # geometry-only inspection before relay allocation; never a gate / bind
m = K._build(kv_wq_leaves=True, kv_wq_binary=True, kv_wq_leaf_s=True, kv_wq_head=False, kv_wq_wide=True, kv_wq_mirror=True, split=True)
d = m['die']
heads = [i for i in m['insts'] if i.master in ('qkd_rhead', 'qkd_rhead_ft')]
ov = []
ins = m['insts']
for a, b in itertools.combinations(ins, 2):
    if min(a.x + a.w, b.x + b.w) - max(a.x, b.x) > 0.01 and min(a.y + a.h, b.y + b.h) - max(a.y, b.y) > 0.01:
        ov.append((a.name, b.name))
outside = [i.name for i in ins if i.x < -0.01 or i.y < -0.01 or i.x + i.w > d['w'] + 0.01 or i.y + i.h > d['h'] + 0.01]
rep = dict(tag=os.environ.get('TAG'), die_um=[d['w'], d['h']], die_mm2=round(d['w'] * d['h'] / 1e6, 3),
           head=K.HEAD, head_ft=K.SPLIT_HEAD_FT, head_plans=[K.HEAD_R4_PLAN, K.HEAD_FT_PLAN], eng_h=K.ENG_H, tile_y=K.TILE_Y,
           v143_ft=K.V143_FT, grp_y=m['geo'].get('grp_y'), stack_pitch=m['geo'].get('stack_pitch'), stack_h=m['geo'].get('stack_h'),
           seam_um={s_: round(m['geo']['grp_y']['W' + 'N'][0] - m['geo']['grp_y']['W' + 'S'][1], 3) for s_ in ('W',)}, n_heads=len(heads), inst_overlaps=len(ov), inst_overlap_sample=ov[:10], outside=outside[:10])
# kv_expand leaf placement for one head of each master (yosys elaborate of the bound parent, its plan, its checks)
try:
    import kv_expand as E
    leaf = {}
    for mod, vd in E.VIEWS.items():
        lef = E.ROOT / vd / f'{mod}.lef'
        if lef.exists():
            nm, blk, sz, ports = E.lef_macro(lef)
            for r in ports.values():
                r['w'] = 1 if r['bits'] == {None} else max(r['bits']) + 1
            leaf[nm] = dict(view=vd, lef=blk, size=sz, ports=ports)
    FR = E.frames()
    for mst in ('qkd_rhead', 'qkd_rhead_ft'):
        h = next(i for i in heads if i.master == mst)
        fw, fh = h.w, h.h
        b = K.BINDINGS[mst]
        J = E.elaborate(b['module'], b['file'], leaf, b.get('parameters'))
        rects, errs = [], []
        for cname, c in J['cells'].items():
            cell = cname.lstrip('\\'); ct = E.ALIAS.get(E.base_type(c['type']), E.base_type(c['type']))
            if ct not in leaf:
                errs.append(f'{cell} ({ct}) has no closed view'); continue
            cx, cy, co = FR[mst]['plan'](cell, fw, fh)
            w_, h_ = leaf[ct]['size']
            if min(cx, cy) < -0.001 or cx + w_ > fw + 0.05 or cy + h_ > fh + 0.05:
                errs.append(f'{h.name}/{cell}: closed leaf outside contract frame')
            r = (cell, cx, cy, cx + w_, cy + h_)
            for o in rects:
                if min(r[3], o[3]) - max(r[1], o[1]) > 0.001 and min(r[4], o[4]) - max(r[2], o[2]) > 0.001:
                    errs.append(f'{h.name}: overlapping closed leaves {cell} / {o[0]}')
            rects.append(r)
        rep[f'expand_{mst}'] = dict(inst=h.name, module=b['module'], frame=[fw, fh], leaves=len(rects), errors=errs[:20], n_errors=len(errs))
except Exception as e:
    import traceback; rep['expand_error'] = traceback.format_exc()[-1500:]
print(json.dumps(rep, indent=1, default=str))
