# Workload Planning Examples

> Use these as few-shot examples for DID Agent Text-to-Cypher. Replace parameter placeholders before execution.

## q017: Please tell me which deliveries are coming in the next 3 months weeks

**Business intent**  
Lists the deliveries that are coming within the specified period.

**Parameters**

```json
{
"months": 3,
	  "person": "Chen, Sizhen",
}
```

**Cypher**

```cypher
WITH date() as Date_Today, date() + duration({months: {{months:number of months}}}) as Date_Future_Three_Months
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= Date_Today AND d.Planned_Delivery_Date <= Date_Future_Three_Months
RETURN p.Name AS Person_Name, d.Planned_Delivery_Date as Planned_Delivery_Date, d.Name as Delivery, Date_Future_Three_Months
ORDER BY Planned_Delivery_Date
```

## q018: Please list the deliveries I am involved in and their delivery dates in the next two weeks, sorted by priority

**Business intent**  
Lists the deliveries for the person in the next two weeks, sorted by delivery date.

**Parameters**

```json
{
"person": "Chen, Sizhen"
}
```

**Cypher**

```cypher
WITH date() as Date_Today, date() + duration({weeks: 2}) as Date_Future_Two_Weeks
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= Date_Today AND d.Planned_Delivery_Date <= Date_Future_Two_Weeks
RETURN p.Name AS Person_Name, d.Planned_Delivery_Date as Planned_Delivery_Date, d.Name as Delivery, Date_Future_Three_Months
ORDER BY Planned_Delivery_Date
```

## q019: Please summarize the planned delivery dates and the remaining days for all ongoing deliveries

**Business intent**  
Summarizes the planned delivery dates and the remaining days for all ongoing deliveries.

**Parameters**

```json
{
"person": "Chen, Sizhen"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.DID_Status = 'Ongoing'
RETURN d.Name AS Delivery_Name, d.Planned_Delivery_Date as Planned_Delivery_Date, duration.inDays(date(), d.Planned_Delivery_Date).days AS Days_to_Planned_Delivery
ORDER BY Planned_Delivery_Date
```

## q020: Please summarize my delivery as SPL in the next three months

**Business intent**  
Summarizes delivery of the person as SPL in the next 3 months, including study names, delivery dates.

**Parameters**

```json
{
"person": "Chen, Sizhen",
		"months": 3
}
```

**Cypher**

```cypher
WITH date() as Date_Today, date() + duration({months: {{months:number of months}}}) as Date_Future_Three_Months
MATCH (p:Person {Name: {{person:Name of the person}}})-[wa:WORKS_AS]->(s:Study)-[:HAS_DELIVERY]->(d:Delivery)
WHERE wa.Role in ['SDSL', 'POC'] AND d.Planned_Delivery_Date >= Date_Today AND d.Planned_Delivery_Date <= Date_Future_Three_Months
RETURN d.Planned_Delivery_Date AS Planned_Delivery_Date, d.Name AS Delivery_Name
ORDER BY Planned_Delivery_Date
```

## q021: Please list the weekly work progress for the next two weeks, with a minimum work completion for each week

**Business intent**  
Summarizes the weekly work progress for the next two weeks with a minimum work completion for each week.

**Parameters**

```json
{
"person": "Chen, Sizhen",
		"weeks": 2
}
```

**Cypher**

```cypher
WITH date() as Date_Today, date() + duration({weeks: {{weeks:number of weeks}}}) as Date_Future_Two_Weeks
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= Date_Today AND d.Planned_Delivery_Date <= Date_Future_Two_Weeks
RETURN p.Name AS Person_Name, d.Planned_Delivery_Date as Planned_Delivery_Date, d.Name as Delivery, Date_Future_Three_Months
ORDER BY Planned_Delivery_Date
```

## q022: Based on my lot allocation, predict my workload

**Business intent**  
Predicts the workload based on the lot allocation by summarizing the total tasks assigned.

**Parameters**

