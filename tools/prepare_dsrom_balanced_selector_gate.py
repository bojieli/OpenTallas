"""Fullshape source-bound legal/fault/mutant gate preparation; never launch HDL."""
import argparse
import json
from pathlib import Path
import prepare_dsrom_full_selector_dma_fixture as V
import prepare_dsrom_balanced_selector_candidate as C
ROOT=V.ROOT
BASE=C.BASE

def bench(template):
    s=template.replace('module bench_dsrom_full_selector_dma_prepare;', 'module bench_dsrom_balanced_selector_gate_prepare #(parameter integer MUTANT=0);')
    s=s.replace('reg clk=0,rst_n=0,go=0,o_valid=0,o_last=0;', 'reg clk=0,rst_n=0,go=0,o_valid=0,o_last=0,o_err=0,engine_fault=0;\n  reg [1:0] o_rank=0;\n  reg [14:0] src=0,dst=8192,ibase=4096;')
    s=s.replace('wire ref_ev,cand_ev,', 'wire [511:0] ref_ed,cand_ed;\n  wire ref_ev,cand_ev,')
    s=s.replace('.e_data(),.e_last(ref_el)', '.e_data(ref_ed),.e_last(ref_el)').replace('.e_data(),.e_last(cand_el)', '.e_data(cand_ed),.e_last(cand_el)')
    s=s.replace('integer normal_cases=0,abort_cases=0;', 'integer normal_cases=0,abort_cases=0,fault_cases=0,active_case=-1;\n  integer ref_return_groups=0,cand_return_groups=0,fetch_words=0;\n  integer ref_return_cycle[0:511];\n  reg [2:0] ref_return_nw[0:511];\n  reg ref_return_last[0:511];\n  reg [2047:0] ref_return_data[0:511];')
    s=s.replace('.src(15\'d0)', '.src(src)').replace('.dst(15\'d8192)', '.dst(dst)').replace('.ibase(15\'d4096)', '.ibase(ibase)')
    s=s.replace('.TK_BALANCED(1),.TK_STATION(1)', '.TK_BALANCED(MUTANT==4?0:1),.TK_STATION(MUTANT==4?0:1),.TK_MUTANT(MUTANT==4?0:MUTANT)')
    s=s.replace(".o_rank(2'd0),.o_err(1'b0),.engine_fault(1'b0)",'.o_rank(o_rank),.o_err(o_err),.engine_fault(engine_fault)')
    s=s.replace('!=368)', '!=(MUTANT==4?0:368))')
    s=s.replace('// Candidate module is an explicit unmet package dependency; no stub permitted.', '// Full candidate dependencies are packaged; no HDL qualification claimed.')
    s=s.replace('  // VM captures pre-NBA', '''  task automatic value_diff(input string kind,input integer index,input [511:0] wanted,input [511:0] got);
    if(MUTANT>=1 && MUTANT<=3) begin
      $display("MUTANT_DIFF mode=%0d case=%0d kind=%s index=%0d expected=%h actual=%h",MUTANT,active_case,kind,index,wanted,got);$finish;
    end
    $display("VALUE_DIFF case=%0d kind=%s index=%0d expected=%h actual=%h",active_case,kind,index,wanted,got);
    $fatal(1,"FULL_VALUE_DIFF");
  endtask
  task automatic count_diff(input string kind,input integer wanted,input integer got);
    if(MUTANT>=1 && MUTANT<=3) begin
      $display("MUTANT_DIFF mode=%0d case=%0d kind=%s index=0 expected=%0d actual=%0d",MUTANT,active_case,kind,wanted,got);$finish;
    end
    $display("COUNT_DIFF case=%0d kind=%s expected=%0d actual=%0d",active_case,kind,wanted,got);
    $fatal(1,"FULL_COUNT_DIFF");
  endtask

  // VM captures pre-NBA''')
    s=s.replace('ref_retire=-1;cand_retire=-1;ref_seen_busy=0;cand_seen_busy=0;', 'ref_retire=-1;cand_retire=-1;ref_seen_busy=0;cand_seen_busy=0;ref_return_groups=0;cand_return_groups=0;fetch_words=0;')
    s=s.replace('      if(ref_ev && (!ref_em', '''      if(ref_re!==cand_re || (ref_re && ref_ra!==cand_ra)) $fatal(1,"NATIVE_VM_READ_DIFF");
      if(ref_ev!==cand_ev) $fatal(1,"NATIVE_EMIT_VALID_DIFF");
      if(ref_ev) begin
        if(ref_ed!==cand_ed || ref_el!==cand_el || ref_em!==cand_em || ref_et!==cand_et) $fatal(1,"NATIVE_EMIT_PACKET_DIFF");
        if(fetch_words>=2*operand_half) $fatal(1,"NATIVE_EXTRA_INPUT_DIFF");
        if(ref_ed!==operands[fetch_words][511:0] || ref_el!==(fetch_words==2*operand_half-1)) $fatal(1,"NATIVE_OPERAND_ORDER_DIFF");
        fetch_words=fetch_words+1;
      end
      if(ref_ev && (!ref_em''')
    s=s.replace('    $display("CASE_PASS case=', '    if(fetch_words!=2*operand_half) $fatal(1,"NATIVE_INPUT_COUNT_DIFF");\n    $display("CASE_PASS case=')
    s=s.replace('cand_words=%0d delta=%0d",index,runtime_n,wanted,ref_words,cand_words,cand_retire-ref_retire);', 'cand_words=%0d delta=%0d fetch_words=%0d",index,runtime_n,wanted,ref_words,cand_words,cand_retire-ref_retire,fetch_words);')
    # Independent candidate word checking precedes ref timing/ordinal comparisons.
    start=s.index('        if(cand_groups>=ref_groups)')
    stop=s.index('        for(lane=0;',start)
    packet_checks=s[start:stop]
    s=s[:start]+s[stop:]
    marker='        cand_groups=cand_groups+1;'
    s=s.replace(marker,packet_checks+marker)
    s=s.replace('if(cand_wd[512*lane+:512]!==assertions[cand_words]) $fatal(1,"CAND_VALUE_DIFF");',
                'if(cand_wd[512*lane+:512]!==assertions[cand_words]) value_diff("CAND_VALUE_DIFF",cand_words,assertions[cand_words],cand_wd[512*lane+:512]);')
    s=s.replace('if(!abort_mode && (cand_words!=expected_words || cand_groups!=ref_groups)) $fatal(1,"CAND_RETIRE_COUNT_DIFF");',
                'if(!abort_mode && cand_words!=expected_words) count_diff("CAND_RETIRE_COUNT_DIFF",expected_words,cand_words);\n        if(!abort_mode && cand_groups!=ref_groups) $fatal(1,"CAND_RETIRE_GROUP_DIFF");')
    # Compare core return flags/payload before formed writes; for mutant controls
    # run independent numerical checks first, preserving all later checks as well.
    s=s.replace('      #1;\n      if(ref_fault', '''      if(reference.tk_ov) begin
        if(ref_return_groups>=512) $fatal(1,"REF_RETURN_BOUND_DIFF");
        ref_return_nw[ref_return_groups]=reference.tk_nw;
        ref_return_last[ref_return_groups]=reference.tk_ol;
        ref_return_data[ref_return_groups]=reference.tk_od;
        ref_return_cycle[ref_return_groups]=cycle;
        if(reference.tk_nw==0 || reference.tk_nw>4) $fatal(1,"REF_PUBLIC_NW_DIFF");
        if(reference.tk_ol!==(4*(ref_return_groups+1)>=expected_words)) $fatal(1,"REF_PUBLIC_LAST_DIFF");
        ref_return_groups=ref_return_groups+1;
      end
      if(candidate.tk_ov) begin
        // Direct independent assertions also catch an early corrupt return,
        // before reference ordinal/time checks could obscure the actual value.
        for(lane=0;lane<4;lane=lane+1) if(lane<candidate.tk_nw) begin
          if(4*cand_return_groups+lane>=expected_words) count_diff("CAND_RETURN_EXTRA_WORD",expected_words,4*cand_return_groups+lane+1);
          if(candidate.tk_od[512*lane+:512]!==assertions[4*cand_return_groups+lane])
            value_diff("CAND_VALUE_DIFF",4*cand_return_groups+lane,assertions[4*cand_return_groups+lane],candidate.tk_od[512*lane+:512]);
        end
        if(cand_return_groups>=ref_return_groups) $fatal(1,"CAND_PUBLIC_ORDER_DIFF");
        if(candidate.tk_nw!==ref_return_nw[cand_return_groups] || candidate.tk_ol!==ref_return_last[cand_return_groups] ||
           candidate.tk_od!==ref_return_data[cand_return_groups]) $fatal(1,"CAND_PUBLIC_PACKET_DIFF");
        if(cycle-ref_return_cycle[cand_return_groups]!=(MUTANT==4?0:340)) $fatal(1,"CAND_PUBLIC_EVENT_DIFF");
        cand_return_groups=cand_return_groups+1;
      end
      #1;
      if(ref_fault''')
    s=s.replace('tick();rst_n=0;go=0;o_valid=0;o_last=0;active=0;', 'tick();rst_n=0;go=0;o_valid=0;o_last=0;o_err=0;engine_fault=0;o_rank=0;active=0;\n    src=0;dst=8192;ibase=4096;')
    s=s.replace('    expected_words=(wanted+15)/16;', '    active_case=index;\n    expected_words=(wanted+15)/16;')
    s=s.replace('    if(!$value$plusargs', '    if(MUTANT<0 || MUTANT>4) $fatal(1,"UNKNOWN_PROFILE");\n    if(!$value$plusargs')
    task='''  task automatic check_sticky_fault(input integer kind,input integer wanted_busy);
    repeat(204) tick(); //99 input +99 return +6 settling/observation edges.
    if(ref_fault!==1 || cand_fault!==1 || ref_busy!==wanted_busy[0] || cand_busy!==wanted_busy[0])
      $fatal(1,"FAULT_FLAG_OR_OWNERSHIP_DIFF");
    repeat(8) begin
      tick();
      if(!ref_fault || !cand_fault || ref_we!=0 || cand_we!=0) $fatal(1,"FAULT_STICKY_DIFF");
    end
    fault_cases=fault_cases+1;$display("FAULT_PASS kind=%0d busy=%0d",kind,wanted_busy);
    reset_fixture();observe_reset_drain();
  endtask
  task automatic bad_command_case(input integer kind);
    reset_fixture();n=32;tk_k=1;stride=1024;operand_half=32;tag=100+kind;
    case(kind)
      0:tk_k=0;
      1:n=0;
      2:n=129;
      3:tk_k=2049;
      4:dst=8193;
      5:ibase=8192;
      6:src=32760;
      7:begin dst=32764;tk_k=1024;end
      default:$fatal(1,"UNKNOWN_BAD_COMMAND_CASE");
    endcase
    go=1;tick();go=0;
    check_sticky_fault(kind,0);
  endtask
  task automatic external_fault_case(input integer kind);
    reset_fixture();n=32;tk_k=1;stride=1024;operand_half=32;tag=100+kind;
    if(kind==8) o_err=1;
    else if(kind==9) engine_fault=1;
    else begin go=1;tick();go=0;tick();end
    if(kind==10) begin go=1;tick();go=0;end
    if(kind==11) begin o_rank=1;o_valid=1;o_data=0;tick();o_valid=0;o_rank=0;end
    tick();o_err=0;engine_fault=0;
    check_sticky_fault(kind,kind>=10?1:0);
  endtask
  task automatic core_fault_case(input integer kind);
    integer beat,half;
    reset_fixture();
    if(kind==14) begin
      $readmemh($sformatf("%s/inputs/case_05.mem",image_root),operands,0,63);n=31;
    end else begin
      $readmemh($sformatf("%s/fault_inputs/kind_%0d.mem",image_root,kind),operands,0,63);n=32;
    end
    tk_k=1;stride=1024;operand_half=32;tag=100+kind;go=1;tick();go=0;repeat(3) tick();
    half=integer'(n);
    for(beat=0;beat<2*half;beat=beat+1) begin
      if(!ref_ready || !cand_ready) $fatal(1,"FAULT_INPUT_ACCEPTANCE_DIFF");
      o_valid=1;o_data=operands[beat<half?beat:32+beat-half];o_last=(beat==2*half-1);tick();
    end
    o_valid=0;o_last=0;
    check_sticky_fault(kind,1);
  endtask

'''
    s=s.replace('  initial begin\n    if(MUTANT<0',task+'  initial begin\n    if(MUTANT<0')
    start=s.index('    // Generated calls include37')
    s=s[:start]+'''    if(MUTANT>=1 && MUTANT<=3) begin
      if(MUTANT<1 || MUTANT>3) $fatal(1,"UNKNOWN_MUTANT_MODE");
      run_case(0,512,1,0);
      $fatal(1,"MUTANT_NO_DIFFERENCE");
    end else begin
      `include "case_calls.svh"
      for(integer kind=0;kind<8;kind=kind+1) bad_command_case(kind);
      for(integer kind=8;kind<12;kind=kind+1) external_fault_case(kind);
      for(integer kind=12;kind<15;kind=kind+1) core_fault_case(kind);
      if(normal_cases!=37 || abort_cases!=4 || fault_cases!=15) $fatal(1,"COMPLETION_COUNT_DIFF");
      $display("FULL_SELECTOR_DMA_PASS profile=%0d cases=37 aborts=4 faults=15 functional_only=1",MUTANT);$finish;
    end
  end
endmodule
'''
    return s

