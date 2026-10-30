TOK-KV actual HOST producer + native SRAM endpoint, 2026-10-29 18:55 PDT.
Extends the 18:52 modeled-producer experiment (retained unchanged).
Executed intel1 /srv/opentallas-scratch2/claude/codex-kvtok-1847/actual_host,
unit oth-ubuntu-3242715-1793325297, ot-run mem2 threads1 terminal0.
Actual qkd_host_record_port + qkd_program_auth_tx + native static SRAM endpoint,
CRC and p192 SRAM model. Only the route boundaries are behavioral registers:
87 outbound = bind86 + boundary1; actual HOST producer2; 68 inbound = bind67 + boundary1.
No force/backdoor, no synthesized fake valid/payload. Host begins actual kind13
record from begin_v, epoch42a1, counts1024PW/8DW. Fixed TXDP1=157 emits once,
all548 bits equal declared typed payload, producer fault0 and endpoint fault0.
Stale TXDP1=4 and absent observed_v controls both reproduce actual abort/cause80.
Fixed clock833ps. Endpoint FEG disabled only because authorization is outside this
mechanism; actual calendar is configured over cfg ports and starts normally.
No RTL source edit/new cycles, no token/whole-die/throughput/physical PASS claim.
Inherited full v3 probe remains live; the actual source-backed component answers
why the missing producer fault occurs and why the 153-cycle TXDP correction fixes it.
