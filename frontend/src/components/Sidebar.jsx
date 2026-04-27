import { Plus, Disc, FileText, Trash2 } from 'lucide-react';

export default function Sidebar({ onFileUpload, onReset, uploadedFiles = [] }) {
    return (
        <aside className="sidebar">
            <div className="brand-section">
                <div style={{ width: 16, height: 16, background: '#fff', borderRadius: 4 }}></div>
                <span className="brand-title">DocSense</span>
            </div>

            <label className="action-btn-primary">
                <Plus size={16} />
                <span>New Import</span>
                <input
                    type="file"
                    onChange={onFileUpload}
                    accept=".pdf,.csv,.xlsx,.xls,.txt,.docx,.pptx,.png,.jpg,.jpeg"
                />
            </label>

            <div className="nav-section">
                <h4>Workspace</h4>
                {uploadedFiles.length === 0 ? (
                    <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', fontStyle: 'italic' }}>
                        No active files
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {uploadedFiles.map((file, i) => (
                            <div key={i} className="file-item">
                                <FileText size={14} />
                                <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                                    {file.name}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <button className="reset-btn" onClick={onReset}>
                <Trash2 size={13} />
                <span>Clear Session</span>
            </button>
        </aside>
    );
}
