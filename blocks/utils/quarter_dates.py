def quarter_to_months(q: str) -> list[int]:
    q = q.upper().strip()
    return {
        "Q1": [1,2,3],
        "Q2": [4,5,6],
        "Q3": [7,8,9],
        "Q4": [10,11,12],
    }.get(q, [6,7,8])  # Default: Sommer
