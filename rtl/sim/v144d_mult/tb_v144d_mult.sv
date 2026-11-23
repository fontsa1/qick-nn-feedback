// tb_v144d_mult: drives the two HLS-generated DSP templates of the v1.44d diagnostic NN_live (copied unchanged from
// neural_net4_live576s/NN_live_prj/solution1/impl/verilog/ of the diagnostic build) with the four constants K_u that
// the ACC_L pipeline wires to them (NN_live_NN_live_Pipeline_ACC_L.v lines 1171-1177), and compares dout with the exact
// product and with (K - 2^18) * x. Random signed operands; 4-cycle latency (NUM_STAGE 4: a/b/m/p registers).
`timescale 1ns/1ps
module tb_v144d_mult;
    reg clk = 0; always #1 clk = ~clk;
    localparam integer NT = 20000;
    reg  signed [16:0] a0, d0; reg signed [17:0] x18; reg signed [45:0] c46;
    wire [36:0] y_am [0:2]; wire [45:0] y_mac;
    reg [17:0] K18 [0:2]; initial begin K18[0] = 18'd226161; K18[1] = 18'd236037; K18[2] = 18'd226455; end
    genvar g;
    generate for (g = 0; g < 3; g = g + 1) begin : U
        NN_live_am_addmul_17s_17s_18ns_37_4_1 #(.ID(1), .NUM_STAGE(4), .din0_WIDTH(17), .din1_WIDTH(17), .din2_WIDTH(18), .dout_WIDTH(37))
            dut (.clk(clk), .reset(1'b0), .ce(1'b1), .din0(a0), .din1(d0), .din2(K18[g]), .dout(y_am[g]));
    end endgenerate
    NN_live_mac_muladd_18s_19ns_46s_46_4_1 #(.ID(1), .NUM_STAGE(4), .din0_WIDTH(18), .din1_WIDTH(19), .din2_WIDTH(46), .dout_WIDTH(46))
        dmac (.clk(clk), .reset(1'b0), .ce(1'b1), .din0(x18), .din1(19'd478404), .din2(c46), .dout(y_mac));
    // history of inputs for the latency
    reg signed [17:0] s_hist [0:7]; reg signed [17:0] x_hist [0:7]; reg signed [45:0] c_hist [0:7];
    integer i, t, ok_exact [0:3], ok_wrap [0:3], lat;
    longint signed s, e, w;
    initial begin
        for (i = 0; i < 4; i = i + 1) begin ok_exact[i] = 0; ok_wrap[i] = 0; end
        a0 = 0; d0 = 0; x18 = 0; c46 = 0;
        for (t = 0; t < NT + 8; t = t + 1) begin
            @(negedge clk);
            for (i = 7; i > 0; i = i - 1) begin s_hist[i] = s_hist[i-1]; x_hist[i] = x_hist[i-1]; c_hist[i] = c_hist[i-1]; end
            a0 = $random; d0 = $random; x18 = $random; c46 = {$random, $random};
            s_hist[0] = a0 + d0; x_hist[0] = x18; c_hist[0] = c46;
            if (t >= 8) begin
                // dout observed now (after negedge) corresponds to inputs applied 3 negedges earlier (a/ad, m, p regs)
                for (i = 0; i < 3; i = i + 1) begin
                    s = s_hist[3];
                    e = s * longint'(K18[i]);
                    w = s * (longint'(K18[i]) - 262144);
                    if ($signed(y_am[i]) == e[36:0] && longint'($signed(y_am[i])) == e) ok_exact[i] = ok_exact[i] + 1;
                    if (longint'($signed(y_am[i])) == w) ok_wrap[i] = ok_wrap[i] + 1;
                end
                e = longint'(x_hist[3]) * 478404 + longint'(c_hist[1]);  // in2 (c) is not registered in the template: it enters p two cycles after x
                if ($signed(y_mac) == e[45:0]) ok_exact[3] = ok_exact[3] + 1;
                w = longint'(x_hist[3]) * (478404 - 524288) + longint'(c_hist[1]);
                if ($signed(y_mac) == w[45:0]) ok_wrap[3] = ok_wrap[3] + 1;
            end
        end
        for (i = 0; i < 3; i = i + 1)
            $display("am_addmul_18ns K=%0d (as 18-bit signed: %0d): exact %0d/%0d, (K-2^18)*x %0d/%0d", K18[i], $signed(K18[i]), ok_exact[i], NT, ok_wrap[i], NT);
        $display("mac_muladd_19ns K=478404: exact %0d/%0d, (K-2^19)*x %0d/%0d", ok_exact[3], NT, ok_wrap[3], NT);
        $finish;
    end
endmodule
