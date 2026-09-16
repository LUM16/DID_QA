"""Registry-driven, read-only result templates for the DID graph."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

Usage = dict[str, int]
Chat = Callable[[str, str], tuple[str, Usage]]
Query = Callable[[str], list[dict[str, Any]]]

DID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*_\d+$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VALID_STATUS = {"planned": "Planned", "ongoing": "Ongoing", "completed": "Completed"}


@dataclass(frozen=True)
class FixedTemplate:
    """A fixed result contract and its allowed extracted parameters."""

    intent: str
    title: str
    required: tuple[str, ...]
    optional: tuple[str, ...]
    chart: dict[str, Any] | None
    data_note: str
    query: Callable[[dict[str, Any]], str]


def _esc(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def _quoted(value: Any) -> str:
    return f"'{_esc(value)}'"


def _limit(params: dict[str, Any]) -> int:
    value = params.get("limit", 20)
    return value if isinstance(value, int) and 1 <= value <= 100 else 20


def _date_filters(
    params: dict[str, Any], field: str = "d.Planned_Delivery_Date"
) -> str:
    clauses: list[str] = []
    if params.get("start_date"):
        clauses.append(f"toString({field}) >= {_quoted(params['start_date'])}")
    if params.get("end_date"):
        clauses.append(f"toString({field}) <= {_quoted(params['end_date'])}")
    return (" AND " + " AND ".join(clauses)) if clauses else ""


def _status_filter(params: dict[str, Any], field: str = "d.DID_Status") -> str:
    return f" AND {field} = {_quoted(params['status'])}" if params.get("status") else ""


def _person_where(params: dict[str, Any], alias: str = "p") -> str:
    return f"{alias}.Name = {_quoted(params['person'])}"


def _did_where(params: dict[str, Any], alias: str = "d", key: str = "did") -> str:
    return f"toString({alias}.DID) = {_quoted(params[key])}"


def _study_where(params: dict[str, Any], alias: str = "s") -> str:
    value = _quoted(params["study"])
    return f"({alias}.Name = {value} OR {alias}.IPort_Study = {value})"


def _lot_filters(params: dict[str, Any]) -> str:
    clauses: list[str] = []
    if params.get("source"):
        clauses.append(f"lot.Source = {_quoted(params['source'])}")
    if params.get("task_type"):
        label = {"tlf": "TLF", "adam": "ADAM", "sdtm": "SDTM"}.get(
            str(params["task_type"]).casefold()
        )
        if not label:
            raise ValueError("task_type must be TLF, ADaM, or SDTM.")
        clauses.append(f"lot:{label}")
    return (" AND " + " AND ".join(clauses)) if clauses else ""


def _person_monthly_hours(p: dict[str, Any]) -> str:
    return f"""
MATCH (person:Person)-[time:TIME_ON]->(:DIDN_Month)
WHERE {_person_where(p, 'person')}{_date_filters(p, 'time.From_Date')}
WITH substring(toString(time.From_Date), 0, 7) AS month, sum(toFloat(time.Hour)) AS hours
WHERE month IS NOT NULL AND month <> ''
RETURN month, round(hours, 1) AS hours
ORDER BY month
"""


def _person_did_effort(p: dict[str, Any]) -> str:
    return f"""
MATCH (person:Person)-[time:TIME_ON]->(:DIDN_Month)-[:BELONGS_TO]->(d:Delivery)
OPTIONAL MATCH (s:Study)-[:HAS_DELIVERY]->(d)
WHERE {_person_where(p, 'person')}{_date_filters(p, 'time.From_Date')}{_status_filter(p)}
RETURN d.DID AS did, s.Name AS study, d.DID_Status AS status,
       d.Planned_Delivery_Date AS planned_delivery_date,
       round(sum(toFloat(time.Hour)), 1) AS hours,
       round(sum(toFloat(time.Hour)) / CASE WHEN coalesce(d.Task_Num, 0) > 0 THEN d.Task_Num ELSE 1 END, 1) AS hours_per_task
ORDER BY hours DESC, did
LIMIT {_limit(p)}
"""


def _person_delivery_summary(p: dict[str, Any]) -> str:
    return f"""
MATCH (person:Person)-[work:WORKS_ON]->(d:Delivery)
OPTIONAL MATCH (s:Study)-[:HAS_DELIVERY]->(d)
WHERE {_person_where(p, 'person')}{_date_filters(p)}{_status_filter(p)}
RETURN d.DID AS did, s.Name AS study, d.DID_Status AS status,
       d.Planned_Delivery_Date AS planned_delivery_date,
       coalesce(work.Task_Num_Total, work.CSR_Task_Num_Total, 0) AS task_count,
       coalesce(work.TLF_Num_Total, work.CSR_TLF_Num_Total, 0) AS tlf_count
