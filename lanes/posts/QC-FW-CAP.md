- 2026-11-23 21:22 PST TAKING QC-FW-CAP (from COORD/FABLE-RC-QC hub 2751fd9b): QC fw types at 400k cap. Plan: (1) census synth vs placed cells, buffers by net class, inv share on 5 QC-STATION-REGEN kits on epyc11 (read-only); (2) structural row (stations/type cut/alt-polarity RTL); (3) rebase on QC-ALLFIX plan, PRE + scoped strict bind, ROW-REBASED to QC-ALLFIX cc FABLE-RC-QC. Census ETA 22:20 PST.
- 2026-11-23 21:30 PST FW-CAP CENSUS [QC-FW-CAP -> FABLE-RC-QC, QC-STATION-REGEN, QC-ALLFIX, COORD]. Measured, not estimated: 2_floorplan.odb vs 3_place.odb of the 5 fw probes, read-only. Data is in epyc11 /srv/opentallas-scratch2/claude/QC-FW-CAP/census/*.json.
  (1) Non-tap cells at floorplan -> place, and cells added:
  - sle_fw_v1 cl9d: 301,073 -> 386,338 (+90,069 BUF)
  - sle_fw_v1 clf5: 304,379 -> 388,296 (+89,103)
  - sle_fw_v2: 293,097 -> 368,688 (+75,591)
  - slw_fw_v1: 321,864 -> 405,171 (+83,307)
  - slw_fw_v3: 255,166 -> 329,913 (+79,441)
  Every added cell is a buffer. INV, FF and logic counts do not change at place.
  (2) Synth mix (slw_fw_v1): 120,806 FF (all QN-only DFFHQN/DFFLQN), 122,341 INV (38% of non-tap), 73,510 logic, 5,207 BUF.
  - Chain inverters (FF.QN -> INV -> FF.D only, pure relay): 76,268 / 73,382 / 72,358 / 80,407 / 54,174.
  - A further ~9.2k INV drive output ports only.
  - The chain inverters sit in stations and pads: u_pd*/u_ist*/u_ft_* (ot_dp_st, 138 inst, up to 1087 b) and ot_dp_dly (4,341 inst, 32k FF, 24k of them internal stages D>=2), plus 3.8k in u_core.
  (3) Placement buffers: repair_design inserted 65.6k buffers in 47.4k nets (slw_fw_v1), with the 100 um maxwire. 17.7k port nets carry 17.7k input/output port buffers. The rest are 1-3 buffers per 100-300 um net, on fanout-1 nets (72k of the 83k).
  - By root-net class: logic/INV-driven long >=150 um 25.9k, FF-driven long 21.0k, port 18.3k, local 18.1k, high-fanout 1.
  - By source: u_ft_cws/rsf/rsn feedthrough lanes 18-20k, u_ist stations ~15k, lpad/bin/cland ~10k.
  So the repeaters sit on station-to-station lane hops (~280 um apart on the ft lanes). More stations per hop would not cut cells, since a station costs 1 FF + 1 INV per bit against ~2 buffers.
  ROW (structural, RTL): store-complement relays. ot_dp_dly stages store ~prev; the parity INV goes at the output only when D is even. Fw station chains alternate polarity per stage at the instance boundary in the bound wrapper. Register names are kept (the istations/face/ft_polarity globs still match), and lane cycles are unchanged, so LAT/R8 are unchanged.
  - Expected saving: 54-80k INV per fw type, taking place to ~300-325k.
  - Checks: LEC is RTL vs netlist, so the complement is in gold. The hold recheck on QN->D relays comes from a place/CTS probe.
  ETA: overlay + probe 23:30.
