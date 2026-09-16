# DID Agent 固定结果模板目录

本文将 [`examples/`](examples/) 中的安全业务样例归并为可实施的固定结果模板。
它是未来 App 图表/表格路由的设计目录，不修改、不替代，也不直接执行原有样例中的
Cypher。固定实现必须根据当前 Neo4j schema 重新验证查询、参数和返回字段。

## 1. 目标与原则

目标是让用户可以自然提问，而得到稳定、可比较、可视化的结果：

```text
自然语言问题
  -> LLM 受限 intent 分类
  -> LLM 受限参数提取
  -> Neo4j 实体唯一校验
  -> 固定只读 Cypher
  -> 固定图表/表格/少量确定性摘要
```

LLM 只能选择已注册的 `intent` 并提取参数；它不能生成图表数值、预测数值或固定
模板的 Cypher。分类低置信度、参数缺失、实体歧义或组合需求超出模板时，回退到
现有 `neo4j_query` 流程。

## 2. 通用结果合同

所有固定模板建议返回相同外层结构：

```json
{
  "response_type": "fixed_result",
  "intent": "person_monthly_hours",
  "title": "Monthly recorded hours",
  "subtitle": "Chen, Zhenchao (Riven)",
  "summary": ["..."],
  "metrics": [{"label": "Total recorded hours", "value": 3782.0, "unit": "hours"}],
  "visualizations": [
    {"type": "bar", "x": "month", "y": "hours", "data": []}
  ],
  "table": {"columns": ["month", "hours"], "rows": []},
  "cypher": "read-only query",
  "data_note": "Recorded TIME_ON hours"
}
```

### 通用显示规则

- 数值图默认按值降序；时间图按日期升序。
- 图表下始终显示可下载/可查看的底层表格。
- `TIME_ON.Hour` 标注为 **recorded hands-on hours**，不是日历周期。
- 没有 `TIME_ON` 时，不能把 `WORKS_ON` 任务数标成实际工时。
- 空结果必须展示明确原因，而不是只显示空白区域。
- 默认限制明细表行数；排名图默认 Top 10 或 Top 20，并允许展开完整表。
- 所有模板只使用只读 Cypher，并沿用人员、Study、DID 的唯一校验规则。

## 3. 模板总览

| Intent | 主展示 | 主要维度 | 对应样例 |
|---|---|---|---|
| `person_monthly_hours` | 月度柱状/折线图 | 月份、实际工时 | 新增月度图表能力 |
| `person_did_effort` | DID 横向条形图 + 表 | DID、工时、任务 | q005, q012, dashboard_q005 |
| `person_delivery_summary` | KPI 卡 + 表 | DID、Study、任务、日期 | q001, q002, q013 |
| `person_domain_experience` | Domain 条形图 + 表 | Domain、次数、角色 | q006-q008, q015, q134 |
| `person_efficiency_comparison` | 对比柱状图 + KPI | 时间段、任务、每任务工时 | q010, q011, q042 |
| `person_assignment_list` | 排期表/时间线 | DID、状态、计划日期 | q017-q024, q026, q083, q092 |
| `personal_workload_mix` | 堆叠柱状图 + 表 | TLF/ADaM/SDTM、Gen/QC | q022, q025, q039 |
| `delivery_priority_list` | 风险排序表 | DID、到期日、剩余天数 | q019, q028, q079, q082, q089 |
| `delivery_overlap_timeline` | 时间线 + 冲突表 | DID、日期窗口 | q080, q088, q090, q091 |
| `did_person_contribution` | 横向条形图 + 表 | 人员、工时或任务数 | q067, q070, q071, q078, q121 |
| `did_lot_breakdown` | 分组/堆叠图 + 表 | TLF/ADaM/SDTM | q075, dashboard_q009, q110 |
| `did_task_composition` | 堆叠柱状图 + 表 | 任务类型、人员、角色 | q067, q071, q073, q140_1-q140_3 |
| `did_comparison` | 并列柱状图 + 差异表 | DID1、DID2、交付物类型 | q076, q101 |
| `delivery_search_results` | 筛选表格 | DID、状态、日期、Study | q072, q096, q104, q107, q108, q139 |
| `study_delivery_timeline` | 时间线/Gantt 表 | DID、计划/实际日期 | q040, q043, q077 |
| `study_task_composition` | KPI 卡 + 堆叠柱状图 | DID、TLF/ADaM/SDTM | q066, q073 |
| `study_people_and_roles` | 表格 + 角色计数 | 人员、Domain、角色 | q106, q112, q120, q113 |
| `study_tlf_ranking` | Top-N 横向条形图 + 表 | Study、TLF 数 | dashboard_q001-q003 |
| `study_portfolio_table` | 表格 + 轻量 KPI | Study、SDSL、TA、阶段 | dashboard_q007-q008 |
| `team_member_workload` | 分组/堆叠柱状图 + 表 | 成员、任务、角色 | q046-q049, q057-q065 |
| `team_capacity_timeline` | 月度堆叠图/热力图 | 团队、月份、任务 | q049, q057, q063, q084 |
| `lead_contribution_summary` | 分组柱状图 + 表 | TA/Group Lead/Site、任务、工时 | dashboard_q013-q016 |
| `tlf_search_results` | 搜索结果表 | TLF、DID、Study、日期 | q094-q100, q111 |
| `expert_recommendation` | 推荐表 + 依据说明 | 人员、匹配依据、经验 | q117-q118, q125, q129-q133 |
| `collaboration_network_table` | 表格 + 少量摘要 | 成员、协作者、Domain | q045, q126 |
| `delivery_location_detail` | 单条详情卡/表 | DID、路径、系统、Study | q093 |

