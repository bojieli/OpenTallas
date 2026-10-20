# Exact normal PC6 sr8 async-reset review packet

Read-only proof rebind of the earlier `e08f61cb5` primitive-source packet to the
actual normal gates `qkd_kvs_pc{,_h}_sr8-20261020-054430` on agidock128.
This packet changes no canonical helper and grants no runtime admission.
The plain two-D-stage BRP refusal remains valid until ROOT reviews a separate
exact async-conditioner interface.

Both gates use the same selected generated SV file, SHA256
`77d444acbeab1f50152c681e876428175cd864a7263ed9dc0892175943b1c91e`.
All 27 source files per selected spec are separately hashed and archived,
along with the exact spec, kit, actual mapped source and parser. Actual mapped
SHA256 values are:

- PC: `3d29020a23951d425b99ef4f72b0a795502ebad6b618814c3c769524cecf6bc3`
- PC_H: `0cbd66c288fe86c6aaaee2c17b1c821ccd4901dfbddf7941ac9c1882a825e514`

Both source-bound graph audits PASS. Each raw reset reaches precisely nine
actual ASR RESETN pins: one first and eight final stages. First D and every
SETN are Liberty-proven one; reset polarity is zero; every stage uses its
literal destination clock. First QN reaches only eight final D pins with the
required inversion; no first export or side consumer is accepted. Every final
consumer is enumerated by actual cell/pin/polarity/function. Final load maxima
are 13 for rst_n/ck and 17 for hrst_n/hck. All native drivers have maximum32.
All eight causal graph mutations per bank, across four banks, are REFUSED:
root polarity/value, first D, clock, QN polarity, bypass, extra consumer and
missing stage. The last run additionally records every ASR/HQN consumer clock.

The actual runtime image is exactly
`sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`,
the same pinned image used for the earlier canonical-model proof. Actual native
Liberty receipts are archived; actual TT/FF sequential byte hashes match the
proof libraries. SS/TT/FF ASR sequential equations and canonical model hashes
are checked again by the graph runner. The existing canonical nine-ASR theorem
and its twelve causal SAT witnesses remain in the earlier e08 packet; this run
rebinds that exact proven graph shape and cell identity rather than claiming a
new whole-PC functional proof.

The complete release observer/calendar inventory is in
`observer_calendar_summary.json` and the graph JSON. In each top, 25 plain D
observers use ck and 128 use hck. The core final releases additionally drive
73 ASR RESETN consumers in PC, 72 in PC_H, all clocked by ck. Each bank has one
actual combinational clamp; the runner proves its reset output value for all
other inputs using its actual Liberty function. No generic combinational
consumer exemption is used.

For each destination clock independently, raw assertion clears logical release
with the clock stopped. After raw release, destination edge1 captures first
stage, edge2 establishes final logical release, and edge3 is the first legal
ordinary-D observer capture or released-ASR functional capture. All listed
sequential consumers use their own bank clock; no cross-clock coincidence is
assumed. Parent boot/calendar and external raw-reset aggregate admission remain
separate obligations. Tying the four raw inputs across both tops yields36
loads and needs parent distribution; the standalone proof grants no parent
fanout, physical reach, clock, lifecycle or placement qualification.

Runs: agidock units `oth-ubuntu-255347-1792506837` and
`oth-ubuntu-257877-1792506931`, both terminal exit0. `packet_inputs.tar.gz`
contains the immutable reproduction inputs. Run `python3 source_graph.py`
inside its extracted directory on the fleet. Full logs are retained.
