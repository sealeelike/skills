<!-- README = 索引。一个 # 一个 skill:名字 / 简介 / 链接。TCP 这个额外标注 SSH 授权 caution。 -->

# audit-tune-tcp-node

<!-- 简介:一句话说明这个 skill 干什么 -->

> [!CAUTION]
> This skill requires you to provide your agent with an SSH login method that has sudo privileges.

tcp调参skill。

A measurement-driven agent skill that audits, benchmarks, and safely tunes remote Linux TCP nodes over SSH.

- 先测全再调
- 多次测试，找到最佳值
- 覆盖多项参数：`congestion control`, `qdisc`, `socket buffers`, `initial windows`, `reordering/recovery`, `MTU/MSS`, and `connection-rate knobs`
- 交付修改项以及相应实测增益
- 参数有快照，可回滚

**Quickstart**

Prompt your agent:

```
I want to try this skill. https://github.com/sealeelike/skills.
```

---

MIT © Sea Lee
