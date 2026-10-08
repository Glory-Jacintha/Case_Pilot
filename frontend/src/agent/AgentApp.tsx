import { useEffect, useMemo, useState } from "react";
import "./AgentApp.css";

type Page =
  | "dashboard"
  | "cases"
  | "review"
  | "transactions"
  | "history"
  | "policies"
  | "data";

type CaseItem = {
  case_id: string;
  session_id: string;
  customer_id?: string | null;
  order_id?: string | null;
  refund_id?: string | null;
  domain?: string | null;
  issue_type?: string | null;
  customer_message?: string | null;
  transaction_amount?: number | null;
  authorization?: string | null;
  requires_human?: boolean;
  action_type?: string | null;
  action_reason?: string | null;
  investigation?: string | null;
  evidence?: Record<string, unknown> | string | null;
  attempted_strategies?: string[];
  resolution_attempts?: Array<Record<string, unknown>>;
  required_dependencies?: string[];
  completed_dependencies?: string[];
  workflow?: string[];
  transaction_currency?: string | null;
  human_approval_threshold?: number | null;
  approval_reason?: string | null;
  status: string;
  interrupt?: Record<string, unknown> | null;
};

type PendingResponse = {
  count: number;
  cases: CaseItem[];
};

type DecisionResponse = {
  success: boolean;
  decision: "APPROVED" | "REJECTED";
  case_id: string;
  status: string;
  message: string;
  transaction_amount?: number | null;
  authorization?: string | null;
  requires_human?: boolean;
  action_result?: Record<string, unknown>;
};

const API_BASE_URL = "http://127.0.0.1:8000";

const navItems: { id: Page; label: string; icon: string }[] = [
  { id: "dashboard", label: "Dashboard", icon: "⌂" },
  { id: "cases", label: "Cases", icon: "▤" },
  { id: "review", label: "Human Review", icon: "!" },
  { id: "transactions", label: "Transactions", icon: "₹" },
  { id: "history", label: "History", icon: "↺" },
  { id: "policies", label: "Policies", icon: "◇" },
  { id: "data", label: "Data", icon: "▦" },
];

