# Person Productivity Examples

> Use these as few-shot examples for DID Agent Text-to-Cypher. Replace parameter placeholders before execution.

## q001: Summarize the my deliveries during a certain time period

**Business intent**  
Summarize the deliveries of a specific person during a specified time period.

**Parameters**

```json
{
"person": "Chen, Sizhen",
      "startDate": "2025-01-01",
      "endDate": "2025-12-31"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Actual_Delivery_Date >= date({{startDate}}) AND d.Actual_Delivery_Date <= date({{endDate}})
RETURN
p.Name AS Person_Name,
COUNT(d) AS Total_Deliveries,
SUM(d.TLF_Num) AS Total_TLF_Volume,
SUM(d.Total_Task_Num) AS Total_Tasks
ORDER BY Total_Deliveries DESC
```

## q002: Summarize which studies I participated in delivering during a certain period. For each study, how many tasks were delivered? What percentage of the study's total tasks were delivered?

**Business intent**  
Summarize the studies a specific person delivered during a specified period, along with the number of tasks delivered and the percentage of tasks relative to the total study tasks.

**Parameters**

```json
{
"person": "Chen, Sizhen",
      "startDate": "Chen, Sizhen",
      "endDate": "2025-12-31"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person:Name of the person}}})-[wo:WORKS_ON]->(d:Delivery)<-[:HAS_DELIVERY]-(s:Study)
WHERE d.Actual_Delivery_Date >= date({{startDate}} AND d.Actual_Delivery_Date <= date({{endDate}}
WITH s, COLLECT(d.Name) AS deliveries, SUM(wo.Task_Num_Total) AS Person_Task_Sum,REDUCE(Total_Study_Task_Num = 0, de IN [(s)-[:HAS_DELIVERY]->(de:Delivery) | de] | Total_Study_Task_Num + COALESCE(de.Total_Task_Num, 0)) AS Total_Study_Task_Num
RETURN s.Name as Study_Name, Person_Task_Sum, deliveries, Total_Study_Task_Num, 100 * Person_Task_Sum / Total_Study_Task_Num AS Percent_Study_Task
ORDER BY Study_Name
```

## q003: How many TLFs were completed in the past year?

**Business intent**  
Summarize the total number of TLFs completed in the past year.

**Parameters**

```json
{
"person": "Chen, Sizhen",
		"years":1
}
```

**Cypher**

```cypher
WITH date() - duration({years: {{years: number of year}}}) AS Last_Year_Date
MATCH (p:Person {Name: {{person:Name of the person}}})-[wo:WORKS_ON] -> (d:Delivery)
where d.Actual_Delivery_Date >= Last_Year_Date
RETURN SUM(wo.TLF_Num_Total) AS Total_TLFs
```

## q005: How many datasets or tables are associated with each DID, and how many hours were spent on each DID?

**Business intent**  
Shows the number of datasets and the total hours spent for each DID.

**Parameters**

```json
{
"person": "Chen, Sizhen"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person:Name of the person}}})-[to:TIME_ON]->(didn:DIDN_Month)-[:BELONGS_TO]->(d:Delivery)
RETURN d.Name AS DIDN, SUM(to.Hour) AS Hours
```

## q006: Which studies and domains have I participated in?

**Business intent**  
Lists all the studies and domains the person has participated in.

**Parameters**

```json
{
"person": "Chen, Sizhen"
}
```

**Cypher**

```cypher
MATCH (p: Person {Name:{{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)<-[:HAS_DELIVERY]-(s:Study)
MATCH (d)-[rel:HAS_SDTM {Generation:p.Name}]->(sdtm:SDTM)
WITH s, 'GEN' AS Role, sdtm.Name AS Domain
RETURN DISTINCT(s.Name) AS Study_Name, Role, Domain
UNION
MATCH (p: Person {Name:{{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)<-[:HAS_DELIVERY]-(s:Study)
MATCH (d)-[rel:HAS_SDTM {QC:p.Name}]->(sdtm:SDTM)
WITH s, 'QC' AS Role, sdtm.Name AS Domain
RETURN DISTINCT(s.Name) AS Study_Name, Role, Domain
ORDER BY Study_Name, Role, Domain
```

