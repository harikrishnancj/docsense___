import { useState, useRef, useEffect } from 'react';
import { ArrowUp, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { processDocument } from '../api/client';
import remarkGfm from 'remark-gfm';

export default function IntelligenceContext({ files, onNewResults, onProcessing }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isInternalProcessing, setIsInternalProcessing] = useState(false);
    const scrollRef = useRef(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, isInternalProcessing]);

    const handleSend = async () => {
        if (!input.trim() || isInternalProcessing) return;

        if (!files || files.length === 0) {
            setMessages(prev => [...prev, { role: 'user', content: input }, { role: 'assistant', content: 'Please import a document to begin analysis.' }]);
            setInput('');
            return;
        }

        const userMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        const currentInput = input;
        setInput('');

        setIsInternalProcessing(true);
        if (onProcessing) onProcessing(true);

        try {
            const response = await processDocument(files[0], currentInput);
            const assistantMessage = {
                role: 'assistant',
                content: response.rag_response || response.summary || 'Analysis complete. Results available in dashboard.'
            };
            setMessages(prev => [...prev, assistantMessage]);

            if (onNewResults) {
                onNewResults(response);
            }
        } catch (error) {
            setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${error.message}` }]);
        } finally {
            setIsInternalProcessing(false);
            if (onProcessing) onProcessing(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <section className="console-pane">
            <div className="console-messages" ref={scrollRef}>
                {messages.length === 0 && (
                    <div style={{ marginTop: 'auto', marginBottom: 'auto', textAlign: 'center', color: 'var(--text-tertiary)' }}>
                        <h3 style={{ fontSize: '16px', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '8px' }}>DocSense Intelligence</h3>
                        <p style={{ fontSize: '13px' }}>Ask questions about your documents.</p>
                    </div>
                )}

                {messages.map((msg, i) => (
                    <div key={i} className={`message-node ${msg.role}`}>
                        <span className="msg-role">{msg.role === 'user' ? 'You' : 'System'}</span>
                        <div className="msg-content">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                        </div>
                    </div>
                ))}

                {isInternalProcessing && (
                    <div className="message-node assistant">
                        <span className="msg-role">System</span>
                        <div className="msg-content" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <Loader2 size={14} className="animate-spin" />
                            <span>Processing...</span>
                        </div>
                    </div>
                )}
            </div>

            <div className="input-area">
                <div className="input-box">
                    <input
                        type="text"
                        placeholder="Ask a question..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={handleKeyPress}
                        disabled={isInternalProcessing}
                    />
                    <button
                        className="send-btn"
                        onClick={handleSend}
                        disabled={!input.trim() || isInternalProcessing}
                    >
                        <ArrowUp size={16} />
                    </button>
                </div>
            </div>
        </section>
    );
}
