#!/usr/bin/env python3
"""Generate default-off actual publication mux copies; no HDL execution."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/rtl/dsrom_ckv_publication_source_prepare_20261003'


def replace_once(s,old,new):
    if s.count(old)!=1:raise ValueError('source equation count changed: '+old)
    return s.replace(old,new)


def source():
    pins=json.loads((BASE/'input_pins.json').read_text());out={}
    for p in pins:
        raw=(BASE/p['archive']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=p['sha256']:raise ValueError('source pin mismatch')
        out[Path(p['path']).name]=raw.decode()
    inner=out['ot_chip_v41x_kv_reqmux.sv'];outer=out['ot_chip_v41x_kv_rope_reqmux.sv']
    for name in ['ot_chip_v41x_kv_reqmux','ot_chip_v41x_kv_rope_reqmux']:
        text=inner if name.endswith('kv_reqmux') else outer
        text=replace_once(text,'module '+name+' #(','module '+name+'_ckvlease_r1 #(\n    parameter integer CKV_RX_LEASE = 0,')
        if name.endswith('kv_reqmux'):inner=text
        else:outer=text
    inner=replace_once(inner,') (\n    input  wire [3:0]',') (\n    input wire clk, rst_n,\n    output wire [3:0] writer_idle, writer_fault,\n    input  wire [3:0]')
    inner=replace_once(inner,'wire choose_w = w_v[s];','''wire write_pending, write_owner_c, fair_turn;
        if (CKV_RX_LEASE != 0) begin : g_lease
            // Exactly three new bits per stack, already in the full-parent model.
            reg pending_r, owner_c_r, turn_r;
            assign write_pending = pending_r;
            assign write_owner_c = owner_c_r;
            assign fair_turn = turn_r;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin pending_r <= 0; owner_c_r <= 0; turn_r <= 0; end
                else begin
                    if (m_wr_done[s] && pending_r) pending_r <= 0;
                    if (m_v[s] && m_rdy[s]) begin
                        turn_r <= choose_w;
                        if (m_we[s]) begin pending_r <= 1; owner_c_r <= !choose_w; end
                    end
                end
        end else begin : g_original
            assign write_pending = 1'b0;
            assign write_owner_c = 1'b0;
            assign fair_turn = 1'b0;
        end
        // Pending writes block new writes, but not tagged reads. No same-edge
        // completion credit: readiness uses the pre-edge pending register.
        wire eligible_w = w_v[s] && (!w_we[s] || !write_pending);
        wire eligible_c = c_v[s] && (!c_we[s] || !write_pending);
        wire choose_w = CKV_RX_LEASE ?
            (eligible_w && (!eligible_c || !fair_turn)) : w_v[s];
        assign writer_idle[s] = !write_pending;
        assign writer_fault[s] = CKV_RX_LEASE && m_wr_done[s] && !write_pending;''')
    changes={
        'assign m_v[s] = w_v[s] || c_v[s];':'assign m_v[s] = CKV_RX_LEASE ? (eligible_w || eligible_c) : (w_v[s] || c_v[s]);',
        'assign c_rdy[s] = !choose_w && m_rdy[s];':'assign c_rdy[s] = CKV_RX_LEASE ? (eligible_c && !choose_w && m_rdy[s]) : (!choose_w && m_rdy[s]);',
        "assign m_we[s] = choose_w ? w_we[s] : 1'b0;":"assign m_we[s] = choose_w ? w_we[s] : (CKV_RX_LEASE ? c_we[s] : 1'b0);",
        "assign m_wdata[s*256 +: 256] = choose_w ? w_wdata[s*256 +: 256] : '0;":"assign m_wdata[s*256 +: 256] = choose_w ? w_wdata[s*256 +: 256] : (CKV_RX_LEASE ? c_wdata[s*256 +: 256] : '0);",
        "assign m_wstrb[s*32 +: 32] = choose_w ? w_wstrb[s*32 +: 32] : '0;":"assign m_wstrb[s*32 +: 32] = choose_w ? w_wstrb[s*32 +: 32] : (CKV_RX_LEASE ? c_wstrb[s*32 +: 32] : '0);",
        'assign w_wr_done[s] = m_wr_done[s];':'assign w_wr_done[s] = CKV_RX_LEASE ? (m_wr_done[s] && write_pending && !write_owner_c) : m_wr_done[s];',
        "assign c_wr_done[s] = 1'b0; // selected CKV is read-only":"assign c_wr_done[s] = CKV_RX_LEASE && m_wr_done[s] && write_pending && write_owner_c;"}
    for old,new in changes.items():inner=replace_once(inner,old,new)
    outer=replace_once(outer,'input  wire clk, rst_n,','input  wire clk, rst_n,\n    output wire [3:0] writer_idle,')
    outer=replace_once(outer,'wire [3:0] bad_tag;','wire [3:0] bad_tag, writer_fault;')
    outer=replace_once(outer,'&& !c_we[s];','&& (CKV_RX_LEASE || !c_we[s]);')
    outer=replace_once(outer,'|| c_we[s]))','|| (!CKV_RX_LEASE && c_we[s])))')
    outer=replace_once(outer,'ot_chip_v41x_kv_reqmux #(.HAW(HAW), .TAGW(TAGW-1)) u_kv (','ot_chip_v41x_kv_reqmux_ckvlease_r1 #(.CKV_RX_LEASE(CKV_RX_LEASE), .HAW(HAW), .TAGW(TAGW-1)) u_kv (\n        .clk(clk), .rst_n(rst_n), .writer_idle(writer_idle), .writer_fault(writer_fault),')
    outer=replace_once(outer,'if (|bad_tag) fault<=1;','if ((|bad_tag) || (|writer_fault)) fault<=1;')
    return dict(ot_chip_v41x_kv_reqmux_ckvlease_r1=inner,ot_chip_v41x_kv_rope_reqmux_ckvlease_r1=outer)


def select(pending,turn,wv,ww,cv,cw):
    """Independent finite admission model, not an RTL execution result."""
    ew=wv and (not ww or not pending);ec=cv and (not cw or not pending)
    chosen='w' if ew and (not ec or not turn) else ('c' if ec else None)
    return chosen


class Writer:
    def __init__(self):self.pending=None;self.turn=False;self.visible=[]
    def accept(self,owner,sector):
        if owner not in ['w','c'] or self.pending is not None:raise ValueError('unowned or overlapping write')
        self.pending=(owner,sector);self.turn=owner=='w'
    def complete(self):
        if self.pending is None:raise ValueError('unowned completion')
        owner,sector=self.pending;self.visible.append((owner,sector));self.pending=None
        return owner


def prepare(out):
    if out.exists():raise ValueError('fresh directory required')
    copies=source();out.mkdir(parents=True)
    for name,text in copies.items():(out/(name+'.sv')).write_text(text)
    model=json.loads((ROOT/'results/uarch/dsrom_ckv_receive_lease_g0_20261003/model_r4.json').read_text())
    ledger=model['incremental']['state_bits_per_die']
    assert ledger['mux_write_outstanding']+ledger['mux_write_owner']+ledger['mux_fair_turn']==12
    plan=dict(status='ACTUAL_PUBLICATION_MUX_SOURCE_COPIES_ONLY_NOT_CONNECTED_FULL_GATE',model_commit='eae838a3ad98bde6505694aa8d4d74385856e63f',callback_commit='a019e516c1d237a1dbacf5aece5eb11ea6a6029d',default_off='CKV_RX_LEASE=0',
        instance=dict(stacks=4,sector_bits=256,mask_bits=32,HAW=30,outer_TAGW=16,inner_TAGW=15,own_row_sectors=9),
        ledger=dict(new_mux_state_bits_per_die=12,new_state_per_stack=3,new_full_group_bits=48,already_in_eae_price=True,additional_payload_storage_bits=0,existing_outer_arbitration_bits=4,existing_outer_arbitration_charged_again=False),
        semantics=dict(owner='one accepted write owner per stack retained until returned m_wr_done, independent of current arbitration',publication='request admission is not visibility; actual idx_hbm backing-write and returned completion callbacks required',drain='writer_idle exposed for complete lease/group barrier; must be joined before reset/reuse',credit='pre-edge pending prevents same-edge freed-slot reuse',reads='tagged reads may proceed during pending write; write completion cannot be routed from current selected requester',fault='unowned m_wr_done produces candidate combinational writer_fault, sampled by existing outer sticky fault; no added fault FF',reset='common reset requires all actual downstream writes/endpoints drained; reset while outstanding is not an admitted transition'),
        source_backend='retained idx_hbm source masked backing write then registered wr_done; no Russell R14 substitution or seventh client',
        readiness=dict(HDL_generated=True,HDL_compiled=False,connected_service=False,connected_full512_gate=False,hardware_area_mapping=False,physical_admission=False,fulltoken_credit=False),
        remaining=['full service lease/accepted-write counter + 16-bit peer generation/registered ACKs','nine-sector service writer_wait advancing only returned completion','actual core/tile/die ready and QK/PV descriptor/output retirement join','four-route wrapper/host callback serializer and generation reverse','reviewed source-sized full512 gate and measured host resource admission before compile'])
    (out/'source_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (out/'source_manifest.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir())},indent=2)+'\n')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();prepare(a.out)