## q007: Which domains have I worked on in the past period, how many times, and which ones were the most and least frequent?

**Business intent**  
Summarizes the number of times each domain was worked on, and identifies the most and least frequent.

**Parameters**

```json
{
"person": "Chen, Sizhen",
      "startDate": "2025-01-01",
      "endDate": "2025-03-31"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Actual_Delivery_Date >= date({{startDate}}) AND d.Actual_Delivery_Date <= date({{endDate}})
MATCH (d)-[rel:HAS_SDTM]->(sdtm:SDTM)
WHERE p.Name in [rel.Generation, rel.QC]
WITH sdtm.Name AS Domain, COUNT(sdtm.Name) AS CNT_SDTM
WITH collect({Domain:Domain, CNT_SDTM:CNT_SDTM}) AS rows, MAX(CNT_SDTM) AS Max_CNT_SDTM, MIN(CNT_SDTM) AS Min_CNT_SDTM
UNWIND rows AS row
WITH row.Domain AS Domain, row.CNT_SDTM AS CNT_SDTM, Max_CNT_SDTM, Min_CNT_SDTM
RETURN Domain, CNT_SDTM,CASE WHEN CNT_SDTM = Max_CNT_SDTM THEN 'Y' ELSE '' END AS Max_Domain,CASE WHEN CNT_SDTM = Min_CNT_SDTM THEN 'Y' ELSE '' END AS Min_Domain
```

## q008: Which studies have I participated in, sorted by TA and domain?

**Business intent**  
Lists all the studies the person has participated in, sorted by TA and domain.

**Parameters**

```json
{
"person": "Chen, Sizhen",
}
```

**Cypher**

```cypher
MATCH (p: Person {Name:{{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)<-[:HAS_DELIVERY]-(s:Study)
MATCH (s)-[:HAS_DETAIL]->(info:Study_Info)
WITH p, s, d, info.TA as TA
MATCH (d)-[rel:HAS_SDTM {Generation:p.Name}]->(sdtm:SDTM)
WITH DISTINCT(s.Name) AS Study_Name, TA, 'GEN' AS Role, sdtm.Name AS Domain
RETURN TA, Domain, Role, Study_Name
UNION
MATCH (p: Person {Name:{{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)<-[:HAS_DELIVERY]-(s:Study)
MATCH (s)-[:HAS_DETAIL]->(info:Study_Info)
WITH p, s, d, info.TA as TA
MATCH (d)-[rel:HAS_SDTM {QC:p.Name}]->(sdtm:SDTM)
WITH DISTINCT(s.Name) AS Study_Name, TA, 'QC' AS Role, sdtm.Name AS Domain
RETURN TA, Domain, Role, Study_Name
ORDER BY TA, Domain, Role, Study_Name
```

## q009: How many hours did I work on study XXXX in the past two weeks?

**Business intent**  
Calculates the total hours worked on a specific study in the past two weeks.

**Parameters**

```json
{
"person": "Chen, Sizhen",
	  "days" : 14,
      "study_name": "C4591007"
}
```

**Cypher**

```cypher
WITH date()-duration({days: {{days: number of days}}}) AS Date_Past_Two_Weeks
MATCH (p:Person {Name: {{person:Name of the person}}})-[to:TIME_ON]->(didn:DIDN_Month)-[:BELONGS_TO]->(d:Delivery)<-[:HAS_DELIVERY]-(s:Study {Name: {{stduy_name: Name of the study}}})
WHERE date(to.From_Date) >= Date_Past_Two_Weeks
RETURN s.Name AS Study_Name, SUM(to.Hour) AS Hours
```

## q010: Please summarize the delivery efficiency of the past two weeks

**Business intent**  
Summarizes the delivery efficiency (number of deliveries and average tasks) in the past two weeks.

**Parameters**

```json
{
"person": "Chen, Sizhen",
		"weeks" : 2
}
```

**Cypher**

