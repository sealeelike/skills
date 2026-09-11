<!-- README = 索引。一个 # 一个 skill:名字 / 简介 / 链接。TCP 这个额外标注 SSH 授权 caution。 -->

# handwriting-video-to-svg

iPad/平板手写录屏转矢量因果律 SVG 书写动画。

Convert iPad/tablet handwriting screen recordings (GoodNotes, Notability, Procreate, Apple Notes) into causally-exact, zero-aliasing, infinite-resolution vector SVG handwriting animations.

- 拒绝“粗笔画蒙版侧漏横切”的硬伤，100% 还原物理书写时序（Per-frame causal reveal）
- 终帧采用顶级三次贝塞尔曲线拟合（Potrace Bézier），无限分辨率、零锯齿
- 生产环境异步组件打包支持（`--bundle`），0ms 首屏阻塞，自适应暗色主题

## Quickstart

Prompt your agent:

```
I want to try this skill. Clone https://github.com/sealeelike/skills and install handwriting-video-to-svg from it.
```

---

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
I want to try this skill. https://github.com/sealeelike/skills/tree/main/audit-tune-tcp-node
```

---

MIT © Sea Lee
