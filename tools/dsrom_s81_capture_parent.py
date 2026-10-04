"""Actual S81 enclosing capture hookup; selected behavioral VM, no physical credit.

Original ports/arithmetic/last-write ordering are preserved. Failed visibility
quarantines accepted debt instead of crediting an overwritten VM assignment.
"""
from pathlib import Path
import hashlib,json
from dsrom_s81_phase_capture_join import install_bound_spine
from dsrom_s81_capture_install import replace_once as one
ROOT=Path(__file__).resolve().parents[1]
SPINE='rtl/v41die/ot_v41_spine_w17w10.sv'
ADAPTER='rtl/v41die/ot_v41_rom_adapt.sv'

PARAM='    parameter integer S81_CAPTURE=0,\n'
INPUTS="""    input wire [ROM_R*19-1:0] capture_root_rows,
    input wire [46:0] capture_identity,
    input wire capture_reset_request,
    output wire capture_live,capture_drained,capture_fault,
"""


def hook(role,s):
    anchor='    parameter integer IDX_DRAIN_LOOKAHEAD=0,'
    s=one(s,anchor,PARAM+anchor)
    ports=INPUTS
    if role=='core':ports+='    input wire [ROM_R-1:0] capture_vm_accept,\n'
    else:ports+='    output wire [ROM_R-1:0] capture_vm_accept,\n'
    if role=='top':
        ports=ports.replace('input wire [46:0] capture_identity','output wire [46:0] capture_identity')
    s=one(s,'    input  wire              clk,',ports+'    input  wire              clk,')
    connections='''.capture_root_rows(capture_root_rows),.capture_identity(capture_identity),
        .capture_reset_request(capture_reset_request),.capture_vm_accept(capture_vm_accept),
        .capture_live(capture_live),.capture_drained(capture_drained),.capture_fault(capture_fault),'''
    if role=='core':
        s=one(s,'ot_v41_rom_adapt #(', 'ot_v41_rom_adapt #(.S81_CAPTURE(S81_CAPTURE),')
        s=one(s,'.s_go(s_go),', '.capture_command_ready(!capture_live && !capture_fault && !capture_reset_request),.s_go(s_go),')
        s=one(s,'ot_v41_spine_w17w10 #(', 'ot_v41_spine_w17w10 #(.CAPTURE_ENABLE(S81_CAPTURE),.CAPTURE_S81_PROFILE(S81_CAPTURE),.CAPTURE_CAPACITY(1),.CAPTURE_VM_ALWAYS_ACCEPT(1),')
        s=one(s,'.go(s_go), .i_ph(s_ph)', connections+'\n            .go(s_go), .i_ph(s_ph)')
        s=one(s,"assign rom_ready_w = 1'b1;", "assign capture_live=0;assign capture_drained=1;assign capture_fault=0;\n        assign rom_ready_w = 1'b1;")
    else:
        target={'tile':'ot_hdc_core_v41x','die':'ot_chip_v41x_tile','top':'ot_chip_v41x_die_owner_safe_c8'}[role]
        s=one(s,target+' #(',target+' #(.S81_CAPTURE(S81_CAPTURE),')
        anchor={ 'tile':'.clk(clk), .rst_n(rst_n), .start(start)',
                 'die':'.clk(clk), .rst_n(rn), .rom_fb(rom_fb)',
                 'top':'.clk(clk), .rst_n(rst_n), .rom_fb(rom_fb)'}[role]
        s=one(s,anchor,connections+'\n        '+anchor)
    if role=='tile':
        s=one(s,'for (q = 0; q < ROM_R; q = q + 1) if (rom_we[q]) vm[rom_waddr[q*AW +: VM_AW]] <= rom_wdata[32*q +: 32];',
          'for (q = 0; q < ROM_R; q = q + 1) if (rom_we[q] && (!S81_CAPTURE || capture_vm_accept[q])) vm[rom_waddr[q*AW +: VM_AW]] <= rom_wdata[32*q +: 32];')
        s=one(s,'\nendmodule',VM_ACCEPT+'\nendmodule')
    if role=='die':
        s=one(s,'assign c8_write_quiet=(&c8_jquiet)',
          "wire capture_visibility_quiet=!S81_CAPTURE || (!capture_live && capture_drained && !capture_fault && !(|capture_vm_accept));\n    assign c8_write_quiet=capture_visibility_quiet && (&c8_jquiet)")
        s=one(s,'assign c8_write_quarantine=|c8_jquarantine;assign c8_write_fault=|c8_jfault;',
          'assign c8_write_quarantine=(|c8_jquarantine) || (S81_CAPTURE && capture_fault);assign c8_write_fault=(|c8_jfault) || (S81_CAPTURE && capture_fault);')
    if role=='top':
        s=one(s,'\nendmodule',"\n    assign capture_identity=C8_CONTEXT ? c8_engine_identity : c8_position_identity;\nendmodule")
        s=one(s,'\nendmodule',COMMIT_TRACE+'\nendmodule')
    return s