```cypher
WITH date()-duration({weeks: {{weeks: number of weeks}}}) AS Date_Past_Two_Weeks
MATCH (p:Person {Name:{{person:Name of the person}}})-[to:TIME_ON]->(didn:DIDN_Month)-[:BELONGS_TO]->(d:Delivery)<-[wo:WORKS_ON]-(p)
WHERE d.Actual_Delivery_Date >= Date_Past_Two_Weeks
WITH SUM(to.Hour) AS Total_Hour, SUM(wo.Task_Num_Total) AS Total_Task
WITH Total_Hour/Total_Task AS Hour_Per_Task
RETURN Hour_Per_Task
```

## q011: How much time does it take to complete one task based on the tasks I worked on in the past six months?

**Business intent**  
Estimates the time taken to complete one task based on recent tasks worked on.

**Parameters**

```json
{
"person": "Chen, Sizhen",
		"months": 6
}
```

**Cypher**

```cypher
WITH date()-duration({months: {{months: number of months}}}) AS Date_Past_Six_Month
MATCH (p:Person {Name:{{person:Name of the person}}})-[to:TIME_ON]->(didn:DIDN_Month)-[:BELONGS_TO]->(d:Delivery)<-[wo:WORKS_ON]-(p)
WHERE d.Actual_Delivery_Date >= Date_Past_Six_Month
WITH SUM(to.Hour) AS Total_Hour, SUM(wo.Task_Num_Total) AS Total_Task
WITH Total_Hour/Total_Task AS Hour_Per_Task
RETURN Hour_Per_Task
```

## q012: Please analyze the status of DIDs over the past 6 months and time spent on each

**Business intent**  
Analyzes the and time spent on each DID over the past 6 months.

**Parameters**

```json
{
"person": "Chen, Sizhen",
		"months": 6
}
```

**Cypher**

```cypher
WITH date()-duration({months: {{months: number of months}}}) AS Date_Past_Six_Month
MATCH (p:Person {Name:{{person:Name of the person}}})-[to:TIME_ON]->(didn:DIDN_Month)-[:BELONGS_TO]->(d:Delivery)
WHERE d.Actual_Delivery_Date >= Date_Past_Six_Month
WITH d.Name as DID, SUM(to.Hour) AS Total_Hour
RETURN DID, Total_Hour
```

## q013: Which DID did I spend the most time on in the past two weeks?

**Business intent**  
Finds which DID had the most time spent on in the past two weeks.

**Parameters**

```json
{
"person": "Chen, Sizhen",
		"weeks" : 2
}
```

**Cypher**

```cypher
WITH date()-duration({weeks: {{weeks: number of weeks}}}) AS Date_Past_Two_Weeks
MATCH (p:Person {Name:{{person:Name of the person}}})-[to:TIME_ON]->(didn:DIDN_Month)-[:BELONGS_TO]->(d:Delivery)
WHERE d.Actual_Delivery_Date >= Date_Past_Two_Weeks
WITH d.Name as DID, SUM(to.Hour) AS Total_Hour
RETURN DID, Total_Hour
ORDER BY Total_Hour DESC
```

## q015: Which domains have been worked on in the past period, and how many times?

**Business intent**  
Summarizes the domains worked on in the past period and the number of times each domain was worked on.

**Parameters**

```json
{
"person": "Chen, Sizhen",
        "startDate": "2025-01-01",
        "endDate": "2025-03-31"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Actual_Delivery_Date >= date({{startDate}} AND d.Actual_Delivery_Date <= date({{endDate}}
MATCH (d)-[rel:HAS_SDTM]->(sdtm:SDTM)
WHERE p.Name in [rel.Generation, rel.QC]
WITH sdtm.Name AS Domain, COUNT(sdtm.Name) AS CNT_SDTM
RETURN Domain, CNT_SDTM
```

## q016: Please help me summarize goals for direct report(s) to fill in the PLI system

**Business intent**  
Summarizes the goals for direct report(s) in terms of total studies, TLFs, and tasks for filling in the PLI system.

**Parameters**

```json
{
"Semester": 1,
		  "person": "Chen, Sizhen",
}
```

**Cypher**

