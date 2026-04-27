import { useState } from 'react';
import { BarChart2, Table, Image } from 'lucide-react';

export default function InsightDashboard({ lastResults }) {
    const [activeTab, setActiveTab] = useState('visuals');

    const charts = lastResults?.visuals?.charts || [];
    const tables = lastResults?.extracted_tables || [];
    const imgs = lastResults?.extracted_images || [];
    const descs = lastResults?.image_descriptions || [];
    const insights = lastResults?.image_insights || [];

    const hasData = (charts && charts.length > 0) || (tables && tables.length > 0) || (imgs && imgs.length > 0);

    return (
        <section className="evidence-pane">
            <div className="tabs-header">
                <button
                    className={`tab-btn ${activeTab === 'visuals' ? 'active' : ''}`}
                    onClick={() => setActiveTab('visuals')}
                >
                    Visuals
                </button>
                <button
                    className={`tab-btn ${activeTab === 'tables' ? 'active' : ''}`}
                    onClick={() => setActiveTab('tables')}
                >
                    Tables
                </button>
                <button
                    className={`tab-btn ${activeTab === 'scans' ? 'active' : ''}`}
                    onClick={() => setActiveTab('scans')}
                >
                    Scans
                </button>
            </div>

            <div className="evidence-content">
                {!hasData ? (
                    <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: '13px' }}>
                        No data available
                    </div>
                ) : (
                    <>
                        {activeTab === 'visuals' && (
                            <div>
                                {charts.map((c, i) => (
                                    <div key={i} className="card">
                                        <div className="card-title">
                                            <span>{c.title}</span>
                                        </div>
                                        <img
                                            src={`http://localhost:8000/${c.file}`}
                                            alt="chart"
                                            className="insight-img"
                                        />
                                    </div>
                                ))}
                            </div>
                        )}

                        {activeTab === 'tables' && (
                            <div>
                                {tables.map((tbl, i) => (
                                    <div key={i} className="card">
                                        <div className="card-title">
                                            <span>{tbl.source}</span>
                                        </div>
                                        <div style={{ overflowX: 'auto' }}>
                                            <table className="clean-table">
                                                <thead>
                                                    <tr>
                                                        {tbl.columns?.map((col, j) => (
                                                            <th key={j}>{col}</th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {tbl.data?.slice(0, 5).map((row, j) => (
                                                        <tr key={j}>
                                                            {tbl.columns?.map((col, k) => (
                                                                <td key={k}>{row[col]}</td>
                                                            ))}
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {activeTab === 'scans' && (
                            <div>
                                {imgs.map((img, i) => (
                                    <div key={i} className="card">
                                        <div className="card-title">
                                            <span>Vision Analysis</span>
                                        </div>
                                        <img
                                            src={`http://localhost:8000/uploaded_docs/extracted_images/${img.split(/[\\\/]/).pop()}`}
                                            alt="scan"
                                            className="insight-img"
                                            style={{ marginBottom: '1rem' }}
                                        />
                                        <p style={{ fontSize: '13px', lineHeight: 1.5, color: 'var(--text-secondary)' }}>
                                            {descs[i]}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </>
                )}
            </div>
        </section>
    );
}
