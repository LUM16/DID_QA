# Team, DU, Manager and TA Lead Examples

> Use these as few-shot examples for DID Agent Text-to-Cypher. Replace parameter placeholders before execution.

## q045: Which studies have my DU members (under manager {{manager:Person name}}) participated in, and what domain are involved

**Business intent**  
Auto-parameterized query to get studies and domains participated by DU members under a specific manager

**Parameters**

```json
{
"manager": "tao, yuxi"
}
```

**Cypher**

```cypher
MATCH (manager:Person) WHERE replace(toUpper(manager.Name), " ", "") = replace(toUpper("{{manager:Person name}}", " ", "")) OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(person:Person) OPTIONAL MATCH (person)-[:WORKS_ON]->(delivery:Delivery) OPTIONAL MATCH (delivery)-[hasSdtm:HAS_SDTM]->(sdtm:SDTM) WHERE (hasSdtm.QC CONTAINS person.Name OR hasSdtm.Generation CONTAINS person.Name) RETURN person.Name AS DU_Member_Name, collect(DISTINCT delivery.Study) AS Studies, collect(DISTINCT delivery.DID) AS DID_List, collect(DISTINCT sdtm.Name) AS SDTM_Names ORDER BY DU_Member_Name;
```

## q046: Please summarize how many tasks were delivered by my DU (under manager {{manager:Person name}}) in S1 and S2 of {{year:Year}}

**Business intent**  
Auto-parameterized query to summarize DU tasks in S1/S2 of a specific year

**Parameters**

```json
{
"manager": "tao, yuxi",
      "year": 2025
}
```

**Cypher**

```cypher
WITH {{year:Year}} AS targetYear, [1, 2, 3, 4, 5, 6] AS targetMonths WITH targetYear * 12 + targetMonths[0] AS minMonth, targetYear * 12 + targetMonths[5] AS maxMonth, targetYear * 12 + 1 AS startS1, targetYear * 12 + 3 AS endS1, targetYear * 12 + 4 AS startS2, targetYear * 12 + 6 AS endS2 MATCH (manager:Person) WHERE replace(toUpper(manager.Name), " ", "") = replace(toUpper("{{manager:Person name}}", " ", "")) OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(person:Person) WITH manager, collect(person) AS duMembers, minMonth, maxMonth, startS1, endS1, startS2, endS2 UNWIND duMembers + [manager] AS person OPTIONAL MATCH (person)-[w:WORKS_ON]->(delivery:Delivery) WHERE delivery.DID_Status = 'Completed' AND (delivery.Year * 12 + delivery.Month) >= minMonth AND (delivery.Year * 12 + delivery.Month) <= maxMonth OPTIONAL MATCH (delivery)-[:HAS_DELIVERY]->(study:Study) OPTIONAL MATCH (study)-[:HAS_DETAIL]->(info:Study_Info) WITH person, delivery, w, study, info, startS1, endS1, startS2, endS2 WITH person.Name AS DU_Member_Name, SUM(CASE WHEN (delivery.Year * 12 + delivery.Month) >= startS1 AND (delivery.Year * 12 + delivery.Month) <= endS1 THEN w.Task_Num_Total ELSE 0 END) + SUM(CASE WHEN person.Name = delivery.SDSL THEN delivery.Total_Task_Num ELSE 0 END) AS Total_Tasks_S1, SUM(CASE WHEN (delivery.Year * 12 + delivery.Month) >= startS2 AND (delivery.Year * 12 + delivery.Month) <= endS2 THEN w.Task_Num_Total ELSE 0 END) + SUM(CASE WHEN person.Name = delivery.SDSL THEN delivery.Total_Task_Num ELSE 0 END) AS Total_Tasks_S2 WITH DU_Member_Name, Total_Tasks_S1, Total_Tasks_S2 WITH SUM(Total_Tasks_S1) AS Total_Tasks_S1_All, SUM(Total_Tasks_S2) AS Total_Tasks_S2_All, collect(DU_Member_Name) AS DU_Members, collect(Total_Tasks_S1) AS DU_Tasks_S1, collect(Total_Tasks_S2) AS DU_Tasks_S2 RETURN DU_Members, DU_Tasks_S1, DU_Tasks_S2, Total_Tasks_S1_All AS Total_Tasks_S1_All, Total_Tasks_S2_All AS Total_Tasks_S2_All ORDER BY DU_Members;
```

## q047: Please summarize the total number of tasks completed by my DU (under manager {{manager:Person name}}) from {{start_month:Month}} {{start_year:Year}} to the present, list all DIDs, and provide a breakdown by person

**Business intent**  
Auto-parameterized query to summarize DU tasks from a specific month/year to present, with DID list

**Parameters**

```json
{
"manager": "tao, yuxi",
      "start_year": 2025,
      "start_month": 1
}
```

**Cypher**

