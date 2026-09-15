import { useState } from "react";
import "./App.css";

type Message = {
  id: number;
  sender: "bot" | "user";
  text: string;
};

const quickActions = [
  {
    icon: "📦",
    title: "Order issue",
    message: "I have a problem with my order",
  },
  {
    icon: "🚚",
    title: "Delivery issue",
    message: "I have a problem with my delivery",
  },
  {
    icon: "💳",
    title: "Payment issue",
    message: "I have a problem with my payment",
  },
  {
    icon: "💰",
    title: "Refund issue",
    message: "I haven't received my refund",
  },
  {
    icon: "↩",
    title: "Return an item",
    message: "I want to return an item",
  },
];

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      sender: "bot",
      text: "Hi! I'm CasePilot 👋\n\nI can help you with orders, deliveries, payments, returns, and refunds.\n\nTell me what happened and I'll help you find a solution.",
    },
  ]);

  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const sendMessage = async (messageText?: string) => {
    const text = (messageText ?? input).trim();

    if (!text || isTyping) return;

    const userMessage: Message = {
      id: Date.now(),
      sender: "user",
      text,
    };

    setMessages((previous) => [...previous, userMessage]);
    setInput("");
    setIsTyping(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          customer_message: text,
        }),
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }

      const data = await response.json();

      const botMessage: Message = {
        id: Date.now() + 1,
        sender: "bot",
        text: data.message,
      };

      setMessages((previous) => [...previous, botMessage]);
    } catch (error) {
      console.error("CasePilot API error:", error);

      const errorMessage: Message = {
        id: Date.now() + 1,
        sender: "bot",
        text:
          "I'm having trouble connecting to CasePilot right now. Please try again in a moment.",
      };

      setMessages((previous) => [...previous, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      sendMessage();
    }
  };

  return (
    <div className="app-shell">
      {/* Background decoration */}
      <div className="background-glow glow-one"></div>
      <div className="background-glow glow-two"></div>

      {/* Header */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <span>✦</span>
          </div>

          <div>
            <div className="brand-name">CasePilot</div>
            <div className="brand-subtitle">AI Customer Support</div>
          </div>
        </div>

        <div className="header-status">
          <span className="status-dot"></span>
          <span>Online</span>
        </div>
      </header>

      {/* Main content */}
      <main className="main-content">
        <section className="chat-container">
          {/* Chat header */}
          <div className="chat-header">
            <div className="agent-profile">
              <div className="agent-avatar">
                ✦
              </div>

              <div>
                <h1>CasePilot</h1>
                <p>Your AI support assistant</p>
              </div>
            </div>

            <div className="secure-badge">
              <span>⌁</span>
              Secure conversation
            </div>
          </div>

          {/* Messages */}
          <div className="messages-area">
            <div className="welcome-section">
              <div className="welcome-icon">✦</div>

              <h2>How can we help?</h2>

              <p>
                Tell us what happened. CasePilot will investigate your
                issue and help you find the right resolution.
              </p>
            </div>

            <div className="messages-list">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`message-row ${message.sender}`}
                >
                  {message.sender === "bot" && (
                    <div className="small-avatar">✦</div>
                  )}

                  <div className={`message-bubble ${message.sender}`}>
                    {message.text.split("\n").map((line, index) => (
                      <span key={index}>
                        {line}
                        {index < message.text.split("\n").length - 1 && (
                          <br />
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="message-row bot">
                  <div className="small-avatar">✦</div>

                  <div className="typing-bubble">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Quick actions */}
          <div className="quick-actions">
            <p>What do you need help with?</p>

            <div className="quick-action-list">
              {quickActions.map((action) => (
                <button
                  key={action.title}
                  className="quick-action"
                  onClick={() => sendMessage(action.message)}
                >
                  <span className="quick-icon">{action.icon}</span>
                  <span>{action.title}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Input */}
          <div className="input-section">
            <div className="input-wrapper">
              <input
                type="text"
                placeholder="Tell me what happened..."
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isTyping}
              />

              <button
                className="send-button"
                onClick={() => sendMessage()}
                disabled={!input.trim() || isTyping}
                aria-label="Send message"
              >
                ↑
              </button>
            </div>

            <div className="input-hint">
              <span>↵</span> Press Enter to send
            </div>
          </div>
        </section>

        {/* Right-side information */}
        <aside className="info-panel">
          <div className="info-card intro-card">
            <div className="card-icon">✦</div>

            <h3>Support, without the runaround.</h3>

            <p>
              CasePilot investigates your issue, checks the relevant
              information, and works toward a resolution.
            </p>
          </div>

          <div className="info-card">
            <div className="info-card-heading">
              <span className="heading-icon">✓</span>
              <h3>What I can help with</h3>
            </div>

            <ul>
              <li>
                <span>📦</span>
                Orders
              </li>
              <li>
                <span>🚚</span>
                Deliveries
              </li>
              <li>
                <span>💳</span>
                Payments
              </li>
              <li>
                <span>↩</span>
                Returns
              </li>
              <li>
                <span>💰</span>
                Refunds
              </li>
            </ul>
          </div>

          <div className="info-card privacy-card">
            <div className="privacy-icon">🔒</div>

            <div>
              <h3>Your information is protected</h3>
              <p>
                Only the information needed to investigate your case
                is used.
              </p>
            </div>
          </div>
        </aside>
      </main>

      {/* Footer */}
      <footer className="footer">
        <span>CasePilot</span>
        <span>•</span>
        <span>AI-powered customer resolution</span>
      </footer>
    </div>
  );
}

export default App;