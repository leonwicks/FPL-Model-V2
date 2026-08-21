# Data dictionary conventions

All tables include `source`, `season`, `competition`, `source_url`, and timezone-aware `ingested_at_utc` where applicable. They are non-null lineage fields unless a provider payload itself is unavailable, in which case ingestion fails before writing. Provider columns not listed in the stable/core dictionaries are retained under their normalized source names; their observed dtype and first/last season are tracked in `schemas/*.json`.

Examples are illustrative, not matching keys across providers. `string` IDs are never coerced to floating point. JSON denotes deterministic compact JSON text for nested provider values.

For the catalogue, dynamic-field rules, combined-table naming, and sourcing
function descriptions, see [the agent data reference](../AGENT_DATA_REFERENCE.md)
and [the ingestion reference](../INGESTION_REFERENCE.md).
