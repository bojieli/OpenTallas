Actual generated HEAD transport/reset coupon: PASS.

Input consumer implementation and plan are bf4bf660a (later a480f95d1 changes tests only). Both complete generated wrappers and real leaves are used for hd_st_k5, hd_spn_end and hd_serdes. Real HOST276 TX/RX carries three source-relative records; no production dates/producer are invented.

Before START: both old/new spine payload paths deliver all three records exactly. Station payload also moves in both. New declared station/spine epochs are1, old-role epochs0. Actual u_phy reset is1 in the candidate and0 in the old-role control. Actual u_spo/u_spr reset and undeclared mission FT epochs remain0. Therefore the old-role regression is caught by bootstrap epoch/PHY reset, not blanket payload suppression.

After START: 201 every-cycle selected transport/epoch comparisons are equal, including changing station payload. Mission spine resets release normally. Added data pipeline cycles0. This does not prove actual PMA packet traffic, production boot dates/START authority, physical timing or a token pass.

Replay source: tools/s81_head/head_transport_coupon.sh SELECTED_PLAN FRESH_OUT stages actual wrappers and a mutation removing only bootstrap_buses/bootstrap_contents. Its generated coupon/run.sh must run through ot-run (--mem16 --threads8). Source checkout must contain the selected type source closure and declared pin tables. The portable stage helper reproduces all29 actual staged source/script files byte-for-byte (receipt hashes).

Completed job: intel2:/srv/opentallas-scratch2/claude/codex-head-transport-0930, unit1112175-1793118939, client1111488. Initial setup failures retained: invalid -j8 argument; then module end-label renaming and three missing FEC include headers. Those were corrected before the passing build. Build37.85s, reported allocation4.88GB. No failed verdict overwritten.
