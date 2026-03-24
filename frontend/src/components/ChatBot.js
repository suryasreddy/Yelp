import React, { useState, useRef, useEffect } from 'react';
import { sendChatMessage } from '../api';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';

const QUICK_ACTIONS = [
  'Find dinner tonight',
  'Best rated near me',
  'Vegan options',
  'Romantic dinner',
];

const storageKey = (userId) => `chatbot_messages_${userId || 'guest'}`;

const greeting = (user) => ({
  role: 'assistant',
  content: user
    ? `Hi ${user.name?.split(' ')[0]}! I'm your restaurant discovery assistant. Tell me what you're in the mood for — cuisine, vibe, budget, dietary needs — and I'll suggest spots that fit.`
    : "Hi! I'm your restaurant assistant. Log in to get personalized picks based on your saved preferences.",
  isGreeting: true,
});

function loadStoredMessages(userId) {
  try {
    const saved = localStorage.getItem(storageKey(userId));
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.length > 1) return parsed;
    }
  } catch (_) {}
  return null;
}

/** Prior turns for the API — omit the template greeting message. */
function buildConversationHistory(messages) {
  return messages
    .filter((m) => !m.isGreeting)
    .map((m) => ({ role: m.role, content: m.content }));
}

function isFarewellIntent(text) {
  const t = (text || '').toLowerCase().trim();
  if (!t) return false;
  const patterns = [
    /\bbye\b/,
    /\bgoodbye\b/,
    /\bsee you\b/,
    /\bsee ya\b/,
    /\bcatch you later\b/,
    /\bthanks,?\s*bye\b/,
    /\bthank you,?\s*bye\b/,
    /\bthat'?s all\b/,
  ];
  return patterns.some((p) => p.test(t));
}

export default function ChatBot({ onClose, floating = false, embedded = false }) {
  const { user } = useAuth();

  const [messages, setMessages] = useState(() => loadStoredMessages(user?.id) || [greeting(user)]);

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey(user?.id), JSON.stringify(messages));
    } catch (_) {}
  }, [messages, user?.id]);

  useEffect(() => {
    const stored = loadStoredMessages(user?.id);
    if (stored) setMessages(stored);
    else setMessages([greeting(user)]);
  }, [user?.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const clearChat = () => {
    const fresh = [greeting(user)];
    setMessages(fresh);
    try {
      localStorage.setItem(storageKey(user?.id), JSON.stringify(fresh));
    } catch (_) {}
  };

  const sendMessage = async (text) => {
    if (!text.trim()) return;
    if (!user) {
      toast.error('Please log in to use the AI assistant');
      return;
    }

    const userMsg = { role: 'user', content: text };
    const history = buildConversationHistory(messages);

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await sendChatMessage({
        message: text,
        conversation_history: history,
      });
      const { response, recommendations } = res.data;
      const recs = Array.isArray(recommendations) ? recommendations : [];
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response, recommendations: recs },
      ]);

      // Natural goodbye flow: reset chat, and close floating modal if present.
      if (isFarewellIntent(text)) {
        setTimeout(() => {
          clearChat();
          if (onClose && floating) onClose();
        }, 1400);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I ran into an issue. Please try again!' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div
      className={`chatbot-container ${floating ? 'chatbot-floating' : ''} ${
        embedded ? 'chatbot-embedded' : ''
      }`}
    >
      <div className="chatbot-header">
        <div className="chatbot-header-left">
          <div className="chatbot-avatar">🤖</div>
          <div>
            <div className="chatbot-title">Yelp AI Assistant</div>
            <div className="chatbot-subtitle">Personalized recommendations</div>
          </div>
        </div>
        <div className="chatbot-header-right">
          <button
            className="chatbot-clear"
            onClick={clearChat}
            title="New conversation"
          >
            ↺
          </button>
          {onClose && (
            <button className="chatbot-close" onClick={onClose}>
              ✕
            </button>
          )}
        </div>
      </div>

      <div className="chatbot-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message chat-message-${msg.role}`}>
            {msg.role === 'assistant' && <div className="chat-avatar">🤖</div>}
            <div className="chat-bubble">
              <p className="chat-bubble-text">{msg.content}</p>
              {msg.recommendations?.length > 0 && (
                <div className="chat-recommendations">
                  {msg.recommendations.map((rec, j) => (
                    <Link
                      to={`/restaurant/${rec.id}`}
                      key={j}
                      className="chat-rec-card"
                    >
                      <div className="chat-rec-name">{rec.name}</div>
                      <div className="chat-rec-meta">
                        <span>⭐ {rec.rating}</span>
                        <span>{rec.price_tier}</span>
                        <span>{rec.cuisine_type}</span>
                      </div>
                      {rec.reason && (
                        <div className="chat-rec-reason">"{rec.reason}"</div>
                      )}
                    </Link>
                  ))}
                </div>
              )}
            </div>
            {msg.role === 'user' && (
              <div className="chat-user-avatar">
                {user?.name?.[0]?.toUpperCase() || 'U'}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="chat-message chat-message-assistant">
            <div className="chat-avatar">🤖</div>
            <div className="chat-bubble chat-thinking">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {!user && (
        <div className="chatbot-login-prompt">
          <Link to="/login" className="chatbot-login-btn">
            Log in for personalized results
          </Link>
        </div>
      )}

      <div className="chatbot-quick-actions">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action}
            type="button"
            className="quick-action-btn"
            disabled={loading}
            onClick={() => sendMessage(action)}
          >
            {action}
          </button>
        ))}
      </div>

      <form className="chatbot-input-area" onSubmit={handleSubmit}>
        <input
          className="chatbot-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask me for restaurant recommendations..."
          disabled={loading}
        />
        <button
          type="submit"
          className="chatbot-send-btn"
          disabled={loading || !input.trim()}
        >
          ➤
        </button>
      </form>
    </div>
  );
}