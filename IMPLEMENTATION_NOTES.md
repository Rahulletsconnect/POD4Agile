# REQ-1015: implementation notes

**Requirement**

Build a customer notification and audit trail feature for account closure. When a customer or branch officer closes an account, the system must notify all associated signers by email and SMS within 5 minutes. Each notification must include the account number (masked to the last 4 digits), closure date, and a contact number for disputes. If a notification fails, the system must retry up to 3 times and then raise an alert for the operations team. The system must retain proof of every notification (recipient, channel, timestamp, delivery status) for 7 years and make it searchable by account number and date range for auditors. Only users with the Auditor or Operations role can view notification history. Closed accounts cannot be reopened without a new approval workflow.

**Planned tasks**

- [ ] Analyze requirement and confirm dependencies and risks
- [ ] Implement: Build a customer notification and audit trail feature for account closure.
- [ ] Implement: When a customer or branch officer closes an account, the system must notify all associated signers by email and SMS within 5 minutes.
- [ ] Implement: Each notification must include the account number (masked to the last 4 digits), closure date, and a contact number for disputes.
- [ ] Implement: If a notification fails, the system must retry up to 3 times and then raise an alert for the operations team.
- [ ] Implement: The system must retain proof of every notification (recipient, channel, timestamp, delivery status) for 7 years and make it searchable by account number and date range for auditors.
- [ ] Implement: Only users with the Auditor or Operations role can view notification history.
- [ ] Implement: Closed accounts cannot be reopened without a new approval workflow.
- [ ] Write automated and manual tests covering each scenario
- [ ] Validate traceability, compliance and release readiness

_Automated coding was not run for this branch — see the PR description for why. This file is a placeholder for a developer to implement against._
