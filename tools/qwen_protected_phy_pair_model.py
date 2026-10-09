"""W5: two real physical read slots, independent tagged pairing; boot-only write fallback."""
def model():
    from tools.qwen_protected_phy_model import model as historical
    r=historical()
    r.update(schema='opentallas.qwen.protected_phy.pair.v1',
        adopted=False,physical_qualified=False,native_JEDEC_binding=False,
        read_physical_transactions=2,read_physical_bytes=64,
        physical_outstanding_reads_per_PC=2,
        read_launch='DATA request thenECC request onnextavailablephysicalrequestedge; neverwaitforDATAresponsebeforeECClaunch',
        read_return='independenttaggedDATAslot andECCslot; accepteitherorder, exactPC/tag/beatmatch; duplicateorunknownfault',
        read_latency='max(actualDATAcompletion,actualECCcompletion) +registeredpairpublication; norequestserializationlatency, nativebank/row/two-burstcost stillmustmeasure',
        write_supported='embeddingbootclass1 ONLY; runtimeKVWRITE rejected, nativewriteledgerprovider OPEN',
        write_sequence=['bootECC RD','bootDATA WR','bootECC RMW WR','bootDATA RD fence','bootECC RD fence'],
        mutable_register_payload_bits=1339,register_area_proxy_um2=1339*.32,
        native_requirements=['actualtwooutstandingreadcredits','distinctphysicalDATA/ECCclasses do not advance logical counttwice','32PCphysicalrequestarbiter andnativeJEDEC','actualruntimeKVpairedwriteledger/vendorcompletion, never5xbootfallback','staticgeneratorregionmap binding'],
        gate='actual256model, requeststalls andoutoforder pairedreturns, exact288, tag/PC/duplicate/bitmutants, rollover/defaultoff; no wholearray')
    return r
