# Tuning Decisions

Diagnose before changing values. Prefer the smallest reversible change that targets measured
behavior.

## Congestion Control and Qdisc

- Keep an already functional BBR plus `fq` setup unless an A/B test identifies a concrete
  problem.
- CUBIC collapse on a lossy high-RTT path supports retaining a loss-tolerant model; it does
  not prove every BBR version or setting is optimal.
- Use an aggregate shaper only when loss or latency appears near a known policer ceiling and
  low-rate tests are clean. Shaping cannot repair low-load random loss.
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
- A larger initial burst may improve median completion while worsening loss or p95. Keep it
  only when the capacity guardrail and tail behavior remain acceptable.
- Persist route metrics through the active network manager or interface lifecycle. Avoid
  editing generated cloud-init files unless cloud-init networking is deliberately disabled.

## Loss, Reordering, and Recovery

- Confirm low-load loss with UDP and repeated tests before blaming congestion control.
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