## 4. 人员与个人工作模板

### 4.1 `person_monthly_hours`

- **问题意图**：某人近期忙不忙、工作量变化、月度/季度实际投入趋势。
- **必填参数**：`person`；可选 `start_date`、`end_date`。
- **固定查询数据**：`(:Person)-[:TIME_ON]->(:DIDN_Month)`，按 `From_Date` 或
  `Year + Month` 聚合 `Hour`。
- **主展示**：月度柱状图；较长时间范围可用折线图。
- **辅助内容**：累计工时、最近月份工时、环比变化（仅有上月时计算）。
- **数据注记**：只代表已记录工时。
- **现状**：已在 App 中实现为 `monthly_hours_chart`；未来应统一命名为本 intent。

### 4.2 `person_did_effort`

- **问题意图**：某人在不同 DID 的投入、最耗时 DID、近期 DID 工时。
- **参数**：`person`；可选日期范围、Study、状态。
- **主展示**：按工时降序的横向条形图。
- **表格**：DID、Study、状态、计划/实际日期、实际工时、任务数、每任务工时。
- **对应样例**：q005、q012、q013、dashboard_q005。
- **空数据回退**：可显示 `WORKS_ON` 分配任务，但必须将图标题改为“Assigned task
  count”，不能混入 recorded hours。

### 4.3 `person_delivery_summary`

- **问题意图**：某人某时间段完成了什么、参与过哪些 Study、完成多少交付。
- **参数**：`person`、`start_date`、`end_date`；可选 `status`。
- **主展示**：三个 KPI 卡（DID 数、任务数、TLF 数）加 DID/Study 表格。
- **对应样例**：q001、q002、q013。
- **少量描述**：只描述最大任务量 Study 或最近完成 DID；不能评价个人绩效。

### 4.4 `person_domain_experience`

- **问题意图**：某人做过哪些 Domain、哪些最多、擅长什么 TA/Domain。
- **参数**：`person`；可选日期范围、`role`（Generation/QC）。
- **主展示**：Top Domain 横向条形图。
- **表格**：TA、Domain、角色、Study、DID、出现次数。
- **对应样例**：q006、q007、q008、q015、q125、q134。

### 4.5 `person_efficiency_comparison`

- **问题意图**：每任务耗时、两个时间段效率比较。
- **参数**：`person`、日期范围或 `year`。
- **主展示**：时间段对比柱状图（总工时、总任务、工时/任务）。
- **KPI**：每任务工时；只有任务数大于零时才计算。
- **对应样例**：q010、q011、q042。
- **注意**：用于本人工作复盘或资源规划，不默认做跨人员排名。

## 5. 计划、交付与 DID 模板

