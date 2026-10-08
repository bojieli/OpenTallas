#!/usr/bin/env python3
"""Price isolated control DMR in the reused NC1 SM; no arithmetic duplication.

This is a proposal and source inventory, not an implementation coverage claim.
Run before implementing the corresponding default-off control successor.
"""
import argparse
import ast
import re
import hashlib
import json
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def validate_inventory(plan):
    """Independent source-declaration count catches missing issuer flops/width drift."""
    names = {'RW': 12, 'SW': 3, 'XW': 7, 'IL': 8}
    def evaluate(expr):
        def visit(n):
            if isinstance(n, ast.Constant) and isinstance(n.value, int): return n.value
            if isinstance(n, ast.Name): return names[n.id]
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub)):
                a, b = visit(n.left), visit(n.right)
                return a+b if isinstance(n.op, ast.Add) else a-b
            raise ValueError('unsupported declaration expression '+expr)
        return visit(ast.parse(expr.strip(), mode='eval').body)
    source = (ROOT/'rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv').read_text()
    source = source[source.index('localparam integer SW'):]
    source = re.sub(r'//[^\n]*', '', source)
    bits, registers = 2, ['busy', 'arrive']  # output regs declared in port list
    for match in re.finditer(r'\breg\s*(?:\[([^]]+)\]\s*)?([^;]+);', source):
        width = 1
        if match[1]:
            a, b = match[1].split(':'); width = abs(evaluate(a)-evaluate(b))+1
        for item in match[2].split(','):
            array = re.search(r'\[([^:]+):([^]]+)\]', item)
            entries = abs(evaluate(array[1])-evaluate(array[2]))+1 if array else 1
            bits += width*entries; registers.append(item.strip().split()[0])
    priced = sum(r['raw_bits'] for r in plan['inventory'] if r['name'].startswith('issuer'))
    assert bits == priced, (bits, priced)
    shapes = []
    for fmt, k, lanes, unit in [('fp4',5120,8,32),('fp4',2304,8,32),('fp8',5120,4,32),('bf16',5120,64,1),('bf16',4096,64,1)]:
        chunks=math.ceil(k/(8*unit)); groups=math.ceil(chunks/lanes)
        assert groups <= 2**plan['shape']['LEV'] and groups*8 <= plan['shape']['XD']
        shapes.append(dict(format=fmt,K=k,groups=groups,records_per_row=groups*8))
    return dict(issuer_declaration_bits=bits,priced_issuer_bits=priced,issuer_register_declarations=len(registers),
                issuer_width_coverage='PASS',supported_full_K_shapes=shapes,
                scope='Independent issuer declaration width audit only. Other groups remain formula inventory/explicit allowances; this is not all-state or RTL qualification.')


