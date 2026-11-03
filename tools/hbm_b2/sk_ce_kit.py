#!/usr/bin/env python3
"""Build the current HBM tail CE cores, preserving the QUAD5 proven arithmetic.

The plan already replaced sink_clk with registered sk_en data. Old hardened
recipes still select the generated-clock tops. This adapter supplies the exact
CE tops and derives the remainder by cutting only its Sinkhorn instance.
"""
from pathlib import Path
import importlib.util, json, re, sys
REPO=Path(__file__).resolve().parents[2]
HERE=REPO/"physical/die_plan/hbm_arch_cores"
CE=REPO/"rtl/hbm_accel/cores_split/sk_en_q4"

def must(text,old,new):
    if text.count(old)!=1: raise ValueError((old,text.count(old)))
    return text.replace(old,new)

def rest_source():
    a=(CE/"ot_hgi_hc_tail_static_se.sv").read_text()
    a=re.search(r"(?ms)^module ot_hgi_hc_tail_static_se\b.*?^endmodule",a)[0]
    a=must(a,"module ot_hgi_hc_tail_static_se #(","module ot_hbm_hc_tail_static_rest_ce #(")
    a=must(a,"    output reg fault\n);","    output reg fault,\n    output wire [511:0] sk_in_e,\n    input wire sk_in_ready, sk_out_valid, sk_fault,\n    input wire [511:0] sk_y\n);")
    i=a.index("    wire sk_en_hop;");j=a.index("    reg sink_fault;")
    a=a[:i]+"    assign sk_in_e = se; assign sr = sk_in_ready; assign sv = sk_out_valid;\n    assign sy = sk_y; assign sf = sk_fault; assign sbusy = 1\x27b0;\n"+a[j:]
    b=(CE/"ot_hbm_hc_tail_unit_static_se.sv").read_text()
    b=re.search(r"(?ms)^module ot_hbm_hc_tail_unit_static_se\b.*?^endmodule",b)[0]
    b=must(b,"module ot_hbm_hc_tail_unit_static_se #(","module ot_hbm_hc_tail_rest_core_ce #(")
    b=must(b,"    output wire          fault\n);","    output wire          fault,\n    output wire sk_en_sk, sk_in_valid,\n    output wire [511:0] sk_in_e,\n    input wire sk_in_ready, sk_out_valid, sk_fault,\n    input wire [511:0] sk_y\n);")
    b=must(b,"ot_hgi_hc_tail_static_se #(.MUT_PRE(MUT_PRE), .NSTA(NSTA)) u_tail (","ot_hbm_hc_tail_static_rest_ce #(.MUT_PRE(MUT_PRE), .NSTA(NSTA)) u_tail (")
    b=must(b,".e_ready(), .result_v(tv), .result(result), .fault(tf));",".e_ready(), .result_v(tv), .result(result), .fault(tf),\n        .sk_in_e(sk_in_e), .sk_in_ready(sk_in_ready), .sk_out_valid(sk_out_valid), .sk_fault(sk_fault), .sk_y(sk_y));\n    assign sk_en_sk = sk_en_o; assign sk_in_valid = sl;")
    # Optional address predecode. The existing calendar computes the NEXT
    # address a cycle ahead; no data, valid, reset or external cycle is retimed.
    a=must(a,"    parameter integer NSTA=0          // die stations", "    parameter integer PREDECODE_INDEX=0,\n    parameter integer NSTA=0          // die stations")
    a=must(a,"    wire [4:0] i=p1?", "    wire [4:0] i_comb=p1?")
    anchor="    wire mv=p1||(p7&&i>=4), av=p2||p3||p5||(p7&&i<4);"
    predecode="""    wire [4:0] i;
    generate if (PREDECODE_INDEX != 0) begin:g_predecode_index
        // Match the control block's exact nonblocking priority, including
        // launch+capture and held/inactive ages. The invalid-cycle address
        // is preserved too, so all unchanged arithmetic sees identical bits.
        wire [8:0] age_next=launch?9'd1:
            (active&&age<EREADY+1)?age+9'd1:age;
        wire active_next=sink_capture?1'b0:launch?1'b1:active;
        function automatic [4:0] address(input [8:0] a,input act);
            if(act&&a>=P1&&a<P1+24)address=5'(a-P1);
            else if(act&&a>=P2&&a<P2+24)address=5'(a-P2);
            else if(act&&a>=P3&&a<P3+16)address=5'(a-P3+8);
            else if(act&&a>=P4&&a<P4+24)address=5'(a-P4);
            else if(act&&a>=P5&&a<P5+8)address=5'(a-P5);
            else if(act&&a>=P6&&a<P6+8)address=5'(a-P6);
            else address=5'(a-P7);
        endfunction
        reg [4:0] i_q;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)i_q<=5'(0-P7);
            else i_q<=address(age_next,active_next);
        assign i=i_q;
    end else begin:g_comb_index
        assign i=i_comb;
    end endgenerate
"""
    a=must(a,anchor,predecode+anchor)
    # RE-FORM 11-03 (OWNER TWO-STRIKES, DIE-HBM-61/RTL-TAILX): registered phase
    # flags + index (next-age predecode), an operand capture register between the
    # 24:1 operand select and every arithmetic front end, and a two-stage max4.
    # Internal re-timing only: MAX +2 issue edges, P3 +2; every external port
    # keeps its cycle (results/hbm_reform_tailx_1103, cycles table d44v).
    a=must(a,"    parameter integer PREDECODE_INDEX=0,\n","    parameter integer PREDECODE_INDEX=0,\n    parameter integer REFORM=1,       // 0 = pre-RE-FORM single-stage form (bench gold only)\n")
    a=must(a,"MAX=55,P3=56,","MAX=55+REFORM,P3=56+2*REFORM,")
    a=must(a,"reg [31:0] t[0:23],b[0:23],s[0:2],mx[0:3];","reg [31:0] t[0:23],b[0:23],s[0:2],mx[0:3],mlo[0:3],mhi[0:3];")
    old_p="".join(f"    wire p{k}=active&&age>=P{k}&&age<P{k}+{n};\n" for k,n in ((1,24),(2,24),(3,16),(4,24),(5,8),(6,8),(7,8)))
    new_p=old_p.replace("    wire p","    wire p").replace("=active","_c=active").replace("wire p1_c","wire p1_c")
    new_p=new_p.replace("wire p1=","wire p1_c=")
    new_p+="""    wire p1,p2,p3,p4,p5,p6,p7;
    generate if (PREDECODE_INDEX >= 2 || REFORM != 0) begin:g_predecode_phase
        // Phase flags registered from the next age (same priority as the
        // control block below), so no age compare sits in front of the select.
        wire [8:0] age_nx=launch?9'd1:
            (active&&age<EREADY+1)?age+9'd1:age;
        wire act_nx=sink_capture?1'b0:launch?1'b1:active;
        reg [7:1] p_q;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)p_q<=7'd0;
            else p_q<={act_nx&&age_nx>=P7&&age_nx<P7+8, act_nx&&age_nx>=P6&&age_nx<P6+8,
                       act_nx&&age_nx>=P5&&age_nx<P5+8, act_nx&&age_nx>=P4&&age_nx<P4+24,
                       act_nx&&age_nx>=P3&&age_nx<P3+16, act_nx&&age_nx>=P2&&age_nx<P2+24,
                       act_nx&&age_nx>=P1&&age_nx<P1+24};
        assign {p7,p6,p5,p4,p3,p2,p1}=p_q;
    end else begin:g_comb_phase
        assign {p7,p6,p5,p4,p3,p2,p1}={p7_c,p6_c,p5_c,p4_c,p3_c,p2_c,p1_c};
    end endgenerate
"""
    a=must(a,old_p,new_p)
    a=must(a,"    wire [4:0] i_comb=p1?5'(age-P1):p2?5'(age-P2):p3?5'(age-P3+8):\n        p4?5'(age-P4):p5?5'(age-P5):p6?5'(age-P6):5'(age-P7);",
             "    wire [4:0] i_comb=p1_c?5'(age-P1):p2_c?5'(age-P2):p3_c?5'(age-P3+8):\n        p4_c?5'(age-P4):p5_c?5'(age-P5):p6_c?5'(age-P6):5'(age-P7);")
    a=must(a,"generate if (PREDECODE_INDEX != 0) begin:g_predecode_index","generate if (PREDECODE_INDEX != 0 || REFORM != 0) begin:g_predecode_index")
    i=a.index("    wire [31:0] ma=t[i],mb=");j=a.index("    function automatic greater")
    a=a[:i]+"""    wire [31:0] mb=p1?s[(i<4)?0:(i<8)?1:2]:32'h40000000;
    wire [31:0] ab=p2?b[i]:p3?(mx[(i-8)>>2]^32'h80000000):
        p5?32'h3f800000:(MUT_PRE?32'd0:HC_EPS);
    // OPQ: operand capture register (RE-FORM). t[i] is captured once and feeds
    // mul a, add a, exp x (sign flipped below i=8) and div b; valids and the
    // second operands are captured with it. Every unit issues one edge later
    // and its index delay line is one edge longer, so write-back slots move by
    // exactly one edge; the schedule constants above absorb the MAX/P3 shift.
    localparam integer OPQ=(REFORM!=0)?1:0;
    wire mv_u,av_u,ev_u,dv_u,neg_u;
    wire [31:0] ti_u,mb_u,ab_u;
    generate if (OPQ != 0) begin:g_operand_q
        reg mv_q,av_q,ev_q,dv_q,neg_q;
        reg [31:0] ti_q,mb_q,ab_q;
        always @(posedge clk or negedge rst_n)
            if(!rst_n){mv_q,av_q,ev_q,dv_q}<=4'd0;
            else {mv_q,av_q,ev_q,dv_q}<={mv,av,p4,p6};
        always @(posedge clk)begin ti_q<=t[i];mb_q<=mb;ab_q<=ab;neg_q<=(i<8);end
        assign {mv_u,av_u,ev_u,dv_u,neg_u}={mv_q,av_q,ev_q,dv_q,neg_q};
        assign ti_u=ti_q; assign mb_u=mb_q; assign ab_u=ab_q;
    end else begin:g_operand_c
        assign {mv_u,av_u,ev_u,dv_u,neg_u}={mv,av,p4,p6,i<8};
        assign ti_u=t[i]; assign mb_u=mb; assign ab_u=ab;
    end endgenerate
    wire [31:0] ey,dy,my,ay;
    wire mo,ao,eo,do_,ef,df;
    wire [1:0] me,ae;
    wire [4:0] mi,ai,ei,di;
    ot_hdc_fp32_mul_fast mul(.clk(clk),.rst_n(rst_n),.valid_in(mv_u),.a(ti_u),.b(mb_u),.y(my),.err(me),.valid_out(mo));
    ot_hdc_fp32_add_fast add(.clk(clk),.rst_n(rst_n),.valid_in(av_u),.a(ti_u),.b(ab_u),.y(ay),.err(ae),.valid_out(ao));
    ot_hdc_v41x_exp #(.LM(3),.LA(3)) exp_(.clk(clk),.rst_n(rst_n),.v(ev_u),
        .x({ti_u[31]^neg_u,ti_u[30:0]}),.y(ey),.vo(eo),.fault(ef));
    ot_hdc_v41x_fdiv div_(.clk(clk),.rst_n(rst_n),.v(dv_u),.a(32'h3f800000),.b(ti_u),.y(dy),.vo(do_),.fault(df));
    ot_hdc_delay #(.W(5),.D(3+OPQ)) mt(clk,rst_n,i,mi);
    ot_hdc_delay #(.W(5),.D(3+OPQ)) at(clk,rst_n,i,ai);
    ot_hdc_delay #(.W(5),.D(49+OPQ)) et(clk,rst_n,i,ei);
    ot_hdc_delay #(.W(5),.D(19+OPQ)) dt(clk,rst_n,i,di);
"""+a[j:]
    old_max="""        if(active&&age==MAX)for(integer r=0;r<4;r=r+1)begin:maximum
            reg [31:0] v;
            v=t[8+4*r];
            for(integer c=1;c<4;c=c+1)if(greater(t[8+4*r+c],v))v=t[8+4*r+c];
            mx[r]<=v;
        end
"""
    new_max=old_max.replace("if(active&&age==MAX)","if(REFORM==0&&active&&age==MAX)")+"""        // RE-FORM two-stage max4: stable pair winners at MAX (a tie keeps the
        // lower index; greater() ties only +-0 against +-0, which P3's add
        // makes unobservable), the final compare one edge later.
        if(REFORM!=0&&active&&age==MAX)for(integer r=0;r<4;r=r+1)begin
            mlo[r]<=greater(t[9+4*r],t[8+4*r])?t[9+4*r]:t[8+4*r];
            mhi[r]<=greater(t[11+4*r],t[10+4*r])?t[11+4*r]:t[10+4*r];
        end
        if(REFORM!=0&&active&&age==MAX+1)for(integer r=0;r<4;r=r+1)
            mx[r]<=greater(mhi[r],mlo[r])?mhi[r]:mlo[r];
"""
    a=must(a,old_max,new_max)
    b=must(b,"    parameter integer NSTA = 0,", "    parameter integer PREDECODE_INDEX = 0,\n    parameter integer NSTA = 0,")
    b=must(b,".NSTA(NSTA)) u_tail", ".NSTA(NSTA), .PREDECODE_INDEX(PREDECODE_INDEX), .REFORM(REFORM)) u_tail")
    b=must(b,"    parameter integer PREDECODE_INDEX = 0,\n", "    parameter integer PREDECODE_INDEX = 0,\n    parameter integer REFORM = 1,     // RE-FORM 11-03 (0 = bench gold only)\n")
    return "// GENERATED by tools/hbm_b2/sk_ce_kit.py: QUAD5 CE remainder, Sinkhorn cut only.\n`timescale 1ns/1ps\n`default_nettype none\n"+a+"\n\n"+b+"\n`default_nettype wire\n"