```cypher
WITH date({year: {{start_year:Year}}, month: {{start_month:Month}}, day: 1}) AS startOfPeriod, date() AS today MATCH (manager:Person) WHERE replace(toUpper(manager.Name), " ", "") = replace(toUpper("{{manager:Person name}}", " ", "")) OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(person:Person) WITH manager, collect(person) AS duMembers, startOfPeriod, today UNWIND duMembers + [manager] AS person OPTIONAL MATCH (person)-[w:WORKS_ON]->(delivery:Delivery) WHERE delivery.DID_Status = 'Completed' AND delivery.Actual_Delivery_Date >= startOfPeriod AND delivery.Actual_Delivery_Date <= today OPTIONAL MATCH (delivery)-[:HAS_DELIVERY]->(study:Study) OPTIONAL MATCH (study)-[:HAS_DETAIL]->(info:Study_Info) WITH person, delivery, w, study, info, startOfPeriod, today WITH person.Name AS DU_Member_Name, SUM(w.Task_Num_Total) + SUM(CASE WHEN person.Name = delivery.SDSL THEN delivery.Total_Task_Num ELSE 0 END) AS Total_Task, collect(delivery.DID) AS Delivery_IDs WITH DU_Member_Name, Total_Task, Delivery_IDs WITH SUM(Total_Task) AS Total_Tasks_All, collect(DU_Member_Name) AS DU_Members, collect(Total_Task) AS DU_Tasks RETURN DU_Members, DU_Tasks, Total_Tasks_All AS Total_Tasks_All ORDER BY DU_Members;
```

## q048: Please summarize tasks completed by my DU members (under manager {{manager:Person name}}) from {{start_month:Month}} {{start_year:Year}} to present, and compare with department average (under dept leader {{dept_leader:Person name}})

**Business intent**  
Auto-parameterized query to compare DU members' tasks with department average in a specific period

**Parameters**

```json
{
"manager": "tao, yuxi",
      "dept_leader": "Shen, Henry",
      "start_year": 2025,
      "start_month": 1
}
```

**Cypher**

```cypher
WITH date({year: {{start_year:Year}}, month: {{start_month:Month}}, day: 1}) AS startOfPeriod, date() AS today, "{{manager:Person name}}" AS targetManagerName, "{{dept_leader:Person name}}" AS deptLeaderName MATCH (manager:Person) WHERE lower(replace(manager.Name, " ", "")) = lower(replace(targetManagerName, " ", "")) OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(duMember:Person) WITH startOfPeriod, today, deptLeaderName, manager, collect(duMember) + [manager] AS allDuPersons UNWIND allDuPersons AS duPerson OPTIONAL MATCH (duPerson)-[w:WORKS_ON]->(delivery:Delivery) WHERE delivery.DID_Status = 'Completed' AND delivery.Actual_Delivery_Date >= startOfPeriod AND delivery.Actual_Delivery_Date <= today WITH startOfPeriod, today, deptLeaderName, duPerson.Name AS duMemberName, COALESCE(SUM(w.Task_Num_Total), 0) + COALESCE(SUM(CASE WHEN duPerson.Name = delivery.SDSL THEN delivery.Total_Task_Num ELSE 0 END), 0) AS duPersonTotalTask MATCH (deptLeader:Person) WHERE lower(replace(deptLeader.Name, " ", "")) = lower(replace(deptLeaderName, " ", "")) OPTIONAL MATCH (subordinate:Person)-[:REPORTS_TO*]->(deptLeader) OPTIONAL MATCH (subordinate)-[sw:WORKS_ON]->(subDelivery:Delivery) WHERE subDelivery.DID_Status = 'Completed' AND subDelivery.Actual_Delivery_Date >= startOfPeriod AND subDelivery.Actual_Delivery_Date <= today WITH duMemberName, duPersonTotalTask, COUNT(DISTINCT subordinate) AS deptPersonCount, COALESCE(SUM(sw.Task_Num_Total), 0) + COALESCE(SUM(CASE WHEN subordinate.Name = subDelivery.SDSL THEN subDelivery.Total_Task_Num ELSE 0 END), 0) AS deptTotalTask WITH duMemberName, duPersonTotalTask, deptTotalTask, CASE WHEN deptPersonCount = 0 THEN 0 ELSE deptTotalTask / TOFLOAT(deptPersonCount) END AS deptAvgTaskPerPerson RETURN duMemberName AS DU_Member_Name, duPersonTotalTask AS Total_Tasks_Per_DU_Member, round(deptAvgTaskPerPerson, 2) AS Avg_Tasks_Per_Person_In_Dept ORDER BY duMemberName;
```

## q049: How many tasks will my DU members (including myself) plan to complete in the next {{months:Number of months}} months?

**Business intent**  
Counts planned tasks for each DU member in the next N months

**Parameters**

```json
{
"months": 3,
      "manager": "Liang, Jia Yi (Erin)"
}
```

**Cypher**

