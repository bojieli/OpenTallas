#!/bin/bash
# Source/file completeness parse of a Qwen compute-die GEN (LEAD-QW2 10-21, owner: required before EVERY GEN launch):
# yosys `hierarchy -check` over the die top and the full RTL file closure of every die master, resolved from the GEN's
# own source tree exactly as the strict bind resolves it (tools/die_port_bind.py --elab-out, same files / straps /
# hard-macro models as tools/qwen_split/port_bind_compute.sh).  Parse + hierarchy only, no synthesis.
# usage: die_hier_check.sh GEN_DIR [DIE_V]    (run from anywhere; GEN_DIR holds src/ and out/case/die.v)
#   exit 0 = HIER_CHECK PASS (every referenced module defined); writes GEN_DIR/hier_check/{die_top.f,hier.ys,yosys.log,verdict.txt}
set -u
S=$(readlink -f "${1:?GEN dir}"); D=$(readlink -f "${2:-$S/out/case/die.v}"); R=$S/src; O=$S/hier_check
[ -e "$D" ] || { echo "HIER_CHECK FAIL no die.v ($D)"; exit 2; }
mkdir -p $O
cd $R || exit 2
if [ "${HC_REUSE:-0}" = 1 ] && [ -s $O/die_top.f ] && [ -s $O/port_bind_elab.json ]; then :; else
python3 tools/qwen_split/gen_relay_rtl.py $D $O/die_glue.sv > $O/die_glue.json || { echo "HIER_CHECK FAIL glue"; exit 3; }
T45=; grep -q 'ck_fa0' $D && T45="--rtl-file $R/rtl/physical/qfd_tile_rp2_45_slots.sv --rtl-file $R/rtl/physical/qfd_tile_nk_rp2_45.sv --rtl-file $R/rtl/physical/qfd_tile_nl_rp2_45.sv"
UV=${OT_PORT_BIND_UCIE_VIEW:-physical/qwen_missing_phy/nface_tall_1017/ot_qfd_ucie_x64_phy}
ST=${OT_PORT_BIND_STRAPS:-$R/results/arch/qwen_split_compute_1014/q_slice_1017/straps_dv2f18mu.json}
python3 tools/die_port_bind.py $D $T45 --rtl-file $O/die_glue.sv --rtl-file $R/rtl/qwen_split/qfd_link_slots.sv \
  --rtl-file $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv \
  --rtl-file $R/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv \
  --rtl-file $R/$UV/ot_qfd_ucie_x64_phy_bb.v \
  --rtl-file $R/physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy_s597/ot_qfd_serdes_112g_x12_phy_s597_bb.v \
  --allow-model qfd_ckbump --allow-model qfd_sigbump --allow-model ot_qkvd_ucie_x64_phy --allow-model ot_qkvd_ucie_x64_phy_model \
  --allow-model ot_qfd_ucie_x64_phy --allow-model ot_qfd_serdes_112g_x12_phy_s597 \
  --lib-root $R/physical/asap7_memory_macros --define OT_QFD_UP4_CK_ENTRIES --ref-tile-prefer --strap-file $ST \
  --elab-out $O --out $O/port_bind_elab.json > $O/port_bind_elab.txt 2>&1
