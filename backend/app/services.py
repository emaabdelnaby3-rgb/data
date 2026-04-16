from uuid import uuid4


def generate_case_code() -> str:
    return f"CASE-{uuid4().hex[:8].upper()}"


def split_donation(amount: float, needed_amount: float):
    beneficiary_share = min(amount, max(needed_amount, 0))
    organization_share = max(amount - beneficiary_share, 0)
    return round(beneficiary_share, 2), round(organization_share, 2)