ORDER BY planned_delivery_date DESC, did
LIMIT {_limit(p)}
"""


def _person_domain_experience(p: dict[str, Any]) -> str:
    return f"""
MATCH (person:Person)-[:WORKS_ON]->(d:Delivery)-[:HAS_SDTM|HAS_ADAM|HAS_TLF]->(lot)
OPTIONAL MATCH (s:Study)-[:HAS_DELIVERY]->(d)
WHERE {_person_where(p, 'person')}{_date_filters(p)}
RETURN coalesce(lot.Category, lot.Type, 'Unspecified') AS domain,
       count(DISTINCT d) AS did_count, count(lot) AS item_count,
       collect(DISTINCT s.Name)[0..10] AS studies
ORDER BY item_count DESC, domain
LIMIT {_limit(p)}
"""


def _person_efficiency_comparison(p: dict[str, Any]) -> str:
    return f"""
MATCH (person:Person)-[time:TIME_ON]->(:DIDN_Month)-[:BELONGS_TO]->(d:Delivery)
WHERE {_person_where(p, 'person')}{_date_filters(p, 'time.From_Date')}
WITH substring(toString(time.From_Date), 0, 7) AS period,
     sum(toFloat(time.Hour)) AS hours, count(DISTINCT d) AS did_count
RETURN period, round(hours, 1) AS hours, did_count,
       round(hours / CASE WHEN did_count > 0 THEN did_count ELSE 1 END, 1) AS hours_per_did
ORDER BY period
"""


def _person_assignment_list(p: dict[str, Any]) -> str:
    return f"""
MATCH (person:Person)-[work:WORKS_ON]->(d:Delivery)
OPTIONAL MATCH (s:Study)-[:HAS_DELIVERY]->(d)
WHERE {_person_where(p, 'person')}{_date_filters(p)}{_status_filter(p)}
RETURN d.DID AS did, s.Name AS study, d.DID_Status AS status,
       d.Planned_Delivery_Date AS planned_delivery_date,
       d.Reporting_Event AS reporting_event,
       coalesce(work.Task_Num_Total, work.CSR_Task_Num_Total, 0) AS task_count
ORDER BY planned_delivery_date, did
LIMIT {_limit(p)}
"""


def _personal_workload_mix(p: dict[str, Any]) -> str:
    return f"""
MATCH (person:Person)-[work:WORKS_ON]->(d:Delivery)
WHERE {_person_where(p, 'person')}{_date_filters(p)}
RETURN d.DID AS did,
   coalesce(work.TLF_Num_Total, work.CSR_TLF_Num_Total, 0) AS tlf,
   coalesce(work.ADaM_Num_Total, work.CSR_ADaM_Num_Total, 0) AS adam,
   coalesce(work.SDTM_Num_Total, work.CSR_SDTM_Num_Total, 0) AS sdtm,
   coalesce(work.Task_Num_Generation, work.CSR_Task_Num_Generation, 0) AS generation,
   coalesce(work.Task_Num_QC, work.CSR_Task_Num_QC, 0) AS qc
ORDER BY did
LIMIT {_limit(p)}
"""


def _delivery_priority_list(p: dict[str, Any]) -> str:
    owner = (
        _person_where(p)
        if p.get("person")
        else f"p.Manager = {_quoted(p['manager'])}"
    )
    return f"""
MATCH (p:Person)-[work:WORKS_ON]->(d:Delivery)
OPTIONAL MATCH (s:Study)-[:HAS_DELIVERY]->(d)
WHERE {owner}{_date_filters(p)}{_status_filter(p)}
RETURN d.DID AS did, s.Name AS study, d.DID_Status AS status,
       d.Planned_Delivery_Date AS planned_delivery_date,
       duration.inDays(date(), date(toString(d.Planned_Delivery_Date))).days AS days_remaining,
       coalesce(work.Task_Num_Total, work.CSR_Task_Num_Total, 0) AS task_count
ORDER BY days_remaining, planned_delivery_date
LIMIT {_limit(p)}
"""


def _delivery_overlap_timeline(p: dict[str, Any]) -> str:
    owner = _person_where(p) if p.get("person") else f"p.Manager = {_quoted(p['manager'])}"
    return f"""
MATCH (p:Person)-[:WORKS_ON]->(d:Delivery)
OPTIONAL MATCH (s:Study)-[:HAS_DELIVERY]->(d)
WHERE {owner}{_date_filters(p)}
RETURN d.DID AS did, s.Name AS study, d.DID_Status AS status,
       d.Planned_Delivery_Date AS planned_delivery_date,
       count(DISTINCT p) AS assigned_people