def prepare(out):
    if out.exists():raise ValueError('fresh gate directory required')
    out.mkdir(parents=True)
    fixture=out/'fixture';V.prepare(fixture)
    candidate=out/'candidate';C.prepare(candidate)
    (fixture/'bench_dsrom_balanced_selector_gate_prepare.sv').write_text(bench((ROOT/V.TEMPLATE).read_text()))
    (fixture/'fault_inputs').mkdir()
    fault_records=[]
    for kind,value,beat,lane in [(12,0x7fc00001,0,0),(13,0xff800001,31,63)]:
        words=V.scores(512,'all_tie');beats=V.operands(512,words)
        mask=0xffffffff<<(32*lane);beats[beat]=(beats[beat]&~mask)|(value<<(32*lane))
        path=f'fault_inputs/kind_{kind}.mem'
        (fixture/path).write_text(''.join(f'{b:0512x}\n' for b in beats))
        fault_records.append(dict(kind=kind,path=path,score_word=value,beat=beat,lane=lane,sha256=V.sha((fixture/path).read_bytes())))
    V.write_json(fixture/'artifact_manifest.json',{str(p.relative_to(fixture)):V.sha(p.read_bytes()) for p in sorted(fixture.rglob('*')) if p.is_file() and p.name!='artifact_manifest.json'})
    plan=dict(schema='opentallas.fullshape.balanced-selector.functional-gate.v1',
        geometry=json.loads((candidate/'sourceplan.json').read_text())['geometry'],
        hardware_price='implementation_model.json',candidate_default_off=True,mutants_test_only=True,
        candidate_dependencies_complete=True,HDL_compiled=False,HDL_equivalence=False,compile_admitted=False,PR_admitted=False,
        cases=37,reset_aborts=4,fault_cases=15,
        fault_contract={'0':'k0','1':'n0','2':'n greater than NMAX','3':'k greater than total candidates','4':'unaligned fourbank destination',
          '5':'ID source overlaps result','6':'source end exceeds WA address space','7':'destination end exceeds WA address space',
          '8':'o_err idle sticky','9':'engine_fault idle sticky','10':'go while busy retains owner and faults',
          '11':'nonzero GW4 root rank retains owner and faults','12':'positive qNaN score rejects core command',
          '13':'negative signaling NaN score rejects core command','14':'496 candidates not divisible byPF rejects core command'},
        fault_input_pins=fault_records,immutable_input_only=True,assertions_only_expected=True,
        exact_mutant_counts={'0':'37 CASE_PASS +4 ABORT_PASS +15 FAULT_PASS +one FULL_SELECTOR_DMA_PASS',
          '1':'one explicit MUTANT_DIFF CAND_RETIRE_COUNT_DIFF, case0 expected1 actual0',
          '2':'one explicit MUTANT_DIFF CAND_VALUE_DIFF, case0 index0 expected oracle word0 and actualword differs',
          '3':'one explicit MUTANT_DIFF CAND_RETIRE_COUNT_DIFF, case0 expected1 actual0',
          '4':'defaultoff candidate37 CASE_PASS delta0 +4 ABORT_PASS +15 FAULT_PASS +one profile4 terminal'},
        defaultoff_actual_gate_prepared=True,
        expected_event_calibration={'defaultoff_delta':0,'public_return_delta':340,'formed_write_and_retire_delta':368,'absolute_cycle_envelope_not_asserted':True},
        source_fault_semantics='DMA bad/sticky commands fault without clearing ownership; core NaN/badcommand fault returns through99 edges; reset is the release. No invented error ACK.',
        physical_dependencies='Allowed378DBU terminal slots and actual clock/reset/PG/via union pending Arch/Maxwell; no833ps fixture credit',
        remaining_before_launch=['Independent source/interface/state-stage review','Source-bound GO with measured fullshape resource inventory/reservation'],
        runtime_or_fulltoken_claim=False)
    V.write_json(out/'sourceplan.json',plan)
    V.write_json(out/'artifact_manifest.json',{str(p.relative_to(out)):V.sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()})
    return plan

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    plan=prepare(a.out);print(json.dumps({'cases':37,'faults':15,'mutants':3,'compile_admitted':False}))
