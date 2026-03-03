import React, { useState } from 'react';
import { Download, ChevronLeft, Users, CheckCircle, XCircle, Percent } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function Dashboard({ data, onReset }) {
    const [activeTab, setActiveTab] = useState(0);

    // helper: trigger download from base64 with given filename
    const triggerDownload = (base64Data, filename) => {
        if (!base64Data) return;
        try {
            const byteString = atob(base64Data);
            const ab = new ArrayBuffer(byteString.length);
            const ia = new Uint8Array(ab);
            for (let i = 0; i < byteString.length; i++) {
                ia[i] = byteString.charCodeAt(i);
            }
            const blob = new Blob([ab], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error("Error downloading excel", err);
            alert("Failed to download Excel file.");
        }
    };

    const departments = data?.stats?.departments || [];
    const activeDept = departments[activeTab];

    const chartData = [
        { name: 'Passed', count: activeDept?.passed || 0, fill: '#4ade80' },
        { name: 'Failed', count: activeDept?.failed || 0, fill: '#f87171' }
    ];

    const subjectData = activeDept?.subjectStats || [];

    return (
        <div className="dashboard-container action-enter">
            <header className="dashboard-header">
                <div className="dashboard-header-left">
                    <button className="back-btn" onClick={onReset} title="Upload New PDF">
                        <ChevronLeft size={20} />
                        Back
                    </button>
                    <h2 className="title dashboard-title">Analytics</h2>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className="analyze-btn download-btn" onClick={() => {
                        const dateStr = new Date().toISOString().split('T')[0];
                        triggerDownload(data.excelBase64, `KTU_Results_${dateStr}.xlsx`);
                    }} style={{ width: 'auto' }}>
                        <Download size={18} />
                        Download Excel
                    </button>
                    {data?.supplementaryExcelBase64 && (
                        <button className="analyze-btn download-btn" onClick={() => {
                            const dateStr = new Date().toISOString().split('T')[0];
                            triggerDownload(data.supplementaryExcelBase64, `KTU_Supplementary_${dateStr}.xlsx`);
                        }} style={{ width: 'auto' }}>
                            <Download size={18} />
                            Download Supplementary
                        </button>
                    )}
                </div>
            </header>

            {data?.supplementaryCount ? (
                <div className="supplementary-note" style={{ padding: '0 1rem 0.5rem', color: '#fbbf24' }}>
                    {data.supplementaryCount} supplementary student{data.supplementaryCount > 1 ? 's' : ''} were excluded from the regular analysis.
                </div>
            ) : null}

            <div className="dashboard-tabs">
                {departments.map((dept, idx) => (
                    <button
                        key={idx}
                        className={`tab-btn ${activeTab === idx ? 'active' : ''}`}
                        onClick={() => setActiveTab(idx)}
                    >
                        {dept.name}
                    </button>
                ))}
            </div>

            {activeDept && (
                <div className="dashboard-content">
                    <div className="stats-grid">
                        <div className="stat-card">
                            <div className="stat-icon-wrapper total-students">
                                <Users size={24} />
                            </div>
                            <div className="stat-info">
                                <h3>Total Students</h3>
                                <p className="stat-value">{activeDept.total}</p>
                            </div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-icon-wrapper passed-students">
                                <CheckCircle size={24} />
                            </div>
                            <div className="stat-info">
                                <h3>Passed</h3>
                                <p className="stat-value">{activeDept.passed}</p>
                            </div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-icon-wrapper failed-students">
                                <XCircle size={24} />
                            </div>
                            <div className="stat-info">
                                <h3>Failed</h3>
                                <p className="stat-value">{activeDept.failed}</p>
                            </div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-icon-wrapper pass-perc">
                                <Percent size={24} />
                            </div>
                            <div className="stat-info">
                                <h3>Pass Rate</h3>
                                <p className="stat-value">{activeDept.passPercentage}%</p>
                            </div>
                        </div>
                    </div>

                    <div className="charts-grid">
                        <div className="chart-container">
                            <h3 className="chart-title">Overall Result Distribution</h3>
                            <div className="chart-wrapper">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                                        <XAxis dataKey="name" stroke="var(--text-muted)" tick={{ fill: 'var(--text-secondary)' }} />
                                        <YAxis stroke="var(--text-muted)" allowDecimals={false} tick={{ fill: 'var(--text-secondary)' }} />
                                        <Tooltip
                                            cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                            contentStyle={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-primary)', borderRadius: '8px' }}
                                            itemStyle={{ color: 'var(--text-primary)', fontWeight: 'bold' }}
                                        />
                                        <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={60} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        <div className="chart-container">
                            <h3 className="chart-title">Subject-wise Performance</h3>
                            <div className="chart-wrapper">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart
                                        data={subjectData}
                                        margin={{ top: 20, right: 30, left: 0, bottom: 20 }}
                                    >
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                                        <XAxis
                                            dataKey="subject"
                                            stroke="var(--text-muted)"
                                            tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                                            angle={-45}
                                            textAnchor="end"
                                            height={60}
                                        />
                                        <YAxis stroke="var(--text-muted)" allowDecimals={false} tick={{ fill: 'var(--text-secondary)' }} />
                                        <Tooltip
                                            cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                            contentStyle={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-primary)', borderRadius: '8px' }}
                                        />
                                        <Legend wrapperStyle={{ paddingTop: '20px' }} />
                                        <Bar dataKey="passed" name="Passed" fill="#4ade80" radius={[4, 4, 0, 0]} />
                                        <Bar dataKey="failed" name="Failed" fill="#f87171" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
