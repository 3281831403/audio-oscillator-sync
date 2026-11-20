# audio-oscillator-sync

## 题面

合成器加第二个振荡器后，高音区全是锯齿混叠、长音还会跑调：`phase_inc` 每采样相位增量没有取模，长时间渲染后相位精度丢失；方波没有使用 PolyBLEP，边沿混叠严重；硬同步只在 reset 时把从振荡器相位清零，没有处理相位差分数值，接缝处爆音；音分换算误用 `cents / 100`，失谐量相差 12 倍；相位用 float 逐采样累加，低频长音逐渐跑调；三角波用绝对值正弦近似，谐波结构不对；未知波形被静默当作正弦；渲染长度用浮点四舍五入，批量时累计漂移；批量渲染共用相位状态，音符之间互相串扰；`sample_rate=0` 未校验，直接除零。osc/oscillator.py 是核心，tests/test_oscillator.py 15个红。要修的是：上述十处契约缺陷，让 15 条验收测试全部通过。

## 运行方式

在仓库根目录执行：

```text
python -m pytest tests -q
```

初始状态必须恰好收集并失败 15 条测试，即输出尾部为 `15 failed`，且没有 collection error、import error 或 syntax error：

```text
15 failed in 0.0Xs
```

修复只改 `osc/oscillator.py`；实现只使用 Python 标准库（`math`），离线运行，不使用随机数，也不 sleep。

## 字段表

| 字段 | 取值 |
| --- | --- |
| 所属领域 | 游戏、图形与多媒体 |
| 子方向 | 音视频处理 |
| 任务类型 | Bugfix |
| 语言/框架 | Python 3, pytest |
| 环境可复现等级 | 无外部依赖 |

## tests 不可修改

`tests/test_oscillator.py` 是验收测试，不可修改、不可删除或跳过。修复目标是让现有 15 条测试全部通过，而不是改测试来迁就实现。
