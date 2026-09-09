import { useState } from "react";
import "./App.css";

type Page =
  | "dashboard"
  | "cases"
  | "investigation"
  | "transactions"
  | "human"
  | "policies"
  | "data";

type CaseStatus = "Resolved" | "Human Review" | "Processing";

interface Case {
  id: string;
  issue: string;
  orderId: string;
  customer: string;
  amount: number;
  status: CaseStatus;
  strategy: string;
}

const cases: Case[] = [
  {
    id: "CP-0001",
    issue: "Refund",
    orderId: "ORD0000001",
    customer: "Arun Kumar",
    amount: 1999,
    status: "Processing",
    strategy: "Direct Refund",
  },
  {
    id: "CP-0002",
    issue: "Delivery",
    orderId: "ORD0000042",
    customer: "Priya Sharma",
    amount: 3499,
    status: "Human Review",
    strategy: "Human Approval",
  },
  {
    id: "CP-0003",
    issue: "Payment",
    orderId: "ORD0000108",
    customer: "Rahul Das",
    amount: 1299,
    status: "Resolved",
    strategy: "Payment Reconciliation",
  },
  {
    id: "CP-0004",
    issue: "Return",
    orderId: "ORD0000234",
    customer: "Meena Raj",
    amount: 1799,
    status: "Resolved",
    strategy: "Standard Return",
  },
  {
    id: "CP-0005",
    issue: "Refund",
    orderId: "ORD0000512",
    customer: "Vijay Kumar",
    amount: 4999,
    status: "Human Review",
    strategy: "Human Approval",
  },
];

const navItems: { id: Page; label: string; icon: string }[] = [
  { id: "dashboard", label: "Dashboard", icon: "⌂" },
  { id: "cases", label: "Cases", icon: "▣" },
  { id: "investigation", label: "Investigation", icon: "⌕" },
  { id: "transactions", label: "Transactions", icon: "↗" },
  { id: "human", label: "Human Queue", icon: "♙" },
  { id: "policies", label: "Policies", icon: "▤" },
  { id: "data", label: "Data", icon: "◫" },
];

function formatAmount(amount: number) {
  return `₹${amount.toLocaleString("en-IN")}`;
}

function StatusBadge({ status }: { status: CaseStatus }) {
  return (
    <span className={`status-badge ${status.toLowerCase().replace(" ", "-")}`}>
      <span className="status-dot" />
      {status}
    </span>
  );
}