```json
{
"person": "Chen, Sizhen"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person:Name of the person}}})-[wo:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= date()
RETURN d.Name as Delivery, d.Planned_Delivery_Date as Planned_Delivery_Date, 
wo.SDTM_Num_Generation AS SDTM_Num_Generation, wo.SDTM_Num_QC AS SDTM_Num_QC,
wo.ADaM_Num_Generation AS ADaM_Num_Generation, wo.ADaM_Num_QC AS ADaM_Num_QC,
wo.TLF_Num_Generation AS TLF_Num_Generation, wo.TLF_Num_QC AS TLF_Num_QC,
wo.Task_Num_Total AS Task_Num
```

## q023: Please list my work for the next six months

**Business intent**  
List the work schedule over the next six months

**Parameters**

```json
{
"person": "Chen, Sizhen",
		"months": 6
}
```

**Cypher**

```cypher
WITH date() as Date_Today, date() + duration({months: {{months:number of months}}}) as Date_Future_Six_Months
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= Date_Today AND d.Planned_Delivery_Date <= Date_Future_Six_Months
RETURN p.Name AS Person_Name, d.Planned_Delivery_Date as Planned_Delivery_Date, d.Name as Delivery, Date_Future_Three_Months
ORDER BY Planned_Delivery_Date
```

## q024: Please summarize the deliveries and tasks for the next one month/six months

**Business intent**  
Summarizes the deliveries and tasks for the specified period (1 month or 6 months).

**Parameters**

```json
{
"person": "Chen, Sizhen",
	  "months": 6
}
```

**Cypher**

```cypher
WITH date() as Date_Today, date() + duration({months: {{months:number of months}}}) as Date_Future_Six_Months
MATCH (p:Person {Name:{{person:Name of the person}}})-[wo:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= Date_Today and d.Planned_Delivery_Date <= Date_Future_Six_Months
WITH CASE WHEN duration.inDays(Date_Today, d.Planned_Delivery_Date).days < 30 THEN '1 Month' ELSE '6 Months' END AS With_In_Month,  d.Planned_Delivery_Date AS Planned_Delivery_Date, d.Name AS Delivery_Name
RETURN With_In_Month, Planned_Delivery_Date, Delivery_Name
ORDER BY Planned_Delivery_Date
```

## q025: How many tables/listings/figures need to be generated/QC'd within the next month?

**Business intent**  
Summarizes how many tables, listings, and figures need to be generated/QC'd within the next month.

**Parameters**

```json
{
"person": "Chen, Sizhen",
		"months": 1
}
```

**Cypher**

```cypher
WITH date() as Date_Today, date() + duration({months: {{months:number of months}}}) as Date_Future_One_Month
MATCH (p:Person {Name: {{person:Name of the person}}})-[wo:WORKS_ON]->(d:Delivery)-[h_tlf:HAS_TLF]->(tlf:TLF)
WHERE d.Planned_Delivery_Date >= Date_Today AND d.Planned_Delivery_Date <= Date_Future_One_Month AND p.Name=h_tlf.Generation
RETURN tlf.Type as Type, 'GEN' AS Role, count(1) AS CNT
UNION
WITH date() as Date_Today, date() + duration({months: 1}) as Date_Future_One_Month
MATCH (p:Person {Name: {{person:Name of the person}}})-[wo:WORKS_ON]->(d:Delivery)-[h_tlf:HAS_TLF]->(tlf:TLF)
WHERE d.Planned_Delivery_Date >= Date_Today AND d.Planned_Delivery_Date <= Date_Future_One_Month AND p.Name=h_tlf.QC
RETURN tlf.Type as Type, 'QC' AS Role, count(1) AS CNT
ORDER BY Type, Role
```

## q026: Please provide a clear delivery timeline for the next three months in the form of a schedule

**Business intent**  
Provides a detailed delivery timeline for the next three months

**Parameters**

```json
{
"person": "Chen, Sizhen",
		"months": 3
}
```

**Cypher**

```cypher
WITH date() as Date_Today, date() + duration({months: {{months:number of months}}}) as Date_Future_Three_Months
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= Date_Today AND d.Planned_Delivery_Date <= Date_Future_Three_Months
RETURN p.Name AS Person_Name, d.Planned_Delivery_Date as Planned_Delivery_Date, d.Name as Delivery, Date_Future_Three_Months
ORDER BY Planned_Delivery_Date
```

## q028: Can you give me a To-Do list, telling me which tasks should be prioritized, and which tasks are more urgent?

**Business intent**  
Generates a To-Do list with tasks prioritized by delivery dates and urgency.