```cypher
// Step 1: Calculate year and month for the next {{months:Number of months}}
WITH date() AS today, [1,2,3,4,5,6] AS monthOffsets
UNWIND monthOffsets AS offset
WITH today.year AS baseYear, today.month AS baseMonth, offset
WITH baseYear, baseMonth, offset, baseMonth + offset AS rawMonth
WITH baseYear, offset, CASE WHEN rawMonth > 12 THEN baseYear + 1 ELSE baseYear END AS year, CASE WHEN rawMonth > 12 THEN rawMonth - 12 ELSE rawMonth END AS month
// Step 2: Get DU members (including yourself)
MATCH (manager:Person)
WHERE replace(toUpper(manager.Name), " ", "") = replace(toUpper("{{manager:Manager name}}"), " ", "")
OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(duMember:Person)
WITH year, month, offset, manager, duMember
// Step 3: Merge manager and duMember
WITH year, month, offset, [manager, duMember] AS memberPair
UNWIND memberPair AS person
// Step 4: Find deliveries for each member for each month
OPTIONAL MATCH (person)-[w:WORKS_ON]->(delivery:Delivery)
WHERE delivery.Year = year AND delivery.Month = month AND delivery.DID_Status IN ['Ongoing', 'Planned']
WITH person.Name AS DU_Member, offset, SUM(w.Task_Num_Total) AS Tasks_Per_Month
// Step 5: Aggregate for N months
WITH DU_Member, SUM(CASE WHEN offset <= {{months:Number of months}} THEN Tasks_Per_Month ELSE 0 END) AS Tasks_Next_Months
RETURN DU_Member, Tasks_Next_Months
ORDER BY DU_Member
```

## q051: Please summarize all {{status:Delivery status}} deliveries for my DU (under manager {{manager:Person name}})

**Business intent**  
Auto-parameterized query to list specific status deliveries for a DU

**Parameters**

```json
{
"manager": "tao, yuxi",
      "status": ["Ongoing", "Planned"]
}
```

**Cypher**

```cypher
MATCH (manager:Person) WHERE replace(toUpper(manager.Name), " ", "") = replace(toUpper("{{manager:Person name}}", " ", "")) OPTIONAL MATCH (delivery:Delivery) WHERE delivery.DID_Status IN {{status:Delivery status}} AND (delivery.SDSL = manager.Name OR delivery.SDSA_China_PoC = manager.Name OR delivery.SDSA_US_PoC = manager.Name OR delivery.SDSA_India_PoC = manager.Name) WITH delivery.DID AS Delivery_ID, delivery.Planned_Delivery_Date AS Planned_Delivery_Date, delivery.Reporting_Event AS Reporting_Event, delivery.Study AS Study, delivery.SDSL AS Responsible_SDSL, delivery.Reporting_Detail AS Reporting_Detail RETURN Delivery_ID, Planned_Delivery_Date, Reporting_Event, Study, Responsible_SDSL, Reporting_Detail ORDER BY Planned_Delivery_Date;
```

## q053: Please generate a work summary for my DU members (under manager {{manager:Person name}}) over the past {{summary_period:Months}} months and future {{plan_period:Months}} months

**Business intent**  
Auto-parameterized query to generate DU members' past work summary and future plan

**Parameters**

```json
{
"manager": "tao, yuxi",
      "summary_period": 3,
      "plan_period": 3
}
```

**Cypher**

```cypher
WITH date() AS today, date({year: date().year, month: date().month - {{summary_period:Months}}, day: date().day}) AS summaryEnd, date({year: date().year, month: date().month + {{plan_period:Months}}, day: date().day}) AS planEnd, "{{manager:Person name}}" AS targetManagerName MATCH (manager:Person) WHERE replace(toUpper(manager.Name), " ", "") = replace(toUpper(targetManagerName), " ", "") OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(duMember:Person) WITH manager, collect(duMember) + [manager] AS allDuPersons, today, summaryEnd, planEnd UNWIND allDuPersons AS duPerson // Past summary OPTIONAL MATCH (duPerson)-[w:WORKS_ON]->(delivery:Delivery) WHERE delivery.DID_Status = 'Completed' AND delivery.Actual_Delivery_Date >= summaryEnd AND delivery.Actual_Delivery_Date <= today // Future plan OPTIONAL MATCH (duPerson)-[w2:WORKS_ON]->(delivery2:Delivery) WHERE delivery2.DID_Status IN ["Ongoing", "Planned"] AND delivery2.Planned_Delivery_Date >= today AND delivery2.Planned_Delivery_Date <= planEnd WITH duPerson.Name AS DU_Member_Name, collect(DISTINCT {Past_DID: delivery.DID, Past_Tasks: w.Task_Num_Total}) AS Past_Work, collect(DISTINCT {Future_DID: delivery2.DID, Future_Tasks: w2.Task_Num_Total}) AS Future_Plan RETURN DU_Member_Name, Past_Work, Future_Plan ORDER BY DU_Member_Name;
```

## q054: Please summarize all tasks completed by my DU members (under manager {{manager:Person name}}), broken down by season, for the past {{year_count:Years}} years

**Business intent**  
Auto-parameterized query to summarize DU tasks by season for past N years

**Parameters**

```json
{
"manager": "tao, yuxi",
      "year_count": 2
}
```

**Cypher**