function App() {
  const [activePage, setActivePage] = useState<Page>("dashboard");
  const [selectedCase, setSelectedCase] = useState<Case | null>(null);

  const openCase = (item: Case) => {
    setSelectedCase(item);
    setActivePage("investigation");
  };

  return (
    <div className="app-shell">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">C</div>
          <div>
            <h1>CasePilot</h1>
            <span>Resolution Agent</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section-title">WORKSPACE</div>

          {navItems.slice(0, 5).map((item) => (
            <button
              key={item.id}
              className={`nav-item ${activePage === item.id ? "active" : ""
                }`}
              onClick={() => {
                setActivePage(item.id);
                setSelectedCase(null);
              }}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>

              {item.id === "human" && (
                <span className="nav-count">6</span>
              )}
            </button>
          ))}

          <div className="nav-section-title second">SYSTEM</div>

          {navItems.slice(5).map((item) => (
            <button
              key={item.id}
              className={`nav-item ${activePage === item.id ? "active" : ""
                }`}
              onClick={() => {
                setActivePage(item.id);
                setSelectedCase(null);
              }}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="system-status">
            <span className="online-dot" />
            <div>
              <strong>System Online</strong>
              <span>All services operational</span>
            </div>
          </div>
        </div>
      </aside>

      {/* MAIN */}
      <main className="main-content">
        {/* TOP BAR */}
        <header className="topbar">
          <div>
            <div className="breadcrumb">CASEPILOT / WORKSPACE</div>
            <h2>
              {selectedCase
                ? `${selectedCase.id} · Investigation`
                : navItems.find((item) => item.id === activePage)?.label}
            </h2>
          </div>

          <div className="topbar-actions">
            <button className="icon-button">⌕</button>
            <button className="icon-button notification">
              ♢
              <span />
            </button>

            <div className="profile">
              <div className="avatar">G</div>
              <div>
                <strong>Glory</strong>
                <small>Administrator</small>
              </div>
            </div>
          </div>
        </header>

        {/* PAGE */}
        <div className="page-content">
          {activePage === "dashboard" && (
            <Dashboard
              onOpenCase={openCase}
              onNavigate={setActivePage}
            />
          )}

          {activePage === "cases" && (
            <CasesPage onOpenCase={openCase} />
          )}

          {activePage === "investigation" && (
            <InvestigationPage selectedCase={selectedCase} />
          )}

          {activePage === "transactions" && <TransactionsPage />}

          {activePage === "human" && (
            <HumanQueuePage onOpenCase={openCase} />
          )}

          {activePage === "policies" && <PoliciesPage />}

          {activePage === "data" && <DataPage />}
        </div>
      </main>
    </div>
  );
}

/* -------------------------------------------------------
   DASHBOARD
------------------------------------------------------- */

function Dashboard({
  onOpenCase,
  onNavigate,
}: {
  onOpenCase: (item: Case) => void;
  onNavigate: (page: Page) => void;
}) {
  return (
    <>
      <div className="page-heading">
        <div>
          <h3>Good morning, Glory</h3>
          <p>
            Here's what's happening with your customer resolutions.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={() => onNavigate("cases")}
        >
          + New Investigation
        </button>
      </div>

      <div className="stats-grid">
        <StatCard
          title="Total Cases"
          value="128"
          change="+12.4%"
          icon="▣"
        />
        <StatCard
          title="AI Resolved"
          value="91"
          change="71.1%"
          icon="✦"
        />
        <StatCard
          title="Human Review"
          value="17"
          change="13.3%"
          icon="♙"
        />
        <StatCard
          title="Processing"
          value="20"
          change="15.6%"
          icon="◷"
        />
      </div>

      <div className="dashboard-grid">
        <section className="panel recent-panel">
          <div className="panel-header">
            <div>
              <h3>Recent Cases</h3>
              <p>Latest customer support investigations</p>
            </div>

            <button
              className="text-button"
              onClick={() => onNavigate("cases")}
            >
              View all →
            </button>
          </div>

          <CaseTable cases={cases.slice(0, 4)} onOpenCase={onOpenCase} />
        </section>

        <section className="panel resolution-panel">
          <div className="panel-header">
            <div>
              <h3>Resolution Overview</h3>
              <p>Current case distribution</p>
            </div>
          </div>

          <div className="resolution-chart">
            <div className="donut">
              <div>
                <strong>128</strong>
                <span>Cases</span>
              </div>
            </div>

            <div className="chart-legend">
              <Legend label="AI Resolved" value="91" />
              <Legend label="Human Review" value="17" />
              <Legend label="Processing" value="20" />
            </div>
          </div>

          <div className="ai-rate">
            <span>AI resolution rate</span>
            <strong>71.1%</strong>
          </div>
        </section>
      </div>

      <section className="panel activity-panel">
        <div className="panel-header">
          <div>
            <h3>CasePilot Activity</h3>
            <p>Latest system events</p>
          </div>
        </div>

        <div className="activity-list">
          <Activity
            title="Refund investigation completed"
            detail="CP-0001 · Strategy 1 succeeded"
            time="2 min ago"
          />
          <Activity
            title="Human approval required"
            detail="CP-0002 · Transaction exceeds ₹2,000"
            time="8 min ago"
          />
          <Activity
            title="Payment reconciliation completed"
            detail="CP-0003 · Strategy 2 succeeded"
            time="14 min ago"
          />
        </div>
      </section>
    </>
  );
}

/* -------------------------------------------------------
   CASES
------------------------------------------------------- */

function CasesPage({
  onOpenCase,
}: {
  onOpenCase: (item: Case) => void;
}) {
  return (
    <>
      <div className="page-heading">
        <div>
          <h3>Customer Cases</h3>
          <p>Investigate and resolve customer issues.</p>
        </div>

        <button className="primary-button">+ New Case</button>
      </div>

      <div className="filter-bar">
        <div className="search-box">
          <span>⌕</span>
          <input placeholder="Search case, order or customer..." />
        </div>

        <button className="filter-button">All Issues ▾</button>
        <button className="filter-button">All Status ▾</button>
      </div>

      <section className="panel">
        <CaseTable cases={cases} onOpenCase={onOpenCase} />
      </section>
    </>
  );
}

function CaseTable({
  cases,
  onOpenCase,
}: {
  cases: Case[];
  onOpenCase: (item: Case) => void;
}) {
  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>CASE</th>
            <th>ISSUE</th>
            <th>ORDER</th>
            <th>AMOUNT</th>
            <th>STATUS</th>
            <th>STRATEGY</th>
            <th />
          </tr>
        </thead>

        <tbody>
          {cases.map((item) => (
            <tr key={item.id}>
              <td>
                <strong className="case-id">{item.id}</strong>
                <small>{item.customer}</small>
              </td>

              <td>
                <span className="issue-label">{item.issue}</span>
              </td>

              <td>{item.orderId}</td>

              <td>
                <strong>{formatAmount(item.amount)}</strong>
              </td>

              <td>
                <StatusBadge status={item.status} />
              </td>

              <td>
                <span className="strategy">{item.strategy}</span>
              </td>

              <td>
                <button
                  className="row-action"
                  onClick={() => onOpenCase(item)}
                >
                  →
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* -------------------------------------------------------
   INVESTIGATION
------------------------------------------------------- */

function InvestigationPage({
  selectedCase,
}: {
  selectedCase: Case | null;
}) {
  const currentCase = selectedCase || cases[0];

  return (
    <>
      <div className="case-hero">
        <div>
          <span className="case-label">{currentCase.id}</span>
          <h3>Customer Resolution Investigation</h3>
          <p>
            Customer reports an issue related to order{" "}
            <strong>{currentCase.orderId}</strong>.
          </p>
        </div>

        <StatusBadge status={currentCase.status} />
      </div>

      <div className="investigation-layout">
        <div>
          <section className="panel customer-message">
            <div className="panel-header">
              <div>
                <h3>Customer Issue</h3>
                <p>Original customer message</p>
              </div>
            </div>

            <div className="message-bubble">
              "I cancelled my order but haven't received my refund."
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h3>Investigation Trace</h3>
                <p>CasePilot investigation workflow</p>
              </div>
            </div>

            <div className="timeline">
              <TimelineItem
                title="Customer identified"
                detail="Customer record retrieved"
                done
              />
              <TimelineItem
                title="Order retrieved"
                detail={`${currentCase.orderId} · ${formatAmount(
                  currentCase.amount
                )}`}
                done
              />
              <TimelineItem
                title="Payment verified"
                detail="Payment status: SUCCESS"
                done
              />
              <TimelineItem
                title="Refund retrieved"
                detail="Refund record found"
                done
              />
              <TimelineItem
                title="Policy checked"
                detail="CasePilot authorization policy evaluated"
                done
              />
              <TimelineItem
                title="Amount gate"
                detail={
                  currentCase.amount >= 2000
                    ? "Human approval required"
                    : "AI resolution allowed"
                }
                done
              />
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h3>Resolution Strategies</h3>
                <p>Strategies attempted by CasePilot</p>
              </div>
            </div>

            <Strategy
              number="01"
              name="Direct Refund"
              status={
                currentCase.status === "Processing"
                  ? "Processing"
                  : "Successful"
              }
              detail="Attempt to initiate the eligible refund directly."
            />

            <Strategy
              number="02"
              name="Recover Transaction Reference"
              status="Not attempted"
              detail="Use when the direct transaction path fails."
            />

            <Strategy
              number="03"
              name="Alternative Resolution"
              status="Not attempted"
              detail="Final issue-specific recovery strategy."
            />
          </section>
        </div>

        <aside>
          <section className="panel summary-card">
            <div className="panel-header">
              <div>
                <h3>Case Summary</h3>
                <p>Current case information</p>
              </div>
            </div>

            <InfoRow label="Case ID" value={currentCase.id} />
            <InfoRow label="Order ID" value={currentCase.orderId} />
            <InfoRow
              label="Transaction Amount"
              value={formatAmount(currentCase.amount)}
              highlight
            />
            <InfoRow label="Issue Type" value={currentCase.issue} />
            <InfoRow
              label="Authorization"
              value={
                currentCase.amount >= 2000
                  ? "Human Required"
                  : "AI Allowed"
              }
            />

            <div className="summary-divider" />

            <div className="resolution-result">
              <span>RESOLUTION STATUS</span>

              <strong>
                {currentCase.amount >= 2000
                  ? "HUMAN REVIEW"
                  : currentCase.status.toUpperCase()}
              </strong>
            </div>
          </section>

          <section className="panel order-card">
            <div className="panel-header">
              <div>
                <h3>Order Evidence</h3>
                <p>System records</p>
              </div>
            </div>

            <InfoRow label="Product" value="Drone Mini" />
            <InfoRow label="Quantity" value="3" />
            <InfoRow label="Order Status" value="Cancelled" />
            <InfoRow label="Payment" value="Successful" />
            <InfoRow label="Refund" value="Processing" />
          </section>
        </aside>
      </div>
    </>
  );
}

/* -------------------------------------------------------
   HUMAN QUEUE
------------------------------------------------------- */

function HumanQueuePage({
  onOpenCase,
}: {
  onOpenCase: (item: Case) => void;
}) {
  const humanCases = cases.filter(
    (item) => item.status === "Human Review"
  );

  return (
    <>
      <div className="page-heading">
        <div>
          <h3>Human Approval Queue</h3>
          <p>
            Cases requiring human intervention before transaction execution.
          </p>
        </div>

        <div className="queue-count">
          <strong>6</strong>
          <span>pending cases</span>
        </div>
      </div>

      <div className="warning-banner">
        <span>!</span>
        <div>
          <strong>Human approval is mandatory for transactions ≥ ₹2,000.</strong>
          <p>
            CasePilot must not execute financial transactions above the
            authorization threshold.
          </p>
        </div>
      </div>

      <section className="panel">
        <CaseTable cases={humanCases} onOpenCase={onOpenCase} />
      </section>
    </>
  );
}

/* -------------------------------------------------------
   TRANSACTIONS
------------------------------------------------------- */

function TransactionsPage() {
  return (
    <>
      <div className="page-heading">
        <div>
          <h3>Transactions</h3>
          <p>Financial operations performed by CasePilot.</p>
        </div>
      </div>

      <div className="stats-grid three">
        <StatCard title="Refunds" value="43" change="31 completed" icon="↗" />
        <StatCard title="Processing" value="12" change="Awaiting gateway" icon="◷" />
        <StatCard title="Failed" value="4" change="Escalated" icon="!" />
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h3>Recent Refund Transactions</h3>
            <p>Synthetic CasePilot transaction records</p>
          </div>
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>REFUND ID</th>
                <th>ORDER</th>
                <th>AMOUNT</th>
                <th>REASON</th>
                <th>STATUS</th>
              </tr>
            </thead>

            <tbody>
              <tr>
                <td>REF00000001</td>
                <td>ORD0000001</td>
                <td>₹1,999</td>
                <td>Order Cancelled</td>
                <td>
                  <StatusBadge status="Processing" />
                </td>
              </tr>

              <tr>
                <td>REF00000027</td>
                <td>ORD0000027</td>
                <td>₹1,299</td>
                <td>Item Not Received</td>
                <td>
                  <span className="status-badge resolved">
                    <span className="status-dot" />
                    Completed
                  </span>
                </td>
              </tr>

              <tr>
                <td>REF00000031</td>
                <td>ORD0000042</td>
                <td>₹3,499</td>
                <td>Delivery Dispute</td>
                <td>
                  <span className="status-badge human-review">
                    <span className="status-dot" />
                    Human Review
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

/* -------------------------------------------------------
   POLICIES
------------------------------------------------------- */

function PoliciesPage() {
  return (
    <>
      <div className="page-heading">
        <div>
          <h3>Policy Center</h3>
          <p>Rules used during CasePilot investigations.</p>
        </div>
      </div>

      <div className="policy-grid">
        <section className="panel policy-card">
          <span className="policy-tag">PUBLIC GUIDANCE</span>
          <h3>Amazon Policy Guidance</h3>
          <p>
            Publicly available guidance used as reference material for
            the synthetic CasePilot environment.
          </p>

          <div className="policy-rule">
            <strong>Return window</strong>
            <span>Generally 30 days*</span>
          </div>

          <div className="policy-rule">
            <strong>Returnless resolution</strong>
            <span>Available for qualifying cases</span>
          </div>

          <div className="policy-rule">
            <strong>Delivery evidence</strong>
            <span>Tracking / proof of delivery</span>
          </div>
        </section>

        <section className="panel policy-card">
          <span className="policy-tag casepilot">CASEPILOT RULE</span>
          <h3>Transaction Authorization</h3>
          <p>
            Project-specific authorization rules controlling what the AI
            is allowed to execute.
          </p>

          <div className="amount-rule allowed">
            <div>
              <strong>&lt; ₹2,000</strong>
              <span>AI transaction allowed</span>
            </div>
            <b>AI</b>
          </div>

          <div className="amount-rule blocked">
            <div>
              <strong>≥ ₹2,000</strong>
              <span>Human approval required</span>
            </div>
            <b>HUMAN</b>
          </div>
        </section>
      </div>

      <div className="info-note">
        <strong>Important:</strong> Amazon public guidance is reference
        material only. CasePilot does not access or claim to reproduce
        Amazon's internal systems or policies.
      </div>
    </>
  );
}

/* -------------------------------------------------------
   DATA
------------------------------------------------------- */

function DataPage() {
  const datasets = [
    ["Customers", "100,000"],
    ["Orders", "100,000"],
    ["Payments", "100,000"],
    ["Deliveries", "100,000"],
    ["Support Cases", "80,093"],
    ["Refunds", "Synthetic"],
    ["Returns", "Synthetic"],
    ["Products", "Synthetic"],
  ];

  return (
    <>
      <div className="page-heading">
        <div>
          <h3>CasePilot Data</h3>
          <p>Synthetic datasets powering the investigation environment.</p>
        </div>
      </div>

      <div className="data-grid">
        {datasets.map(([name, value]) => (
          <div className="data-card" key={name}>
            <span>{name}</span>
            <strong>{value}</strong>
            <small>CSV dataset</small>
          </div>
        ))}
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h3>Data Architecture</h3>
            <p>Information sources available to CasePilot tools.</p>
          </div>
        </div>

        <div className="data-flow">
          <div>Customer</div>
          <span>→</span>
          <div>Order</div>
          <span>→</span>
          <div>Payment</div>
          <span>→</span>
          <div>Delivery</div>
          <span>→</span>
          <div>Return / Refund</div>
        </div>
      </section>
    </>
  );
}

/* -------------------------------------------------------
   SMALL COMPONENTS
------------------------------------------------------- */

function StatCard({
  title,
  value,
  change,
  icon,
}: {
  title: string;
  value: string;
  change: string;
  icon: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <span>{title}</span>
        <div className="stat-icon">{icon}</div>
      </div>

      <strong>{value}</strong>
      <small>{change}</small>
    </div>
  );
}

function Legend({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="legend-item">
      <span className="legend-marker" />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Activity({
  title,
  detail,
  time,
}: {
  title: string;
  detail: string;
  time: string;
}) {
  return (
    <div className="activity">
      <span className="activity-dot" />
      <div>
        <strong>{title}</strong>
        <span>{detail}</span>
      </div>
      <time>{time}</time>
    </div>
  );
}

function TimelineItem({
  title,
  detail,
  done,
}: {
  title: string;
  detail: string;
  done?: boolean;
}) {
  return (
    <div className="timeline-item">
      <div className={`timeline-marker ${done ? "done" : ""}`}>
        {done ? "✓" : ""}
      </div>

      <div>
        <strong>{title}</strong>
        <span>{detail}</span>
      </div>
    </div>
  );
}

function Strategy({
  number,
  name,
  status,
  detail,
}: {
  number: string;
  name: string;
  status: string;
  detail: string;
}) {
  const success = status === "Successful";
  const processing = status === "Processing";

  return (
    <div className="strategy-row">
      <span className="strategy-number">{number}</span>

      <div className="strategy-info">
        <strong>{name}</strong>
        <span>{detail}</span>
      </div>

      <span
        className={`strategy-status ${success ? "success" : processing ? "processing" : ""
          }`}
      >
        {status}
      </span>
    </div>
  );
}

function InfoRow({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="info-row">
      <span>{label}</span>
      <strong className={highlight ? "highlight" : ""}>{value}</strong>
    </div>
  );
}

export default App;