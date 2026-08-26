# Neo4j Database Schema for DID Agent

This schema describes the DID Neo4j graph used by the DID Agent for Text-to-Cypher generation.

## Nodes

### Study

Properties:

- `Name`
- `SDSL`
- `SDSA_US_PoC`
- `SDSA_China_PoC`
- `SDSA_India_PoC`
- `FSP_Ephicacy_PoC`
- `FSP_Fortrea_PoC`
- `FSP_TCS_PoC`
- `FSP_Other_PoC`
- `IPort_Study`
- `SharePoint_ID`

### Delivery

Properties:

- `Name`
- `DID`
- `DID_Status`
- `Reporting_Event`
- `Reporting_Detail`
- `Draft_or_Final`
- `Planned_Delivery_Date`
- `SDSL`
- `Actual_Delivery_Date`
- `Reporting_Path`
- `Quality`
- `Reporting_System`
- `Delivery_Content`
- `Study`
- `SDTM_Num`
- `ADAM_Num`
- `TLF_Num`
- `Task_Num`
- `Year`
- `Month`
- `ID_in_Portfolio_Milestone_list1`
- `ID_in_Portfolio_Milestone_list2`
- `ID_in_Portfolio_Milestone_list3`
- `ID_in_Portfolio_Milestone_list4`
- `ID_in_Portfolio_Milestone_list5`
- `Total_Task_Num`

### Study_Info

Properties:

- `Name`
- `Plan_Status`
- `Plan_Phase`
- `Study_Type`
- `FAP`
- `FSFV`
- `LSLV`
- `PCD`
- `DBR`
- `Short_Name`
- `Business_Rationale`
- `Generic_Name`
- `Trade_Name`
- `Candidate_Code`
- `Compound_Name`
- `Study_Number_Reg`
- `Registry_Status`
- `Subject_Type`
- `Planned_Countries`
- `Study_Design`
- `Study_Description`
- `Program_Code`
- `Compound_Number`
- `Project_Code`
- `Project_Name`
- `TA`
- `Indications`

### Site

Properties:

- `Name`
- `Category`

### Unblind

Properties:

- `Unblind_Programming_Support`

### Person

Properties:

- `Name`
- `Manager`
- `Group_Lead`
- `TA_Lead`
- `Email`
- `NTID`
- `Status`
- `Onboard_Date`
- `Offboard_Date`
- `Offboard_Year`
- `Service_Year`
- `Team_Lead_Name`
- `Group_Lead_Name`
- `TA_Lead_Name`

### DID0

Properties:

- `Name`
- `DID`

### Study_Month

Properties:

- `Name`
- `Study`
- `Year`
- `Month`
- `DID0_Hour`
- `DIDN_Hour`

### DID0_Month

Properties:

- `Name`
- `DID`
- `DID_Type`
- `Year`
- `Month`
- `Hour`

### DIDN_Month

Properties:

- `Name`
- `DID`
- `DID_Type`
- `Year`
- `Month`
- `Hour`

### SDTM

Properties:

- `Name`
- `Category`
- `Type`

### ADAM

Properties:

- `Name`
- `Category`
- `Type`

### TLF

Properties:

- `Name`
- `Category`
- `Type`
- `Source`

### Submission

Properties:

- `Project_Code`
- `Milestone`
- `Portfolio_ID`
- `Name`
- `Priority_Tier`
- `Submission_Lead`
- `TA`
- `Region`
- `Plan_Finish`

## Relationships

### Study-related relationships

```cypher
(Study)-[:HAS_DELIVERY]->(Delivery)
(Study)-[:HAS_DETAIL]->(Study_Info)
(Study)-[:HAS_DID0]->(DID0)
```

### Delivery-related relationships

```cypher
(Delivery)-[:IS_UNBLIND_SUPPORT]->(Unblind)
(Delivery)-[:HAS_SDTM {Generation, QC}]->(SDTM)
(Delivery)-[:HAS_ADAM {Generation, QC}]->(ADAM)
(Delivery)-[:HAS_TLF {Generation, QC, File_Name, TLF_Number}]->(TLF)
(Delivery)-[:SUPPORT_SUBMISSION]->(Submission)
```

### Person-related relationships

```cypher
(Person)-[:WORKS_AS {Role}]->(Study)
(Person)-[:FROM_SITE]->(Site)
(Person)-[:REPORTS_TO]->(Person)
(Person)-[:WORKS_ON {
  TLF_Num_Total,
  TLF_Num_Generation,
  TLF_Num_QC,
  ADaM_Num_Total,
  ADaM_Num_Generation,
  ADaM_Num_QC,
  SDTM_Num_Total,
  SDTM_Num_Generation,
  SDTM_Num_QC,
  Task_Num_Total,
  Task_Num_Generation,
  Task_Num_QC
}]->(Delivery)
(Person)-[:LEADS_SUBMISSION]->(Submission)
```

### Month and time relationships

```cypher
(Study_Month)-[:BELONGS_TO]->(Study)
(DID0_Month)-[:BELONGS_TO]->(DID0)
(DIDN_Month)-[:BELONGS_TO]->(Delivery)
(DID0_Month)-[:PART_OF]->(Study_Month)
(DIDN_Month)-[:PART_OF]->(Study_Month)
(Person)-[:TIME_ON {Hour, DID_Type}]->(Study_Month)
(Person)-[:TIME_ON {From_Date, To_Date, Hour}]->(DID0_Month)
(Person)-[:TIME_ON {From_Date, To_Date, Hour}]->(DIDN_Month)
```

## Common Cypher Patterns

### Flexible person-name matching

```cypher
replace(toUpper(p.Name), " ", "") = replace(toUpper("{{person_name}}"), " ", "")
```

### Completed deliveries

```cypher
d.DID_Status = "Completed"
```

### Ongoing or planned deliveries

```cypher
d.DID_Status IN ["Ongoing", "Planned"]
```

or:

```cypher
NOT toUpper(d.DID_Status) IN ["COMPLETED", "CANCELLED", "TERMINATED"]
```

### Month range filtering

```cypher
(d.Year * 12 + d.Month) >= minMonth
AND (d.Year * 12 + d.Month) <= maxMonth
```

### Group Lead lookup

```cypher
OPTIONAL MATCH (person)-[:REPORTS_TO*1..]->(groupLead:Person)
WHERE groupLead.Group_Lead = "Y"
```

### TA Lead lookup

```cypher
OPTIONAL MATCH (person)-[:REPORTS_TO*1..]->(taLead:Person)
WHERE taLead.TA_Lead = "Y"
```

## Important Notes

- Use only the labels, relationships, and properties defined here.
- Do not invent labels, relationships, or properties.
- Use read-only Cypher for the CLI Agent.
- Do not use write operations such as `CREATE`, `MERGE`, `DELETE`, `SET`, `REMOVE`, or `DROP`.