```cypher
WITH [date().year - {{year_count:Years}} + 1 .. date().year] AS targetYears, "{{manager:Person name}}" AS targetManagerName, {S1:[1,2,3], S2:[4,5,6], S3:[7,8,9], S4:[10,11,12]} AS seasonMonths MATCH (manager:Person) WHERE replace(toUpper(manager.Name), " ", "") = replace(toUpper(targetManagerName), " ", "") OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(teamMember:Person) WITH allDUMembers = collect(teamMember) + [manager], targetYears, seasonMonths UNWIND targetYears AS year UNWIND keys(seasonMonths) AS season WITH allDUMembers, year, season, year * 12 + seasonMonths[season][0] AS seasonStart, year * 12 + seasonMonths[season][2] AS seasonEnd UNWIND allDUMembers AS duMember OPTIONAL MATCH (duMember)-[worksOn:WORKS_ON]->(delivery:Delivery) WHERE delivery.DID_Status = 'Completed' AND (delivery.Year * 12 + delivery.Month) >= seasonStart AND (delivery.Year * 12 + delivery.Month) <= seasonEnd WITH duMember.Name AS DU_Member_Name, year AS Target_Year, season AS Target_Season, SUM(CASE WHEN (delivery.Year * 12 + delivery.Month) >= seasonStart AND (delivery.Year * 12 + delivery.Month) <= seasonEnd THEN worksOn.Task_Num_Total ELSE 0 END) + SUM(CASE WHEN duMember.Name = delivery.SDSL THEN delivery.Total_Task_Num ELSE 0 END) AS Total_Completed_Tasks RETURN DU_Member_Name, Target_Year, Target_Season, Total_Completed_Tasks ORDER BY DU_Member_Name ASC, Target_Year ASC, Target_Season ASC;
```

## q055: Which {{status:Delivery status}} deliveries of my DU (under manager {{manager:Person name}}) are concentrated in the same time period

**Business intent**  
Auto-parameterized query to find concentrated DU deliveries by month

**Parameters**

```json
{
"manager": "tao, yuxi",
      "status": ["Planned", "Ongoing"]
}
```

**Cypher**

```cypher
WITH "{{manager:Person name}}" AS targetManagerName, {{status:Delivery status}} AS targetStatuses MATCH (manager:Person) WHERE lower(replace(manager.Name, " ", "")) = lower(replace(targetManagerName, " ", "")) WITH manager.Name AS managerName, targetStatuses MATCH (manager:Person {Name: managerName}) OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(duMember:Person) WITH managerName, collect(duMember.Name) + [managerName] AS duMemberNames, targetStatuses MATCH (d:Delivery) WHERE d.DID_Status IN targetStatuses AND d.Year IS NOT NULL AND d.Month IS NOT NULL AND (d.SDSL IN duMemberNames OR d.SDSA_US_PoC IN duMemberNames OR d.SDSA_China_PoC IN duMemberNames OR d.SDSA_India_PoC IN duMemberNames OR d.FSP_Ephicacy_PoC IN duMemberNames OR d.FSP_Fortrea_PoC IN duMemberNames OR d.FSP_TCS_PoC IN duMemberNames OR d.FSP_Other_PoC IN duMemberNames) OPTIONAL MATCH (respPerson:Person) WHERE respPerson.Name IN [d.SDSL, d.SDSA_US_PoC, d.SDSA_China_PoC, d.SDSA_India_PoC, d.FSP_Ephicacy_PoC, d.FSP_Fortrea_PoC, d.FSP_TCS_PoC, d.FSP_Other_PoC] AND respPerson.Name IN duMemberNames WITH d.DID_Status AS Delivery_Status, d.Year AS Delivery_Year, d.Month AS Delivery_Month, d.DID AS DeliveryID, d.Study AS StudyName, d.Planned_Delivery_Date AS PlannedDate, d.Total_Task_Num AS TotalTasks, COALESCE(respPerson.Name, "Unassigned") AS ResponsibleMember WITH DISTINCT Delivery_Status, Delivery_Year, Delivery_Month, DeliveryID, StudyName, PlannedDate, TotalTasks, ResponsibleMember WITH Delivery_Status, Delivery_Year, Delivery_Month, COUNT(DISTINCT DeliveryID) AS Monthly_Delivery_Count, collect(DISTINCT {DID: DeliveryID, Study_Name: StudyName, Planned_Date: PlannedDate, Total_Tasks: TotalTasks, Responsible_Member: ResponsibleMember}) AS Monthly_Delivery_Details RETURN Delivery_Status, toString(Delivery_Year) + "-" + CASE WHEN Delivery_Month < 10 THEN "0" + toString(Delivery_Month) ELSE toString(Delivery_Month) END AS Delivery_Year_Month, Monthly_Delivery_Count, Monthly_Delivery_Details ORDER BY Delivery_Year ASC, Delivery_Month ASC, CASE WHEN Delivery_Status = 'Planned' THEN 1 ELSE 2 END;
```

## q056: Please summarize the number of tasks and time spent by my DU members (under manager {{manager:Person name}}) in each DID in last {{period:Months}} months

**Business intent**  
Auto-parameterized query to summarize DU members' tasks and time per DID in last N months

**Parameters**

```json
{
"manager": "tao, yuxi",
      "period": 1,
      "status": ["Completed", "Ongoing"]
}
```

**Cypher**

