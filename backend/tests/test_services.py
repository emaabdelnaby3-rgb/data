from app.services import generate_receipt_code, split_donation


def test_split_donation_when_amount_over_needed():
    beneficiary, organization = split_donation(5000, 4000)
    assert beneficiary == 4000
    assert organization == 1000


def test_split_donation_when_amount_under_needed():
    beneficiary, organization = split_donation(2500, 4000)
    assert beneficiary == 2500
    assert organization == 0


def test_generate_receipt_code_prefix():
    receipt = generate_receipt_code()
    assert receipt.startswith("RCP-")