**Parameters**

```json
{
"months": 3,
	  "person": "Chen, Sizhen"
}
```

**Cypher**

```cypher
WITH date() as Date_Today, date() + duration({months: {{months:Number of Months}}}) as Date_Future_Three_Months
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= Date_Today AND d.Planned_Delivery_Date <= Date_Future_Three_Months
RETURN p.Name AS Person_Name, d.Planned_Delivery_Date as Planned_Delivery_Date, d.Name as Delivery, Date_Future_Three_Months
ORDER BY Planned_Delivery_Date
```

## q029: Estimate the work hours required for the next three months' workload based on standard work efficiency

**Business intent**  
Estimates the total work hours required for the next three months based on standard work efficiency (average time per task).

**Parameters**

```json
{
"person": "Chen, Sizhen",
	  "months": 3
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person:Name of the person}}})-[to:TIME_ON]->(didn:DIDN_Month)-[:BELONGS_TO]->(d:Delivery)<-[wo:WORKS_ON]-(p)
WHERE d.Actual_Delivery_Date <= date()
WITH SUM(to.Hour) AS Total_Hour, SUM(wo.Task_Num_Total) AS Total_Task
WITH Total_Hour/Total_Task AS Hour_Per_Task, date() as Date_Today, date() + duration({months: {{months:Number of Months}}}) as Date_Future_Three_Months
MATCH (p:Person {Name: {{person:Name of the person}}})-[wo:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= Date_Today AND d.Planned_Delivery_Date <= Date_Future_Three_Months
WITH d.Name as Delivery, wo.Task_Num_Total * Hour_Per_Task AS Expected_Hour
RETURN Delivery, Expected_Hour
```

## q030: Please organize the final tasks for this week from the dLoT that I need to be responsible for, and list by study

**Business intent**  
Organizes the final tasks for the current week and outputs them by study in an Excel-compatible format.

**Parameters**

```json
{
"person": "Chen, Sizhen",
		"weeks": 1,
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= date() AND d.Planned_Delivery_Date <=date()+duration({weeks:{{weeks: Future Weeks}})
MATCH (d)-[r:HAS_SDTM]->(t:SDTM) WHERE p.Name=r.Generation
WITH d.Study AS Study, 'GEN' AS Role, t.Type AS Type, t.Name AS Name
RETURN Study, Type, Role, Name
UNION
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= date() AND d.Planned_Delivery_Date <=date()+duration({weeks:{{weeks: Future Weeks}}})
MATCH (d)-[r:HAS_SDTM]->(t:SDTM) WHERE p.Name=r.QC
WITH d.Study AS Study, 'QC' AS Role, t.Type AS Type, t.Name AS Name
RETURN Study, Type, Role, Name
UNION
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= date() AND d.Planned_Delivery_Date <=date()+duration({weeks:{{weeks: Future Weeks}}})
MATCH (d)-[r:HAS_ADAM]->(t:ADAM) WHERE p.Name=r.Generation
WITH d.Study AS Study, 'GEN' AS Role, t.Type AS Type, t.Name AS Name
RETURN Study, Type, Role, Name
UNION
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= date() AND d.Planned_Delivery_Date <=date()+duration({weeks:{{weeks: Future Weeks}}})
MATCH (d)-[r:HAS_ADAM]->(t:ADAM) WHERE p.Name=r.QC
WITH d.Study AS Study, 'QC' AS Role, t.Type AS Type, t.Name AS Name
RETURN Study, Type, Role, Name
UNION
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= date() AND d.Planned_Delivery_Date <=date()+duration({weeks:{{weeks: Future Weeks}}})
MATCH (d)-[r:HAS_TLF]->(t:TLF) WHERE p.Name=r.GEN
WITH d.Study AS Study, 'GEN' AS Role, t.Type AS Type, t.Name AS Name
RETURN Study, Type, Role, Name
UNION
MATCH (p:Person {Name: {{person:Name of the person}}})-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= date() AND d.Planned_Delivery_Date <=date()+duration({weeks:{{weeks: Future Weeks}}})
MATCH (d)-[r:HAS_TLF]->(t:TLF) WHERE p.Name=r.QC
WITH d.Study AS Study, 'QC' AS Role, t.Type AS Type, t.Name AS Name
RETURN Study, Type, Role, Name
ORDER BY Study, Type, Role, Name
```