```cypher
WITH "{{manager:Person name}}" AS targetManagerName, date() AS today, date({year: date().year, month: date().month - {{period:Months}}, day: 1}) AS pastPeriodStart, {{status:Delivery status}} AS targetStatuses MATCH (manager:Person) WHERE lower(replace(manager.Name, " ", "")) = lower(replace(targetManagerName, " ", "")) OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(duMember:Person) WITH manager, collect(duMember.Name) + [manager.Name] AS duMemberNames, pastPeriodStart, targetStatuses UNWIND duMemberNames AS duMemberName MATCH (duMember:Person {Name: duMemberName}) OPTIONAL MATCH (duMember)-[t:TIME_ON]->(dm:DIDN_Month)-[:BELONGS_TO]->(d:Delivery)<-[w:WORKS_ON]-(duMember) WHERE d.DID_Status IN targetStatuses AND dm.Year = pastPeriodStart.year AND dm.Month = pastPeriodStart.month WITH duMember.Name AS DU_Member, d.DID AS Delivery_ID, d.Study AS Study_Name, COALESCE(SUM(w.Task_Num_Total)) AS Total_Tasks, COALESCE(SUM(t.Hour)) AS Total_Time_Hours RETURN DU_Member, Delivery_ID, Study_Name, Total_Tasks, Total_Time_Hours ORDER BY DU_Member ASC, Total_Tasks DESC;
```

## q057: Summarize, by member and by month, which tasks each DU member is expected to complete in the next {{months:Number of months}} months.

**Business intent**  
Summarizes expected tasks for each DU member in the next N months

**Parameters**

```json
{
"months": 3,
      "manager": "tao, yuxi"
}
```

**Cypher**

```cypher
// Step 1: Calculate year and month for the next {{months:Number of months}}
WITH date() AS today, [0, 1, 2] AS monthOffsets
UNWIND monthOffsets AS offset
WITH today.year AS baseYear, today.month AS baseMonth, offset
WITH baseYear, baseMonth, offset, baseMonth + offset AS rawMonth
WITH CASE WHEN rawMonth > 12 THEN baseYear + 1 ELSE baseYear END AS year, CASE WHEN rawMonth > 12 THEN rawMonth - 12 ELSE baseMonth + offset END AS month
// Step 2: Get DU members (including yourself)
MATCH (manager:Person)
WHERE replace(toUpper(manager.Name), " ", "") = replace(toUpper("{{manager:Manager name}}"), " ", "")
OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(duMember:Person)
WITH year, month, manager, duMember
// Step 3: Merge manager and duMember
WITH year, month, collect(manager) + collect(duMember) AS allMembers
UNWIND allMembers AS person
// Step 4: Count tasks by member and month
OPTIONAL MATCH (person)-[w:WORKS_ON]->(delivery:Delivery)
WHERE delivery.DID_Status IN ['Ongoing', 'Planned'] AND delivery.Year = year AND delivery.Month = month
WITH person.Name AS DU_Member, collect(DISTINCT delivery.DID) AS Delivery_IDs, SUM(w.Task_Num_Total) + SUM(CASE WHEN person.Name = delivery.SDSL THEN delivery.Total_Task_Num ELSE 0 END) AS Expected_Tasks, year, month
// Step 5: Aggregate tasks for N months
WITH DU_Member, collect(DISTINCT Delivery_IDs) AS Delivery_IDs_Nmonths, SUM(Expected_Tasks) AS Total_Expected_Tasks_N_Months
RETURN DU_Member, Total_Expected_Tasks_N_Months, reduce(s = [], ids IN Delivery_IDs_Nmonths | s + ids) AS All_Delivery_IDs
ORDER BY DU_Member
```

## q058: Please summarize all {{status:Delivery status}} deliveries my DU (under manager {{manager:Person name}}) completed, with task breakdown by person

**Business intent**  
Auto-parameterized query to summarize DU's completed deliveries and task breakdown by person

**Parameters**

```json
{
"manager": "tao, yuxi",
      "status": "Completed"
}
```

**Cypher**

```cypher
WITH "{{manager:Person name}}" AS managerName MATCH (manager:Person) WHERE replace(toUpper(manager.Name), " ", "") = replace(toUpper(managerName), " ", "") OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(duMember:Person) WITH manager, collect(duMember) + [manager] AS allDuPersons UNWIND allDuPersons AS duPerson OPTIONAL MATCH (duPerson)-[w:WORKS_ON]->(completedDelivery:Delivery) WHERE completedDelivery.DID_Status = '{{status:Delivery status}}' WITH duPerson.Name AS DU_Member_Name, COUNT(DISTINCT completedDelivery) AS Member_Completed_Deliveries, COLLECT(DISTINCT completedDelivery.Name) AS Member_Delivery_Names, COALESCE(SUM(w.Task_Num_Total), 0) AS Member_Total_Tasks RETURN DU_Member_Name, Member_Completed_Deliveries AS Completed_Deliveries_Per_Member, Member_Delivery_Names AS Delivery_Names_Per_Member, Member_Total_Tasks AS Total_Tasks_Per_Member ORDER BY DU_Member_Name;
```

## q059: Please summarize all {{status:Delivery status}} deliveries for my DU (under manager {{manager:Person name}})

**Business intent**  
Auto-parameterized query to list specific status deliveries for a DU (duplicate of q051, adjusted for consistency)

**Parameters**

```json
{
"manager": "tao, yuxi",
      "status": ["Ongoing", "Planned"]
}
```

**Cypher**

