"""Full input-capture successor, sized before physical build and integration."""
def model():
 from uarch_model_hcoll_pinreg import model as previous
 m=previous();m.update(read_to_tx_edges=6,rx_edges=2,input_capture_registers=1220,
 controller_clock_sinks_upper_bound=6000,sram_write_edge='n+4 from raw reservation; native bypass retained',
 read_edge='n pin capture; n+1 launch; n+2 storecapture; n+3macroread; n+4dout; n+5q_pin; n+6TX',
 transport_acceptance='A(j)=19+floor613j/487; readA-7/writeA-11; TXstart18/RXstart22',
 transport_receive='capture25+lastwordindex; publish27+lastwordindex',
 status='SIZED: all external control/data/epoch/PHY inputs first captured; stored input directly q_pin capture; TX6/RX2')
 return m
if __name__=='__main__':
 import json
 print(json.dumps(model(),indent=2))