ORDER BY planned_delivery_date, did
LIMIT {_limit(p)}
"""


def _did_person_contribution(p: dict[str, Any]) -> str:
    return f"""
MATCH (person:Person)-[time:TIME_ON]->(:DIDN_Month)-[:BELONGS_TO]->(d:Delivery)
WHERE {_did_where(p)}{_date_filters(p, 'time.From_Date')}
RETURN person.Name AS person, round(sum(toFloat(time.Hour)), 1) AS hours
ORDER BY hours DESC, person
LIMIT {_limit(p)}
"""


def _did_lot_breakdown(p: dict[str, Any]) -> str:
    return f"""
MATCH (d:Delivery)-[:HAS_SDTM|HAS_ADAM|HAS_TLF]->(lot)
WHERE {_did_where(p)}{_lot_filters(p)}
RETURN CASE WHEN lot:TLF THEN 'TLF' WHEN lot:ADAM THEN 'ADaM' ELSE 'SDTM' END AS task_type,
       lot.Category AS category, lot.Name AS name, lot.Type AS type,
       lot.Source AS source, count(*) AS item_count
ORDER BY task_type, category, name
LIMIT {_limit(p)}
"""


def _did_task_composition(p: dict[str, Any]) -> str:
    scope = _did_where(p) if p.get("did") else _study_where(p)
    pattern = "(d:Delivery)" if p.get("did") else "(s:Study)-[:HAS_DELIVERY]->(d:Delivery)"
    return f"""
MATCH {pattern}-[:HAS_SDTM|HAS_ADAM|HAS_TLF]->(lot)
WHERE {scope}{_lot_filters(p)}
RETURN d.DID AS did,
       sum(CASE WHEN lot:TLF THEN 1 ELSE 0 END) AS tlf,
       sum(CASE WHEN lot:ADAM THEN 1 ELSE 0 END) AS adam,
       sum(CASE WHEN lot:SDTM THEN 1 ELSE 0 END) AS sdtm
ORDER BY did
LIMIT {_limit(p)}
"""


def _did_comparison(p: dict[str, Any]) -> str:
    return f"""
MATCH (d:Delivery)-[:HAS_SDTM|HAS_ADAM|HAS_TLF]->(lot)
WHERE toString(d.DID) IN [{_quoted(p['did_1'])}, {_quoted(p['did_2'])}]
RETURN d.DID AS did,
       sum(CASE WHEN lot:TLF THEN 1 ELSE 0 END) AS tlf,
       sum(CASE WHEN lot:ADAM THEN 1 ELSE 0 END) AS adam,
       sum(CASE WHEN lot:SDTM THEN 1 ELSE 0 END) AS sdtm
ORDER BY did
"""


def _delivery_search_results(p: dict[str, Any]) -> str:
    conditions = []
    if p.get("did"):
        conditions.append(_did_where(p))
    if p.get("study"):
        conditions.append(_study_where(p, "s"))
    if p.get("keyword"):
        conditions.append(f"toLower(coalesce(d.Reporting_Event, '')) CONTAINS toLower({_quoted(p['keyword'])})")
    if p.get("status"):
        conditions.append(f"d.DID_Status = {_quoted(p['status'])}")
    return f"""
MATCH (s:Study)-[:HAS_DELIVERY]->(d:Delivery)
WHERE {' AND '.join(conditions)}{_date_filters(p)}
RETURN d.DID AS did, s.Name AS study, d.DID_Status AS status,
       d.Planned_Delivery_Date AS planned_delivery_date,
       d.Actual_Delivery_Date AS actual_delivery_date, d.Reporting_Event AS reporting_event
ORDER BY planned_delivery_date DESC, did
LIMIT {_limit(p)}
"""


def _study_delivery_timeline(p: dict[str, Any]) -> str:
    return f"""
MATCH (s:Study)-[:HAS_DELIVERY]->(d:Delivery)
WHERE {_study_where(p)}{_date_filters(p)}{_status_filter(p)}
RETURN d.DID AS did, d.DID_Status AS status,
       d.Planned_Delivery_Date AS planned_delivery_date,
       d.Actual_Delivery_Date AS actual_delivery_date
ORDER BY planned_delivery_date, did
LIMIT {_limit(p)}
"""


def _study_task_composition(p: dict[str, Any]) -> str:
    return f"""