def rest_wrapper(module, tail, contract):
    # Same per-bit cut map as the old rest wrapper; only the clock-output port
    # becomes registered enable data and selects the CE remainder.
    src=HERE/f"split/wip_unverified/ot_hbm_hc_root_static__tail{tail}_rest.sv"
    t=src.read_text()
    t=must(t,f"module ot_hbm_hc_root_static__tail{tail}_rest (",f"module {module} (")
    t=t.replace("ot_hbm_hc_tail_rest_core u_core","ot_hbm_hc_tail_rest_core_ce u_core")
    t=t.replace("sink_clk","sk_en_sk").replace("sk_clk","sk_en_sk")
    if contract != "native-trial":
        cap=299
        t=must(t,"ot_hbm_hc_tail_rest_core_ce u_core (",f"ot_hbm_hc_tail_rest_core_ce #(.CAP({cap})) u_core (")
    return t

def recipes(contract):
    base=json.loads((HERE.parent/"hbm/cores/harden/recipes_split.json").read_text())
    out={}
    for kind in ("step0","steady"):
        r=dict(base[f"ot_hbm_hc_root_static__tail0_sk_{kind}__155.52x172.8"])
        r["files"]=[p if p!="rtl/hdc/v41/ot_hdc_sinkhorn_s.sv" else "rtl/hbm_accel/cores_split/sk_en_q4/ot_hdc_sinkhorn_se.sv" for p in r["files"]]
        r["top"]=f"ot_hdc_sk_{kind}_en";r["params"]=dict(r["params"],EN_LAND=1)
        r["source"]="QUAD5 CE: results/hbm_mu_quad_5/sk_en (equiv + lockstep + mutants PASS); core enables are landed data."
        if contract != "native-trial":
            r["params"]["EN_LAND"]=1
            if kind=="step0":
                r["files"]=[x.replace("ot_hdc_sinkhorn_se.sv","ot_hdc_sinkhorn_se_phys.sv") for x in r["files"]]
                r["top"]="ot_hdc_sk_step0_en_phys";r["params"]["EN_DELAY"]=2
        out[f"ot_hbm_hc_root_static__tailx_sk_{kind}"]=r
    for tail, module in ((0,"ot_hbm_hc_root_static__tailx_rest__v6bc7f2"),(1,"ot_hbm_hc_root_static__tailx_rest__v4f4566")):
        r=dict(base[f"ot_hbm_hc_root_static__tail{tail}_rest__155.52x172.8"])
        r["top"]="ot_hbm_hc_tail_rest_core_ce"
        r["files"]=[x if not x.endswith("/ot_hbm_hc_tail_rest_core.sv") else "rtl/hbm_accel/cores_split/sk_en_q4/ot_hbm_hc_tail_rest_core_ce.sv" for x in r["files"]]
        out[module]=r
    return out

