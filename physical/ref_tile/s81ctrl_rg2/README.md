# s81ctrl_rg2 -- dsfd_ctrl_rg2 (S81 regional HBM controller, 16 per die on the PHY N face)

## S81-SAFE-FIX/CTRL 10-19: safe redesign after the c1/c2 route miss

c1 (6e188c155) and c2 (de953b547, same RTL) both routed TT -6.38 (in->reg: PHY `k_rdy` -> hold-register load
enable over ~340 data flops, 6 levels after the pin) and FF -6.55. Structural redesign, no ECO squeeze:

- `ot_s81ph_ctrl_pcr` (new) replaces `ot_s81ph_ctrl_pc` in the tile. `ot_s81ph_ctrl_pc` is unchanged because the closed
  S81-PH views bind it.
- `ot_s81ph_afifo_g` (new) replaces `ot_s81ph_afifo` for both FIFOs. `ot_s81ph_afifo.sv` still supplies the sync and pulse_x modules.

### Safe-design checklist (owner 10-19)

| # | Item | Result |
|---|------|--------|
| 1 | Pins | **fixed**. `k_rdy` now lands in a flop at the PHY face (`krq` plus one kept copy `krq_c` per data group). `kr_v/kr_tag/kr_beat/kr_data` land in plain pin flops every cycle; the old `kr_v`-gated 277-bit enable is gone. Every other pin was already a flop in RTL (rq pin register, rd/rk/wd/status output flops, k_* output flops, k_wr_done pin flop). The reset lands in 2 registered stages at the face (`reset_landing` stages 2, clock clk). The flow pin-register hook stays off, with the reason in `pin_regs.json`: the RTL already registers every pin in its own domain, and the hook clocks only one domain. |
| 2 | Reach | PASS. The tile is 531.25 x 250 um. Pin flops are at the faces (io_flop_at_pins). The k_rdy pin reaches its copies within one PC half (<= 266 um). |
| 3 | Fanout | **fixed**. The hold-register load enable is built per 32-bit group from KEPT copies of the issue state (`kv_c/pv_c/krq_c`), so each copy drives <= 32 data enables plus its group's FIFO pop. The FIFO read uses a per-group kept one-hot select and empty copy (`g_rd[*].rsel/emp/rwrap`), so each select bit drives 32 AND gates plus the rotate and encode logic (~37). Previously a 3-bit pointer drove 340 x 7 mux selects. The response output register loads every cycle, so there is no longer a 277-load enable on `empty`. The copies are `(* keep *)` regs, kept by attribute through the `ot_keep_regs.tcl` hook (not by module name). |
| 4 | Depth | PASS. The deepest new cone is: copy flops -> 2 gates -> enable; and pop -> one-hot rotate -> Gray compare -> empty copy (~8 levels at ckh 900 ps). There is no combinational in->out path. |
| 5 | Storage | **waived**. Each PC has two 8-deep dual-clock CDC FIFOs (340 b x 8 = 2.7 kb and 277 b x 8 = 2.2 kb). These are clock-domain-crossing buffers with registered one-hot row writes and per-group one-hot reads, not runtime-indexed flop tables. An SRAM for 8 entries would cost more area than the flops it replaces. |
| 6 | Floorplan | **waived (util)**. The outline is the die's exact PHY-face slot. Its width of 531.25 um equals two PHY PC pitches (abutted DFI), so it cannot move. Utilisation is ~7%; 40-60 % would mean a 531 x ~35 um block (15:1), so the 2.1:1 aspect wins. No macros. Full-width std-cell band. Pins: S face ~1.3k PHY pins on 531 um and N face 1,244 rq/rd pins (< 6/um). MU-DIE-S81 may shrink the slot height. |
| 7 | Clock | Two asynchronous roots: clk (stream/core) and ckh (PHY, 900 ps sign-off). The tile is a CDC leaf with hold_budget tile. hold_margin and io_hold_margin are both 0.03. The c2 gate measured TT insertion 392 ps and spread 40.5. The new gate's measured values are in gate_result.json and the review packet. |
| 8 | Schedule | Static. No credits or backpressure were added on the die side. The PHY valid/ready is the HBM boundary (owner hbm-static-onchip), and its transfer rule is unchanged: a request transfers on an edge with `k_v && k_rdy`. Cost: the controller now sees `k_rdy` one cycle late. It presents a word for one cycle (k_v) and decides on the registered k_rdy in the next cycle; a refused word is presented again. So at most 1 request is issued per 2 ckh per PC, and each refusal costs 2 ckh instead of 1. This is handed to MU-DIE-S81 for the schedule and pricing (lanes/MU-DIE-S81.md INBOX). |

Bench: tb_dsfd_ctrl on 16 x rg2 (Verilator 5.050). See results/rtl/s81_ctrl_rg2_1017/bench_safe_1019.txt and the
witness/ logs. Mutants: MUT_RD, MUT_PACK, and the new MUT_KRDY (a refused word is never presented again).