MATCH (s:Study)-[:HAS_DELIVERY]->(d:Delivery)-[:HAS_SDTM|HAS_ADAM|HAS_TLF]->(lot)
WHERE {_study_where(p)}{_status_filter(p)}
RETURN d.DID AS did,
       sum(CASE WHEN lot:TLF THEN 1 ELSE 0 END) AS tlf,
       sum(CASE WHEN lot:ADAM THEN 1 ELSE 0 END) AS adam,
       sum(CASE WHEN lot:SDTM THEN 1 ELSE 0 END) AS sdtm
ORDER BY did
LIMIT {_limit(p)}
"""


def _study_people_and_roles(p: dict[str, Any]) -> str:
    return f"""
MATCH (person:Person)-[works_as:WORKS_AS]->(s:Study)
WHERE {_study_where(p)}
OPTIONAL MATCH (person)-[work:WORKS_ON]->(d:Delivery)<-[:HAS_DELIVERY]-(s)
RETURN person.Name AS person, collect(DISTINCT works_as.Role) AS roles,
       count(DISTINCT d) AS did_count,
       sum(coalesce(work.Task_Num_Total, work.CSR_Task_Num_Total, 0)) AS task_count
ORDER BY person
LIMIT {_limit(p)}
"""


def _study_tlf_ranking(p: dict[str, Any]) -> str:
    return f"""
MATCH (s:Study)-[:HAS_DELIVERY]->(d:Delivery)-[:HAS_TLF]->(:TLF)
OPTIONAL MATCH (s)-[:HAS_DETAIL]->(info:Study_Info)
WHERE true{_date_filters(p)}
RETURN s.Name AS study, count(*) AS tlf_volume,
       info.TA AS ta, info.Plan_Phase AS plan_phase, info.Plan_Status AS plan_status
ORDER BY tlf_volume DESC, study
LIMIT {_limit(p)}
"""


def _study_portfolio_table(p: dict[str, Any]) -> str:
    conditions = []
    for field, prop in (("site", "Site"), ("plan_phase", "Plan_Phase"), ("plan_status", "Plan_Status"), ("ta", "TA")):
        if p.get(field):
            conditions.append(
                f"{'site.Name' if field == 'site' else f'info.{prop}'} = {_quoted(p[field])}"
            )
    return f"""
MATCH (s:Study)-[:HAS_DETAIL]->(info:Study_Info)
OPTIONAL MATCH (person:Person)-[:WORKS_AS]->(s)
OPTIONAL MATCH (person)-[:FROM_SITE]->(site:Site)
WHERE {' AND '.join(conditions) if conditions else 'true'}
RETURN s.Name AS study, s.SDSL AS sdsl, info.TA AS ta,
       info.Plan_Phase AS plan_phase, info.Plan_Status AS plan_status
ORDER BY study
LIMIT {_limit(p)}
"""


def _team_member_workload(p: dict[str, Any]) -> str:
    leader = "p.Manager" if p.get("manager") else "p.TA_Lead_Name"
    value = p.get("manager") or p.get("ta_lead")
    return f"""
MATCH (p:Person)-[work:WORKS_ON]->(d:Delivery)
WHERE {leader} = {_quoted(value)}{_date_filters(p)}{_status_filter(p)}
RETURN p.Name AS person, count(DISTINCT d) AS did_count,
       sum(coalesce(work.Task_Num_Total, work.CSR_Task_Num_Total, 0)) AS task_count,
       sum(coalesce(work.TLF_Num_Total, work.CSR_TLF_Num_Total, 0)) AS tlf,
       sum(coalesce(work.ADaM_Num_Total, work.CSR_ADaM_Num_Total, 0)) AS adam,
       sum(coalesce(work.SDTM_Num_Total, work.CSR_SDTM_Num_Total, 0)) AS sdtm
ORDER BY task_count DESC, person
LIMIT {_limit(p)}
"""


def _team_capacity_timeline(p: dict[str, Any]) -> str:
    leader = "p.Manager" if p.get("manager") else "p.TA_Lead_Name"
    value = p.get("manager") or p.get("ta_lead")
    return f"""
MATCH (p:Person)-[work:WORKS_ON]->(d:Delivery)
WHERE {leader} = {_quoted(value)}{_date_filters(p)}
WITH substring(toString(d.Planned_Delivery_Date), 0, 7) AS month,
     sum(coalesce(work.Task_Num_Total, work.CSR_Task_Num_Total, 0)) AS task_count,
     count(DISTINCT d) AS did_count
WHERE month IS NOT NULL AND month <> ''
RETURN month, task_count, did_count
ORDER BY month
"""


def _lead_contribution_summary(p: dict[str, Any]) -> str:
    field = "p.TA_Lead_Name" if p.get("ta_lead") else ("p.Group_Lead_Name" if p.get("group_lead") else "site.Name")
    value = p.get("ta_lead") or p.get("group_lead") or p.get("site")
    return f"""
