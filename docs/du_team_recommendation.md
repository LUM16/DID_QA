# DU Team Recommendation 指标说明

## 目的与范围

**Recommend DU Team** 是一个基于 Neo4j 历史数据的、可解释的 scope-match
推荐工具。它接收一个新 Delivery 的 TLF、ADaM 和 SDTM scope，并推荐当前最具
相关经验的 DU Team。

它**不是**训练模型，不输出成功概率，也不会自动修改 Neo4j 中的 assignment。
其用途是为人工分配提供可追溯的候选排序、经验依据和 scope gap 提示。

当前实现将 `Person.Team_Lead_Name` 相同的人员视为同一个 DU Team；页面显示的是
该字段的 team lead 名称。这是人员**当前**的 Team 归属，而不是历史 DID 完成时的
组织快照。

## 输入与数据来源

### 上传的新 Delivery scope

支持两种格式：

1. 一个 `.xlsx` 工作簿，必须有 `TLF` 和 `Data` 两个 sheet；
2. 两个 CSV：TLF CSV 和 Data CSV。

| 输入区域 | 读取字段 | 用途 |
|---|---|---|
| TLF | `Title` | TLF 标题语义匹配 |
| TLF | `Type` | TLF 匹配的辅助元数据 |
| TLF | `Source Datasets` | TLF 匹配的辅助元数据，并拆分为候选 ADaM 名称 |
| Data | `SDTM/ADaM` | 标识数据类型 |
| Data | `Domain/Dataset Name` | 精确 ADaM / SDTM coverage |

空标题或空 dataset/domain 名称不会进入计算。名称会进行大小写和标点标准化，
避免纯格式差异导致不匹配。

### Neo4j 历史数据

每个候选 DU 使用下列当前数据库数据：

- `Person.Team_Lead_Name`：将人员归入 DU；
- `Person -[:WORKS_ON]-> Delivery`：该 DU 成员参与的 DID；
- `Delivery.DID_Status = Completed` 且 `Actual_Delivery_Date` 非空：历史经验样本；
- `Delivery -[:HAS_TLF]-> TLF`：TLF title、type、source；
- `Delivery -[:HAS_ADAM]-> ADaM`：ADaM dataset；
- `Delivery -[:HAS_SDTM]-> SDTM`：SDTM domain；
- `Delivery.DID_Status IN (Ongoing, Planned)`：当前 active DID workload signal。

历史 scope 按 **DU × DID** 去重。同一个 DU 的多名人员参与同一 DID 时，该 DID
只作为一次团队历史经验，不会重复加分。

## Overall score

每个 DU 得到一个 0–100 的透明分数：

```text
Overall score =
  35 × TLF semantic coverage
+ 18 × ADaM coverage
+ 12 × SDTM coverage
+ 18 × Similar DID experience score
+ 10 × Recent relevant experience score
+  7 × Workload score
```

每个子分数均在 0–1 范围内。因此所有权重相加为 100。

## 指标定义

### 1. TLF semantic coverage — 35 分

TLF 是当前最高权重的 scope 指标。

对新 Delivery 和某个 DU 的候选历史 DID，系统会使用现有 effort prediction
中的 TLF comparison 逻辑：

- TLF title 的标准化 character 3–5 gram 相似度；
- `Type` 相同的加权信息；
- `Source` 相同的加权信息；
- one-to-one matching：一个目标 TLF 不能重复匹配多个历史 TLF；
- 只有匹配分数 `>= 0.70` 才计为 semantic match。

对于每一个历史 DID：

```text
TLF semantic coverage =
matched target TLF count
/
target TLF count
```

该 DU 的 TLF semantic coverage 取其候选历史 DID 中的**最大值**。因此它回答：

> 该 DU 有没有完成过一个 Delivery，其 TLF scope 最能覆盖当前目标？

这不是把所有历史 DID 的 TLF 无限制合并后得到的 coverage；这样可以避免零散、
互不相关的历史工作被误判为一个完整相似项目。

### 2. ADaM coverage — 18 分

```text
ADaM coverage =
目标 ADaM dataset 中，该 DU 在所有 completed DID 历史里出现过的数量
/
目标 ADaM dataset 总数
```

这是**精确集合匹配**，不使用 ADaM 名称语义相似度。例如目标 `ADAE` 仅在该 DU
历史 scope 中存在 `ADAE` 时才视为覆盖。

页面会显示 `Missing ADaM`，即当前 DU 历史中从未出现的目标 ADaM 名称。

### 3. SDTM coverage — 12 分

```text
SDTM coverage =
目标 SDTM domain 中，该 DU 在所有 completed DID 历史里出现过的数量
/
目标 SDTM domain 总数
```

同样是精确集合匹配。页面会显示 `Missing SDTM`，帮助人工确认关键 domain 是否有
历史经验。

### 4. Similar DID experience score — 18 分

系统先为每个候选历史 DID 计算完整 scope similarity：

```text
Combined DID similarity =
  60% × TLF semantic coverage
+ 25% × ADaM Jaccard overlap
+ 15% × SDTM Jaccard overlap
```

其中 Jaccard overlap 为：

```text
intersection(target, historical)
/
union(target, historical)
```

只将 `combined similarity >= 0.70` 的 DID 计为相似 DID。

