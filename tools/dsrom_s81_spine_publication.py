"""Default-off paired return/fault publication in the EXISTING capture parent.

No phase ledger, ACK or rollback. Fault uses existing warm-quarantine request;
phase identity/quota remain in the original capture until real commit/drain.
This is the enclosing R128 alternative, not a second edge after an E1 pipe.
"""
import re
from pathlib import Path
from dsrom_s81_capture_install import replace_once as one

ROOT = Path(__file__).resolve().parents[1]
LEAF = ROOT/'rtl/dsrom_sys/spine_publication/ot_v41_rom_publication_capture.sv'


def bind_spine(text):
    text = one(text, '    parameter integer CAPTURE_ENABLE = 0,',
               '    parameter integer CAPTURE_PUBLICATION = 0,\n    parameter integer CAPTURE_ENABLE = 0,')
    marker = '    localparam integer CW = 3 * NSEG + 1;'
    head, body = text.split(marker)
    # Change references, never named port labels or external port declarations.
    names = ('r_v','r_row','r_pos','r_fp32','r_bf16','r_e','f_fault')
    for name in names:
        body = re.sub(r'(?<![\w.])'+name+r'(?!\w)', 'pub_'+name, body)
    body = one(body, '.reset_request(capture_reset_request)',
               '.reset_request(capture_reset_request | publication_quarantine)')
    body = one(body, '.phase_live(capture_live)',
               '.phase_live(retained_capture_live)')
    body = one(body, '.phase_drained(capture_drained)',
               '.phase_drained(retained_capture_drained)')
    body = one(body, 'assign ready = st == S_IDLE && (!CAPTURE_ENABLE || cap_ready);',
               'assign ready = st == S_IDLE && (!CAPTURE_ENABLE || cap_ready) && publication_quiet;')
    body = one(body, 'assign idle = st == S_IDLE && (!CAPTURE_ENABLE || cap_idle);',
               'assign idle = st == S_IDLE && (!CAPTURE_ENABLE || cap_idle) && publication_quiet;')
    join = '''
    wire [R-1:0] pub_r_v, pub_r_e;
    wire [16*R-1:0] pub_r_row, pub_r_bf16;
    wire [3*R-1:0] pub_r_pos;
    wire [32*R-1:0] pub_r_fp32;
    wire pub_f_fault;
    wire retained_capture_live, retained_capture_drained;
    ot_v41_rom_publication_capture #(.ENABLE(CAPTURE_PUBLICATION),.WIDTH(69*R+1)) u_publication (
      .clk(clk),.rst_n(rst_n),
      .publication_in({f_fault,r_v,r_row,r_pos,r_fp32,r_bf16,r_e}),
      .publication_out({pub_f_fault,pub_r_v,pub_r_row,pub_r_pos,pub_r_fp32,pub_r_bf16,pub_r_e}));
    // All-copy quarantine, NOT an ACK or retroactive VM rollback. The existing
    // capture inhibits every VM valid on reset_request, latches sticky fault,
    // and retains accepted records/identity. No faulty-phase consumer/retire.
    wire publication_quarantine = CAPTURE_PUBLICATION != 0 &&
      (pub_f_fault || (|(pub_r_v & pub_r_e)));
    wire publication_quiet = CAPTURE_PUBLICATION == 0 ||
      (!(|r_v) && !(|pub_r_v) && !f_fault && !pub_f_fault);
    // Export ALL owned copies through the existing parent interface. A raw
    // fault at the final receipt/retirement boundary is pending publication,
    // not a quiet drained phase while the paired fault waits its capture edge.
    // No new register/ledger, ACK, rollback or warm-reset release authority.
    assign capture_live = retained_capture_live ||
      (CAPTURE_PUBLICATION != 0 && (!publication_quiet || capture_fault));
    assign capture_drained = retained_capture_drained &&
      (CAPTURE_PUBLICATION == 0 || (publication_quiet && !capture_fault));
    initial if (CAPTURE_PUBLICATION != 0 && CAPTURE_ENABLE == 0)
      $fatal(1,"paired publication requires actual finite capture/VM acceptance");
'''
    # BUSY remains the actual phase state/live descriptor. Never derive idle
    # from this one-edge pipe: original rows_left and capture_drained still
    # debit ONLY positive capture_vm_accept, not publication pulses.
    return head + join + marker + body