MATCH (p:Person)-[work:WORKS_ON]->(d:Delivery)
OPTIONAL MATCH (p)-[:FROM_SITE]->(site:Site)
WHERE {field} = {_quoted(value)}{_date_filters(p)}{_status_filter(p)}
OPTIONAL MATCH (p)-[time:TIME_ON]->(:DIDN_Month)-[:BELONGS_TO]->(d)
RETURN {field} AS lead, count(DISTINCT d) AS did_count,
       sum(coalesce(work.Task_Num_Total, work.CSR_Task_Num_Total, 0)) AS task_count,
       round(sum(coalesce(toFloat(time.Hour), 0)), 1) AS recorded_hours
ORDER BY task_count DESC
"""


def _tlf_search_results(p: dict[str, Any]) -> str:
    return f"""
MATCH (s:Study)-[:HAS_DELIVERY]->(d:Delivery)-[:HAS_TLF]->(t:TLF)
WHERE toLower(coalesce(t.Name, '')) CONTAINS toLower({_quoted(p['tlf_keyword'])})
  {'AND ' + _study_where(p) if p.get('study') else ''}
RETURN t.Name AS tlf_title, d.DID AS did, s.Name AS study, d.DID_Status AS status,
       d.Planned_Delivery_Date AS planned_delivery_date, t.Category AS category,
       t.Type AS type, t.Source AS source
ORDER BY planned_delivery_date DESC, tlf_title
LIMIT {_limit(p)}
"""


def _expert_recommendation(p: dict[str, Any]) -> str:
    keyword = _quoted(p["keyword"])
    return f"""
MATCH (person:Person)-[:WORKS_ON]->(d:Delivery)-[:HAS_SDTM|HAS_ADAM|HAS_TLF]->(lot)
OPTIONAL MATCH (s:Study)-[:HAS_DELIVERY]->(d)
WHERE toLower(coalesce(lot.Name, '')) CONTAINS toLower({keyword})
   OR toLower(coalesce(lot.Category, '')) CONTAINS toLower({keyword})
RETURN person.Name AS person, count(DISTINCT d) AS matching_dids,
       count(DISTINCT s) AS matching_studies, collect(DISTINCT lot.Name)[0..5] AS matching_items
ORDER BY matching_dids DESC, person
LIMIT {_limit(p)}
"""


def _collaboration_network_table(p: dict[str, Any]) -> str:
    leader = "member.Manager" if p.get("manager") else "member.Team_Lead_Name"
    value = p.get("manager") or p.get("team_lead")
    return f"""
MATCH (member:Person)-[:WORKS_ON]->(d:Delivery)<-[:WORKS_ON]-(collaborator:Person)
WHERE {leader} = {_quoted(value)} AND member <> collaborator
RETURN member.Name AS member, collaborator.Name AS collaborator,
       count(DISTINCT d) AS shared_dids
ORDER BY shared_dids DESC, member, collaborator
LIMIT {_limit(p)}
"""


def _delivery_location_detail(p: dict[str, Any]) -> str:
    return f"""
MATCH (s:Study)-[:HAS_DELIVERY]->(d:Delivery)
WHERE {_did_where(p)}
RETURN d.DID AS did, s.Name AS study, d.Reporting_Path AS reporting_path,
       d.Reporting_System AS reporting_system, d.Reporting_Detail AS reporting_detail,
       d.Delivery_Content AS delivery_content
