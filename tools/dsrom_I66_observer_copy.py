"""Generate a default-off SIMULATION ONLY wrapper copy; never edit RTL owners.

The new hooks observe local source events. They do not implement stage dispatch,
credit, capture ACK, transport, or a physical VM provider. A generated class and
current compiler/source enrollment must be reviewed before use.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT/'results/uarch/dsrom_I66_provider_clock_contract_20261002/inputs/runtime_wrapper.sv.txt'
COPY = ROOT/'rtl/test/v41_runtime/ot_v41_rt_die_I66_observation_only.sv'
BEGIN = '// BEGIN I66 SIMULATION OBSERVER\n'
END = '// END I66 SIMULATION OBSERVER\n'
PARAM = '    parameter integer SIM_OBSERVE_I66 = 0, // simulation hooks; off by default\n'
HOOKS = r'''// BEGIN I66 SIMULATION OBSERVER
    // synthesis translate_off
    // No engine writes, delayed evals, new hardware ports or transport ACKs.
    // Simulation sequence is correlation only; it is not a DUT generation.
    generate if (SIM_OBSERVE_I66 != 0) begin : g_i66_observer
        longint unsigned obs_edge = 0;
        longint unsigned obs_sequence = 0;
        reg [ROM_R-1:0] pending_we = '0;
        reg [ROM_R*30-1:0] pending_addr = '0;
        reg [ROM_R*32-1:0] pending_data = '0;
        reg [3:0] cdma_we = '0;
        reg [4*15-1:0] cdma_addr = '0;
        reg [4*512-1:0] cdma_data = '0;
        integer port_i, post_i, lane_i;
        initial if (ROM_PHW != 10 || ROM_R != 128 || ROM_BST != 17 || ROM_FBW != 1632)
            $fatal(1, "I66 observer requires enrolled PHW10/R128/BST17/FBW1632");
        always @(posedge clk) begin
            obs_edge = obs_edge + 1;
            pending_we = '0;
            cdma_we = '0;
            if (dut.u_tile.u_core.rst_n) begin
                if (dut.u_tile.u_core.pc == 14'd66)
                    $display("I66_OBS core_pre edge=%0d rank=%0d token=%0d user=%0d pos=%0d pc=%0d st=%0d unit=%0d d_wait=%0h waited=%0d unit_ready=%0d q_gate=%0d kv_gate=%0d m0_gate=%0d win_admit=%0d qe_go=%0d rom_q_go=%0d rom_ready=%0d rom_idle=%0d coll_busy=%0d fs=%0h d_skip=%0d qe_mode=%0d coll_fault=%0d rope_pf_fault=%0d", obs_edge, RANK, token, user, pos,
                        dut.u_tile.u_core.pc, dut.u_tile.u_core.st, dut.u_tile.u_core.d_unit,
                        dut.u_tile.u_core.d_wait, dut.u_tile.u_core.waited, dut.u_tile.u_core.unit_ready,
                        dut.u_tile.u_core.q_gate, dut.u_tile.u_core.kv_gate, dut.u_tile.u_core.m0_gate,
                        dut.u_tile.u_core.win_admit, dut.u_tile.u_core.qe_go, dut.u_tile.u_core.rom_q_go,
                        dut.u_tile.u_core.rom_ready_w, dut.u_tile.u_core.rom_idle_w, dut.coll_busy, dbg_fs,
                        dut.u_tile.u_core.d_skip, dut.u_tile.u_core.qe_mode, dut.u_tile.u_core.coll_fault, dut.u_tile.u_core.rope_pf_fault);
                if (dut.u_tile.u_core.g_rom.u_radapt.st == 0 && (dut.u_tile.u_core.rom_q_go || dut.u_tile.u_core.rom_m_go)) begin
                    obs_sequence = obs_sequence + 1;
                    $display("I66_OBS ROM_accept edge=%0d rank=%0d sequence=%0d pc=%0d is_QE=%0d indexed=%0d base=%0d stride=%0d", obs_edge, RANK, obs_sequence,
                        dut.u_tile.u_core.pc, dut.u_tile.u_core.rom_q_go,
                        dut.u_tile.u_core.rom_q_go && dut.u_tile.u_core.qe_ind,
                        dut.u_tile.u_core.rom_q_go ? dut.u_tile.u_core.qe_wbase : dut.u_tile.u_core.me_wbase,
                        dut.u_tile.u_core.rom_q_go ? dut.u_tile.u_core.qe_istride : 30'd0);
                end
                if (dut.u_tile.rom_vre)
                    $display("I66_OBS EID_read edge=%0d rank=%0d sequence=%0d address=%0d", obs_edge, RANK, obs_sequence, dut.u_tile.rom_vaddr);
                if (dut.u_tile.u_core.g_rom.u_radapt.st == 2)
                    $display("I66_OBS EID_sample edge=%0d rank=%0d sequence=%0d value=%0d", obs_edge, RANK, obs_sequence, dut.u_tile.rom_vq);
                if (dut.u_tile.u_core.g_rom.u_radapt.st == 3)
                    $display("I66_OBS key_lookup edge=%0d rank=%0d sequence=%0d key=%0d hit=%0d phase=%0d word=%0h fault=%0d", obs_edge, RANK, obs_sequence,
                        dut.u_tile.u_core.g_rom.u_radapt.key, dut.u_tile.u_core.g_rom.u_radapt.hit,
                        dut.u_tile.u_core.g_rom.u_radapt.hit_p,
                        dut.u_tile.u_core.g_rom.u_radapt.keyrom[dut.u_tile.u_core.g_rom.u_radapt.hit_p],
                        dut.u_tile.u_core.g_rom.u_radapt.fault);
                if (dut.u_tile.u_core.g_rom.u_spine.st == 0 && dut.u_tile.u_core.g_rom.s_go)
                    $display("I66_OBS phase_accept edge=%0d rank=%0d sequence=%0d phase=%0d fault=%0d", obs_edge, RANK, obs_sequence,
                        dut.u_tile.u_core.g_rom.s_ph, dut.u_tile.u_core.g_rom.u_radapt.fault);
                if (dut.u_tile.rom_xre)
                    $display("I66_OBS input_read edge=%0d rank=%0d sequence=%0d address=%0d elems=64", obs_edge, RANK, obs_sequence, dut.u_tile.rom_xaddr);
                if (dut.u_tile.u_core.g_rom.u_spine.f_cfg_go || dut.u_tile.u_core.g_rom.u_spine.f_go ||
                    dut.u_tile.u_core.g_rom.u_spine.f_go_bf || dut.u_tile.u_core.g_rom.u_spine.f_xs_v ||
                    dut.u_tile.u_core.g_rom.u_spine.f_xb_v)
                    $display("I66_OBS broadcast_sample edge=%0d rank=%0d sequence=%0d bus=%0h", obs_edge, RANK, obs_sequence, rom_fb);
                $display("I66_OBS source_state edge=%0d rank=%0d sequence=%0d adapter_st=%0d spine_st=%0d rows_left=%0d ld_run=%0d sm_run=%0d fault=%0d", obs_edge, RANK, obs_sequence,
                    dut.u_tile.u_core.g_rom.u_radapt.st, dut.u_tile.u_core.g_rom.u_spine.st,
                    dut.u_tile.u_core.g_rom.u_spine.rows_left, dut.u_tile.u_core.g_rom.u_spine.ld_run,
                    dut.u_tile.u_core.g_rom.u_spine.sm_run, dut.u_tile.u_core.rom_fault_w);
                pending_we = dut.u_tile.rom_we;
                pending_addr = dut.u_tile.rom_waddr;
                pending_data = dut.u_tile.rom_wdata;
                cdma_we = dut.u_tile.xb_we4;
                cdma_addr = dut.u_tile.xb_waddr4;
                cdma_data = dut.u_tile.xb_wdata4;
                if (|cdma_we || dut.u_cdma.busy)
                    $display("I66_OBS CDMA_pre edge=%0d rank=%0d writes=%0h addresses=%0h busy=%0d mode=%0d topk=%0d tr_done=%0d commit_wait=%0d tk_done=%0d fault=%0d", obs_edge, RANK,
                        cdma_we, cdma_addr, dut.u_cdma.busy, dut.u_cdma.e_mode, dut.u_cdma.tk_r,
                        dut.u_cdma.tr_done, dut.u_cdma.commit_wait, dut.u_cdma.tk_done, dut.u_cdma.fault);
                for (port_i = 0; port_i < ROM_R; port_i = port_i + 1) begin
                    if (rom_fr[port_i*69+68])
                        $display("I66_OBS root_sample edge=%0d rank=%0d sequence=%0d port=%0d record=%0h", obs_edge, RANK, obs_sequence, port_i, rom_fr[port_i*69 +: 69]);
                    if (pending_we[port_i])
                        $display("I66_OBS VM_write_accept edge=%0d rank=%0d sequence=%0d port=%0d address=%0d data=%0h", obs_edge, RANK, obs_sequence, port_i,
                            pending_addr[port_i*30 +: 30], pending_data[port_i*32 +: 32]);
                end
            end
        end
        // Observe after NBA, without #delay or altering the host clock/eval loop.
        // Equality is a checked local snapshot, not an interstage provider ACK.
        always @(negedge clk) begin
            for (post_i = 0; post_i < ROM_R; post_i = post_i + 1)
                if (pending_we[post_i])
                    $display("I66_OBS VM_postNBA edge=%0d rank=%0d sequence=%0d port=%0d address=%0d expected=%0h actual=%0h", obs_edge, RANK, obs_sequence, post_i,
                        pending_addr[post_i*30 +: 30], pending_data[post_i*32 +: 32],
                        dut.u_tile.vm[pending_addr[post_i*30 +: 19]]);
            for (post_i = 0; post_i < 4; post_i = post_i + 1)
                if (cdma_we[post_i])
                    for (lane_i = 0; lane_i < 16; lane_i = lane_i + 1)
                        $display("I66_OBS CDMA_VM_postNBA edge=%0d rank=%0d port=%0d lane=%0d expected=%0h actual=%0h busy=%0d fault=%0d", obs_edge, RANK, post_i, lane_i,
                            cdma_data[post_i*512+lane_i*32 +: 32],
                            dut.u_tile.vm[{cdma_addr[post_i*15 +: 15], 4'(lane_i)}], dut.u_cdma.busy, dut.u_cdma.fault);
        end
    end endgenerate
    // synthesis translate_on
// END I66 SIMULATION OBSERVER
'''


def generate():
    original = ORIGINAL.read_text()
    return original.replace('module ot_v41_rt_die #(', 'module ot_v41_rt_die_I66_observation_only #(\n'+PARAM, 1).replace('endmodule', HOOKS+'endmodule', 1)


def inverse(text):
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError('observer markers')
    a, tail = text.split(BEGIN)
    _, b = tail.split(END)
    return (a+b).replace(PARAM, '', 1).replace('module ot_v41_rt_die_I66_observation_only #(\n', 'module ot_v41_rt_die #(', 1)


if __name__ == '__main__':
    COPY.write_text(generate())
