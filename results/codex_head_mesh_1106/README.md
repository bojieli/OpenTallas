# Private HEAD mesh replay landing candidate

Not globally adopted. Exact shared EP/GBX/COLL wrapper sources from336bbc9add435d96aae4a6d9422b60aa6cb1d6b5, which includes alias fixde9f4f6caa8dc1bd7088e1cf8f99c29e5c92f424. Only these three shared files are overlaid; no COLL geometry or generator changes. HEAD core and both lane wrappers explicitly pass default-offRBL.

CandidateRBL1 adds1TXpipeline edge atEP f_tx and0RX; exact external pin/peerarrival delta remains PENDING because gearbox/serializer phase is outside that miter, preserves833ps and allIO/clock budgets. NativeCORE_CRED8 exact miter39708TXframes/3104replaycycles0errors, RPmutant2328errors. Native twoendpoint mesh integrationBQ7FAIL387errors andBQ8FAIL130errors due replay burst capacity; both failure logs retained.

Do not infer true backlog from clipped FIFO peak. Read-only C++ observer links the existingBQ8 compiled archive without changing RTL; it captures actual landing enables. Initial observer unused child reset field and Python nonboolean issue flag defects were diagnosed and corrected. Correct queue model matches actual bounded RTL counts/issue on all22000endpoint cycles; same unbounded arrival recurrence requires conservative records+landing bound10. CandidateBQ10 is derived from that trace, not repeated guessed increments. The BQ10 native test passes400/401 records each in2copies,0dataerrors and0phase1fault, actualCRC6/6 with replay5/6, observedpeak10. Physical status remains separate.

The old originalGRT snapshot was corrupt afterE4ENOSPC; valid3place and exact oldEQ receipts remain. Prior source fault reach issue is already handled by four registered relays in currentwrapper, as reviewed in results/geom_review/codex_head_mesh_1106.