fi
python3 - $O <<'PY' || exit 4
import json, sys, glob, os
o = sys.argv[1]
fl = [l.strip() for l in open(o + '/die_top.f') if l.strip()]
inc = [l[8:] for l in fl if l.startswith('+incdir+')]
dfn = [l[8:] for l in fl if l.startswith('+define+')]
src = [l for l in fl if not l.startswith('+')]
el = json.load(open(o + '/port_bind_elab.json')).get('elab', {})
# memory macros: behavioural/blackbox Verilog of the asap7 macro set when the closure names them; liberty as -lib cells
libs = sorted(set(glob.glob(os.getcwd() + '/physical/asap7_memory_macros/**/*.lib', recursive=True)))
# QKO-QDIE 10-21: ASAP7 standard cells instantiated by RTL (ot_hdc_cg -> ICGx1_ASAP7_75t_R) as liberty cells, TT corner
SCL = os.environ.get('ASAP7_LIB_DIR', os.path.expanduser('~/.local/opentallas-pdk-asap7/lib/NLDM'))
libs += sorted(p for p in glob.glob(SCL + '/asap7sc7p5t_*_TT_nldm*.lib') if not p.endswith('.gz'))
with open(o + '/hier.ys', 'w') as f:
    flags = ' '.join([f'-I{d}' for d in inc] + [f'-D{d}' for d in dfn])
    for p in libs:
        f.write(f'read_liberty -lib -ignore_miss_func {p}\n')
    # QKO-QDIE 10-21: parse the closure as the strict binder resolved it.  (1) a module defined in several closure
    # files (die_glue.sv re-emits qfd_rst_rep / qfd_rst_rep_p8 that physical/qwen_rst_rep also defines) is read only
    # from the file the binder selected (port_bind_elab masters[m].rtl); (2) Yosys 0.52 has no typed `parameter
    # string`: an untyped parameter with the same string default is the same elaboration.  Copies under $O/compat.
    import re
    mrtl = {k: v.get('rtl') for k, v in json.load(open(o + '/port_bind_elab.json')).get('masters', {}).items() if isinstance(v, dict)}
    MOD = re.compile(r'^[ \t]*module[ \t]+([A-Za-z_][\w$]*)', re.M)
    # (3) a closure module with interface-differing variants (binder child_closure.variant_children, e.g. ot_hdc_qadd: the
    #     ref-tile copy of ot_coll_fold_slice_m5 has no parameter L that qfd_dv_scalar sets) parses from the canonical
    #     rtl/hdc | rtl/lib definition, which is the interface superset (L = 3 default = the fast adder, same ports)
    pref = {}
    for mn, vc in (json.load(open(o + '/port_bind_elab.json')).get('child_closure', {}).get('variant_children') or {}).items():
        cands = [p for p in [vc.get('chosen')] + list(vc.get('iface_differ') or []) if p and '/physical/ref_tile/' not in p and re.search(r'/src/rtl/(hdc|lib)/', p)]
        if vc.get('iface_differ') and cands and cands[0] != vc.get('chosen'):
            pref[mn] = cands[0]
            if cands[0] not in src:
                src.append(cands[0])
    txt = {p: open(p, errors='replace').read() for p in src}
    defs = {}
    for p in src:
        for mn in MOD.findall(txt[p]):
            defs.setdefault(mn, []).append(p)
    drop = {}
    for mn, ps in defs.items():
        if len(set(ps)) > 1:
            keep = [pref[mn]] if mn in pref else ([p for p in ps if mrtl.get(mn) and p.endswith('/' + mrtl[mn])] or [ps[-1]])
            for p in set(ps) - {keep[0]}:
                drop.setdefault(p, set()).add(mn)
    os.makedirs(o + '/compat', exist_ok=True)
    ncompat = 0
    for j, p in enumerate(src):
        t = txt[p]; t2 = t
        for mn in drop.get(p, ()):
            t2 = re.sub(r'^[ \t]*module[ \t]+' + re.escape(mn) + r'\b.*?^[ \t]*endmodule\b[^\n]*', '', t2, flags=re.M | re.S)
        t2 = re.sub(r'\b(parameter|localparam)\s+string\b', r'\1', t2)
        if t2 != t:
            q = f'{o}/compat/{j}_{os.path.basename(p)}'
            open(q, 'w').write(t2); p = q; ncompat += 1
        f.write(f'read_verilog -sv -defer {flags} {p}\n')
    print('HIER_COMPAT variant_pref', {k: v.split('/src/')[-1] for k, v in pref.items()}, 'files', ncompat, 'dup_defs', {mn: len(set(ps)) for mn, ps in defs.items() if len(set(ps)) > 1})
    f.write('hierarchy -check -top qfd_die\n')
json.dump(dict(files=len(src), libs=len(libs), elab_unresolved=el.get('unresolved_modules', [])), open(o + '/closure.json', 'w'))
print('HIER_FILES', len(src), 'libs', len(libs), 'elab_unresolved', len(el.get('unresolved_modules', [])))
PY
yosys -q -l $O/yosys.log -s $O/hier.ys > /dev/null 2>&1; rc=$?
miss=$(grep -cE "is not part of the design|referenced in module .* is not" $O/yosys.log)
err=$(grep -m1 -E "^ERROR" $O/yosys.log | cut -c1-300)
if [ $rc -eq 0 ]; then v="HIER_CHECK PASS files=$(python3 -c "import json;print(json.load(open('$O/closure.json'))['files'])") missing=0"
else v="HIER_CHECK FAIL rc=$rc missing_refs=$miss first: $err"; fi
echo "$v" | tee $O/verdict.txt
[ $rc -eq 0 ]