def main():
    if sys.argv[1:]==["--emit-rest"]:
        print(rest_source(),end="");return
    if "--ce-shell-contract" not in sys.argv:
        raise SystemExit("CE kits require explicit --ce-shell-contract native-trial|land1-cap3; no unpriced physical default")
    ci=sys.argv.index("--ce-shell-contract");contract=sys.argv[ci+1];del sys.argv[ci:ci+2]
    if contract not in ("native-trial","land1-cap3"):
        raise SystemExit("CE shell contract has no completed gate: "+contract)
    spec=importlib.util.spec_from_file_location("gen_core_kit_hbm",HERE/"gen_core_kit_hbm.py")
    mod=importlib.util.module_from_spec(spec);sys.path.insert(0,str(HERE));sys.path.insert(0,str(REPO/"tools/die_plan"));spec.loader.exec_module(mod)
    vi=sys.argv.index("--view")+1
    module=sys.argv[vi].split("@")[0]
    if "tailx_rest" in module and "--wrapper" not in sys.argv:
        tail=0 if module.endswith("v6bc7f2") else 1 if module.endswith("v4f4566") else None
        if tail is None:raise SystemExit("unknown rest interface: explicit native cut map required")
        out=Path(sys.argv[sys.argv.index("--out")+1])/"ce_wrappers"
        out.mkdir(parents=True,exist_ok=True);w=out/f"{module}.sv";w.write_text(rest_wrapper(module,tail,contract))
        sys.argv += ["--wrapper",str(w)]
    # Explicit --recipe-key is required: no global default or canonical mapping is changed.
    mod.main(recipe_overrides=recipes(contract))
    out=Path(sys.argv[sys.argv.index("--out")+1]);view=sys.argv[sys.argv.index("--view")+1]
    tag=sys.argv[sys.argv.index("--tag")+1] if "--tag" in sys.argv else ""
    kit=out/(re.sub(r"[^A-Za-z0-9_.-]","_",view)+("-"+tag if tag else ""))
    json.dump(dict(schema="opentallas.hbm.ce_phase_contract.v1",contract=contract,core=module,period_ps=833,enable_period_edges=7,step0_phase_after_steady_edges=2 if contract!="native-trial" else 0,native_tail_latency_edges=503,physical_tail_latency_edges=508 if contract=="land1-cap3" else None,status="FUNCTIONAL_PASS" if contract!="native-trial" else "TRIAL_ONLY_PHYSICAL_PHASE_FAIL",route_hold="CE timing contract awaiting OWNER; no multicycle exception applied"),open(kit/"ce_phase_contract.json","w"),indent=2)

if __name__=="__main__":main()
