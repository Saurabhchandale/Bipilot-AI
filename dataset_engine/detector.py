from typing import Any

import pandas as pd


class DatasetTypeDetector:
    """Detect the most likely business domain for a dataset."""

    DOMAIN_RULES = {
        "Finance": {
            "keywords": [
                "amount",
                "balance",
                "budget",
                "cash",
                "cost",
                "expense",
                "income",
                "invoice",
                "margin",
                "payment",
                "profit",
                "revenue",
            ],
            "kpis": ["total revenue", "profit margin", "expenses", "cash flow"],
        },
        "Sales": {
            "keywords": [
                "customer",
                "deal",
                "discount",
                "lead",
                "order",
                "product",
                "quantity",
                "sales",
                "seller",
                "territory",
            ],
            "kpis": ["sales revenue", "order count", "average order value", "top products"],
        },
        "HR": {
            "keywords": [
                "attendance",
                "department",
                "employee",
                "hire",
                "job",
                "leave",
                "manager",
                "performance",
                "salary",
                "staff",
            ],
            "kpis": ["headcount", "attrition", "salary cost", "performance score"],
        },
        "Marketing": {
            "keywords": [
                "ad",
                "campaign",
                "channel",
                "click",
                "conversion",
                "impression",
                "lead",
                "medium",
                "spend",
                "traffic",
            ],
            "kpis": ["conversion rate", "cost per lead", "campaign ROI", "traffic"],
        },
        "Inventory": {
            "keywords": [
                "inventory",
                "item",
                "location",
                "product",
                "purchase",
                "reorder",
                "sku",
                "stock",
                "supplier",
                "warehouse",
            ],
            "kpis": ["stock level", "reorder risk", "inventory value", "supplier count"],
        },
        "Insurance": {
            "keywords": [
                "agent",
                "claim",
                "coverage",
                "deductible",
                "insured",
                "policy",
                "premium",
                "risk",
                "settlement",
                "underwriting",
            ],
            "kpis": ["claim amount", "premium revenue", "loss ratio", "policy count"],
        },
    }

    def detect(self, dataframe: pd.DataFrame, analysis: dict[str, Any] | None = None) -> dict[str, Any]:
        if dataframe is None or not isinstance(dataframe, pd.DataFrame):
            raise TypeError("DatasetTypeDetector.detect expects a pandas DataFrame.")

        analysis = analysis or {}
        columns = [str(column).lower() for column in dataframe.columns]
        scores = {}
        matched_columns = {}

        for domain, rule in self.DOMAIN_RULES.items():
            score = 0
            matches = []
            for column in columns:
                column_matches = [keyword for keyword in rule["keywords"] if keyword in column]
                if column_matches:
                    score += len(column_matches) * 2
                    matches.append(column)

            score += self._business_signal_bonus(domain, analysis)
            scores[domain] = score
            matched_columns[domain] = sorted(set(matches))

        detected_type = max(scores, key=scores.get) if scores else "Unknown"
        total_score = sum(scores.values())
        confidence = round((scores[detected_type] / total_score) * 100, 2) if total_score else 0

        if scores.get(detected_type, 0) == 0:
            detected_type = "Unknown"
            confidence = 0

        return {
            "detected_type": detected_type,
            "confidence": confidence,
            "scores": scores,
            "matched_columns": matched_columns,
            "recommended_kpis": self.DOMAIN_RULES.get(detected_type, {}).get("kpis", []),
            "recommended_charts": self._recommended_charts(detected_type),
        }

    def _business_signal_bonus(self, domain: str, analysis: dict[str, Any]) -> int:
        columns = analysis.get("columns", {})
        currency_columns = columns.get("currency", [])
        percentage_columns = columns.get("percentage", [])
        datetime_columns = columns.get("datetime", [])

        bonus = 0
        if domain in {"Finance", "Sales", "Insurance"} and currency_columns:
            bonus += 3
        if domain in {"Marketing", "Finance"} and percentage_columns:
            bonus += 2
        if datetime_columns:
            bonus += 1
        return bonus

    def _recommended_charts(self, detected_type: str) -> list[str]:
        common = ["KPI cards", "trend line chart", "category bar chart"]
        domain_specific = {
            "Finance": ["revenue vs expense chart", "profit margin trend"],
            "Sales": ["sales by product", "sales by region", "monthly orders"],
            "HR": ["headcount by department", "salary distribution", "performance ranking"],
            "Marketing": ["campaign performance", "conversion funnel", "channel comparison"],
            "Inventory": ["stock by warehouse", "low stock table", "inventory value chart"],
            "Insurance": ["claims by policy type", "premium vs claim trend", "risk category chart"],
        }
        return common + domain_specific.get(detected_type, [])

