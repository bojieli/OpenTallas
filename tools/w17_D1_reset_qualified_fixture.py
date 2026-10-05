"""Bench-only reset-qualified fixture preparation; no compiler or simulator launch.

The native candidate edits only the existing bench timing coroutine. It is a
paired simulation fixture translation, not a Verilator-regenerated model or an
engine replacement. All engine bodies and root ABI remain source-identical.
"""
import hashlib
import re

OLD_SV_SHA='7eb722d71722fc48d10bacdc0964020e8e101533f94108dfa1fcd86b3b4aeac9'
OLD_CPP_SHA='87f472b86907ae3a3c2584dd999f546520cbfbf93e9a640c998ef37c341ae459'
SV_WAIT='''  // Stable falling-edge observation of the ACTUAL synchronized consumer reset.
  do @(negedge clk); while(probe.dut.rn !== 1'b1);
  $display("D1_RESET_ACCEPT time_ps=%0t rn=%b",$realtime,probe.dut.rn);
'''
SV_CHECK='''    #0.001; // Inspect committed row state after the acceptance edge's NBA.
    if(probe.dut.rn !== 1'b1 ||
       probe.dut.g_packed_kv.g_window_hbm_attention.u_source.u_window.row_valid[row] !== 1'b1 ||
       probe.dut.g_packed_kv.g_window_hbm_attention.u_source.u_window.row_active[row] !== 1'b1 ||
       probe.dut.g_packed_kv.g_window_hbm_attention.u_source.u_window.row_tag[row] !== row ||
       probe.dut.g_packed_kv.g_window_hbm_attention.u_source.u_window.row_user[row] !== 10'd0 ||
       probe.dut.g_packed_kv.g_window_hbm_attention.u_source.u_window.block_valid[row] !== 16'hffff)
      $fatal(1,"D1_PRIME_ACCEPT_NOT_COMMITTED");
    $display("D1_QUALIFIED_PRIME time_ps=%0t row=%0d rn=%b valid=1 active=1 tag=%0d user=0 blocks=ffff",
             $realtime,row,probe.dut.rn,row);
'''


def once(text,old,new):
    if text.count(old)!=1:
        raise ValueError('nonunique/missing pinned transformation span')
    return text.replace(old,new,1)


def copy_sv(original):
    if hashlib.sha256(original.encode()).hexdigest()!=OLD_SV_SHA:
        raise ValueError('original SV bench hash mismatch')
    operations=[('  repeat(4) @(negedge clk);rst_n=1;\n',
                 '  repeat(4) @(negedge clk);rst_n=1;\n'+SV_WAIT),
                ('    do @(posedge clk);while(!window_prime_ready);\n',
                 "    do @(posedge clk);while(probe.dut.rn !== 1'b1 || window_prime_ready !== 1'b1);\n"+SV_CHECK),
                ('  end\n  @(negedge clk);prime_v=0;',
                 """  end
  if(probe.dut.rn !== 1'b1 ||
     probe.dut.g_packed_kv.g_window_hbm_attention.u_source.u_window.row_valid !== {128{1'b1}} ||
     probe.dut.g_packed_kv.g_window_hbm_attention.u_source.u_window.row_active !== {128{1'b1}})
    $fatal(1,"D1_PRIME_SET_INCOMPLETE");
  $display("D1_ALL128_PRIMED time_ps=%0t accepted=128 rn=1",$realtime);
  @(negedge clk);prime_v=0;""")]
    result=original
    for old,new in operations:result=once(result,old,new)
    return result,operations


