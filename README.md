⟐ FLIGHT_MANIFEST → PleaseWork/FLIGHT_MANIFEST.md

# ChaosOrbBot — Distribution Packages
# Core engine: skunkworks/TreeTopologyHeuristics_final.ts
# All distros pull from the same core. Adapters change. Math never changes.

---

## CORE

File: skunkworks/TreeTopologyHeuristics_final.ts
What it does: Shortest path between any two nodes in any connected graph.
Language-agnostic math. No dependencies. No domain logic.

---

## DISTROS

### 1. PyPI Package
File: distros/pypi/
Target: Python developers, data scientists, anyone running pip
Customer needs: Python 3.8+, nothing else
Status: READY TO BUILD

### 2. npm Package
File: distros/npm/
Target: JavaScript/TypeScript developers, web apps
Customer needs: Node.js, nothing else
Status: READY TO BUILD

### 3. PostgreSQL Extension
File: distros/postgres/
Target: Any company running PostgreSQL
Customer needs: PostgreSQL 12+, nothing else
Status: READY TO BUILD

### 4. REST API / Docker Container
File: distros/docker/
Target: Any company, any language, universal fallback
Customer needs: Docker, nothing else
Status: READY TO BUILD

### 5. Snowflake UDF
File: distros/snowflake/
Target: Data teams running Snowflake analytics
Customer needs: Snowflake account, nothing else
Status: NEEDS SNOWFLAKE ENV TO TEST

### 6. Databricks UDF
File: distros/databricks/
Target: Data engineering teams on Databricks
Customer needs: Databricks workspace
Status: NEEDS DATABRICKS ENV TO TEST

### 7. Salesforce Connector
File: distros/salesforce/
Target: Enterprise Salesforce orgs
Customer needs: Salesforce org, managed package install
Status: SCOPED — needs Salesforce specialist

### 8. SAP Connector
File: distros/sap/
Target: Enterprise SAP installations
Customer needs: SAP middleware access
Status: SCOPED — needs SAP specialist

---

## STARTUP DISTRO (bundle)
PyPI + npm + Docker. Three commands, runs anywhere.
Target customer: any startup, any stack, no enterprise contracts needed.

## ENTERPRISE DISTRO (bundle)
PostgreSQL + Snowflake + Databricks + REST API + support contract.
Target customer: mid-to-large org with existing analytics infrastructure.

---

## PROMOTION PATH
Core changes go to skunkworks/TreeTopologyHeuristics_final.ts first.
Validated changes promote to each distro.
Never edit distro files directly — always promote from core.