```text
Similar DID experience score =
  0.6 × best combined DID similarity
+ 0.4 × min(1, similar DID count >= 0.70 / 5)
```

所以：

- 最相似的一个历史 DID 很相关，会提高分数；
- 有多个相似 DID 也会提高分数；
- 相似 DID 数达到 5 个后饱和，不会因为 Team 规模大而无限加分。

页面还展示：

- `Similar DID >= 70%`；
- `Similar DID >= 85%`；
- 最相似的最多 5 个 completed DID。

### 5. Recent relevant experience score — 10 分

只在 `combined similarity >= 0.70` 的历史 DID 中计算。取这些 DID 中最高的
recency score：

| 最相关 DID 的完成时间 | Recent experience score |
|---|---:|
| 最近 180 天 | 1.0 |
| 181–365 天 | 0.7 |
| 366–730 天 | 0.4 |
| 超过 730 天 | 0.15 |
| 没有相似 DID | 0.0 |

该分数表示 Team 是否有近期、并且整体 scope 确实相近的经验；它不会因仅有
不相关的最近 DID 而加分。

### 6. Workload score — 7 分

该指标是轻量级 capacity signal，不是剩余工时或真实 FTE capacity。

```text
active DID count =
该 DU 成员参与的 distinct Planned + Ongoing Delivery 数

workload score =
1 - active DID count / max active DID count among all candidate DUs
```

因此 active DID 较少的 DU 得到较高 workload score。它只占 7 分，不能压过
scope experience 的主要指标。

当前不会计算：

- 可用 FTE；
- 请假、合同工时；
- 已记录 TIME_ON 后的 remaining effort；
- 各 active DID 的精确剩余工作量。

因此 `Active DIDs` 应视为提醒性指标，不应被解释为“该 Team 还剩多少工时”。

## 性能与 TLF similarity cache

TLF semantic matching 是最耗时的部分。系统复用：

```text
artifacts/did_effort_similarity_cache.joblib
```

该缓存与 effort prediction 共用，key 基于目标和历史 TLF 集合的标准化
`title/type/source` 内容，而不是 DID、人员或 DU 名称。缓存命中只会减少计算时间，
**不会改变分数或推荐排序**。

为了避免上传大型 scope 时比较所有历史 TLF，系统先用现有候选筛选逻辑选出近期或
至少有 exact TLF/ADaM/SDTM overlap 的历史 DID；之后按 ADaM + SDTM Jaccard overlap
及完成日期排序，每个 DU 最多对 **50 个** DID 进行昂贵的 TLF semantic matching。

ADaM/SDTM coverage 和 completed DID count 则始终使用该 DU 的完整历史，不受这 50 个
语义候选限制。

页面底部的 cache 信息：

```text
hits  = 从已有缓存读到的 TLF 比较次数
misses = 本次首次完成并写入缓存的 TLF 比较次数
```

## Recommendation level

分数之外，页面也会给出业务友好的等级：

| Level | 条件 |
|---|---|
| `Recommended` | Overall score >= 80，且没有 Missing ADaM 或 Missing SDTM |
| `Suitable with review` | 非 Recommended，但 Overall score >= 65 |
| `Backup option` | Overall score 45–64.9 |
| `Insufficient evidence` | Overall score < 45 |

`Recommended` 的额外 dataset/domain gap 条件是为了防止一个总分高、但缺少目标关键
ADaM 或 SDTM 的 DU 被直接推荐。

## 页面中显示但不计入分数的证据

| 字段 | 用途 |
|---|---|
| Completed DIDs | 该 DU 可用的去重 completed DID 历史数 |
| Semantic candidates | 进入深度 TLF semantic matching 的 DID 数，最多 50 |
| Missing exact historical TLF title match | 目标 TLF 中没有完全相同历史标题的数量；它不等同于 semantic gap |
| Most similar completed DIDs | 人工审核推荐依据 |

特别注意：`Missing exact historical TLF title match` 只表示没有 exact title；标题可能
仍已通过 TLF semantic matching 与历史内容相似。因此不要将这个数直接解释为
“没有 TLF 能力”。

## 当前未纳入的指标

以下信息目前没有进入总分：

- 人员层级的工时效率或 effort prediction；
- TIME_ON 工时；
- Delivery 是否按期、返工、QC finding 或质量评分；
- Team 内有多少不同人员能覆盖同一个关键 TLF/domain；
- 具体人员是否当前可用；
- 新 Delivery 的 target date、priority、TA 或 study type。

这些不是“默认等于零”的负面信号，而是当前版本没有可靠或版本化数据来安全计算。
如未来要加入，应先明确数据口径和业务权重，再通过独立版本更新推荐公式。

## 使用建议

1. 优先查看 Top 3，而不是只看第一名；
2. 同时查看 `Missing ADaM`、`Missing SDTM` 和相似 DID 明细；
3. Top 1 若是 `Backup option` 或 `Insufficient evidence`，应进行 SME review 或考虑
   cross-team assignment；
4. 将最终人工选择的 DU 及后续交付结果保存下来，未来可以评估规则是否符合业务决策；
5. 对很大的新 Delivery，首次上传可能产生 cache misses；之后再评估相同或相似 scope
   会更快。