LIMIT 1
"""


REGISTRY: dict[str, FixedTemplate] = {
    "person_monthly_hours": FixedTemplate("person_monthly_hours", "Monthly recorded hours", ("person",), ("start_date", "end_date", "limit"), {"type": "line", "x": "month", "y": "hours"}, "Recorded hands-on TIME_ON hours.", _person_monthly_hours),
    "person_did_effort": FixedTemplate("person_did_effort", "Recorded effort by DID", ("person",), ("start_date", "end_date", "status", "limit"), {"type": "bar", "x": "did", "y": "hours", "horizontal": True}, "Recorded hands-on TIME_ON hours.", _person_did_effort),
    "person_delivery_summary": FixedTemplate("person_delivery_summary", "Delivery summary", ("person",), ("start_date", "end_date", "status", "limit"), None, "Assigned WORKS_ON task counts.", _person_delivery_summary),
    "person_domain_experience": FixedTemplate("person_domain_experience", "Domain experience", ("person",), ("start_date", "end_date", "role", "limit"), {"type": "bar", "x": "domain", "y": "item_count", "horizontal": True}, "Historical delivery-item participation.", _person_domain_experience),
    "person_efficiency_comparison": FixedTemplate("person_efficiency_comparison", "Effort by period", ("person",), ("start_date", "end_date", "year", "limit"), {"type": "bar", "x": "period", "y": ["hours", "hours_per_did"], "grouped": True}, "Recorded hours per participated DID; not a performance ranking.", _person_efficiency_comparison),
    "person_assignment_list": FixedTemplate("person_assignment_list", "Assignment list", ("person",), ("start_date", "end_date", "status", "limit"), {"type": "timeline", "x": "planned_delivery_date", "y": "did"}, "Assigned WORKS_ON tasks.", _person_assignment_list),
    "personal_workload_mix": FixedTemplate("personal_workload_mix", "Workload mix", ("person",), ("start_date", "end_date", "task_type", "role", "limit"), {"type": "bar", "x": "did", "y": ["tlf", "adam", "sdtm"], "stacked": True}, "Assigned WORKS_ON task counts.", _personal_workload_mix),
    "delivery_priority_list": FixedTemplate("delivery_priority_list", "Delivery priorities", (), ("person", "manager", "start_date", "end_date", "status", "limit"), None, "Priority is ordered by planned date.", _delivery_priority_list),
    "delivery_overlap_timeline": FixedTemplate("delivery_overlap_timeline", "Delivery overlap timeline", (), ("person", "manager", "start_date", "end_date", "limit"), {"type": "bar", "x": "planned_delivery_date", "y": "assigned_people"}, "Assigned people per planned delivery.", _delivery_overlap_timeline),
    "did_person_contribution": FixedTemplate("did_person_contribution", "DID person contribution", ("did",), ("start_date", "end_date", "study", "limit"), {"type": "bar", "x": "person", "y": "hours", "horizontal": True}, "Recorded hands-on TIME_ON hours.", _did_person_contribution),
    "did_lot_breakdown": FixedTemplate("did_lot_breakdown", "DID LoT breakdown", ("did",), ("task_type", "source", "role", "limit"), {"type": "bar", "x": "task_type", "y": "item_count"}, "Delivery output-item counts.", _did_lot_breakdown),
    "did_task_composition": FixedTemplate("did_task_composition", "DID task composition", (), ("did", "study", "start_date", "end_date", "person", "limit"), {"type": "bar", "x": "did", "y": ["tlf", "adam", "sdtm"], "stacked": True}, "Delivery output-item counts.", _did_task_composition),
    "did_comparison": FixedTemplate("did_comparison", "DID comparison", ("did_1", "did_2"), ("task_type",), {"type": "bar", "x": "did", "y": ["tlf", "adam", "sdtm"], "grouped": True}, "Delivery output-item counts.", _did_comparison),
    "delivery_search_results": FixedTemplate("delivery_search_results", "Delivery search results", (), ("did", "study", "keyword", "status", "start_date", "end_date", "limit"), None, "Filtered delivery records.", _delivery_search_results),
    "study_delivery_timeline": FixedTemplate("study_delivery_timeline", "Study delivery timeline", ("study",), ("status", "start_date", "end_date", "limit"), {"type": "timeline", "x": "planned_delivery_date", "y": "did"}, "Planned and actual delivery dates.", _study_delivery_timeline),
    "study_task_composition": FixedTemplate("study_task_composition", "Study task composition", ("study",), ("status", "task_type", "limit"), {"type": "bar", "x": "did", "y": ["tlf", "adam", "sdtm"], "stacked": True}, "Delivery output-item counts.", _study_task_composition),
    "study_people_and_roles": FixedTemplate("study_people_and_roles", "Study people and roles", ("study",), ("domain", "role", "limit"), None, "Assigned roles and task counts.", _study_people_and_roles),
    "study_tlf_ranking": FixedTemplate("study_tlf_ranking", "Study TLF ranking", (), ("start_date", "end_date", "quarter", "limit"), {"type": "bar", "x": "study", "y": "tlf_volume", "horizontal": True}, "TLF item counts.", _study_tlf_ranking),
    "study_portfolio_table": FixedTemplate("study_portfolio_table", "Study portfolio", (), ("site", "plan_phase", "plan_status", "ta", "limit"), None, "Study portfolio records.", _study_portfolio_table),
    "team_member_workload": FixedTemplate("team_member_workload", "Team member workload", (), ("manager", "ta_lead", "start_date", "end_date", "status", "task_type", "limit"), {"type": "bar", "x": "person", "y": "task_count", "horizontal": True}, "Assigned task counts; not a performance ranking.", _team_member_workload),
    "team_capacity_timeline": FixedTemplate("team_capacity_timeline", "Team capacity timeline", (), ("manager", "ta_lead", "start_date", "end_date", "limit"), {"type": "bar", "x": "month", "y": "task_count"}, "Assigned task counts by planned month.", _team_capacity_timeline),
    "lead_contribution_summary": FixedTemplate("lead_contribution_summary", "Lead contribution summary", (), ("ta_lead", "group_lead", "site", "start_date", "end_date", "status", "limit"), {"type": "bar", "x": "lead", "y": "task_count"}, "Assigned task counts and recorded hours.", _lead_contribution_summary),
    "tlf_search_results": FixedTemplate("tlf_search_results", "TLF search results", ("tlf_keyword",), ("study", "limit"), None, "Matching TLF records.", _tlf_search_results),
    "expert_recommendation": FixedTemplate("expert_recommendation", "Relevant experience", ("keyword",), ("domain", "ta", "team", "role", "limit"), None, "Recommendations are based on historical participation records.", _expert_recommendation),
    "collaboration_network_table": FixedTemplate("collaboration_network_table", "Collaboration network", (), ("manager", "team_lead", "start_date", "end_date", "limit"), None, "Shared DID assignments.", _collaboration_network_table),
    "delivery_location_detail": FixedTemplate("delivery_location_detail", "Delivery location detail", ("did",), (), None, "Delivery reporting metadata.", _delivery_location_detail),
}

# The constructor typo-proofing above keeps catalog entries declarative; this is asserted at import.
assert len(REGISTRY) == 26


def intents() -> tuple[str, ...]:
    return tuple(REGISTRY)


def _json_object(raw: str) -> dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", raw.strip())
    payload = json.loads(match.group(0) if match else raw)
    if not isinstance(payload, dict):
        raise ValueError("Fixed-result parameter response must be a JSON object.")
    return payload


def classify(question: str, history: list[dict[str, Any]] | None, chat: Chat) -> tuple[str, Usage]:
    choices = "\n".join(f'- "{intent}"' for intent in intents())
    raw, usage = chat(
        f"""Classify this DID application request. Return exactly one JSON object:
{{"intent": one of the listed intents or "neo4j_query", "confidence": "high"|"low"}}.
Choose a fixed intent only for one supported result view. Use neo4j_query for compound,
unclear, low-confidence, or unsupported requests. Do not calculate values.
Allowed fixed intents:
{choices}""",
        f"Recent conversation:\n{json.dumps((history or [])[-6:], ensure_ascii=False)}\n\nRequest:\n{question}",
    )
    payload = _json_object(raw)
    intent = payload.get("intent")
    if payload.get("confidence", "high") != "high" or intent not in REGISTRY:
        return "neo4j_query", usage
    return intent, usage


def extract_parameters(
    question: str, template: FixedTemplate, history: list[dict[str, Any]] | None, chat: Chat
) -> tuple[dict[str, Any], Usage]:
    allowed = (*template.required, *template.optional)
    example = {key: None for key in allowed}
    raw, usage = chat(
        f"""Extract only parameters for fixed result intent "{template.intent}".
