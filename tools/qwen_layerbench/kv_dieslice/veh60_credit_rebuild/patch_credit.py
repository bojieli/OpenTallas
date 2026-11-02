#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
base,review,out=map(Path,sys.argv[1:]);s=base.read_text();r=review.read_text();original=s
start=r.index('    // W528 application credits are independent');end=r.index('    // credit-based host sender',start);block=r[start:end]
anchor='    // credit-based host sender (IBUF 4 of the host CDC write face)\n'
assert s.count(anchor)==1;s=s.replace(anchor,block+anchor)
old='        if (sent < nfr && c > 0 && !auth_pending && cyc_core >= hold_core && cyc_host >= next_issue_host) begin\n'
a=r.index('        if (!host_drop_class_credits && host_class_credit_v && c > 0) begin\n');b=r.index('            next_issue_host =',a);new=r[a:b]
assert s.count(old)==1;s=s.replace(old,new)
report='        $display("HOST_CLASS_CREDITS returned_frames %0d disabled %0d", host_class_credit_frames, host_drop_class_credits);\n'
anchor2='        $display("KVSLICE_FINALCAL dcal_fault'
i=s.index(anchor2);s=s[:i]+report+s[i:]
helper=r[r.index('\n// Board endpoint W528 application-credit consumer.'):]
assert helper.count('module qwen_kv_board_class_credit(')==1
assert s.endswith('endmodule\n');s+=helper
rev=s.removesuffix(helper).replace(report,'').replace(new,old).replace(block+anchor,anchor)
assert rev==original,'non-credit delta'
assert 'POST_CAL_BUDGET' not in s
assert s.count('.generation(2\'(host_tok_gen))')==1
assert 'always #0.416500 ck_core = ~ck_core;' in s and '`timescale 1ns/1fs' in s
out.write_text(s)
(out.parent/'credit_delta_receipt.json').write_text(json.dumps({'baseline_sha256':hashlib.sha256(original.encode()).hexdigest(),'reviewed_credit_template_sha256':hashlib.sha256(r.encode()).hexdigest(),'candidate_sha256':hashlib.sha256(s.encode()).hexdigest(),'reverse_patch_byte_identical':True,'only_delta':'reviewed board class-credit helper/sender/counter','preserved':['GEN1 far word_generation','original POST-only termination','all existing clock/input bindings','DUT/children/image/ELF sources']},indent=2)+'\n')