function formatAmount(amount?: number | null, currency?: string | null) {
  if (amount == null) return "—";
  if (!currency) {
    return amount.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  const code = currency.toUpperCase();
  const locale = code === "INR" ? "en-IN" : "en-US";
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: code,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

function AgentApp() {
  const [page, setPage] = useState<Page>("dashboard");
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [historyCases, setHistoryCases] = useState<CaseItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState("");
  const [notice, setNotice] = useState("");

  const selectedCase = useMemo(
    () =>
      cases.find(
        (item) => item.case_id === selectedCaseId,
      ) ?? cases[0],
    [cases, selectedCaseId],
  );

  const pendingCases = useMemo(
    () =>
      cases.filter(
        (item) =>
          item.status ===
          "WAITING_FOR_HUMAN_APPROVAL",
      ),
    [cases],
  );

  const loadPendingReviews = async () => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/human-review/pending`,
      );

      if (!response.ok) {
        throw new Error(
          `Backend returned ${response.status}`,
        );
      }

      const data =
        (await response.json()) as PendingResponse;

      setCases(data.cases ?? []);
      setApiError("");

      setSelectedCaseId((current) => {
        if (
          current &&
          (data.cases ?? []).some(
            (item) => item.case_id === current,
          )
        ) {
          return current;
        }

        return data.cases?.[0]?.case_id ?? "";
      });
    } catch (error) {
      console.error(
        "Human review API error:",
        error,
      );
      setApiError(
        "Unable to connect to the CasePilot API. Start FastAPI on port 8000.",
      );
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/history`);
      if (!response.ok) throw new Error(`Backend returned ${response.status}`);
      const data = (await response.json()) as { count: number; cases: CaseItem[] };
      setHistoryCases(data.cases ?? []);
    } catch (error) {
      console.error("History API error:", error);
    }
  };

  useEffect(() => {
    if (page === "dashboard" || page === "cases") {
      void loadPendingReviews();
      return;
    }
    if (page === "review") {
      void loadPendingReviews();
      const interval = window.setInterval(() => {
        void loadPendingReviews();
      }, 10000);
      return () => window.clearInterval(interval);
    }
    if (page === "history" || page === "transactions") {
      void loadHistory();
    }
  }, [page]);

  const handleDecision = async (
    decision: "approve" | "reject",
  ) => {
    if (!selectedCase) {
      return;
    }

    const action =
      decision === "approve"
        ? "approve"
        : "reject";

    try {
      setNotice(
        decision === "approve"
          ? "Sending approval to LangGraph..."
          : "Sending rejection to LangGraph...",
      );

      const response = await fetch(
        `${API_BASE_URL}/api/human-review/${encodeURIComponent(
          selectedCase.case_id,
        )}/${action}`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            reason:
              decision === "approve"
                ? "Approved by support agent."
                : "Rejected by support agent.",
          }),
        },
      );

      const data =
        (await response.json()) as DecisionResponse;

      if (!response.ok) {
        throw new Error(
          data.message ||
          `Request failed with ${response.status}`,
        );
      }

      setNotice(
        decision === "approve"
          ? `Approval recorded for ${selectedCase.case_id}. LangGraph resumed and returned: ${data.status}.`
          : `Rejection recorded for ${selectedCase.case_id}. LangGraph resumed and returned: ${data.status}.`,
      );

      await loadPendingReviews();
      await loadHistory();
    } catch (error) {
      console.error(
        "Human decision error:",
        error,
      );

      setNotice(
        `The decision could not be completed: ${error instanceof Error
          ? error.message
          : "Unknown error"
        }`,
      );
    }
  };

  return (
    <div className="agent-shell">
      <aside className="agent-sidebar">
        <div className="agent-brand">
          <div className="agent-brand-mark">
            CP
          </div>

          <div>
            <div className="agent-brand-name">
              CasePilot
            </div>
            <div className="agent-brand-subtitle">
              Agent Console
            </div>
          </div>
        </div>

        <div className="agent-workspace">
          <span className="workspace-dot" />
          Autonomous Support
        </div>

        <nav className="agent-nav">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`agent-nav-item ${page === item.id
                ? "active"
                : ""
                }`}
              onClick={() => {
                setPage(item.id);
                setNotice("");
              }}
            >
              <span className="agent-nav-icon">
                {item.icon}
              </span>

              <span>{item.label}</span>

              {item.id === "review" &&
                pendingCases.length > 0 && (
                  <span className="nav-count">
                    {pendingCases.length}
                  </span>
                )}
            </button>
          ))}
        </nav>

        <div className="agent-sidebar-bottom">
          <div className="system-card">
            <span className="system-online" />

            <div>
              <strong>
                {apiError
                  ? "API offline"
                  : "System online"}
              </strong>

              <span>
                {apiError
                  ? "FastAPI unavailable"
                  : "LangGraph connected"}
              </span>
            </div>
          </div>

          <div className="agent-user">
            <div className="agent-avatar">
              A
            </div>

            <div>
              <strong>
                Support Agent
              </strong>
              <span>
                Human reviewer
              </span>
            </div>
          </div>
        </div>
      </aside>

      <main className="agent-main">
        <header className="agent-topbar">
          <div>
            <div className="topbar-eyebrow">
              CASEPILOT / AGENT
            </div>

            <h1>
              {
                navItems.find(
                  (item) =>
                    item.id === page,
                )?.label
              }
            </h1>
          </div>

          <div className="topbar-right">
            <div className="live-indicator">
              <span />
              Live
            </div>

            <button
              className="customer-view-button"
              onClick={() => {
                window.location.href =
                  "/";
              }}
            >
              Customer View ↗
            </button>
          </div>
        </header>

        <div className="agent-content">
          {apiError && (
            <div className="agent-notice">
              <span>!</span>
              {apiError}
              <button
                onClick={() =>
                  void loadPendingReviews()
                }
              >
                Retry
              </button>
            </div>
          )}

          {notice && (
            <div className="agent-notice">
              <span>✓</span>
              {notice}

              <button
                onClick={() =>
                  setNotice("")
                }
              >
                ×
              </button>
            </div>
          )}

          {page === "dashboard" && (
            <Dashboard
              cases={cases}
              pendingCases={pendingCases}
              loading={loading}
              onReview={() => {
                setPage("review");
                setSelectedCaseId(
                  pendingCases[0]
                    ?.case_id ?? "",
                );
              }}
              onOpenCase={(id) => {
                setSelectedCaseId(id);
                setPage("cases");
              }}
            />
          )}

          {page === "cases" && (
            <CasesPage
              cases={cases}
              selectedCase={selectedCase}
              selectedCaseId={
                selectedCaseId
              }
              loading={loading}
              onSelect={setSelectedCaseId}
            />
          )}

          {page === "review" && (
            <HumanReview
              cases={pendingCases}
              selectedCase={
                selectedCase
              }
              onSelect={
                setSelectedCaseId
              }
              onApprove={() =>
                void handleDecision(
                  "approve",
                )
              }
              onReject={() =>
                void handleDecision(
                  "reject",
                )
              }
            />
          )}

          {page === "transactions" && (
            <TransactionsPage
              cases={historyCases}
            />
          )}

          {page === "history" && (
            <HistoryPage cases={historyCases} />
          )}

          {page === "policies" && (
            <PoliciesPage />
          )}

          {page === "data" && (
            <DataPage />
          )}
        </div>
      </main>
    </div>
  );
}

