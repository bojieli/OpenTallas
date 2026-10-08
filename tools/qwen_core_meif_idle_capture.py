"""Default-off speculative MEIF capture with complete pending-packet hold."""
def apply(text):
    old='    parameter integer DEC_LA = 0';assert text.count(old)==1
    text=text.replace(old,'    parameter integer DEC_LA_MEIF_IDLE_CAPTURE = 0,\n'+old,1)
    old='    always @(posedge clk) if (me_go) begin\n            mq_nout <= me_nout;'
    assert text.count(old)==1
    new='''    // 2 is an unsafe negative control: overwrite a pending ME packet.
    wire mq_capture = (DEC_LA_MEIF_IDLE_CAPTURE == 2) ? 1'b1 :
        (DEC_LA_MEIF_IDLE_CAPTURE != 0 && DEC_LA_MEIF != 0) ? !me_gop : me_go;
    always @(posedge clk) if (mq_capture) begin
            mq_nout <= me_nout;'''
    return text.replace(old,new,1)