```cypher
WITH {{Semester: Semester of PLI}} AS Semester
MATCH (p:Person {Name:{{person:Name of the person}}})-[wo:WORKS_ON]->(d:Delivery)
WHERE d.Actual_Delivery_Date.Month>=(Semester-1)*6 and d.Actual_Delivery_Date.Month<=Semester*6 AND d.Actual_Delivery_Date.Year=date().Year
WITH d.Actual_Delivery_Date as Actual_Delivery_Date, d.Name as Delivery
RETURN Actual_Delivery_Date, Delivery
ORDER BY Actual_Delivery_Date
```

## q117: recommend new studies or domains for a person based on their past experience.

**Business intent**  
Auto-parameterized query for question.

**Parameters**

```json
{
"personName": "Chen, Zhenchao (Riven)"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {personName}})-[:WORKS_ON]->(d:Delivery)<-[:HAS_DELIVERY]-(s:Study)
OPTIONAL MATCH (s)-[:HAS_DETAIL]->(info:Study_Info)
OPTIONAL MATCH (d)-[r:HAS_ADAM|HAS_SDTM]->(n)
WHERE (r.Generation CONTAINS p.Name OR r.QC CONTAINS p.Name)
RETURN 
p.Name AS Person_Name,
s.Name AS Study_Names,
COLLECT(DISTINCT info.Program_Code) AS Program_Codes,
COLLECT(DISTINCT info.Study_Type) AS Study_Types,
COLLECT(DISTINCT n.Name) AS Related_Domains
```

## q118: recommend new studies or domains for a person based on their past skills.

**Business intent**  
Auto-parameterized query for question.

**Parameters**

```json
{
"personName": "Chen, Zhenchao (Riven)"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {personName}})-[:WORKS_ON]->(d:Delivery)<-[:HAS_DELIVERY]-(s:Study)
OPTIONAL MATCH (s)-[:HAS_DETAIL]->(info:Study_Info)
OPTIONAL MATCH (d)-[r:HAS_ADAM|HAS_SDTM]->(n)
WHERE (r.Generation CONTAINS p.Name OR r.QC CONTAINS p.Name)
RETURN 
p.Name AS Person_Name,
s.Name AS Study_Names,
COLLECT(DISTINCT info.Program_Code) AS Program_Codes,
COLLECT(DISTINCT info.Study_Type) AS Study_Types,
COLLECT(DISTINCT n.Name) AS Related_Domains
```

## q125: Summarize someone's expertise in TA and Domain.

**Business intent**  
Auto-parameterized query for question.

**Parameters**

```json
{
"personName": "Chen, Zhenchao (Riven)"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {personName}})-[:WORKS_ON]->(d:Delivery)<-[:HAS_DELIVERY]-(s:Study)
OPTIONAL MATCH (s)-[:HAS_DETAIL]->(info:Study_Info)
OPTIONAL MATCH (d)-[r:HAS_ADAM|HAS_SDTM]->(n)
WHERE (r.Generation CONTAINS p.Name OR r.QC CONTAINS p.Name)
RETURN 
p.Name AS Person_Name,
s.Name AS Study_Names,
COLLECT(DISTINCT info.Program_Code) AS Program_Codes,
COLLECT(DISTINCT info.Study_Type) AS Study_Types,
COLLECT(DISTINCT n.Name) AS Related_Domains
```

## q134: list domains a person has involved

**Business intent**  
Auto-parameterized query for question.

**Parameters**

```json
{
"personName": "Chen, Zhenchao (Riven)"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {personName}})-[:WORKS_ON]->(d:Delivery)<-[:HAS_DELIVERY]-(s:Study)
OPTIONAL MATCH (s)-[:HAS_DETAIL]->(info:Study_Info)
OPTIONAL MATCH (d)-[r:HAS_ADAM|HAS_SDTM]->(n)
WHERE (r.Generation CONTAINS p.Name OR r.QC CONTAINS p.Name)
RETURN 
p.Name AS Person_Name,
s.Name AS Study_Names,
COLLECT(DISTINCT info.Program_Code) AS Program_Codes,
COLLECT(DISTINCT info.Study_Type) AS Study_Types,
COLLECT(DISTINCT n.Name) AS Related_Domains
```