## q038: Calculate which DIDs I should work on in the next few weeks and months. Please estimate the time required for each week or each month for these DIDs.

**Business intent**  
Auto-parameterized query for question

**Parameters**

```json
{
"person_name": "PERSON_NAME"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person_name:Person name}})-[r:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= date()
  AND d.Planned_Delivery_Date <= date() + duration('P90D')
WITH d, r, d.Planned_Delivery_Date as Due_Date,
     CASE 
       WHEN d.Planned_Delivery_Date <= date() + duration('P7D') THEN 'This_Week'
       WHEN d.Planned_Delivery_Date <= date() + duration('P14D') THEN 'Next_Week'
       WHEN d.Planned_Delivery_Date <= date() + duration('P30D') THEN 'This_Month'
       WHEN d.Planned_Delivery_Date <= date() + duration('P60D') THEN 'Next_Month'
       ELSE 'Future'
     END AS Time_Period
RETURN Time_Period,
       COLLECT(d.DID) as DIDs,
       COUNT(d) as DID_Count,
       SUM(r.TLF_Num_Total) as Total_TLF_Tasks,
       SUM(r.ADaM_Num_Total) as Total_ADaM_Tasks,
       SUM(r.SDTM_Num_Total) as Total_SDTM_Tasks,
       SUM(r.Task_Num_Total) as Total_Tasks,
       MIN(Due_Date) as Earliest_Due_Date,
       MAX(Due_Date) as Latest_Due_Date
ORDER BY 
  CASE Time_Period
    WHEN 'This_Week' THEN 1
    WHEN 'Next_Week' THEN 2
    WHEN 'This_Month' THEN 3
    WHEN 'Next_Month' THEN 4
    ELSE 5
  END
```

## q039: The total duration is 40 hours; what is the percentage of time each project takes this week?

**Business intent**  
Auto-parameterized query for question

**Parameters**

```json
{
"person_name": "PERSON_NAME"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person_name:Person name}})-[r:WORKS_ON]->(d:Delivery)
WHERE d.DID_Status <> 'Completed'
  AND d.Planned_Delivery_Date >= date()
RETURN d.DID, 
       d.Study,
       d.Planned_Delivery_Date,
       r.TLF_Num_Total as TLF_Tasks,
       r.ADaM_Num_Total as ADaM_Tasks,
       r.SDTM_Num_Total as SDTM_Tasks,
       r.Task_Num_Total as Total_Tasks,
       duration.between(date(), d.Planned_Delivery_Date).days as Days_Until_Due
ORDER BY d.Planned_Delivery_Date
```

## q079: Please let me know which {{status:Delivery status}} deliveries my DU (under manager {{manager:Person name}}) is involved in that are approaching their due date in next {{period:Days}} days

**Business intent**  
Auto-parameterized query to list DU's approaching due date deliveries in next N days

**Parameters**

```json
{
"manager": "tao, yuxi",
      "period": 14,
      "status": ["Ongoing", "Planned"]
}
```

**Cypher**

```cypher
WITH "{{manager:Person name}}" AS managerName, date() AS today, date() + duration({days: {{period:Days}}}) AS approachingDueDateEnd MATCH (you:Person) WHERE replace(toUpper(you.Name), " ", "") = replace(toUpper(managerName), " ", "") OPTIONAL MATCH (you)<-[:REPORTS_TO]-(subordinate:Person) WITH you, collect(DISTINCT subordinate.Name) + you.Name AS managerAndSubordinatesNames, today, approachingDueDateEnd MATCH (delivery:Delivery) WHERE (delivery.SDSL IN managerAndSubordinatesNames OR delivery.SDSA_US_PoC IN managerAndSubordinatesNames OR delivery.SDSA_China_PoC IN managerAndSubordinatesNames OR delivery.SDSA_India_PoC IN managerAndSubordinatesNames OR delivery.FSP_Ephicacy_PoC IN managerAndSubordinatesNames OR delivery.FSP_Fortrea_PoC IN managerAndSubordinatesNames OR delivery.FSP_TCS_PoC IN managerAndSubordinatesNames OR delivery.FSP_Other_PoC IN managerAndSubordinatesNames) AND delivery.Planned_Delivery_Date >= today AND delivery.Planned_Delivery_Date <= approachingDueDateEnd AND delivery.DID_Status IN {{status:Delivery status}} AND delivery.Planned_Delivery_Date IS NOT NULL OPTIONAL MATCH (delivery)<-[:HAS_DELIVERY]->(study:Study) RETURN you.Name AS Manager_Name, COUNT(DISTINCT delivery.DID) AS Total_Approaching_Deliveries, collect(DISTINCT {DID: delivery.DID, Study_Name: study.Name, Planned_Due_Date: delivery.Planned_Delivery_Date, Days_Until_Due: duration.between(today, delivery.Planned_Delivery_Date).days}) AS Approaching_Delivery_Details;
```