```cypher
MATCH (manager:Person) WHERE replace(toUpper(manager.Name), " ", "") = replace(toUpper("{{manager:Person name}}", " ", "")) OPTIONAL MATCH (delivery:Delivery) WHERE delivery.DID_Status IN {{status:Delivery status}} AND (delivery.SDSL = manager.Name OR delivery.SDSA_China_PoC = manager.Name OR delivery.SDSA_US_PoC = manager.Name OR delivery.SDSA_India_PoC = manager.Name) WITH delivery.DID AS Delivery_ID, delivery.Planned_Delivery_Date AS Planned_Delivery_Date, delivery.Reporting_Event AS Reporting_Event, delivery.Study AS Study, delivery.SDSL AS Responsible_SDSL, delivery.Reporting_Detail AS Reporting_Detail RETURN Delivery_ID, Planned_Delivery_Date, Reporting_Event, Study, Responsible_SDSL, Reporting_Detail ORDER BY Planned_Delivery_Date;
```

## q060: List DU members (including myself) who do not have any deliveries for next month.

**Business intent**  
Lists DU members with no deliveries next month

**Parameters**

```json
{
"manager": "Fei, Qili"
}
```

**Cypher**

```cypher
// Step 1: Calculate year and month for next month
WITH date() AS today
WITH today.year AS baseYear, today.month AS baseMonth
WITH CASE WHEN baseMonth + 1 > 12 THEN baseYear + 1 ELSE baseYear END AS nextYear, CASE WHEN baseMonth + 1 > 12 THEN baseMonth + 1 - 12 ELSE baseMonth + 1 END AS nextMonth
// Step 2: Get DU members (including yourself)
MATCH (manager:Person)
WHERE replace(toUpper(manager.Name), " ", "") = replace(toUpper("{{manager:Manager name}}"), " ", "")
OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(duMember:Person)
WITH nextYear, nextMonth, collect(manager) + collect(duMember) AS allMembers
UNWIND allMembers AS person
// Step 3: Find deliveries for each member for next month
OPTIONAL MATCH (person)-[:WORKS_ON]->(delivery:Delivery)
WHERE delivery.Year = nextYear AND delivery.Month = nextMonth
WITH person.Name AS DU_Member, collect(delivery) AS deliveries
// Step 4: Only return members with no deliveries
WHERE size(deliveries) = 0
RETURN DU_Member AS DU_Member_No_Delivery_Next_Month
ORDER BY DU_Member
```

## q061: Please summarize tasks and deliveries of each DU for TA Lead {{ta_lead:Person name}}

**Business intent**  
Auto-parameterized query to summarize each DU's tasks/deliveries under a specific TA Lead

**Parameters**

```json
{
"ta_lead": "Zhuang, meinan"
}
```

**Cypher**

```cypher
WITH "{{ta_lead:Person name}}" AS targetTALeadName MATCH path = (taLead:Person)<-[:REPORTS_TO*0..]-(duManager:Person) WHERE replace(toUpper(taLead.Name), " ", "") = replace(toUpper(targetTALeadName), " ", "") AND duManager.Manager = "Y" OPTIONAL MATCH (duManager)<-[:REPORTS_TO]-(duMember:Person) WITH duManager, collect(duMember) + [duManager] AS allDuMembers UNWIND allDuMembers AS duPerson OPTIONAL MATCH (duPerson)-[w:WORKS_ON]->(completedDelivery:Delivery) WHERE completedDelivery.DID_Status = 'Completed' WITH duManager.Name AS DU_Manager_Name, COALESCE(SUM(w.Task_Num), 0) + COALESCE(SUM(CASE WHEN duPerson.Name = completedDelivery.SDSL THEN completedDelivery.Total_Task_Num ELSE 0 END), 0) AS DU_Total_Completed_Tasks, COUNT(DISTINCT completedDelivery) AS DU_Total_Completed_Deliveries RETURN DU_Manager_Name AS DU_Identifier, DU_Total_Completed_Tasks AS Total_Completed_Tasks_Per_DU, DU_Total_Completed_Deliveries AS Total_Completed_Deliveries_Per_DU ORDER BY DU_Manager_Name;
```

## q062: Summarize the workload of each DU member (including myself) for the coming month.

**Business intent**  
Summarizes the workload for each DU member for the coming month

**Parameters**

```json
{
"manager": "Liang, Jia Yi (Erin)"
}
```

**Cypher**

```cypher
// Step 1: Calculate year and month for next month
WITH date() AS today
WITH today.year AS baseYear, today.month AS baseMonth
WITH CASE WHEN baseMonth + 1 > 12 THEN baseYear + 1 ELSE baseYear END AS nextYear, CASE WHEN baseMonth + 1 > 12 THEN baseMonth + 1 - 12 ELSE baseMonth + 1 END AS nextMonth
// Step 2: Get DU members (including yourself)
MATCH (manager:Person)
WHERE replace(toUpper(manager.Name), " ", "") = replace(toUpper("{{manager:Manager name}}"), " ", "")
OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(duMember:Person)
WITH nextYear, nextMonth, collect(manager) + collect(duMember) AS allMembers
UNWIND allMembers AS person
// Step 3: Find deliveries for each member for next month
OPTIONAL MATCH (person)-[w:WORKS_ON]->(delivery:Delivery)
WHERE delivery.Year = nextYear AND delivery.Month = nextMonth
WITH person.Name AS DU_Member, SUM(w.Task_Num_Total) AS Expected_Tasks, collect(DISTINCT delivery.DID) AS Delivery_IDs
RETURN DU_Member AS DU_Member, Expected_Tasks AS Expected_Tasks_Next_Month, Delivery_IDs AS Delivery_IDs_Next_Month
ORDER BY DU_Member
```