Return exactly one JSON object with only these keys: {json.dumps(example)}.
Required keys: {list(template.required)}. Never invent values. Dates must be YYYY-MM-DD.
Use recent context only for explicit references. Do not return Cypher or explanation.""",
        f"Recent conversation:\n{json.dumps((history or [])[-6:], ensure_ascii=False)}\n\nRequest:\n{question}",
    )
    payload = _json_object(raw)
    return {key: payload.get(key) for key in allowed if payload.get(key) not in (None, "")}, usage


def _validate_parameters(template: FixedTemplate, params: dict[str, Any]) -> dict[str, Any]:
    missing = [name for name in template.required if not params.get(name)]
    if missing:
        raise ValueError(f"The fixed result needs: {', '.join(missing)}.")
    if template.intent in {"delivery_priority_list", "delivery_overlap_timeline"} and not (params.get("person") or params.get("manager")):
        raise ValueError("The fixed result needs a person or manager.")
    if template.intent == "did_task_composition" and not (params.get("did") or params.get("study")):
        raise ValueError("The fixed result needs a DID or study.")
    if template.intent == "delivery_search_results" and not any(params.get(k) for k in ("did", "study", "keyword", "status")):
        raise ValueError("The fixed result needs a DID, study, keyword, or status.")
    if template.intent in {"team_member_workload", "team_capacity_timeline"} and not (params.get("manager") or params.get("ta_lead")):
        raise ValueError("The fixed result needs a manager or TA lead.")
    if template.intent == "lead_contribution_summary" and not any(params.get(k) for k in ("ta_lead", "group_lead", "site")):
        raise ValueError("The fixed result needs a TA lead, group lead, or site.")
    if template.intent == "collaboration_network_table" and not (params.get("manager") or params.get("team_lead")):
        raise ValueError("The fixed result needs a manager or team lead.")
    for key in ("did", "did_1", "did_2"):
        if key in params and not DID_PATTERN.fullmatch(str(params[key])):
            raise ValueError(f"Invalid DID: {params[key]!r}.")
    for key in ("start_date", "end_date"):
        if key in params:
            if not DATE_PATTERN.fullmatch(str(params[key])):
                raise ValueError(f"{key} must be YYYY-MM-DD.")
            date.fromisoformat(str(params[key]))
    if params.get("start_date") and params.get("end_date") and params["start_date"] > params["end_date"]:
        raise ValueError("start_date cannot be after end_date.")
    if "status" in params:
        status = str(params["status"]).casefold()
        if status not in VALID_STATUS:
            raise ValueError("status must be planned, ongoing, or completed.")
        params["status"] = VALID_STATUS[status]
    if "limit" in params:
        try:
            params["limit"] = max(1, min(100, int(params["limit"])))
        except (TypeError, ValueError) as exc:
            raise ValueError("limit must be an integer between 1 and 100.") from exc
    return params


def _metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    numeric = ("hours", "task_count", "item_count", "tlf_volume", "did_count", "matching_dids")
    metrics = [{"label": "Rows", "value": len(rows), "unit": ""}]
    for key in numeric:
        values = [row.get(key) for row in rows if isinstance(row.get(key), (int, float))]
        if values:
            metrics.append({"label": key.replace("_", " ").title(), "value": round(sum(values), 1), "unit": "hours" if key == "hours" else ""})
    return metrics[:4]


def _entity_validation_queries(params: dict[str, Any]) -> list[tuple[str, int]]:
    """Return fixed existence/uniqueness checks for entities with graph identifiers."""
    checks: list[tuple[str, int]] = []
    dids = [params[key] for key in ("did", "did_1", "did_2") if params.get(key)]
    if dids:
        values = ", ".join(_quoted(value) for value in dict.fromkeys(dids))
        checks.append(
            (
                "MATCH (d:Delivery) "
                f"WHERE toString(d.DID) IN [{values}] "
                "RETURN count(DISTINCT d) AS matches",
                len(set(dids)),
            )
        )
    if params.get("study"):
        checks.append(
            (
                "MATCH (s:Study) "
                f"WHERE {_study_where(params)} "
                "RETURN count(DISTINCT s) AS matches",
                1,
            )
        )
    return checks


def run_fixed_result(
    intent: str,
    question: str,
    history: list[dict[str, Any]] | None,
    schema: dict[str, Any] | None,
    initial_usage: Usage,
    chat: Chat,
    run_query: Query,
    resolve_person: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Extract validated parameters, then execute only a registered fixed Cypher query."""
    template = REGISTRY[intent]
    params, extraction_usage = extract_parameters(question, template, history, chat)
    if resolve_person:
        for key in ("person", "manager", "ta_lead", "group_lead", "team_lead"):
            if params.get(key):
                params[key] = resolve_person(str(params[key]))
    params = _validate_parameters(template, params)
    for validation_cypher, expected_count in _entity_validation_queries(params):
        validation_rows = run_query(validation_cypher)
        matches = validation_rows[0].get("matches") if validation_rows else 0
        if matches != expected_count:
            raise ValueError("The requested DID or study was not uniquely found.")
    cypher = template.query(params).strip()
    rows = run_query(cypher)
    table = {"columns": list(rows[0]) if rows else [], "rows": rows}
    summary = (
        [f"No matching records were found for {template.title.lower()}."]
        if not rows
        else [f"{len(rows)} matching record(s) returned."]
    )
    visualization = {**template.chart, "data": rows, "title": template.title} if template.chart else None
    return {
        "response_type": "fixed_result",
        "intent": intent,
        "answer": summary[0],
        "title": template.title,
        "subtitle": None,
        "summary": summary,
        "metrics": _metrics(rows),
        "visualizations": [visualization] if visualization else [],
        "table": table,
        "data_note": template.data_note,
        "cypher": cypher,
        "rows": rows,
        "schema": schema,
        "error": None,
        "usage": {
            key: int(initial_usage.get(key, 0)) + int(extraction_usage.get(key, 0))
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        },
        # Kept for saved conversations produced by the original two chart routes.
        "visualization": {
            "chart_type": intent,
            "title": template.title,
            "data": rows,
            "value_field": (template.chart or {}).get("y", "value"),
        } if visualization else None,
    }