### 5.1 `person_assignment_list`

- **问题意图**：某人未来两周/三个月/六个月有哪些交付、待填 daily survey 的 DID。
- **参数**：`person`；可选 `start_date`、`end_date`、`status`。
- **主展示**：按计划日期排序的表格；日期跨度超过两周时增加时间线。
- **表格**：DID、Study、状态、计划日期、剩余天数、任务数、Reporting Event。
- **对应样例**：q017-q024、q026、q083、q092、dashboard_q006。

### 5.2 `personal_workload_mix`

- **问题意图**：个人接下来工作构成、TLF 生成/QC 量、项目占比。
- **参数**：`person`、日期范围；可选 `task_type`、`role`。
- **主展示**：按 DID 的 TLF/ADaM/SDTM 堆叠柱状图；角色问题使用 Gen/QC 分组柱状图。
- **辅助内容**：总任务 KPI 与详细分配表。
- **对应样例**：q022、q025、q039。

### 5.3 `delivery_priority_list`

- **问题意图**：ongoing DID 到期日、哪些应先交付、紧急 To-Do。
- **参数**：`person` 或 `manager`；可选未来天数、状态。
- **主展示**：可排序风险表；而不是饼图。
- **表格**：DID、计划日期、剩余天数、状态、任务数、优先级解释。
- **风险颜色**：逾期、7 天内、30 天内、其余；阈值必须配置化。
- **对应样例**：q019、q028、q079、q082、q089。

### 5.4 `delivery_overlap_timeline`

- **问题意图**：未来交付重叠、团队低负载期、双周报告。
- **参数**：人员/团队范围、时间范围。
- **主展示**：按周或月的时间线；可增加“同一周期交付数”柱状图。
- **表格**：交付日期、DID、Study、状态、冲突窗口。
- **对应样例**：q080、q088、q090、q091。

### 5.5 `did_person_contribution`

- **问题意图**：某 DID 谁主要负责、各自投入多少工时、任务占比。
- **参数**：`did`；可选 Study、日期范围。
- **主展示**：按实际 `TIME_ON.Hour` 排序的横向条形图。
- **表格**：人员、实际工时、工时占比、任务数、任务占比、Gen/QC（可用时）。
- **无工时回退**：显示 `WORKS_ON` 人员和 `Task_Num_Total`；标题与说明必须标注
  “assigned task count”。
- **对应样例**：q067、q070、q071、q078、q121、dashboard_q010。
- **现状**：已在 App 中实现为 `did_effort_distribution_chart`，含上述无工时回退。

### 5.6 `did_lot_breakdown`

- **问题意图**：某 DID LoT、数据集/表/图清单及数量。
- **参数**：`did`；可选 `task_type`、`source`、`role`。
- **主展示**：TLF/ADaM/SDTM 分类数量图。
- **表格**：类型、Category、Name、Source、Generation、QC、File Name、TLF Number。
- **对应样例**：q075、dashboard_q009、q110。

### 5.7 `did_task_composition`

- **问题意图**：某 DID 或多个 DID 的任务类型和 Generation/QC 构成。
- **参数**：`did` 或 `study`；可选日期范围、人员。
- **主展示**：DID 维度堆叠柱状图；系列为 TLF、ADaM、SDTM 或 Gen、QC。
- **表格**：DID、人员、各任务数、总数。
- **对应样例**：q067、q071、q073、q140_1、q140_2、q140_3。

### 5.8 `did_comparison`

- **问题意图**：两个 DID 的 TLF/ADaM/SDTM 差异。
- **参数**：`did_1`、`did_2`；可选 `task_type`。
- **主展示**：两 DID 各类别数量的并列柱状图。
- **表格**：各类总数、仅 DID1 有的项目、仅 DID2 有的项目。
- **对应样例**：q076、q101。
- **注意**：差异项目通常是字符串列表，应该保留表格或展开面板，不能只用图表。

### 5.9 `delivery_search_results`

- **问题意图**：按关键字、状态、日期或 daily survey 条件搜索 DID。
- **参数**：关键字、日期、状态、人员或 Study，至少一个。
- **主展示**：可筛选表格；可附状态数量 KPI。
- **对应样例**：q072、q096、q104、q107、q108、q139。