def build():
    rw, sw, xw, il, lev, alat = 12, 3, 7, 8, 4, 7
    tagw, cw, opw = 16, 22, 40
    inv = []
    def add(name, bits, source, signals, status='REQUIRES_OPT_IN_DMR_IMPLEMENTATION'):
        assert bits > 0
        inv.append(dict(name=name, raw_bits=bits, source=source, signals=signals,
                        protection_status=status))
    issue='rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv'
    # Explicit declaration counts for ENABLE1, RMAX4096, IL8, XD128.
    add('issuer_descriptor',13+16+8+1,issue,'rows_q,c_q,g_q,gs_q')
    add('issuer_cursors',2*3+2*13+2*8+2*16+13+2*7+3*21+2*13+8+2*7+13,issue,
        'ph,si,rb/rb_n,gi/gi_n,ti/ti_n,rem,xa_r/xa_n,items_q/wb/wb_n,cr/cr_n,cg,cxb/cxb_n,rsi_q')
    add('issuer_slot_tables',il*(13+8+7),issue,'s_row,s_g,s_xb')
    add('issuer_predicates_and_outputs',3+3*8+16+8+1+1+3+1+3+2,issue,
        'busy,arrive,issuing,valid_mask,next_mask,slot_glast,c_end,g_end,init_q,turn_q,lt_q/lt_n_q/c1_q,lw_q,lg_q/lg_n_q/g1_q,row_ok_q/ls_q')
    add('issuer_lookahead_products',4*15+2*17,issue,'pp0..pp3,s01,s23')
    add('issuer_delayed_slot_write',1+3+13+8+7+1,issue,'sw_q,sw_slot,sw_row,sw_g,sw_xb,sw_last')
    stack='rtl/hbm_accel/sm/ot_hbm_accel_stack.sv'
    add('stack_input_output_metadata',2+sw+rw+2+rw,stack,'iv_q,ilast_q,islot_q,itag_q,ov,otag,fault')
    add('stack_ownership_lookahead',lev*(2*il+2),stack,'pend_v,seen,have_q,seen_q; every slot at every level')
    add('stack_level_pipeline_metadata',lev*alat*(1+sw+rw+1),stack,'meta[last,slot,tag] plus valid delay; pend_d/opa_q are arithmetic flops, not ownership')
    sm='rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv'
    add('top_boundary_metadata',2*(1+opw+11+1+3+2+rw),sm,'start,op,rsp valid/tag,release,busy/arrive/released,result valid/fault/row PIO chains')
    add('top_format_and_s1',2+3+tagw+xw,sm,'fmt_q,s1_v/first/last/tag/xa')
    add('x_write_metadata',1+xw+2+4*(4+2)*(1+xw+2),sm,'w0_en/addr/oh; DW4, L2, leaf we/wa/woh per SUB4; data codec separate')
    add('leaf_distribution_metadata',4*((2+1+1+1)*cw+(2+1)*(1+xw)),sm,'DS2,L2,E3,E4 controls incl all validity/format/tag; x read control/address')
    add('gather_metadata',4*(3+1)*(1+tagw+1)+1+tagw+1,sm,'G1,DG3,tree-input valid/tag/fault and registered aggregate')
    add('result_boundary_metadata',2+rw,sm,'rv_q,fault_q,rrow_q')
    # Descriptor and request channels contain CONTROL payload; duplicate FIFO contents too.
    for width,name in [(56,'descriptor'),(42,'request')]:
        add('credit_channel_'+name,2*3+2*3+7*width+2*(width+2),sm,
            'cred,cnt,wp,rp,mem[DEPTH7],forward valid/data PIO2,return valid PIO2')
    tree='rtl/gpu/ot_gpu_tree.sv'
    add('tree_tag_valid_pipelines',(4*(7*1+7*4)+7*2)*(tagw+1),tree,
        'four blockdot LB2 trees, four BF16 L16 trees, one SUB4 combine tree; exclude arithmetic data')
    add('column_control_pipeline_allowance',4*1024,'rtl/gpu/ot_gpu_bd_col.sv',
        'Bounded allocation 1024 control bits/sub for both column first/last/valid/tag delay paths, sticky faults and bterm control. MUST replace allowance with elaborated inventory before qualification.',
        'PRICED_ALLOWANCE_REQUIRES_ELABORATED_INVENTORY')
    bulk='rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv'
    add('native_bulk_state_extracted',1949,bulk,
        'Scheduler extracted1949 bits: desc384,queue7,active57,ring/full/alloc/cons/used/outstanding1067,eligibility18,hf/rok16,addr40,qnz/qone8,next/rsp32,predecode128,bankfull/rspqq19,hiincrement26,bankptr56,SRAMqueue/parity/WE91. Outer model must exclude alias1067; allocated bitmap and slot identities remain additional.',
        'IMPLEMENTED_NATIVE_DMR_PENDING_TEST_AND_PHYSICAL')
    raw=sum(r['raw_bits'] for r in inv)
    # 64-bit local comparison groups, duplicated sticky poison at each group.
    guards=sum(math.ceil(r['raw_bits']/64) for r in inv)
    extra_flops=raw+2*guards
    xor=raw
    or2=raw-guards
    # Independent next-state logic required; allowance, never report as measured.
    nextstate_gates=4*raw
    cell=(extra_flops*.2916+(xor+or2+nextstate_gates+4*guards)*.3)/1e6
    sources=sorted(set(r['source'] for r in inv)|{'rtl/gpu/ot_gpu_tc_col.sv','tools/hbrom_control_model.py','tools/hbrom_protection_model.py'})
    inventory={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
    plan = dict(schema='opentallas.hbrom.inner-control-plan.v1',status='PRICED_PROPOSAL_NOT_IMPLEMENTED_NOT_SIGNOFF',
        shape=dict(NC=1,SUB=4,LBS=2,LSB=16,IL=il,RMAX=4096,XD=128,LEV=lev,ALAT=alat,DS=2,DG=3,DW=4,PIO=2,STK=1),
        sources_sha256=inventory,inventory=inv,
        scheme=dict(enable_default=0,kind='Isolated control DMR with independent next-state cones; shared arithmetic',
          control='Duplicate every listed stored control field including unused-slot metadata, pipeline valids, formats, tags, pointer lookahead and ownership. Independent control cones must survive synthesis; local comparator covers both replicas before enable/address/retirement effects.',
          stack='Share pend_d and FP32 adders, duplicate pend_v/seen/have_q/seen_q and meta. Compare pending-slot select, operand-select, write-enable/address, go/lone and retirement tags. A control discrepancy poisons the current operation; suppress publication and prevent further external writes.',
          fault='Fail-stop detection, no correction or replay promise. Sticky poison itself duplicated; either asserted copy or disagreement blocks publication. Recover only at verified quiescence.',
          scope='Single control-storage or single independent control-cone divergence; common-mode/equal corruption outside DMR guarantee. No ROM ECC or ROM data parity introduced.',
          arithmetic='Ordinary flipflop arithmetic data, including pend_d/opa_q, accumulators and product/adder pipelines, retains fault-free execution assumption. No duplicate arithmetic requested. Any such state mapped to SRAM must use SRAM protection instead.',
          integration='Outer hbrom_control_model protects NEW scheduler state. This inventory adds native-inner state; physical removal of redundant native bookkeeping can subtract it only with source evidence.'),
        area=dict(raw_control_bits=raw,incremental_flops=extra_flops,local_compare_groups=guards,xor2=xor,or2=or2,
                  nextstate_twoinput_gate_allowance=nextstate_gates,dff_um2=.2916,gate_allowance_um2=.3,
                  incremental_cell_allowance_mm2=cell,incremental_packed_50pct_mm2=2*cell,
                  status='Uncharacterized gate and native-bulk/column inventory allowances, not synthesized bound; arithmetic excluded; existing primary control already in NC1 area'),
        latency=dict(issue_guard_extra=1,activation_write_guard_extra=1,result_publication_extra=1,
          recurrence_extra=0,peak_records_per_cycle=1,
          rule='Guard adds one matched control+data feed stage before column ingress and one result publication stage. Do NOT insert per-MAC or per-stack-level wait states. Local state/command comparisons inside loops must fit existing cycles at SS; otherwise this proposal is not qualified and must be repriced. Guard valid/address at actual SRAM write edge; mismatch suppresses write before it commits.',
          overlap='Outer scheduler one-cycle ROM issue / activation publish / output publish seals may absorb these SAME physical stages only if netlist proves they coincide; otherwise add cycles. Baseline separate upper allowance is +2 cycles/op plus +1 activation ingress latency; no steady-state issue penalty assumed pending SS.'),
        explicit_gaps=['All protection described here absent in original native RTL; external protected wrapper alone cannot see or cover inner pend_v/seen or tag upset.',
          'Column metadata exact elaborated bit inventory still required; allowance cannot establish all-state coverage. Native bulk extracted1949 bits owned by scheduler; no all-state qualification implied.',
          'Shared guard comparators, common inputs, reset and clock common-mode failures remain outside DMR guarantee.',
          'SECDED codec staging-control metadata must be added to actual protected successor inventory when SRAM agent creates codec pipeline.',
          'Final netlist must enumerate every sequential CONTROL bit and assign protected replica/check or justified non-control classification; no unclassified mutable-control bits allowed.'],
        gates=['Full K5120/2304 and exact padded reduction golden with finite stalls and format switches',
          'Fault injection issuer slots/cursors/valids, stack each pend_v/seen and metadata stage, credit FIFO pointers/counts, format, source/row tags, SRAM write address/enables; zero wrong published rows and no wrong memory write',
          'Fault sticky until quiescent reset, including upset in poison latch itself',
          'Independent DMR cones not optimized together; source and elaborated state coverage manifests',
          'Contextual SS setup and FF hold at60ps/25ps; repriced cycles/area >=1percent adoption gate'])

    plan['validation'] = validate_inventory(plan)
    return plan


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='results/uarch/hbrom/inner_control_plan.json');a=p.parse_args()
    out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(build(),indent=2)+'\n')
    print(out)
if __name__=='__main__':main()
