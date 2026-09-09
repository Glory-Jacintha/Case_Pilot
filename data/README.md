# CasePilot Final Dataset v2

This package is a portfolio/learning dataset for CasePilot.

## Source data
- Historical customer-support dataset: filtered and transformed into support_cases.csv.
- 100K order dataset: adapted into orders.csv and used as the basis for synthetic operational tables.

## Files
customers.csv
orders.csv
payments.csv
deliveries.csv
returns.csv
products.csv
refunds.csv
support_cases.csv
resolution_strategies.csv
case_history_examples.csv
amazon_policy.json
casepilot_policy.json
data_dictionary.csv

## Design
The support dataset answers "What did the customer report?"
The operational tables answer "What actually happened in the business systems?"

## Important distinction
amazon_policy.json contains public Amazon policy guidance and should not be represented as Amazon's internal policy engine.
casepilot_policy.json contains project-specific rules:
- amount >= INR 2000 -> human approval
- amount < INR 2000 -> AI may act when policy checks pass
- maximum 3 distinct issue-appropriate strategies
- stop on first validated success
- escalate after 3 distinct failures