def cpp_operations():
    root='vlSelfRef.tb_D1_scope_core__DOT__probe__DOT__dut__DOT__'
    window=root+'g_packed_kv__DOT__g_window_hbm_attention__DOT__u_source__DOT__u_window__DOT__'
    row='tb_D1_scope_core__DOT__unnamedblk1__DOT__row'
    path='rtl/test/w17_D1_reset_qualified_fixture/tb_D1_scope_core.sv'
    wait='''    // D1 copied-bench reset acceptance; no engine or ready-state writes.
    do {
        Vtb_D1_scope_core___024root____VbeforeTrig_ha6b021a6__0(vlSelf, "@(negedge tb_D1_scope_core.clk)");
        co_await vlSelfRef.__VtrigSched_ha6b021a6__0.trigger(0U, nullptr, "@(negedge tb_D1_scope_core.clk)",
            "'''+path+'''", 86);
    } while ((('''+root+'''rst_s >> 1U) & 1U) != 1U);
    VL_PRINTF_MT("D1_RESET_ACCEPT time_ps=%llu rn=1\\n", (unsigned long long)vlSymsp->_vm_contextp__->time());
'''
    old_ready='''        } while ((1U & (~ (IData)(vlSelfRef.tb_D1_scope_core__DOT__probe__DOT__dut__DOT__g_packed_kv__DOT__g_window_hbm_attention__DOT__source_prime_ready))));'''
    new_ready='''        } while (((('''+root+'''rst_s >> 1U) & 1U) != 1U) ||
                 ('''+root+'''g_packed_kv__DOT__g_window_hbm_attention__DOT__source_prime_ready != 1U));'''
    check='''        co_await vlSelfRef.__VdlySched.delay(1ULL, nullptr, "'''+path+'''", 96);
        if (((('''+root+'''rst_s >> 1U) & 1U) != 1U) ||
            !(('''+window+'''row_valid['''+row+''' >> 5U] >> ('''+row+''' & 31U)) & 1U) ||
            !(('''+window+'''row_active['''+row+''' >> 5U] >> ('''+row+''' & 31U)) & 1U) ||
            '''+window+'''row_tag['''+row+'''] != '''+row+''' ||
            '''+window+'''row_user['''+row+'''] != 0U ||
            '''+window+'''block_valid['''+row+'''] != 0xffffU) {
            VL_PRINTF_MT("D1_PRIME_ACCEPT_NOT_COMMITTED row=%u\\n", (unsigned)'''+row+''');
            VL_STOP_MT("'''+path+'''", 104, "", false);
        }
        VL_PRINTF_MT("D1_QUALIFIED_PRIME time_ps=%llu row=%u rn=1 valid=1 active=1 tag=%u user=0 blocks=ffff\\n",
            (unsigned long long)vlSymsp->_vm_contextp__->time(), (unsigned)'''+row+''', (unsigned)'''+row+''');
'''
    reset='    vlSelfRef.tb_D1_scope_core__DOT__rst_n = 1U;\n'
    finish_anchor='    }\n    Vtb_D1_scope_core___024root____VbeforeTrig_ha6b021a6__0(vlSelf, \n'
    finish='    }\n'
    conditions=[f"((({root}rst_s >> 1U) & 1U) != 1U)"]+[f"({window}{name}[{word}U] != 0xffffffffU)"
                for name in ('row_valid','row_active') for word in range(4)]
    finish+='    if ('+' ||\n        '.join(conditions)+') {\n'
    finish+='        VL_PRINTF_MT("D1_PRIME_SET_INCOMPLETE\\n");\n'
    finish+='        VL_STOP_MT("'+path+'", 117, "", false);\n    }\n'
    finish+='    VL_PRINTF_MT("D1_ALL128_PRIMED time_ps=%llu accepted=128 rn=1\\n", (unsigned long long)vlSymsp->_vm_contextp__->time());\n'
    finish+='    Vtb_D1_scope_core___024root____VbeforeTrig_ha6b021a6__0(vlSelf, \n'
    return [(reset,reset+wait),(old_ready,new_ready+ '\n'+check),(finish_anchor,finish)]


def copy_cpp(original):
    if hashlib.sha256(original.encode()).hexdigest()!=OLD_CPP_SHA:
        raise ValueError('original generated TU hash mismatch')
    begin=original.index('VlCoroutine Vtb_D1_scope_core___024root___eval_initial__TOP__Vtiming__0(Vtb_D1_scope_core___024root* vlSelf) {')
    end=original.index('VlCoroutine Vtb_D1_scope_core___024root___eval_initial__TOP__Vtiming__1(Vtb_D1_scope_core___024root* vlSelf) {',begin)
    body=original[begin:end]
    operations=cpp_operations()
    for old,new in operations:body=once(body,old,new)
    candidate=original[:begin]+body+original[end:]
    if inverse(candidate,operations)!=original:
        raise ValueError('native inverse mismatch')
    return candidate,operations,{'prefix_bytes':begin,'original_body_bytes':end-begin,
                                'engine_prefix_SHA256':hashlib.sha256(original[:begin].encode()).hexdigest(),
                                'engine_suffix_SHA256':hashlib.sha256(original[end:].encode()).hexdigest()}


def inverse(candidate,operations):
    result=candidate
    for old,new in reversed(operations):result=once(result,new,old)
    return result


def edge_model():
    # Reset rises at negedge4000. rst_s is01 after4500 and11 after5500 NBA.
    # Wait observes rn=0 at negedge5000 andrn=1 at negedge6000, then original
    # row loop drives first prime at next negedge7000. Each check is edge+1ps.
    accepts=[{'row':i,'drive_ps':7000+1000*i,'sample_ps':7500+1000*i,
              'commit_check_ps':7501+1000*i,'rn':1,'valid':1,'active':1,
              'tag':i,'user':0,'blocks':0xffff} for i in range(128)]
    return {'reset_release_ps':4000,'synchronized_rn_high_after_NBA_ps':5500,
            'reset_wait_samples':[{'time_ps':5000,'rn':0},{'time_ps':6000,'rn':1}],
            'accepts':accepts,'start_ps':135000,'start_deassert_ps':136000,'all128_commit_witness_ps':134501,
            'fixture_shift_cycles':2,'original_first_counted_prime_ps':5500,
            'descriptor_sample_ps_conditional_same_pipeline':141500,
            'first_prefetch_ps_conditional_same_pipeline':142500,
            'service_bound':'BOUND_MISSING','fulltoken':False}


def verify_healthy_accepts(events):
    if any(not isinstance(event,dict) or any(type(value) is not int for value in event.values()) for event in events):
        raise ValueError('exact integer event fields required')
    if len(events)!=128:
        raise ValueError('exact128 accepted rows required')
    for expected,actual in zip(edge_model()['accepts'],events):
        if actual!=expected:
            raise ValueError('reset-qualified row identity/commit/edge mismatch')
    return {'first_row':0,'last_row':127,'accepted_rows':128,'first_row_qualified':True,
            'all_rows_qualified':True,'runtime_credit':False,'service_bound':'BOUND_MISSING'}
