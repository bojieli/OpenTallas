#!/usr/bin/env python3
"""Private opt-in ROWS256 physical LP profile; shared generator defaults unchanged."""
import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import lp
for name in sys.argv[1:]:
    path=lp.ROOT/f'results/arch/landed_parent_1018/collq/spec_{name}_ars256.json'
    spec=json.loads(path.read_text());spec['_spec_path']=str(path.relative_to(lp.ROOT))
    spec['defines']=list(dict.fromkeys(spec.get('defines',[])+['OT_COLL_LP_PUB32']))
    spec['child_sources']=list(dict.fromkeys(spec['child_sources']+['rtl/common/landed_parent/ot_coll_lp_native_helpers.sv','rtl/common/landed_parent/ot_pl_land_n32.sv']))
    path.write_text(json.dumps(spec,indent=1)+'\n')
    lp.gen(spec)
    parent=lp.Parent(spec);plan=parent.plan()
    top=spec['top_lp'];out=lp.ROOT/spec['out_dir'];rtlpath=out/(top+'.sv');rtl=rtlpath.read_text()
    # HBMc/COLL-LP 10-22 (safe24 census): ring writers on the existing n32 kept-selector local writer (12 data bits per
    # kept one-hot copy), ariter partial products in kept leaves, u_rdc clear from 4 kept reset-qualified leaves.
    rtl=rtl.replace('ot_pl_land_vector_reset_w #(', 'ot_pl_land_vector_reset_w #(.KEPT_ENABLE(1), .N32GB(12), ')
    rtl,k=re.subn(r'ot_hgi_coll_ariter_tag\s+u_ariter\b',r'ot_hgi_coll_ariter_tag #(.PP_LEAF(1)) u_ariter',rtl)
    assert k==1
    rtl,n=re.subn(r'ot_pl_pad #\(\.W\(1\), \.N\((.*?)\)\) (u_lprc_\w+)',r'ot_pl_pad #(.W(1), .N(\1), .RESET_COPIES(16)) \2',rtl)
    assert n>0
    rtl,k=re.subn(r'ot_hgi_coll_reduce_static_ctl\s+u_rdc\b',r'ot_hgi_coll_reduce_static_ctl #(.MODE_COPY_MUT((MUT==6)?1:0), .CLEAR_LEAVES(4)) u_rdc',rtl)
    assert k==1
    rtlpath.write_text(rtl)
    # MUT 6 (publication group 17 hi rail) is a default mutant of the bench (it was only run via MUTS=...).
    benchpath=out/(top+'_bench.sh');bench=benchpath.read_text()
    assert bench.count('${MUTS:-0 1 2 4}')==1
    benchpath.write_text(bench.replace('${MUTS:-0 1 2 4}','${MUTS:-0 1 2 4 6}').replace('+ mutants [1, 2, 4]','+ mutants [1, 2, 4, 6]'))
    audit=lp.audit(spec,rtl);assert audit['ok'],audit
    recordpath=lp.ROOT/spec.get('record_dir',spec['out_dir'])/(top+'_record.json');record=json.loads(recordpath.read_text())
    reset_copies=sum(15 for child in parent.insts if plan['t'].get(child['inst'],0)+parent.rx>0 and any(pin in spec.get('reset_pins',[]) and expression.strip()==parent.rst for pin,expression in child['conns'].items()))
    record['landing_implementation'].update(writer_kept_enable=True,writer_n32_group_bits=12,ariter_pp_leaves=4,rdc_clear_leaves=4,child_pad_reset_copies=16,publication_dual_rail_groups=32,publication_bits_per_group=16,private_generator='tools/landed_parent/specs/coll_ars256_native.py')
    record['flops']['reset']+=reset_copies
    record['flops']['private_pub_mode']=64
    recordpath.write_text(json.dumps(record,indent=2)+'\n')
    print('COLL_LP_NATIVE_GENERATED',name,'child_pads',n,'extra_reset_FFs',reset_copies,'audit PASS')
