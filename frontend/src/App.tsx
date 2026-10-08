import { useEffect, useRef, useState } from "react";
import "./App.css";
import AgentApp from "./agent/AgentApp";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type Conversation = {
  id: string;
  title: string;
  messages: Message[];
};

type ChatResponse = {
  message: string;
  transaction_amount?: number | null;
  authorization?: string | null;
  requires_human?: boolean;
  status?: string;
};

const API_BASE_URL = "http://127.0.0.1:8000";

const createMessage = (
  role: "user" | "assistant",
  content: string,
): Message => ({
  id: `${Date.now()}-${Math.random()}`,
  role,
  content,
});

const createConversation = (): Conversation => ({
  id: `${Date.now()}-${Math.random()}`,
  title: "New conversation",
  messages: [
    createMessage(
      "assistant",
      "Hello! I'm CasePilot, your customer support assistant. How can I help you today?",
    ),
  ],
});

function App() {
  const isAgent =
    new URLSearchParams(window.location.search).get("mode") ===
    "agent";

  if (isAgent) {
    return <AgentApp />;
  }

  return <CustomerApp />;
}

function CustomerApp() {
  const [conversations, setConversations] = useState<
    Conversation[]
  >([createConversation()]);

  const [activeConversationId, setActiveConversationId] =
    useState(conversations[0].id);

  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const messagesEndRef =
    useRef<HTMLDivElement | null>(null);

  const activeConversation = conversations.find(
    (conversation) =>
      conversation.id === activeConversationId,
  );

  const messages =
    activeConversation?.messages ?? [];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isTyping]);

  const appendAssistantMessage = (
    conversationId: string,
    content: string,
  ) => {
    setConversations((current) =>
      current.map((conversation) => {
        if (
          conversation.id !== conversationId
        ) {
          return conversation;
        }

        return {
          ...conversation,
          messages: [
            ...conversation.messages,
            createMessage(
              "assistant",
              content,
            ),
          ],
        };
      }),
    );
  };

  const handleNewChat = () => {
    const newConversation =
      createConversation();

    setConversations((current) => [
      newConversation,
      ...current,
    ]);

    setActiveConversationId(
      newConversation.id,
    );
    setInput("");
  };

  const handleSend = async () => {
    const message = input.trim();

    if (
      !message ||
      isTyping ||
      !activeConversation
    ) {
      return;
    }

    const conversationId =
      activeConversation.id;

    const userMessage = createMessage(
      "user",
      message,
    );

    setConversations((current) =>
      current.map((conversation) => {
        if (
          conversation.id !==
          conversationId
        ) {
          return conversation;
        }

        const isFirstUserMessage =
          conversation.messages.filter(
            (item) => item.role === "user",
          ).length === 0;

        return {
          ...conversation,
          title: isFirstUserMessage
            ? message.length > 32
              ? `${message.substring(0, 32)}...`
              : message
            : conversation.title,
          messages: [
            ...conversation.messages,
            userMessage,
          ],
        };
      }),
    );

    setInput("");
    setIsTyping(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            session_id: conversationId,
            customer_message: message,
          }),
        },
      );

      if (!response.ok) {
        const errorText =
          await response.text();

        throw new Error(
          errorText ||
          `Request failed with ${response.status}`,
        );
      }

      const data =
        (await response.json()) as ChatResponse;

      appendAssistantMessage(
        conversationId,
        data.message ||
        "CasePilot processed your request.",
      );
    } catch (error) {
      console.error(
        "CasePilot API error:",
        error,
      );

      appendAssistantMessage(
        conversationId,
        "I couldn't connect to CasePilot right now. Please make sure the FastAPI backend is running on port 8000 and try again.",
      );
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      void handleSend();
    }
  };

  const handleSuggestion = (
    text: string,
  ) => {
    setInput(text);
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand">
            <div className="brand-icon">
              CP
            </div>

            <div>
              <div className="brand-name">
                CasePilot
              </div>

              <div className="brand-subtitle">
                AI Support Assistant
              </div>
            </div>
          </div>
        </div>

        <button
          className="new-chat-button"
          onClick={handleNewChat}
        >
          <span className="plus-icon">
            +
          </span>
          New Chat
        </button>

        <div className="history-section">
          <div className="history-title">
            CONVERSATIONS
          </div>

          <div className="conversation-list">
            {conversations.map(
              (conversation) => (
                <button
                  key={conversation.id}
                  className={`conversation-item ${conversation.id ===
                    activeConversationId
                    ? "active"
                    : ""
                    }`}
                  onClick={() =>
                    setActiveConversationId(
                      conversation.id,
                    )
                  }
                >
                  <span className="conversation-icon">
                    ◦
                  </span>

                  <span className="conversation-title">
                    {conversation.title}
                  </span>
                </button>
              ),
            )}
          </div>
        </div>

        {/* ------------------------------------------------ */}
        {/* CasePilot Capabilities */}
        {/* ------------------------------------------------ */}

        <div className="capabilities-section">
          <div className="capabilities-title">
            CASEPILOT CAN HELP WITH
          </div>

          <div className="capabilities-list">
            <div className="capability-item">
              <span className="capability-icon">□</span>
              <span>Orders</span>
            </div>

            <div className="capability-item">
              <span className="capability-icon">₹</span>
              <span>Payments</span>
            </div>

            <div className="capability-item">
              <span className="capability-icon">⌁</span>
              <span>Delivery</span>
            </div>

            <div className="capability-item">
              <span className="capability-icon">↩</span>
              <span>Returns & Refunds</span>
            </div>

            <div className="capability-item">
              <span className="capability-icon">×</span>
              <span>Cancellations</span>
            </div>

            <div className="capability-item">
              <span className="capability-icon">◇</span>
              <span>Product Questions</span>
            </div>
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="status-dot" />
          <span>
            CasePilot is online
          </span>
        </div>
      </aside>

      <main className="chat-area">
        <header
          className="chat-header"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            width: "100%",
          }}
        >
          <div>
            <div className="chat-header-title">
              Customer Support
            </div>

            <div className="chat-header-status">
              <span className="online-dot" />
              AI assistant available
            </div>
          </div>

          <a
            href="?mode=agent"
            className="agent-console-button"
          >
            <span>Agent Console</span>
            <span className="agent-console-arrow">↗</span>
          </a>
        </header>

        <section className="messages-container">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`message-row ${message.role}`}
            >
              {message.role ===
                "assistant" && (
                  <div className="avatar assistant-avatar">
                    CP
                  </div>
                )}

              <div
                className={`message-bubble ${message.role}`}
              >
                {message.content}
              </div>

              {message.role ===
                "user" && (
                  <div className="avatar user-avatar">
                    You
                  </div>
                )}
            </div>
          ))}

          {isTyping && (
            <div className="message-row assistant">
              <div className="avatar assistant-avatar">
                CP
              </div>

              <div className="message-bubble assistant typing">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </section>

        {messages.length <= 1 && (
          <div className="suggestions">
            <button
              onClick={() =>
                handleSuggestion(
                  "What is the status of my order?",
                )
              }
            >
              📦 Order status
            </button>

            <button
              onClick={() =>
                handleSuggestion(
                  "I want to request a refund.",
                )
              }
            >
              💳 Request a refund
            </button>

            <button
              onClick={() =>
                handleSuggestion(
                  "Where is my delivery?",
                )
              }
            >
              🚚 Track delivery
            </button>

            <button
              onClick={() =>
                handleSuggestion(
                  "Can I return my product?",
                )
              }
            >
              ↩ Return an item
            </button>
          </div>
        )}

        <div className="input-area">
          <div className="input-wrapper">
            <textarea
              value={input}
              onChange={(event) =>
                setInput(event.target.value)
              }
              onKeyDown={handleKeyDown}
              placeholder="Ask CasePilot anything about your order..."
              rows={1}
              disabled={isTyping}
            />

            <button
              className="send-button"
              onClick={() =>
                void handleSend()
              }
              disabled={
                !input.trim() ||
                isTyping
              }
              aria-label="Send message"
            >
              ↑
            </button>
          </div>

          <div className="input-disclaimer">
            CasePilot can make mistakes. Please
            verify important information.
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
