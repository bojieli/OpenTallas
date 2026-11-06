from pathlib import Path
import re,hashlib,json,shutil
p=Path(__file__).resolve().parent;b=p/'obj_modes';name='Vtb_delpipe___024root__0.cpp';s=(b/name).read_text();out=p/'directed_reset_stimulus';out.mkdir(exist_ok=False)
pat=r'vlSelfRef\.tb_delpipe__DOT__del_flit\[66U\]\s*=.*?;';m=list(re.finditer(pat,s,re.S));assert len(m)==1
inject='''
    static unsigned proof_reset_before_capture = 0;
    static unsigned proof_reset_pending_cohort = 0;
    if (vlSelfRef.tb_delpipe__DOT__rst_n && vlSelfRef.tb_delpipe__DOT__a_busy && vlSelfRef.tb_delpipe__DOT__u_old__DOT__u_x__DOT___60260_ == 0 && proof_reset_before_capture < 2) {
        vlSelfRef.tb_delpipe__DOT__rst_n = 0;
        vlSelfRef.tb_delpipe__DOT__resets++;
        proof_reset_before_capture++;
        VL_PRINTF("DIRECTED_RESET before_precompute cyc=%u\\n",vlSelfRef.tb_delpipe__DOT__cyc);
    } else if (vlSelfRef.tb_delpipe__DOT__rst_n && vlSelfRef.tb_delpipe__DOT__u_new__DOT__u_x__DOT__ot_del_cap_q && proof_reset_pending_cohort < 2) {
        vlSelfRef.tb_delpipe__DOT__rst_n = 0;
        vlSelfRef.tb_delpipe__DOT__resets++;
        proof_reset_pending_cohort++;
        VL_PRINTF("DIRECTED_RESET pending_cohort cyc=%u\\n",vlSelfRef.tb_delpipe__DOT__cyc);
    }
'''
m=m[0];text=s[:m.end()]+inject+s[m.end():];(out/name).write_text(text);shutil.copy2(b/'Vtb_delpipe__ALL.a',out/'Vtb_delpipe__ALL.a')
(out/'scope.json').write_text(json.dumps({'scope':'testbench stimulus only; both actual new-hash DUTs unchanged','reset_before_precompute':2,'reset_while_internal_cohort_pending':2,'original_cpp_sha256':hashlib.sha256(s.encode()).hexdigest(),'test_cpp_sha256':hashlib.sha256(text.encode()).hexdigest()},indent=2)+'\n')
