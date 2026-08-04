import React, { useState } from 'react';

// Modern CSS Glassmorphic Styling
const styles = `
  .app-container { display: flex; flex-direction: column; min-height: 100vh; background: #0b0f19; color: #f9fafb; }
  .header { display: flex; align-items: center; justify-content: space-between; padding: 1rem 2rem; border-bottom: 1px solid #1f2937; background: #111827; }
  .logo { font-size: 1.25rem; font-weight: 700; background: linear-gradient(135deg, #6366f1, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .nav { display: flex; gap: 1.5rem; }
  .nav-btn { background: none; border: none; color: #9ca3af; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; font-size: 0.875rem; font-weight: 500; transition: all 0.2s; }
  .nav-btn.active { color: #f9fafb; background: #1f2937; border: 1px solid #374151; }
  .nav-btn:hover { color: #f9fafb; }
  .main-content { padding: 2rem; flex: 1; max-width: 1280px; margin: 0 auto; width: 100%; box-sizing: border-box; }
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin-bottom: 2rem; }
  .card { background: #111827; border: 1px solid #1f2937; border-radius: 0.75rem; padding: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
  .metric-label { font-size: 0.875rem; color: #9ca3af; margin-bottom: 0.5rem; }
  .metric-value { font-size: 1.75rem; font-weight: 700; color: #f9fafb; }
  .metric-change { font-size: 0.75rem; color: #10b981; margin-top: 0.25rem; }
  .badge { display: inline-block; padding: 0.25rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
  .badge-success { background: rgba(16, 185, 129, 0.15); color: #10b981; }
  .badge-warning { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
  .badge-purple { background: rgba(99, 102, 241, 0.15); color: #818cf8; }
  .table { width: 100%; border-collapse: collapse; text-align: left; }
  .table th { padding: 0.75rem 1rem; color: #9ca3af; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; border-bottom: 1px solid #1f2937; }
  .table td { padding: 1rem; border-bottom: 1px solid #1f2937; font-size: 0.875rem; }
  .btn { background: #6366f1; color: white; border: none; padding: 0.5rem 1rem; border-radius: 0.375rem; font-size: 0.875rem; font-weight: 500; cursor: pointer; }
  .btn:hover { background: #4f46e5; }
  .code-block { background: #0b0f19; border: 1px solid #1f2937; border-radius: 0.375rem; padding: 1rem; font-family: monospace; font-size: 0.8125rem; overflow-x: auto; color: #a7f3d0; }
  .waterfall-bar { height: 8px; border-radius: 4px; background: linear-gradient(90deg, #6366f1, #a855f7); }
`;

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'workflows' | 'traces' | 'evals' | 'models' | 'settings'>('dashboard');

  return (
    <div className="app-container">
      <style>{styles}</style>
      
      {/* Top Navigation */}
      <header className="header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div className="logo">⚡ VORTEX</div>
          <span className="badge badge-purple">v1.0.0</span>
          <span className="badge badge-success">● System Operational</span>
        </div>
        <nav className="nav">
          <button className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>Dashboard</button>
          <button className={`nav-btn ${activeTab === 'workflows' ? 'active' : ''}`} onClick={() => setActiveTab('workflows')}>Workflows</button>
          <button className={`nav-btn ${activeTab === 'traces' ? 'active' : ''}`} onClick={() => setActiveTab('traces')}>OTel Traces</button>
          <button className={`nav-btn ${activeTab === 'evals' ? 'active' : ''}`} onClick={() => setActiveTab('evals')}>Evaluations</button>
          <button className={`nav-btn ${activeTab === 'models' ? 'active' : ''}`} onClick={() => setActiveTab('models')}>Model Gateway</button>
          <button className={`nav-btn ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>Settings</button>
        </nav>
      </header>

      {/* Main View Router */}
      <main className="main-content">
        {activeTab === 'dashboard' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2>Execution Engine Dashboard</h2>
              <button className="btn">+ New Workflow Run</button>
            </div>

            <div className="grid-4">
              <div className="card">
                <div className="metric-label">Total Workflow Runs</div>
                <div className="metric-value">1,428</div>
                <div className="metric-change">↑ 12% vs last week</div>
              </div>
              <div className="card">
                <div className="metric-label">Execution Latency (p95)</div>
                <div className="metric-value">420 ms</div>
                <div className="metric-change">↓ 35ms platform overhead</div>
              </div>
              <div className="card">
                <div className="metric-label">Semantic Cache Hit Rate</div>
                <div className="metric-value">94.8%</div>
                <div className="metric-change">Saved $142.50 in LLM API fees</div>
              </div>
              <div className="card">
                <div className="metric-label">Total Token Cost</div>
                <div className="metric-value">$18.42</div>
                <div className="metric-change">Budget: $100.00 / month</div>
              </div>
            </div>

            <div className="card">
              <h3 style={{ marginTop: 0, marginBottom: '1rem' }}>Active Execution Queues & Workers</h3>
              <table className="table">
                <thead>
                  <tr>
                    <th>Worker ID</th>
                    <th>Stream Queue</th>
                    <th>Status</th>
                    <th>Processed Jobs</th>
                    <th>Avg Processing Time</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>worker-node-01</code></td>
                    <td><code>vortex:tasks:default</code></td>
                    <td><span className="badge badge-success">ACTIVE</span></td>
                    <td>842</td>
                    <td>145 ms</td>
                  </tr>
                  <tr>
                    <td><code>worker-node-02</code></td>
                    <td><code>vortex:tasks:default</code></td>
                    <td><span className="badge badge-success">ACTIVE</span></td>
                    <td>586</td>
                    <td>152 ms</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'workflows' && (
          <div>
            <h2>Workflow Runs & Execution Timeline</h2>
            <div className="card" style={{ marginBottom: '1.5rem' }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Run ID</th>
                    <th>Workflow Name</th>
                    <th>Status</th>
                    <th>Tokens</th>
                    <th>Cost (USD)</th>
                    <th>Created At</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>8f278669-c875...</code></td>
                    <td>hitl-approval-workflow</td>
                    <td><span className="badge badge-success">COMPLETED</span></td>
                    <td>1,840</td>
                    <td>$0.0124</td>
                    <td>Just now</td>
                  </tr>
                  <tr>
                    <td><code>37ad10cb-6216...</code></td>
                    <td>research-summary-agent</td>
                    <td><span className="badge badge-warning">AWAITING_APPROVAL</span></td>
                    <td>2,450</td>
                    <td>$0.0182</td>
                    <td>2 mins ago</td>
                  </tr>
                  <tr>
                    <td><code>58cb1105-1329...</code></td>
                    <td>rag-quality-eval-pipeline</td>
                    <td><span className="badge badge-success">COMPLETED</span></td>
                    <td>920</td>
                    <td>$0.0045</td>
                    <td>15 mins ago</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="card">
              <h3>Node Inspector & Payload State</h3>
              <div className="code-block">
{`{
  "run_id": "8f278669-c875-4101-8bf5-215d57ec94fe",
  "status": "COMPLETED",
  "nodes": {
    "human1": { "status": "approved", "feedback": "Approved by Ops" },
    "deploy": { "status": "success", "artifact": "vortex-v1.0.0-tar.gz" }
  },
  "total_tokens": 1840,
  "total_cost_usd": 0.0124
}`}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'traces' && (
          <div>
            <h2>OpenTelemetry Distributed Tracing</h2>
            <div className="card">
              <h3>Root Span: <code>workflow.execute (research-summary-agent)</code></h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                    <span>Node: <code>input_guardrail</code></span>
                    <span>12 ms (Pass)</span>
                  </div>
                  <div className="waterfall-bar" style={{ width: '5%' }}></div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                    <span>Node: <code>semantic_cache_lookup</code></span>
                    <span>4 ms (Hit - 0.98 similarity)</span>
                  </div>
                  <div className="waterfall-bar" style={{ width: '3%', background: '#10b981' }}></div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                    <span>Node: <code>llm_generate (openai/gpt-4o)</code></span>
                    <span>320 ms (1,840 tokens)</span>
                  </div>
                  <div className="waterfall-bar" style={{ width: '70%' }}></div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                    <span>Node: <code>eval_faithfulness</code></span>
                    <span>45 ms (Score: 0.94)</span>
                  </div>
                  <div className="waterfall-bar" style={{ width: '15%' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'evals' && (
          <div>
            <h2>Evaluation Engine & Quality Benchmarks</h2>
            <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
              <div className="card">
                <div className="metric-label">Faithfulness Score</div>
                <div className="metric-value">0.94</div>
                <div className="metric-change">Threshold: 0.70 (PASSED)</div>
              </div>
              <div className="card">
                <div className="metric-label">Answer Relevance</div>
                <div className="metric-value">0.91</div>
                <div className="metric-change">Threshold: 0.70 (PASSED)</div>
              </div>
              <div className="card">
                <div className="metric-label">Toxicity Safety</div>
                <div className="metric-value">1.00</div>
                <div className="metric-change">Zero violations detected</div>
              </div>
              <div className="card">
                <div className="metric-label">Regression Tests</div>
                <div className="metric-value">100%</div>
                <div className="metric-change">12 / 12 test suites passing</div>
              </div>
            </div>

            <div className="card">
              <h3>Registered Evaluation Datasets</h3>
              <table className="table">
                <thead>
                  <tr>
                    <th>Dataset Name</th>
                    <th>Target Node</th>
                    <th>Scorer</th>
                    <th>Threshold</th>
                    <th>Last Score</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>faithfulness_v1</td>
                    <td>synthesize_node</td>
                    <td>FaithfulnessScorer</td>
                    <td>0.80</td>
                    <td><span className="badge badge-success">0.94</span></td>
                  </tr>
                  <tr>
                    <td>relevance_v1</td>
                    <td>summarize_node</td>
                    <td>RelevanceScorer</td>
                    <td>0.75</td>
                    <td><span className="badge badge-success">0.91</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'models' && (
          <div>
            <h2>Model Gateway & Failover Chains</h2>
            <div className="card">
              <table className="table">
                <thead>
                  <tr>
                    <th>Provider</th>
                    <th>Model Identifier</th>
                    <th>Input $/1M</th>
                    <th>Output $/1M</th>
                    <th>Circuit Breaker</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>OpenAI</td>
                    <td><code>openai/gpt-4o</code></td>
                    <td>$2.50</td>
                    <td>$10.00</td>
                    <td><span className="badge badge-success">CLOSED (Healthy)</span></td>
                  </tr>
                  <tr>
                    <td>Anthropic</td>
                    <td><code>anthropic/claude-3-5-sonnet</code></td>
                    <td>$3.00</td>
                    <td>$15.00</td>
                    <td><span className="badge badge-success">CLOSED (Healthy)</span></td>
                  </tr>
                  <tr>
                    <td>Google</td>
                    <td><code>google/gemini-1.5-pro</code></td>
                    <td>$1.25</td>
                    <td>$5.00</td>
                    <td><span className="badge badge-success">CLOSED (Healthy)</span></td>
                  </tr>
                  <tr>
                    <td>Local LLM</td>
                    <td><code>local/llama-3.1-8b</code></td>
                    <td>$0.00</td>
                    <td>$0.00</td>
                    <td><span className="badge badge-purple">LOCAL</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div>
            <h2>System Settings & API Keys</h2>
            <div className="card">
              <h3>Active API Keys</h3>
              <table className="table" style={{ marginBottom: '1.5rem' }}>
                <thead>
                  <tr>
                    <th>Key Prefix</th>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Rate Limit (RPM)</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>vx-live-9f2b8a...</code></td>
                    <td>Production Master Key</td>
                    <td><span className="badge badge-purple">owner</span></td>
                    <td>1,200</td>
                    <td><span className="badge badge-success">ACTIVE</span></td>
                  </tr>
                  <tr>
                    <td><code>vx-test-147a3c...</code></td>
                    <td>Staging Test Key</td>
                    <td><span className="badge badge-purple">member</span></td>
                    <td>300</td>
                    <td><span className="badge badge-success">ACTIVE</span></td>
                  </tr>
                </tbody>
              </table>

              <button className="btn">+ Generate New API Key</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