## q080: Please tell me which deliveries will overlap in timeline in the next two months.

**Business intent**  
Auto-parameterized query for question

**Parameters**

```json
{
"person_name": "PERSON_NAME"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person_name:Person name}})-[:WORKS_ON]->(d1:Delivery)
MATCH (p)-[:WORKS_ON]->(d2:Delivery)
WHERE d1.DID <> d2.DID
  AND d1.Planned_Delivery_Date <= date() + duration('P60D')
  AND d2.Planned_Delivery_Date <= date() + duration('P60D')
  AND d1.Planned_Delivery_Date <= d2.Planned_Delivery_Date + duration('P30D')
  AND d1.Planned_Delivery_Date + duration('P30D') >= d2.Planned_Delivery_Date
RETURN d1.DID as DID1, d1.Planned_Delivery_Date as Date1, d1.Study as Study1,
       d2.DID as DID2, d2.Planned_Delivery_Date as Date2, d2.Study as Study2
ORDER BY d1.Planned_Delivery_Date
```

## q082: Please remind me which of these DIDs should be delivered first.

**Business intent**  
Auto-parameterized query for question

**Parameters**

```json
{
"person_name": "PERSON_NAME"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person_name:Person name}})-[:WORKS_ON]->(d:Delivery)
WHERE d.DID_Status <> 'Completed'
RETURN d.DID, d.Planned_Delivery_Date, d.DID_Status, d.Study,
       duration.between(date(), d.Planned_Delivery_Date).days as Days_Until_Due
ORDER BY d.Planned_Delivery_Date
```

## q083: Which DIDs have my name on them, but I have not yet filled in the daily survey for?

**Business intent**  
Auto-parameterized query for question

**Parameters**

```json
{
"person_name": "PERSON_NAME"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person_name:Person name}})-[r:WORKS_ON]->(d:Delivery)
WHERE NOT EXISTS {
  MATCH (p)-[:TIME_ON]->(dm:DIDN_Month)
  WHERE dm.DID = d.DID
}
RETURN d.DID, d.Planned_Delivery_Date, d.DID_Status
ORDER BY d.Planned_Delivery_Date
```

## q084: Based on historical delivery data, which resource bottlenecks might occur in the next three months?

**Business intent**  
Auto-parameterized query for question

**Parameters**

```json
{
{}
}
```

**Cypher**

```cypher
MATCH (p:Person)-[r:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= date() - duration('P90D')
WITH p,
     SUM(CASE WHEN d.Planned_Delivery_Date < date() THEN r.Task_Num_Total ELSE 0 END) as Past_3_Months_Tasks,
     SUM(CASE WHEN d.Planned_Delivery_Date >= date() THEN r.Task_Num_Total ELSE 0 END) as Next_3_Months_Tasks
WHERE Next_3_Months_Tasks >= 2 * Past_3_Months_Tasks AND Past_3_Months_Tasks > 0
RETURN p.Name as Person, 
       Past_3_Months_Tasks, 
       Next_3_Months_Tasks,
       ROUND(Next_3_Months_Tasks * 100.0 / Past_3_Months_Tasks, 2) as Increase_Percentage,
       'High Risk - Workload doubled or more' as Risk_Level
ORDER BY Next_3_Months_Tasks DESC
```

## q088: Please remind me if there will be any periods in my DU with particularly few deliveries.

**Business intent**  
Auto-parameterized query for question

**Parameters**

```json
{
"manager_name": "Wang, Yinglu",
      "min_deliveries": 2
}
```

