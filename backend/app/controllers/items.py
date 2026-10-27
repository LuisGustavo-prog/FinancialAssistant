from app.core.guards import is_income_editable


def expense_item(row: dict) -> dict:
    return {
        "id": row["id"],
        "amount": row["amount"],
        "occurred_on": row["occurred_on"],
        "description": row["description"],
        "category": {"id": row["category_id"], "name": row["category_name"]},
        "payment_method": row["payment_method"],
    }


def extra_income_item(row: dict) -> dict:
    return {
        "id": row["id"],
        "amount": row["amount"],
        "occurred_on": row["occurred_on"],
        "description": row["description"],
        "source": row["source"],
        "is_editable": is_income_editable(row["source"]),
    }