function Dashboard({
  cases,
  pendingCases,
  loading,
  onReview,
  onOpenCase,
}: {
  cases: CaseItem[];
  pendingCases: CaseItem[];
  loading: boolean;
  onReview: () => void;
  onOpenCase: (id: string) => void;
}) {
  const completed = cases.filter(
    (item) =>
      item.status === "COMPLETED",
  ).length;

  const processing = cases.filter(
    (item) =>
      item.status ===
      "AI_PROCESSING" ||
      item.status ===
      "PROCESSING",
  ).length;

  return (
    <>
      <section className="welcome-row">
        <div>
          <p className="section-kicker">
            OVERVIEW
          </p>

          <h2>
            Support operations at a glance
          </h2>

          <p>
            Monitor autonomous case
            resolution and intervene only
            when authorization is required.
          </p>
        </div>

        {pendingCases.length > 0 && (
          <button
            className="primary-button"
            onClick={onReview}
          >
            Review{" "}
            {pendingCases.length} pending
            case
            {pendingCases.length > 1
              ? "s"
              : ""}{" "}
            →
          </button>
        )}
      </section>

      <section className="metrics-grid">
        <MetricCard
          label="Active Cases"
          value={
            loading
              ? "…"
              : String(cases.length)
          }
          detail="Cases currently known to the API"
        />

        <MetricCard
          label="Human Approval"
          value={String(
            pendingCases.length,
          )}
          detail="Requires authorization"
          emphasis
        />

        <MetricCard
          label="AI Processing"
          value={String(processing)}
          detail="Currently resolving"
        />

        <MetricCard
          label="Completed"
          value={String(completed)}
          detail="Validated outcomes"
        />
      </section>

      <section className="dashboard-grid">
        <div className="panel">
          <PanelHeader
            title="Current Cases"
            subtitle="Cases returned by the CasePilot API"
          />

          {cases.length === 0 ? (
            <EmptyState
              text={
                loading
                  ? "Loading cases..."
                  : "No active cases are currently waiting or registered."
              }
            />
          ) : (
            <div className="case-table">
              <div className="case-table-head">
                <span>Case</span>
                <span>Order</span>
                <span>Domain</span>
                <span>Amount</span>
                <span>Status</span>
              </div>

              {cases.map((item) => (
                <button
                  className="case-row"
                  key={item.case_id}
                  onClick={() =>
                    onOpenCase(
                      item.case_id,
                    )
                  }
                >
                  <strong>
                    {item.case_id}
                  </strong>
                  <span>
                    {item.order_id ?? "—"}
                  </span>
                  <span>
                    {item.domain ?? "—"}
                  </span>
                  <span>
                    {formatAmount(
                      item.transaction_amount,
                      item.transaction_currency,
                    )}
                  </span>
                  <StatusBadge
                    status={item.status}
                  />
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="panel">
          <PanelHeader
            title="Human Review"
            subtitle="Live LangGraph approval queue"
          />

          {pendingCases.length ===
            0 ? (
            <EmptyState
              text="No cases are waiting for human approval."
            />
          ) : (
            pendingCases.map((item) => (
              <button
                className="review-preview"
                key={item.case_id}
                onClick={onReview}
              >
                <div className="review-preview-top">
                  <span className="warning-dot" />
                  <strong>
                    {item.case_id}
                  </strong>
                  <span>
                    {formatAmount(
                      item.transaction_amount,
                      item.transaction_currency,
                    )}
                  </span>
                </div>

                <p>
                  {item.customer_message ??
                    "Pending transaction approval."}
                </p>

                <small>
                  {(
                    item.workflow ??
                    []
                  ).join(" → ") ||
                    item.domain ||
                    "Case workflow"}
                </small>
              </button>
            ))
          )}
        </div>
      </section>
    </>
  );
}

function CasesPage({
  cases,
  selectedCase,
  selectedCaseId,
  loading,
  onSelect,
}: {
  cases: CaseItem[];
  selectedCase?: CaseItem;
  selectedCaseId: string;
  loading: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="page-grid">
      <div className="panel">
        <PanelHeader
          title="Cases"
          subtitle="Live cases returned by CasePilot"
        />

        {cases.length === 0 ? (
          <EmptyState
            text={
              loading
                ? "Loading cases..."
                : "No cases are currently registered."
            }
          />
        ) : (
          <div className="case-table">
            <div className="case-table-head">
              <span>Case</span>
              <span>Order</span>
              <span>Domain</span>
              <span>Amount</span>
              <span>Status</span>
            </div>

            {cases.map((item) => (
              <button
                className={`case-row ${item.case_id ===
                  selectedCaseId
                  ? "selected"
                  : ""
                  }`}
                key={item.case_id}
                onClick={() =>
                  onSelect(
                    item.case_id,
                  )
                }
              >
                <strong>
                  {item.case_id}
                </strong>
                <span>
                  {item.order_id ?? "—"}
                </span>
                <span>
                  {item.domain ?? "—"}
                </span>
                <span>
                  {formatAmount(
                    item.transaction_amount,
                    item.transaction_currency,
                  )}
                </span>
                <StatusBadge
                  status={item.status}
                />
              </button>
            ))}
          </div>
        )}
      </div>

      {selectedCase ? (
        <CaseDetails
          item={selectedCase}
        />
      ) : (
        <div className="panel">
          <EmptyState text="Select a case to inspect its state." />
        </div>
      )}
    </div>
  );
}

function CaseDetails({
  item,
}: {
  item: CaseItem;
}) {
  return (
    <div className="panel case-details">
      <div className="case-detail-header">
        <div>
          <span className="detail-label">
            CASE
          </span>
          <h2>{item.case_id}</h2>
        </div>

        <StatusBadge
          status={item.status}
        />
      </div>

      <div className="detail-grid">
        <Detail
          label="Customer"
          value={
            item.customer_id ?? "—"
          }
        />

        <Detail
          label="Order"
          value={item.order_id ?? "—"}
        />

        <Detail
          label="Domain"
          value={item.domain ?? "—"}
        />

        <Detail
          label="Amount"
          value={formatAmount(
            item.transaction_amount,
            item.transaction_currency,
          )}
        />
      </div>

      <div className="detail-section">
        <span className="detail-label">
          CUSTOMER REQUEST
        </span>

        <p className="request-text">
          “
          {item.customer_message ??
            "No request recorded."}
          ”
        </p>
      </div>

      <Timeline
        workflow={
          item.workflow ??
          (item.domain
            ? [item.domain]
            : [])
        }
      />

      <div className="detail-section">
        <span className="detail-label">
          VERIFIED EVIDENCE
        </span>

        <div className="evidence-list">
          {renderEvidence(item).map(
            (evidence) => (
              <div
                className="evidence-item"
                key={evidence}
              >
                <span>✓</span>
                {evidence}
              </div>
            ),
          )}
        </div>
      </div>
    </div>
  );
}

function renderEvidence(
  item: CaseItem,
): string[] {
  if (
    item.evidence &&
    typeof item.evidence ===
    "object"
  ) {
    return Object.entries(
      item.evidence,
    ).map(
      ([key, value]) =>
        `${key}: ${typeof value === "string"
          ? value
          : JSON.stringify(value)
        }`,
    );
  }

  if (
    typeof item.evidence ===
    "string"
  ) {
    return [item.evidence];
  }

  if (item.investigation) {
    return [item.investigation];
  }

  return [
    "Evidence is available in the LangGraph case state.",
  ];
}

function HumanReview({
  cases,
  selectedCase,
  onSelect,
  onApprove,
  onReject,
}: {
  cases: CaseItem[];
  selectedCase?: CaseItem;
  onSelect: (id: string) => void;
  onApprove: () => void;
  onReject: () => void;
}) {
  return (
    <div className="review-layout">
      <div className="review-list panel">
        <PanelHeader
          title="Approval Queue"
          subtitle={`${cases.length} case${cases.length === 1
            ? ""
            : "s"
            } waiting`}
        />

        {cases.length === 0 ? (
          <EmptyState
            text="No approval cases are currently pending."
          />
        ) : (
          cases.map((item) => (
            <button
              key={item.case_id}
              className={`queue-item ${selectedCase?.case_id ===
                item.case_id
                ? "selected"
                : ""
                }`}
              onClick={() =>
                onSelect(
                  item.case_id,
                )
              }
            >
              <div>
                <strong>
                  {item.case_id}
                </strong>
                <span>
                  {item.order_id ?? "No order"}
                </span>
              </div>

              <div>
                <strong>
                  {formatAmount(
                    item.transaction_amount,
                    item.transaction_currency,
                  )}
                </strong>
                <small>
                  {item.domain ?? "—"}
                </small>
              </div>
            </button>
          ))
        )}
      </div>

      <div className="review-main">
        {!selectedCase ? (
          <div className="panel completed-review">
            <div className="completed-icon">
              —
            </div>

            <h2>
              No pending approval
            </h2>

            <p>
              The queue is currently
              empty.
            </p>
          </div>
        ) : (
          <>
            <div className="approval-banner">
              <div className="approval-icon">
                !
              </div>

              <div>
                <strong>
                  Human approval required
                </strong>

                <span>
                  LangGraph is paused and
                  waiting for an authorization
                  decision.
                </span>
              </div>
            </div>

            <div className="panel approval-panel">
              <div className="approval-header">
                <div>
                  <span className="detail-label">
                    CASE{" "}
                    {selectedCase.case_id}
                  </span>

                  <h2>
                    {selectedCase.action_type ===
                      "CREATE_REFUND"
                      ? "Refund authorization"
                      : "Transaction authorization"}
                  </h2>
                </div>

                <StatusBadge
                  status={
                    selectedCase.status
                  }
                />
              </div>

              <div className="approval-amount">
                <span>
                  Transaction amount
                </span>

                <strong>
                  {formatAmount(
                    selectedCase.transaction_amount,
                    selectedCase.transaction_currency,
                  )}
                </strong>

                <small>
                  Authorization:{" "}
                  <b>
                    {selectedCase.authorization ??
                      "HUMAN_REQUIRED"}
                  </b>
                </small>
              </div>

              <div className="detail-grid">
                <Detail
                  label="Customer"
                  value={
                    selectedCase.customer_id ??
                    "—"
                  }
                />

                <Detail
                  label="Order"
                  value={
                    selectedCase.order_id ??
                    "—"
                  }
                />

                <Detail
                  label="Current Domain"
                  value={
                    selectedCase.domain ??
                    "—"
                  }
                />

                <Detail
                  label="Action"
                  value={
                    selectedCase.action_type ??
                    "—"
                  }
                />
              </div>

              <div className="detail-section">
                <span className="detail-label">
                  ORIGINAL REQUEST
                </span>

                <p className="request-text">
                  “
                  {selectedCase.customer_message ??
                    "No customer request recorded."}
                  ”
                </p>
              </div>

              <Timeline
                workflow={
                  selectedCase.workflow ??
                  []
                }
              />

              <div className="detail-section">
                <span className="detail-label">
                  AI INVESTIGATION
                </span>

                <div className="evidence-list">
                  {renderEvidence(
                    selectedCase,
                  ).map(
                    (evidence) => (
                      <div
                        className="evidence-item"
                        key={evidence}
                      >
                        <span>✓</span>
                        {evidence}
                      </div>
                    ),
                  )}
                </div>
              </div>

              {selectedCase.attempted_strategies &&
                selectedCase
                  .attempted_strategies
                  .length > 0 && (
                  <div className="detail-section">
                    <span className="detail-label">
                      STRATEGIES ATTEMPTED
                    </span>

                    <div className="evidence-list">
                      {selectedCase.attempted_strategies.map(
                        (strategy) => (
                          <div
                            className="evidence-item"
                            key={strategy}
                          >
                            <span>✓</span>
                            {strategy}
                          </div>
                        ),
                      )}
                    </div>
                  </div>
                )}

              <div className="recommendation">
                <div className="recommendation-title">
                  <span>✦</span>
                  AI Recommendation
                </div>

                <p>
                  Review the verified case
                  evidence above and decide
                  whether the requested
                  transaction should be
                  authorized.
                </p>
              </div>

              <div className="approval-actions">
                <button
                  className="reject-button"
                  onClick={onReject}
                >
                  Reject
                </button>

                <button
                  className="approve-button"
                  onClick={onApprove}
                >
                  Approve{" "}
                  {selectedCase.action_type ===
                    "CREATE_REFUND"
                    ? "Refund"
                    : "Action"}
                </button>
              </div>

              <p className="approval-footnote">
                Approve/Reject calls the FastAPI
                human-review endpoint, which
                resumes the paused LangGraph thread
                using Command(resume=...).
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function HistoryPage({
  cases,
}: {
  cases: CaseItem[];
}) {
  return (
    <div className="panel">
      <PanelHeader
        title="Case History"
        subtitle="Completed, rejected, escalated, and previously reviewed CasePilot cases"
      />

      {cases.length === 0 ? (
        <EmptyState text="No historical cases are available yet." />
      ) : (
        <div className="history-list">
          {cases.map((item) => (
            <div className="history-row" key={item.case_id}>
              <div className="history-main">
                <div>
                  <strong>{item.case_id}</strong>
                  <span>{item.order_id || "No order"} · {item.domain || "—"}</span>
                </div>
                <StatusBadge status={item.status} />
              </div>

              <div className="history-meta">
                <span>{formatAmount(item.transaction_amount, item.transaction_currency)}</span>
                <span>{item.authorization || "—"}</span>
              </div>

              <p>{item.customer_message || "No customer message recorded."}</p>

              {item.approval_reason && (
                <small>Human decision: {item.approval_reason}</small>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


function TransactionsPage({
  cases,
}: {
  cases: CaseItem[];
}) {
  return (
    <div className="panel">
      <PanelHeader
        title="Transactions"
        subtitle="Financial actions associated with live cases"
      />

      {cases.length === 0 ? (
        <EmptyState text="No live transaction cases are available." />
      ) : (
        <div className="transaction-list">
          {cases.map((item) => (
            <div
              className="transaction-row"
              key={item.case_id}
            >
              <div className="transaction-id">
                <span className="transaction-icon">
                  ₹
                </span>

                <div>
                  <strong>
                    {item.refund_id ??
                      `CASE-${item.case_id}`}
                  </strong>

                  <span>
                    {item.order_id ??
                      item.case_id}
                  </span>
                </div>
              </div>

              <strong>
                {formatAmount(
                  item.transaction_amount,
                  item.transaction_currency,
                )}
              </strong>

              <StatusBadge
                status={item.status}
              />

              <span className="transaction-auth">
                {item.authorization ===
                  "HUMAN_REQUIRED"
                  ? "Human approval"
                  : "AI eligible / non-financial"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PoliciesPage() {
  return (
    <div className="policy-grid">
      <div className="panel policy-hero">
        <span className="detail-label">
          CASEPILOT POLICY
        </span>

        <h2>
          Autonomous resolution controls
        </h2>

        <p>
          These are the current CasePilot
          business controls represented in the
          Agent Console. The authoritative policy
          remains the policy configuration used by
          the backend.
        </p>
      </div>

      <div className="policy-card">
        <span>
          Autonomous transaction limit
        </span>

        <strong>Currency-specific</strong>

        <small>
          Thresholds are configured per transaction currency in the CasePilot policy.
        </small>
      </div>

      <div className="policy-card">
        <span>
          Human approval rule
        </span>

        <strong>Per currency</strong>

        <small>
          At or above the configured currency threshold requires LangGraph human authorization.
        </small>
      </div>

      <div className="policy-card">
        <span>Maximum strategies</span>

        <strong>3</strong>

        <small>
          Each attempt must use a distinct,
          issue-appropriate approach.
        </small>
      </div>

      <div className="policy-card">
        <span>Success rule</span>

        <strong>
          Validated outcome
        </strong>

        <small>
          A strategy is successful only after the
          intended business outcome is validated
          with system evidence.
        </small>
      </div>
    </div>
  );
}

function DataPage() {
  const datasets = [
    ["customers", "Customer profiles"],
    ["orders", "Order state and totals"],
    ["payments", "Payment transactions"],
    ["deliveries", "Delivery and tracking"],
    ["returns", "Return records"],
    ["products", "Product information"],
    ["refunds", "Refund lifecycle"],
    ["support_cases", "Case history"],
  ];

  return (
    <div className="panel">
      <PanelHeader
        title="Operational Data"
        subtitle="CasePilot data sources used by the resolution engine"
      />

      <div className="data-grid">
        {datasets.map(
          ([name, description]) => (
            <div
              className="data-card"
              key={name}
            >
              <div className="data-icon">
                ▦
              </div>

              <div>
                <strong>{name}</strong>
                <span>
                  {description}
                </span>
              </div>

              <small>
                RDS PostgreSQL
              </small>
            </div>
          ),
        )}
      </div>

      <div className="data-note">
        <span>i</span>

        The Agent Console displays state
        returned by the CasePilot backend. It
        does not create approval cases itself.
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  detail,
  emphasis = false,
}: {
  label: string;
  value: string;
  detail: string;
  emphasis?: boolean;
}) {
  return (
    <div
      className={`metric-card ${emphasis ? "emphasis" : ""
        }`}
    >
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function PanelHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <div className="panel-header">
      <div>
        <h3>{title}</h3>
        <span>{subtitle}</span>
      </div>
    </div>
  );
}

function Detail({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="detail-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Timeline({
  workflow,
}: {
  workflow: string[];
}) {
  return (
    <div className="timeline">
      <span className="detail-label">
        WORKFLOW
      </span>

      {workflow.length === 0 ? (
        <div className="empty-state">
          Workflow history is not available
          yet.
        </div>
      ) : (
        <div className="timeline-track">
          {workflow.map(
            (step, index) => (
              <div
                className="timeline-step"
                key={`${step}-${index}`}
              >
                <div className="timeline-node">
                  {index <
                    workflow.length - 1
                    ? "✓"
                    : "•"}
                </div>

                <span>{step}</span>

                {index <
                  workflow.length - 1 && (
                    <div className="timeline-line" />
                  )}
              </div>
            ),
          )}
        </div>
      )}
    </div>
  );
}

function StatusBadge({
  status,
}: {
  status: string;
}) {
  const className =
    status.toLowerCase();

  return (
    <span
      className={`status-badge ${className}`}
    >
      <span />
      {statusLabel(status)}
    </span>
  );
}

function EmptyState({
  text,
}: {
  text: string;
}) {
  return (
    <div className="empty-state">
      {text}
    </div>
  );
}

export default AgentApp;
