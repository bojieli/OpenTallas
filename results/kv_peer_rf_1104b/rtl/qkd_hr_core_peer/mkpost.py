import sys,re
src=sys.argv[1]; srv=sys.argv[2]; out=sys.argv[3]
t=open(src).read()
a=t.index("// KV-PEER12: MU 1-only flat copy"); b=t.index(" reg[3:0]owned,issued")
t=t[:a]+" function automatic sel4(input[3:0]x,input[1:0]i);sel4=i[1]?(i[0]?x[3]:x[2]):(i[0]?x[1]:x[0]);endfunction\n"+t[b:]
t=t[t.index("`timescale"):]
t=t.replace("`timescale 1ns/1ps\n","`timescale 1ns/1ps\n// DIE-KV-70 11-04 RE-FORM of qkd_host_post_collector_mu: identity compares drive only f (sticky, blocks post_go); the retire and CQ\n// actions load on their pulse.  4-bit per-user flags read through sel4 so RTL and gate name the same registers.\n",1)
t=t.replace("module qkd_host_post_collector_mu","module qkd_host_post_collector_r3")
def R(a,b,cnt=1):
    global t
    assert t.count(a)>=1 and (cnt==0 or t.count(a)==cnt),(a,t.count(a))
    t=t.replace(a,b)
R("wire alone=","wire o_h=sel4(owned,h),ts_h=sel4(terminal_seen,h),is_h=sel4(issued,h),re_h=sel4(retired,h),cqn_h=sel4(cq_needed,h),cqs_h=sel4(cq_seen,h);\n wire o_a=sel4(owned,ua),i_i=sel4(issued,ui),r_i=sel4(retired,ui),nx_i=sel4(nx_v,ui),nx_h=sel4(nx_v,h);\n wire o_r=sel4(owned,ur),i_r=sel4(issued,ur),r_r=sel4(retired,ur);\n wire o_c=sel4(owned,uc),r_c=sel4(retired,uc),cn_c=sel4(cq_needed,uc),cs_c=sel4(cq_seen,uc);\n wire o_t=sel4(owned,ut),ts_t=sel4(terminal_seen,ut);\n wire t_bad=!o_t||ts_t||terminal_tag!=tag[ut]||terminal_gen!=gen[ut]||pn==3'd4;\n wire alone=")
R("wire post_go=pn!=0&&owned[h]&&terminal_seen[h]&&","wire post_go=pn!=0&&o_h&&ts_h&&")
R("&&issued[h]&&retired[h]&&(!cq_needed[h]||cq_seen[h]||MUT==1);","&&is_h&&re_h&&(!cqn_h||cqs_h||MUT==1);")
R("step_issue_v&&issued[ui]&&retired[ui]&&!nx_v[ui]&&","step_issue_v&&i_i&&r_i&&!nx_i&&")
R("if(owned[ua])f<=1;","if(o_a)f<=1;")
R("if(issued[ui]||step_pos","if(i_i||step_pos")
R("if(!owned[ur]||!issued[ur]||retired[ur]||!exact_step||bad_sr)f<=1;\n    else begin retired[ur]<=1;cq_needed[ur]<=step_retire_cq;token[ur]<=step_retire_token;end",
  "if(!o_r||!i_r||r_r||!exact_step||bad_sr)f<=1;\n    retired[ur]<=1;cq_needed[ur]<=step_retire_cq;token[ur]<=step_retire_token;")
R("if(!owned[uc]||!retired[uc]||!cq_needed[uc]||cq_seen[uc]||!exact_cq||bad_sc)f<=1;\n    else cq_seen[uc]<=1;","if(!o_c||!r_c||!cn_c||cs_c||!exact_cq||bad_sc)f<=1;\n    cq_seen[uc]<=1;")
R("if(!owned[ut]||terminal_seen[ut]||terminal_tag!=tag[ut]||terminal_gen!=gen[ut]||pn==3'd4)f<=1;","if(t_bad)f<=1;")
R("else if(nx_v[h])begin","else if(nx_h)begin")
R("3'(terminal_accepted&&!(!owned[ut]||terminal_seen[ut]||terminal_tag!=tag[ut]||terminal_gen!=gen[ut]||pn==3'd4))","3'(terminal_accepted&&!t_bad)")
R("wire post_go=pn!=0&&o_h&&","wire post_ready=pn!=0&&o_h&&")
R(" // next-issue hold: the user's owned step retired"," reg post_go_q;always @(posedge ck or negedge por_n)if(!por_n)post_go_q<=0;else post_go_q<=post_ready&&!post_go_q;\n wire post_go=post_go_q&&!f;   // POST +1 edge; a held true condition is a legal source timing\n // next-issue hold: the user's owned step retired")
R(" wire[1:0]h=pq[pr];\n"," reg[1:0]h;always @(posedge ck)h<=pq[pr];   // head user registered: after a pop owned[old head] is already clear; a just written single entry is the only owned+seen user\n reg t_bad_q;\n")
R("    if(t_bad)f<=1;\n    else begin terminal_seen[ut]<=1;release_required[ut]<=cancel_release_required;pq[pw]<=ut;pw<=pw+1'b1;end\n","    terminal_seen[ut]<=1;release_required[ut]<=cancel_release_required;pq[pw]<=ut;pw<=pw+1'b1;\n")
R("   pn<=pn+3'(terminal_accepted&&!t_bad)-3'(post_go);\n","   t_bad_q<=terminal_accepted&&t_bad;if(t_bad_q)f<=1;   // terminal compares drive only the sticky fault (+1 edge)\n   pn<=pn+3'(terminal_accepted)-3'(post_go);\n")
R("   pw<=0;pr<=0;pn<=0;pr_v<=0;","   t_bad_q<=0;pw<=0;pr<=0;pn<=0;pr_v<=0;")
open(out,"w").write(t)
s=open(srv).read()
a=s.index("// KV-PEER12: MU 1-only flat copy"); b=s.rindex(" qkd_host_lifecycle_collected_mu #(")
s=s[:a]+s[b:]
s=s[s.index("`timescale"):]
s=s.replace("module qkd_host_coordinator_services_mu","module qkd_host_coordinator_services_r3").replace("qkd_host_lifecycle_collected_mu #(","qkd_host_lifecycle_r3 #(").replace("qkd_host_post_collector_mu #(","qkd_host_post_collector_r3 #(")
open(out.replace("qkd_host_post_collector_r3","qkd_host_coordinator_services_r3"),"w").write(s)
