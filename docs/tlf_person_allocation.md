# TLF-only person allocation

The **Allocate TLF People** Streamlit tab recommends separate Generation and QC
people for each uploaded TLF within one DU Team Lead group. It accepts the same
`C5001001_61.xlsx` format as DU-team recommendation (`TLF` and `Data` sheets),
or paired TLF/Data CSV files. Only the TLF rows are used for allocation.

## Refresh evidence manually

The UI never calls Neo4j. An operator refreshes a local snapshot after graph
updates:

```cmd
py tlf_person_allocation.py refresh-snapshot
```

The snapshot contains completed `Person × DID × TLF` role evidence and each
person's current active DID count. Its reads follow the graph schema:
`(:Person)-[:WORKS_ON]->(:Delivery)-[:HAS_TLF]->(:TLF)`. `Generation` and `QC`
are read from the `HAS_TLF` relationship. Set
`TLF_PERSON_ALLOCATION_SNAPSHOT_PATH` for a persistent deployment location.
The default path supports the same Git-LFS-pointer download fallback as the
existing DU snapshot; override its URL with
`TLF_PERSON_ALLOCATION_SNAPSHOT_URL`.

## Guardrails and scores

Vox receives the entered Team Lead name and **only** the literal
`Team_Lead_Name` values from the snapshot. Its JSON result must exactly equal
one of those candidates; invented or altered teams are rejected.

For each role, a person's best completed role-evidence record is scored out of
100:

| Component | Points |
| --- | ---: |
| Semantic TLF title match | 40 |
| Exact TLF title | 15 |
| Exact Type and Source (2.5 each) | 5 |
| Recent relevant completed DID | 5 |
| Current active-DID workload (lower is better) | 35 |

Semantic comparisons use the shared
`artifacts/did_effort_similarity_cache.joblib`, with one uploaded TLF compared
to one historical TLF per cache entry. To prevent an unbounded comparison
matrix, each person's evidence is first restricted to rows with an exact title,
matching Type/Source, or a meaningful shared title word; at most 25 such rows
per person and role enter semantic matching. A person with no such evidence is
not presented as a semantic candidate.

Every role displays a primary and up to two evidence-qualified backups.
Generation and QC primaries must be different. If no different QC person has
QC role evidence, the only same-person QC fallback is labeled **LEAD REVIEW
REQUIRED**. If that person lacks QC evidence too, no QC primary is invented.

To prevent concentration within a run, every primary already assigned to a
person deducts **12 points** from their later primary score. There is no hard
assignment cap: the dynamic penalty preserves a complete recommendation for
large inputs while making concentrated assignments progressively less likely.