## q063: Please summarize {{status:Delivery status}} deliveries and tasks for my DU (under manager {{manager:Person name}}) in next {{period:Months}} months, and compare with other DUs in my department (under dept leader {{dept_leader:Person name}})

**Business intent**  
Auto-parameterized query to compare DU's future deliveries/tasks with department average

**Parameters**

```json
{
"manager": "tao, yuxi",
      "dept_leader": "Shen, Henry",
      "period": 3,
      "status": ["Ongoing", "Planned"]
}
```

**Cypher**

```cypher
WITH "{{manager:Person name}}" AS yourName, "{{dept_leader:Person name}}" AS deptLeaderName, (date().year * 12 + date().month) AS minMonth, (date().year * 12 + date().month) + {{period:Months}} AS maxMonth MATCH (you:Person) WHERE replace(toUpper(you.Name), " ", "") = replace(toUpper(yourName), " ", "") OPTIONAL MATCH (you)<-[:REPORTS_TO]-(duMember:Person) WITH duMember,you, collect(duMember) + [you] AS yourDuMembers, minMonth, maxMonth, deptLeaderName UNWIND yourDuMembers AS duPerson OPTIONAL MATCH (duDelivery:Delivery) WHERE duDelivery.DID_Status IN {{status:Delivery status}} AND (duDelivery.Year * 12 + duDelivery.Month) > minMonth AND (duDelivery.Year * 12 + duDelivery.Month) <= maxMonth AND (duPerson.Name = duDelivery.SDSL OR duPerson.Name = duDelivery.SDSA_China_PoC OR duPerson.Name = duDelivery.SDSA_US_PoC OR duPerson.Name = duDelivery.SDSA_India_PoC) WITH you.Name AS DU_Name, COUNT(DISTINCT duDelivery) AS yourDu_Future_Deliveries, COALESCE(SUM(duDelivery.Total_Task_Num), 0) AS yourDu_Future_Tasks, minMonth, maxMonth, deptLeaderName MATCH (deptLeader:Person) WHERE replace(toUpper(deptLeader.Name), " ", "") = replace(toUpper(deptLeaderName), " ", "") OPTIONAL MATCH (deptLeader)<-[:REPORTS_TO*]-(duManager:Person) WHERE duManager.Manager = "Y" OPTIONAL MATCH (duManager)<-[:REPORTS_TO]-(deptMember:Person) WITH deptMember,duManager, duManager.Name AS Dept_DU_Manager, collect(deptMember) + [duManager] AS deptDuMembers, minMonth, maxMonth, DU_Name, yourDu_Future_Deliveries, yourDu_Future_Tasks UNWIND deptDuMembers AS deptPerson OPTIONAL MATCH (deptDelivery:Delivery) WHERE deptDelivery.DID_Status IN {{status:Delivery status}} AND (deptDelivery.Year * 12 + deptDelivery.Month) > minMonth AND (deptDelivery.Year * 12 + deptDelivery.Month) <= maxMonth AND (deptPerson.Name = deptDelivery.SDSL OR deptPerson.Name = deptDelivery.SDSA_China_PoC OR deptPerson.Name = deptDelivery.SDSA_US_PoC OR deptPerson.Name = deptDelivery.SDSA_India_PoC) WITH Dept_DU_Manager, COUNT(DISTINCT deptDelivery) AS deptDu_Future_Deliveries, COALESCE(SUM(deptDelivery.Total_Task_Num), 0) AS deptDu_Future_Tasks, DU_Name, yourDu_Future_Deliveries, yourDu_Future_Tasks WITH DU_Name, yourDu_Future_Deliveries, yourDu_Future_Tasks, COLLECT({Dept_DU_Manager: Dept_DU_Manager, Future_Deliveries: deptDu_Future_Deliveries, Future_Tasks: deptDu_Future_Tasks}) AS allDeptDUs, ROUND(AVG(deptDu_Future_Deliveries), 1) AS dept_Avg_Future_Deliveries, ROUND(AVG(deptDu_Future_Tasks), 1) AS dept_Avg_Future_Tasks RETURN {Your_DU: DU_Name, Future_Period_Deliveries: yourDu_Future_Deliveries, Future_Period_Tasks: yourDu_Future_Tasks} AS Your_DU_Summary, {Dept_Avg_Future_Deliveries: dept_Avg_Future_Deliveries, Dept_Avg_Future_Tasks: dept_Avg_Future_Tasks} AS Dept_Average_Summary, allDeptDUs AS All_Dept_DUs_Detail;
```

## q064: Please summarize tasks and deliveries of each TA from {{start_month:Month}} {{start_year:Year}} to present

**Business intent**  
Auto-parameterized query to summarize each TA's tasks/deliveries in a specific period

**Parameters**