**Cypher**

```cypher
MATCH (manager:Person {Name: {{manager_name:Manager name}}})
MATCH (manager)<-[:REPORTS_TO]-(p:Person)-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= date()
WITH d.Month as Month, d.Year as Year, COUNT(d) as Delivery_Count
WHERE Delivery_Count < {{min_deliveries:Minimum delivery threshold}}
RETURN Year, Month, Delivery_Count, 'Low delivery period in DU' as Alert
ORDER BY Year, Month
```

## q089: If I am involved in multiple DIDs, please tell me which of these should be delivered first.

**Business intent**  
Auto-parameterized query for question

**Parameters**

```json
{
"person_name": "PERSON_NAME"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person_name:Person name}})-[r:WORKS_ON]->(d:Delivery)
WHERE d.DID_Status <> 'Completed'
RETURN d.DID, d.Planned_Delivery_Date, d.DID_Status, d.Study,
       duration.between(date(), d.Planned_Delivery_Date).days as Days_Until_Due
ORDER BY d.Planned_Delivery_Date DESC
```

## q090: Send a bi-weekly upcoming delivery report to the TA lead.

**Business intent**  
Auto-parameterized query for question

**Parameters**

```json
{
"ta_lead_name": "TA_LEAD_NAME"
}
```

**Cypher**

```cypher
MATCH (ta:Person {TA_Lead_Name: {{ta_lead_name:TA Lead name}}})
MATCH path = (ta)<-[:REPORTS_TO*1..]-(p:Person)
MATCH (p)-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date <= date() + duration('P14D')
  AND d.Planned_Delivery_Date >= date()
RETURN p.Name as Team_Member, 
       length(path) as Reporting_Level,
       d.DID, d.Planned_Delivery_Date, d.DID_Status, d.Study
ORDER BY d.Planned_Delivery_Date DESC, p.Name
```

## q091: Please regularly update me on the delivery status of my DU across the entire department.

**Business intent**  
Auto-parameterized query for question

**Parameters**

```json
{
{}
}
```

**Cypher**

```cypher
MATCH (team_lead:Person)
WHERE team_lead.Manager = 'Y'
MATCH (team_lead)<-[:REPORTS_TO]-(member:Person)
OPTIONAL MATCH (member)-[:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= date() - duration('P30D')
  OR d.Actual_Delivery_Date >= date() - duration('P30D')
WITH team_lead, member, COLLECT(DISTINCT d.DID) as Member_DIDs_List
WITH team_lead,
     COUNT(DISTINCT member) as Team_Size,
     SUM(SIZE(Member_DIDs_List)) as Total_Deliveries_Past_Month,
     COLLECT({Member: member.Name, DIDs: Member_DIDs_List}) as Member_DIDs
RETURN team_lead.Name as Team_Lead,
       team_lead.Team_Lead_Name as DU_Name,
       Team_Size,
       Total_Deliveries_Past_Month,
       Member_DIDs
ORDER BY team_lead.Name
```

## q092: Which DIDs have I been assigned tasks for, but I have never filled out the daily survey for?

**Business intent**  
Auto-parameterized query for question

**Parameters**

```json
{
"person_name": "PERSON_NAME"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person_name:Person name}})-[r:WORKS_ON]->(d:Delivery)
WHERE NOT EXISTS {
  MATCH (p)-[:TIME_ON]->(dm:DIDN_Month)
  WHERE dm.DID = d.DID
}
RETURN d.DID, d.Planned_Delivery_Date, d.DID_Status, d.Study
ORDER BY d.Planned_Delivery_Date DESC
```

## q102: Please tell me which DID I should fill in for today's work.

**Business intent**  
Auto-parameterized query for question

**Parameters**

```json
{
"person_name": "PERSON_NAME"
}
```

**Cypher**

```cypher
MATCH (p:Person {Name: {{person_name:Person name}})-[r:WORKS_ON]->(d:Delivery)
WHERE d.Planned_Delivery_Date >= date()
  AND d.DID_Status <> 'Completed'
RETURN d.DID, d.Planned_Delivery_Date, d.DID_Status, d.Study,
       duration.between(date(), d.Planned_Delivery_Date).days as Days_Until_Due
ORDER BY d.Planned_Delivery_Date
```
