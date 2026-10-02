# Tuning Decisions

Diagnose before changing values. Prefer the smallest reversible change that targets measured
behavior.

## Congestion Control and Qdisc

- Keep an already functional BBR plus `fq` setup unless an A/B test identifies a concrete
  problem.
- **Topology Distinction: High-BDP vs Low-BDP Constrained Nodes**:
  - *High-BDP paths*: CUBIC collapse on a lossy high-RTT path supports retaining a loss-tolerant
    model (BBR); single-flow capacity requires BBR to scale.
  - *Short-haul low-BDP constrained routes (<= 50 Mbps, RTT 20–70 ms, strict 1–2 MB host policers)*:
    Single-flow CUBIC may benchmark cleanly near line rate in isolation. However, in real workloads
    (modern messaging apps, API polling, web cold start), the client opens 6–10 concurrent short
    flows simultaneously. With `initcwnd 60`, an aggregate burst of $N \times 60$ packets instantly
    over-runs the host's policer, creating transient micro-reordering (`reord_seen`) and drop events.
    CUBIC misinterprets this micro-reordering as fatal congestion, halving `cwnd` to <= 60 and clamping
    pacing rate to ~10 Mbps, collapsing cold-start speeds to 100–500 KB/s.
    **Rule**: On small-bandwidth nodes serving interactive multi-connection traffic, **mandate BBR + FQ**.
    BBR does not react to benign ACK reordering with window collapse, allowing concurrent flows to
    saturate the physical line rate instantly (e.g. 4+ MB/s) and complete cold starts in 1–2 RTTs.
- CUBIC collapse on a lossy high-RTT path supports retaining a loss-tolerant model; it does
  not prove every BBR version or setting is optimal.
- Use an aggregate shaper only when loss or latency appears near a known policer ceiling and
  low-rate tests are clean. Shaping cannot repair low-load random loss.
- An `fq` EDT release ceiling is the right tool when the drop point is a policer and the path
  queues nothing: it bounds BBR's probe bursts without adding a queue. Verify all three
  preconditions first — flat RTT under full load, retransmissions confined to the first seconds
  of a connection, and `TCPDSACKRecv` flat (real loss, not reordering) — then sweep the ceiling
  and keep the highest value that removes them:
  `tc qdisc change dev eth0 root fq maxrate <value>`.
  Measured: 6k-33k retransmits → 0-9 and end-to-end goodput 361-413 → 420-434 Mbps on a
  500 Mbit port (knee between 490 and 510, kept 490); and 11% → 3% loss at peak, 17-31% →
  0-0.1% off peak, with short-flow p95 14.7 s → 2.7 s on a 200 Mbit port (kept 200).
- Keep the ceiling at the port's own advertised rate unless the knee is measurably below it. A
  lower cap costs capacity on every flow, and on a congested path it reduces nothing: on the
  200 Mbit node at peak, caps of 150 and 100 Mbit left loss at 7-8% with half the throughput.
  If loss does not fall as the cap falls, the loss is not the host's — persist nothing.
- Never set `maxrate 0`: the kernel reads a zero rate as a one-second per-packet interval and
  stalls the flow. "Unlimited" is `34359738360bit`.
- A per-interface ceiling does not fix a multi-flow aggregate that over-runs the policer:
  measured `-P 4` retransmits stayed ~15k-24k at caps of 200, 150 and 120 Mbit. Do not claim it
  does; report the aggregate limit as a path finding.
- Preserve a pacing-capable leaf qdisc when testing BBR behind a classful shaper.

## Socket Buffers

- Size buffers from measured BDP plus modest headroom. Avoid copied "hundreds of megabytes"
  profiles.
- On BBR, single-flow throughput is often capped by sender `wmem` below ~2×BDP (BBR keeps
  cwnd_gain×BDP in flight), independent of loss. Verify single-flow before concluding buffers
  "don't help" — multi-flow tests hide this.
- Consider host RAM and the number of simultaneously active high-BDP sockets.
- Increasing maxima protects sustained capacity; it usually does little for a tiny new
  connection by itself.
- Verify whether application-level `SO_SNDBUF` or `SO_RCVBUF` overrides kernel defaults.

## Initial Windows and Short Flows

- Test route `initcwnd` and `initrwnd` values such as 20 and 32 with real small-object A/B
  measurements.
- Consider the **Multi-Flow Multiplier ($N \times \text{initcwnd}$)**:
  On constrained ports (<= 50 Mbps) with strict policers, raising `initcwnd` (e.g. 60) improves
  isolated single flows but multiplies concurrent burst intensity. When 8 connections open at
  once, 480 packets (~650 KB) are injected into the first RTT (~70 Mbps instantaneous line rate),
  colliding with policer limits. If `initcwnd` is high, `fq` and `BBR` are mandatory to pace
  and absorb bursts.
- A larger initial burst may improve median completion while worsening loss or p95. Keep it
  only when the capacity guardrail and tail behavior remain acceptable.
- Persist route metrics through the active network manager or interface lifecycle. Avoid
  editing generated cloud-init files unless cloud-init networking is deliberately disabled.

## Loss, Reordering, and Recovery

- Confirm low-load loss with UDP and repeated tests before blaming congestion control.
- After a loss episode, check whether BBR's rate estimate locked low (`bbr:(bw:...)` in `ss -tin`)
  and whether the sender fell into RTO backoff (`cwnd:1 ssthresh:2 backoff:1`). With
  `tcp_no_metrics_save=0` a collapsed `cwnd`/`ssthresh` can be inherited by the next connection
  to the same destination; that A/B'd inconclusive in testing, so treat `tcp_no_metrics_save=1`
  as an untested candidate rather than a fix.
- Treat `tcp_reordering` changes as experiments. RACK/SACK may already adapt, and a larger
  threshold can delay recovery from real loss.
- Do not disable SACK, DSACK, window scaling, or modern recovery features without strong
  evidence.
- Flush per-destination TCP metrics only for a fair A/B test and only with runtime-write
  permission.

## MTU and MSS

- Use PMTU evidence, route state, and observed MSS. Do not force a smaller MSS merely because
  the client access link uses PPPoE.
- Enable MTU probing when there is evidence of an ICMP black hole, not as a universal tweak.

## Connection Rate and Handshakes

- Raise `tcp_max_syn_backlog` only for measured or expected bursts of new connections.
- `somaxconn` also depends on the application's listen backlog.
- `tcp_fastopen` only grants kernel capability; the application and client must enable and
  support it.
- Connection reuse, TLS 1.3 resumption, HTTP/2, HTTP/3, QUIC, or application multiplexing
  can save more RTTs than sysctl tuning.

## Path Findings and User Scope

- Use path measurements to reject ineffective host tuning and to bound expected results.
- For a node-parameter request, do not turn provider, route, carrier, region, or client-access
  changes into recommendations unless the user explicitly requests them or controls them.
- Mention an uncontrollable path limitation in at most a brief diagnostic note, then return
  to qdisc, congestion control, buffers, recovery, initial windows, and other node-side
  controls.
- If no node-side change is proven, report that directly and identify reversible A/B
  candidates that need higher authority. Do not substitute "change the route" for a
  node-side answer.
- Use provider route branding only as a clue; verify both directions.

## Persistence and Rollback

- Record original values and exact persistence paths.
- Prefer a new narrowly named config file over modifying an unrelated tuning bundle.
- Avoid duplicate keys across sysctl files.
- Validate active values after loading the file.
- For route hooks, run the hook manually once and verify the next interface-up or reboot when
  the user permits.
- Report a concrete rollback path for every persistent change.
