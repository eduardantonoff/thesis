import React, { useState, useRef, useEffect, useCallback } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { FaChevronLeft } from 'react-icons/fa';

import 'katex/dist/katex.min.css';
import './App.css';

// API endpoints centralized
const API_ENDPOINTS = {
  SESSION_STATE: 'http://localhost:8000/session-state',
  PROFILE: 'http://localhost:8000/profile',
  PLAN: 'http://localhost:8000/plan',
  ASSESSMENT: 'http://localhost:8000/assessment',
  CHAT: 'http://localhost:8000/chat',
};

const USER_ID = 'my_user_id';

function App() {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  
  // User data states
  const [sessionState, setSessionState] = useState('');
  const [userProfile, setUserProfile] = useState('Loading profile...');
  const [userPlan, setUserPlan] = useState([]);
  const [evaluationPlan, setEvaluationPlan] = useState([]);

  const chatBoxRef = useRef(null);

  // Fetch all user data on component mount
  useEffect(() => {
    fetchAllData();
  }, []);

  // Auto-scroll to the bottom of chat when messages change
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  // Fetch all data from server
  const fetchAllData = async () => {
    try {
      const [sessionResponse, profileResponse, planResponse, evaluationResponse] = await Promise.all([
        axios.get(API_ENDPOINTS.SESSION_STATE),
        axios.get(API_ENDPOINTS.PROFILE, { params: { user_id: USER_ID } }),
        axios.get(API_ENDPOINTS.PLAN),
        axios.get(API_ENDPOINTS.ASSESSMENT),
      ]);

      setSessionState(sessionResponse.data.next || '');
      setUserProfile(profileResponse.data.profile || 'No profile data found.');
      setUserPlan(planResponse.data.plan || []);
      setEvaluationPlan(evaluationResponse.data.plan || []);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  // Individual data fetching functions
  const fetchSessionState = useCallback(async () => {
    try {
      const response = await axios.get(API_ENDPOINTS.SESSION_STATE);
      setSessionState(response.data.next || '');
    } catch (error) {
      console.error('Error fetching session state:', error);
    }
  }, []);

  const fetchUserProfile = useCallback(async () => {
    try {
      const res = await axios.get(API_ENDPOINTS.PROFILE, {
        params: { user_id: USER_ID },
      });
      setUserProfile(res.data.profile || 'No profile data found.');
    } catch (err) {
      console.error('Error fetching profile:', err);
      setUserProfile('Failed to load user profile.');
    }
  }, []);

  const fetchUserPlan = useCallback(async () => {
    try {
      const res = await axios.get(API_ENDPOINTS.PLAN);
      setUserPlan(res.data.plan || []);
    } catch (err) {
      console.error('Error fetching plan:', err);
    }
  }, []);

  const fetchEvaluationPlan = useCallback(async () => {
    try {
      const res = await axios.get(API_ENDPOINTS.ASSESSMENT);
      setEvaluationPlan(res.data.plan || []);
    } catch (err) {
      console.error('Error fetching evaluation plan:', err);
    }
  }, []);

  // UI event handlers
  const toggleSidebar = () => setIsSidebarCollapsed(prev => !prev);
  const handleInputChange = (e) => setUserInput(e.target.value);

  const handleSendMessage = useCallback(async (message) => {
    if (!message.trim()) return;
    
    const userMsg = { sender: 'user', content: message.trim() };
    setUserInput('');
    setChatLoading(true);

    try {
      // Add user message to chat
      setMessages(prev => [...prev, userMsg]);
      
      // Get bot response
      const response = await axios.get(API_ENDPOINTS.CHAT, { 
        params: { user_input: message } 
      });
      
      // Add bot message to chat
      const botReply = { 
        sender: 'bot', 
        content: response.data.response || 'Something went wrong...' 
      };
      setMessages(prev => [...prev, botReply]);

      // Refresh data after chat interaction
      await Promise.all([
        fetchSessionState(), 
        fetchUserProfile(), 
        fetchUserPlan(), 
        fetchEvaluationPlan()
      ]);
    } catch (error) {
      console.error('Error:', error);
      const errorMsg = {
        sender: 'bot',
        content: `Sorry, something went wrong: ${error.message}`,
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setChatLoading(false);
    }
  }, [fetchSessionState, fetchUserProfile, fetchUserPlan, fetchEvaluationPlan]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(userInput);
    }
  };

  const handleContinueSession = () => handleSendMessage('continue');

  return (
    <div className="app-container">
      {/* SIDEBAR */}
      <div className={`sidebar ${isSidebarCollapsed ? 'collapsed' : ''}`}>
        <button 
          className="sidebar-toggle" 
          onClick={toggleSidebar} 
          aria-label="Toggle Sidebar"
        >
          <FaChevronLeft />
        </button>

        {!isSidebarCollapsed && (
          <div className="sidebar-board">
            <h3>Profile:</h3>
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
              {userProfile}
            </ReactMarkdown>

            {sessionState === 'learning session' && userPlan.length > 0 && (
              <>
                <h3>Current Learning Session:</h3>
                <div className="plan-list">
                  {userPlan.map((item, idx) => (
                    <div key={idx} className="plan-item">
                      <strong>{idx + 1}. {item.title}</strong>
                      <p>{item.learning_objective}</p>
                    </div>
                  ))}
                </div>
              </>
            )}

            {sessionState === 'evaluation session' && evaluationPlan.length > 0 && (
              <>
                <h3>Current Evaluation Session:</h3>
                <div className="plan-list">
                  {evaluationPlan.map((item, idx) => (
                    <div key={idx} className="plan-item">
                      <strong>{idx + 1}. {item.title}</strong>
                      <p>{item.description}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* MAIN CONTENT */}
      <div className={`main-content ${isSidebarCollapsed ? 'expanded' : ''}`}>
        <div className="chat-container">
          <div className="top-bar">
            {sessionState === 'learning session' ? (
              <div className="learning-session-active">learning session</div>
            ) : sessionState === 'evaluation session' ? (
              <div className="learning-session-active">evaluation session</div>
            ) : null}
          </div>

          <div className="chat-box" ref={chatBoxRef}>
            {messages.map((message, index) => {
              const isBot = message.sender === 'bot';
              return (
                <div key={index} className={`message ${isBot ? 'bot' : 'user'}`}>
                  <div className="message-content">
                    {isBot ? (
                      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                        {message.content}
                      </ReactMarkdown>
                    ) : (
                      <p>{message.content}</p>
                    )}
                  </div>
                </div>
              );
            })}

            {chatLoading && (
              <div className="message bot">
                <div className="loading-indicator" aria-live="polite">
                  <div className="loading-dot"></div>
                  <div className="loading-dot"></div>
                  <div className="loading-dot"></div>
                </div>
              </div>
            )}
          </div>

          <div className="input-area">
            {sessionState === 'learning session' ? (
              <button 
                className="continue-btn" 
                onClick={handleContinueSession} 
                disabled={chatLoading}
              >
                Continue
              </button>
            ) : (
              <textarea
                value={userInput}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Type your message here..."
                disabled={chatLoading}
                rows={2}
                aria-label="Chat Input"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;