def dependencies(paths,out):
    out=Path(out)
    matches=[p for p in paths if p.as_posix().endswith(SPINE)]
    if len(matches)!=1:raise ValueError('actual selected spine missing/ambiguous')
    receipt=install_bound_spine(matches[0],out/'spine')
    spine=Path(receipt['generated'])
    # Core address port is AW30; actual tile VM is 19bit, not 1Giword.
    spine.write_text(one(spine.read_text(),'.VM_AW(VAW)', '.VM_AW(19)'))
    receipt['before_actual_VM_bound_sha256']=receipt['generated_sha256']
    receipt['generated_sha256']=hashlib.sha256(spine.read_bytes()).hexdigest()
    receipt['actual_VM_AW']=19
    (out/'spine'/'source_join.json').write_text(json.dumps(receipt,indent=2)+'\n')
    adapters=[p for p in paths if p.as_posix().endswith(ADAPTER)]
    if len(adapters)!=1:raise ValueError('actual selected adapter missing/ambiguous')
    s=adapters[0].read_text()
    s=one(s,'    parameter integer AW = 30,',PARAM+'    parameter integer AW = 30,')
    s=one(s,'    input  wire              clk,','    input wire capture_command_ready,\n    input  wire              clk,')
    s=one(s,'assign ready = st == S_IDLE && s_ready;',
          'assign ready = st == S_IDLE && (S81_CAPTURE ? capture_command_ready : s_ready);')
    # S_GO still uses actual spine ready AFTER lookup. No extra state/edge.
    adapter=out/'adapter'/adapters[0].name;adapter.parent.mkdir(parents=True,exist_ok=False);adapter.write_text(s)
    replacements={matches[0]:spine,adapters[0]:adapter}
    result=[replacements.get(p,p) for p in paths]
    for p in receipt['sources']:
        p=Path(p)
        if p!=spine and p not in result:result.append(p)
    # Retained C8 completion extension accidentally left its separator in a
    # comment. Copy-only syntax repair, no interface/event/arithmetic change.
    phys=[p for p in result if p.name=='ot_chip_v41x_hbm3e_phy_c8.sv']
    if len(phys)==1:
        text=phys[0].read_text()
        old='output wire [31:0]          w_reads        // W port sector reads,'
        if old in text:
            dest=out/'syntax'/phys[0].name;dest.parent.mkdir(parents=True,exist_ok=False)
            dest.write_text(one(text,old,'output wire [31:0]          w_reads,       // W port sector reads'))
            result=[dest if p==phys[0] else p for p in result]
    return result


VM_ACCEPT=r'''
    // Literal retained last-write-wins VM semantics: credit only surviving rows.
    // This is a behavioral mutable-VM context, NOT a 128-port SRAM fit claim.
    reg [ROM_R-1:0] capture_commit;
    integer cr,cs,cl;
    reg [VM_AW-1:0] ca;
    always @* begin
      capture_commit=0;ca=0;
      for(cr=0;cr<ROM_R;cr=cr+1)begin
        ca=rom_waddr[cr*AW +: VM_AW];
        capture_commit[cr]=S81_CAPTURE && rst_n && !capture_reset_request && X_ROM && rom_we[cr] && (rom_waddr[cr*AW +:AW] < (AW'(1)<<VM_AW));
        // Later ROM ports and all later source-owned writers retain precedence.
        for(cs=cr+1;cs<ROM_R;cs=cs+1)
          if(rom_we[cs] && ca==rom_waddr[cs*AW +:VM_AW])capture_commit[cr]=0;
        for(cs=0;cs<G;cs=cs+1)for(cl=0;cl<W;cl=cl+1)
          if(vw_me_we[cs] && vw_me_mask[cs*W+cl] && ca==VM_AW'({vw_me_addr[cs*AW +:VM_AW-4],4'b0}+cl))capture_commit[cr]=0;
        for(cs=0;cs<SW;cs=cs+1)begin
          if(vw_su_we[cs] && ca==vw_su_addr[cs*AW +:VM_AW])capture_commit[cr]=0;
          if(vw_rd_we[cs] && ca==vw_rd_addr[cs*AW +:VM_AW])capture_commit[cr]=0;
        end
        for(cs=0;cs<SUN;cs=cs+1)
          if(xs_vm_we[cs] && ca==xs_vm_waddr[cs*AW +:VM_AW])capture_commit[cr]=0;
        for(cs=0;cs<SUN/8;cs=cs+1)
          if(xs_res_we[cs] && ca==xs_res_addr[cs*AW +:VM_AW])capture_commit[cr]=0;
        if(vw_xe_we && ca==vw_xe_addr[VM_AW-1:0])capture_commit[cr]=0;
        for(cl=0;cl<32;cl=cl+1)begin
          if(ww_q_we && ww_q_mask[cl] && ca==VM_AW'(ww_q_addr[VM_AW-1:0]+cl))capture_commit[cr]=0;
          if(ww_x_we && ww_x_mask[cl] && ca==VM_AW'(ww_x_addr[VM_AW-1:0]+cl))capture_commit[cr]=0;
        end
        for(cl=0;cl<16;cl=cl+1)begin
          if(xa_we && ca=={xa_waddr,4'(cl)})capture_commit[cr]=0;
          for(cs=0;cs<4;cs=cs+1)
            if(xb_we4[cs] && ca=={xb_waddr4[cs*(VM_AW-4) +:(VM_AW-4)],4'(cl)})capture_commit[cr]=0;
        end
      end
    end
    assign capture_vm_accept=capture_commit;
'''

COMMIT_TRACE=r'''
`ifndef SYNTHESIS
    initial if(S81_CAPTURE && (!C8_CONTEXT || !C8_PUBLICATION || ROM_R!=128))
      $fatal(1,"S81 capture requires native R128 saved C8 identity/publication");
    always @(posedge clk) if(rst_n && S81_CAPTURE && S81_COMMAND_TRACE)begin
      for(integer rr=0;rr<ROM_R;rr=rr+1)if(capture_vm_accept[rr])
        $display("S81_VM_COMMIT stage=%0d rank=%0d identity=%0d root=%0d addr=%0d raw=%08x",S81_TRACE_STAGE,RANK,capture_identity,rr,dut.u_tile.rom_waddr[rr*30 +:30],dut.u_tile.rom_wdata[rr*32 +:32]);
      if(c8_retire_v && (capture_live || capture_fault || !c8_write_quiet))
        $fatal(1,"C8 retirement before actual ROM visibility/fault fence");
    end
`endif
'''