```json
{
"start_year": 2025,
      "start_month": 1
}
```

**Cypher**

```cypher
WITH date({year: {{start_year:Year}}, month: {{start_month:Month}}, day: 1}) AS startOfPeriod, date() AS today MATCH (taLeader:Person) WHERE taLeader.TA_Lead = 'Y' OPTIONAL MATCH path = (subordinate:Person)-[:REPORTS_TO*0..]->(taLeader) OPTIONAL MATCH (subordinate)-[w:WORKS_ON]->(delivery:Delivery) WHERE delivery.DID_Status IN ['Completed'] AND delivery.Actual_Delivery_Date >= startOfPeriod AND delivery.Actual_Delivery_Date <= today WITH taLeader.Name AS TA_Leader_Name, COLLECT(DISTINCT delivery.DID) AS Period_Delivery_Ids, COALESCE(SUM(w.Task_Num_Total), 0) + COALESCE(SUM(CASE WHEN subordinate.Name = delivery.SDSL THEN delivery.Total_Task_Num ELSE 0 END), 0) AS Period_Total_Tasks WITH TA_Leader_Name, size(Period_Delivery_Ids) AS Period_Total_Deliveries, Period_Total_Tasks WHERE Period_Total_Deliveries > 0 OR Period_Total_Tasks > 0 RETURN TA_Leader_Name, Period_Total_Deliveries, Period_Total_Tasks ORDER BY TA_Leader_Name, Period_Total_Tasks DESC;
```

## q065: Please summarize the number of tasks completed by each person in my DU (under manager {{manager:Person name}}), categorized by {{task_type:Task type}} Generation and QC

**Business intent**  
Auto-parameterized query to summarize DU members' tasks by Generation/QC for specific task types

**Parameters**

```json
{
"manager": "tao, yuxi",
      "task_type": "SDTM,ADaM,TLF"
}
```

**Cypher**

```cypher
WITH "{{manager:Person name}}" AS targetManagerName MATCH (manager:Person) WHERE replace(toUpper(manager.Name), " ", "") = replace(toUpper(targetManagerName), " ", "") OPTIONAL MATCH (manager)<-[:REPORTS_TO]-(duMember:Person) WITH manager, collect(duMember) + [manager] AS allDuMembers UNWIND allDuMembers AS duPerson OPTIONAL MATCH (duPerson)-[workOn:WORKS_ON]->(delivery:Delivery) WHERE delivery.DID_Status = 'Completed' RETURN delivery.Study AS Study_Name, delivery.DID AS Study_DID, duPerson.Name AS DU_Member_Name, workOn.{{task_type:Task type}}_Num_Generation AS {{task_type:Task type}}_Generation_Tasks, workOn.{{task_type:Task type}}_Num_QC AS {{task_type:Task type}}_QC_Tasks, workOn.Task_Num_Total AS Total_Completed_Tasks_Per_Study ORDER BY Study_Name, Study_DID, DU_Member_Name;
```

## q068: Please let me know how many {{status:Delivery status}} deliveries my DU (under manager {{manager:Person name}}) will have in next {{period:Months}} months

**Business intent**  
Auto-parameterized query to count DU's upcoming deliveries in next N months

**Parameters**

```json
{
"manager": "Ma, Xin",
      "period": 1,
      "status": ["Ongoing", "Planned"]
}
```

**Cypher**

```cypher
WITH "{{manager:Person name}}" AS yourName, date() AS today, (date().year * 12 + date().month) + {{period:Months}} AS nextPeriodCode MATCH (you:Person) WHERE replace(toUpper(you.Name), " ", "") = replace(toUpper(yourName), " ", "") OPTIONAL MATCH (you)-[:REPORTS_TO]->(duManager:Person) OPTIONAL MATCH (duManager)<-[:REPORTS_TO]-(duColleague:Person) WITH you, duManager, collect(duColleague) + [you] + CASE WHEN duManager IS NOT NULL THEN [duManager] ELSE [] END AS allDuMembers, nextPeriodCode UNWIND allDuMembers AS duMember MATCH (delivery:Delivery) WHERE (delivery.Year * 12 + delivery.Month) <= nextPeriodCode AND delivery.DID_Status IN {{status:Delivery status}} AND (delivery.SDSL = duMember.Name OR delivery.SDSA_US_PoC = duMember.Name OR delivery.SDSA_China_PoC = duMember.Name OR delivery.SDSA_India_PoC = duMember.Name OR delivery.FSP_Ephicacy_PoC = duMember.Name OR delivery.FSP_Fortrea_PoC = duMember.Name OR delivery.FSP_TCS_PoC = duMember.Name OR delivery.FSP_Other_PoC = duMember.Name) AND delivery.Year IS NOT NULL AND delivery.Month IS NOT NULL RETURN you.Name AS Your_Name, duManager.Name AS DU_Manager_Name, COUNT(DISTINCT delivery.DID) AS Total_DU_Upcoming_Deliveries_Next_Period, collect(DISTINCT {DID: delivery.DID, Study_Name: delivery.Study, Planned_Delivery_Date: delivery.Planned_Delivery_Date}) AS DU_Upcoming_Delivery_Details ORDER BY Your_Name, DU_Manager_Name;
```
