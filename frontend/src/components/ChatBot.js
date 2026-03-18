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

export default function ChatBot({ onClose, floating = false }) {
  const { user } = useAuth();
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: user
        ? `Hi ${user.name?.split(' ')[0]}! 👋 I'm your Yelp assistant. Tell me what you're craving and I'll find the perfect spot for you!`
        : "Hi! I'm your Yelp assistant. Log in to get personalized restaurant recommendations based on your preferences!",
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text) => {
    if (!text.trim()) return;
    if (!user) { toast.error('Please log in to use the AI assistant'); return; }

    const userMsg = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await sendChatMessage({ message: text, conversation_history: history });
      const { response, recommendations } = res.data;
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response, recommendations },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I ran into an issue. Please try again!' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => { e.preventDefault(); sendMessage(input); };

  return (
    <div className={`chatbot-container ${floating ? 'chatbot-floating' : ''}`}>
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
            onClick={() => setMessages([{
              role: 'assistant',
              content: user
                ? `Hi ${user.name?.split(' ')[0]}! 👋 What are you in the mood for?`
                : 'Hi! Log in for personalized recommendations.',
            }])}
            title="New conversation"
          >
            ↺
          </button>
          {onClose && <button className="chatbot-close" onClick={onClose}>✕</button>}
        </div>
      </div>

      <div className="chatbot-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message chat-message-${msg.role}`}>
            {msg.role === 'assistant' && <div className="chat-avatar">🤖</div>}
            <div className="chat-bubble">
              <p>{msg.content}</p>
              {msg.recommendations?.length > 0 && (
                <div className="chat-recommendations">
                  {msg.recommendations.map((rec, j) => (
                    <Link to={`/restaurant/${rec.id}`} key={j} className="chat-rec-card">
                      <div className="chat-rec-name">{rec.name}</div>
                      <div className="chat-rec-meta">
                        <span>⭐ {rec.rating}</span>
                        <span>{rec.price_tier}</span>
                        <span>{rec.cuisine_type}</span>
                      </div>
                      {rec.reason && <div className="chat-rec-reason">"{rec.reason}"</div>}
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
              <span></span><span></span><span></span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {!user && (
        <div className="chatbot-login-prompt">
          <Link to="/login" className="chatbot-login-btn">Log in for personalized results</Link>
        </div>
      )}

      <div className="chatbot-quick-actions">
        {QUICK_ACTIONS.map((action) => (
          <button key={action} className="quick-action-btn" onClick={() => sendMessage(action)}>
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
        <button type="submit" className="chatbot-send-btn" disabled={loading || !input.trim()}>
          ➤
        </button>
      </form>
    </div>
  );
}