## 6. Study、TA 与 Dashboard 模板

### 6.1 `study_delivery_timeline`

- **问题意图**：某 Study 完成的交付及计划/实际时间线；个人参与 Study 的交付时间线。
- **参数**：`study` 或 `person`；可选状态、日期范围。
- **主展示**：计划日期/实际日期时间线；也可使用 Gantt 风格表格。
- **表格**：DID、状态、计划日期、实际日期、偏差天数。
- **对应样例**：q040、q043、q077。

### 6.2 `study_task_composition`

- **问题意图**：某 Study 的 DID 数及 TLF/ADaM/SDTM 任务构成。
- **参数**：`study`；可选状态、`task_type`。
- **主展示**：任务总数 KPI + 每 DID 堆叠柱状图。
- **对应样例**：q066、q073。

### 6.3 `study_people_and_roles`

- **问题意图**：Study 有哪些 programmer、谁负责哪些 Domain、谁是 SDSL。
- **参数**：`study`；可选 Domain、角色。
- **主展示**：人员/角色/Domain 表格；可显示人员数 KPI。
- **对应样例**：q106、q112、q113、q120。

### 6.4 `study_tlf_ranking`

- **问题意图**：TLF 最多的 Study，按最近三个月、季度或全量筛选。
- **参数**：可选 `start_date`、`end_date`、`quarter`、`limit`。
- **主展示**：Top-N Study 横向条形图。
- **表格**：Study、TLF Volume、SDSL、TA、Plan Phase、Plan Status。
- **对应样例**：dashboard_q001、dashboard_q002、dashboard_q003。

### 6.5 `study_portfolio_table`

- **问题意图**：符合地区、阶段、状态等条件的 Study 组合。
- **参数**：`site`、`plan_phase`、`plan_status`、TA 等可选筛选条件。
- **主展示**：Study 表格 + 总 Study 数 KPI；不强制图表。
- **对应样例**：dashboard_q007、dashboard_q008。

### 6.6 `lead_contribution_summary`

- **问题意图**：按 TA Lead、Group Lead、Site、年份汇总任务和工时。
- **参数**：lead/site、日期范围、状态。
- **主展示**：分组柱状图；时间范围存在时可按年度堆叠。
- **表格**：负责人/地点、任务数、记录工时、DID 数。
- **对应样例**：dashboard_q013-q016。

## 7. 团队容量模板

### 7.1 `team_member_workload`

- **问题意图**：某 manager/DU/TA Lead 下的成员任务、完成量或 Gen/QC 分布。
- **参数**：`manager` 或 `ta_lead`；可选 `start_date`、`end_date`、状态、任务类型。
- **主展示**：成员横向条形图；Gen/QC 使用堆叠柱状图。
- **表格**：成员、DID 数、任务总数、TLF/ADaM/SDTM、Gen/QC。
- **对应样例**：q046-q049、q057-q065。
- **限制**：这是容量规划视图，不应默认按效率或人员表现排序。

### 7.2 `team_capacity_timeline`

- **问题意图**：团队未来多月任务、瓶颈、低负载期、交付状态更新。
- **参数**：`manager` / `ta_lead` / `department_lead`；日期范围。
- **主展示**：成员或 DU × 月份的热力图，或按月任务堆叠柱状图。
- **表格**：月份、成员/DU、任务数、DID 数、到期交付数。
- **对应样例**：q049、q057、q063、q084、q088、q091。

### 7.3 `collaboration_network_table`

- **问题意图**：团队成员协作对象、参与的 Study/DID/Domain。
- **参数**：`manager` 或 `team_lead`；可选日期范围。
- **主展示**：成员、协作人员、Study、DID、Domain 的表格；必要时加协作数量条形图。
- **对应样例**：q045、q126。

## 8. TLF 搜索、推荐与详情模板

### 8.1 `tlf_search_results`

- **问题意图**：特定标题/关键词在哪些 DID 出现、最近更新、重复 TLF。
- **参数**：`tlf_keyword`；可选第二关键词、Study、`limit`。
- **主展示**：可排序搜索结果表；默认按实际/计划日期倒序。
- **表格**：TLF Title、DID、Study、状态、日期、Category、Type、Source。
- **对应样例**：q094、q095、q097、q100、q103、q111。

