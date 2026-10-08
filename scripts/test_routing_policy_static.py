from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_application_hardcoded_approval_threshold():
    paths = [
        ROOT / "app/graph/actions.py",
        ROOT / "app/graph/nodes.py",
        ROOT / "app/graph/routing.py",
        ROOT / "app/graph/validation.py",
        ROOT / "app/graph/customer_response.py",
        ROOT / "app/tools/action_tools.py",
        ROOT / "app/api/main.py",
    ]
    forbidden = (
        "HUMAN_APPROVAL_THRESHOLD",
        "autonomous_transaction_limit_inr",
        "amount >= 2000.0",
        "amount >= 2000",
        "₹2,000",
    )
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    for value in forbidden:
        assert value not in text


def test_currency_thresholds_are_policy_data():
    policy = (ROOT / "data/casepilot_policy.json").read_text(encoding="utf-8")
    assert '"human_approval_thresholds"' in policy
    assert '"INR": 2000' in policy
    assert '"USD": 140' in policy
    assert '"CAD": 190' in policy