### 8.2 `expert_recommendation`

- **问题意图**：找熟悉某 TLF、Domain、TA 或建模工作的同事。
- **参数**：关键词、Domain/TA、可选团队范围、任务角色。
- **主展示**：推荐表，而不是性能排名图。
- **表格**：候选人员、匹配 Study/DID 数、相关 TLF/Domain、Generation/QC 角色、
  最近相关工作日期。
- **少量描述**：可确定性地说明“基于历史参与记录推荐”，不使用“最佳”“最差”等
  绩效语言。
- **对应样例**：q117、q118、q125、q129-q133。

### 8.3 `delivery_location_detail`

- **问题意图**：DID 在哪里运行、CDARS/SIGMA 路径、系统。
- **参数**：`did`。
- **主展示**：详情卡或两列表格。
- **对应样例**：q093。

## 9. Intent 分类与参数提取合同

分类器的输出应限制在注册 intent 加回退：

```json
{
  "intent": "team_capacity_timeline",
  "confidence": "high"
}
```

第二步根据 intent 使用专用参数 schema。例如：

```json
{
  "person": "Chen, Zhenchao (Riven)",
  "start_date": "2026-07-01",
  "end_date": "2026-09-30"
}
```

所有参数必须经过以下校验后才能执行固定查询：

| 参数 | 校验 |
|---|---|
| `person` / `manager` / `ta_lead` | Neo4j `Person.Name` 唯一匹配；歧义时要求用户澄清 |
| `did` | 格式校验并确认 `Delivery.DID` 存在 |
| `study` | 确认 `Study.Name` 或规范 Study 标识唯一 |
| 日期 | ISO `YYYY-MM-DD`；开始日期不得晚于结束日期 |
| `status` | 映射至允许的 `planned`、`ongoing`、`completed` |
| `limit` | 限制在安全的正整数范围，例如 1-100 |

当分类置信度低、所需参数缺失，或用户同时要求多个不兼容模板时，返回
`neo4j_query` 而不是猜测固定模板。

## 10. 实施顺序

### Phase 1 - 已有高频个人/DID 视图

1. `person_monthly_hours`
2. `did_person_contribution`
3. `person_did_effort`
4. `person_assignment_list`
5. `delivery_priority_list`
6. `did_lot_breakdown`
7. `did_task_composition`

其中前两个已存在初步实现；其余模板应先依据当前 schema 建立固定查询和测试。

### Phase 2 - Study 与团队 Dashboard

1. `study_delivery_timeline`
2. `study_task_composition`
3. `study_tlf_ranking`
4. `team_member_workload`
5. `team_capacity_timeline`
6. `lead_contribution_summary`

### Phase 3 - 搜索、比较与推荐

1. `tlf_search_results`
2. `did_comparison`
3. `expert_recommendation`
4. `collaboration_network_table`
5. `delivery_location_detail`

## 11. 每个模板的验收标准

在接入 App 前，每个 intent 至少应具备：

1. LLM 分类的中文、英文及自然表达测试；
2. 参数提取、实体唯一匹配、缺失/歧义参数测试；
3. 当前 Neo4j schema 下的固定 Cypher 测试；
4. 空结果和零工时的明确展示测试；
5. 图表字段、排序、单位和数据注记测试；
6. 不调用自由生成 Cypher 的测试；
7. 不影响 `effort_prediction` 与 `neo4j_query` 回退路径的回归测试。

## 12. 来源

模板归并自以下现有参考文件，源文件保持不变：

- [`person_productivity.md`](examples/person_productivity.md)
- [`workload_planning.md`](examples/workload_planning.md)
- [`study_delivery.md`](examples/study_delivery.md)
- [`lot_tlf_sdtm_adam.md`](examples/lot_tlf_sdtm_adam.md)
- [`team_manager.md`](examples/team_manager.md)
- [`reporting_dashboard.md`](examples/reporting_dashboard.md)
- [`uncategorized.md`](examples/uncategorized.md)

`sensitive_excluded.md` 不应作为生产 App 固定模板或 LLM few-shot 来源。
