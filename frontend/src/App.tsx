import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertCircle, ArrowDownToLine, BookOpen, Check, ChevronDown, CircleHelp, FileCheck2,
  FileText, FolderOpen, LoaderCircle, MessageSquareText, RefreshCw, Search, ShieldCheck,
  SlidersHorizontal, Sparkles, Trash2, Upload, X,
} from 'lucide-react';

type Doc = { id: string; name: string; format: string; created_at: string; state: string; sha256: string };
type Block = { id: string; text: string; start: number; end: number; page: number | null; kind: 'paragraph' | 'heading'; location: string };
type DocDetail = Doc & { extraction_revision?: number; text: string; blocks: Block[]; warnings: string[] };
type Issue = { playbook_guidance?: { acceptable_alternatives: string[]; fallback_language: string | null }; id: string; rule_id: string; severity: 'high' | 'medium' | 'low'; category: string; observed_language: string | null; absence: boolean; source_anchor: Block | null; explanation: string; preferred_position: string; negotiating_response: string; status: 'unresolved' | 'accepted' | 'rejected'; notes: string; confidence: 'OBJECTIVE' | 'NEEDS_REVIEW'; origin: 'deterministic' | 'ai' };
type Check = { rule_id: string; category: string; outcome: 'COMPLIANT' | 'ISSUE' | 'NEEDS_REVIEW' | 'NOT_APPLICABLE'; properties: Record<string, unknown> };
type Review = { verification_warning?: string | null; id: string; document_id: string; playbook_id: string; playbook_name: string; created_at: string; issues: Issue[]; checks: Check[]; ai_status: string; ai_error: string | null; playbook_snapshot: object };
type Playbook = { id: string; name: string; version: string; description: string; yaml?: string };
type Health = { extraction_revision: number; status: string; ai_configured: boolean; retention_days: number; max_upload_bytes: number };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json() as { detail?: unknown };
      if (Array.isArray(body.detail)) detail = body.detail.map((item) => typeof item === 'string' ? item : item?.msg ?? JSON.stringify(item)).join('; ');
      else if (typeof body.detail === 'string') detail = body.detail;
    } catch { /* Keep the useful HTTP status when the body is not JSON. */ }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

function dateLabel(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}
function formatBytes(value: number) { return value < 1024 * 1024 ? `${Math.round(value / 1024)} KB` : `${(value / (1024 * 1024)).toFixed(1)} MB`; }
function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string>('');
  const [detail, setDetail] = useState<DocDetail | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [review, setReview] = useState<Review | null>(null);
  const [selectedPlaybook, setSelectedPlaybook] = useState('');
  const [activeTab, setActiveTab] = useState<'issues' | 'checks' | 'source'>('issues');
  const [query, setQuery] = useState('');
  const [severity, setSeverity] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [selectedIssue, setSelectedIssue] = useState('');
  const [playbookModal, setPlaybookModal] = useState(false);
  const [editingPlaybookId, setEditingPlaybookId] = useState('');
  const [playbookText, setPlaybookText] = useState('');
  const [playbookError, setPlaybookError] = useState('');
  const [consent, setConsent] = useState(false);
  const [provider, setProvider] = useState('');
  const [model, setModel] = useState('');
  const [maxTokens, setMaxTokens] = useState('1024');
  const [maxCost, setMaxCost] = useState('0.05');

  useEffect(() => { setConsent(false); }, [selectedDoc, review?.id, model, provider]);

  const refresh = useCallback(async () => {
    setError('');
    try {
      const [h, docs, books] = await Promise.all([api<Health>('/health'), api<Doc[]>('/documents'), api<Playbook[]>('/playbooks')]);
      setHealth(h); setDocuments(docs); setPlaybooks(books);
      setSelectedPlaybook((current) => books.some((book) => book.id === current) ? current : books[0]?.id ?? '');
      setSelectedDoc((current) => docs.some((doc) => doc.id === current) ? current : docs[0]?.id ?? '');
    } catch (err) { setError((err as Error).message); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  const loadDocument = useCallback(async (id: string) => {
    if (!id) { setDetail(null); setReviews([]); setReview(null); return; }
    setBusy('document'); setError('');
    try {
      const [doc, history] = await Promise.all([api<DocDetail>(`/documents/${id}`), api<Review[]>(`/documents/${id}/reviews`)]);
      setDetail(doc); setReviews(history);
      if (history.length) { const latest = await api<Review>(`/reviews/${history[0].id}`); setReview(latest); setSelectedIssue(latest.issues[0]?.id ?? ''); }
      else { setReview(null); setSelectedIssue(''); }
    } catch (err) { setError((err as Error).message); setDetail(null); }
    finally { setBusy(''); }
  }, []);
  useEffect(() => { void loadDocument(selectedDoc); }, [selectedDoc, loadDocument]);

  const upload = async (file?: File) => {
    if (!file) return;
    setBusy('upload'); setError(''); setNotice('');
    try {
      const form = new FormData(); form.append('file', file);
      const created = await api<DocDetail>('/documents', { method: 'POST', body: form });
      await refresh(); setSelectedDoc(created.id); setNotice(`${created.name} is ready for review.`);
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(''); }
  };
  const runReview = async () => {
    if (!selectedDoc || !selectedPlaybook) return;
    setBusy('review'); setError(''); setNotice('');
    try {
      const next = await api<Review>(`/documents/${selectedDoc}/reviews`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ playbook_id: selectedPlaybook }) });
      setReview(next); setSelectedIssue(next.issues[0]?.id ?? ''); setReviews((current) => [next, ...current]); setNotice('Review complete.');
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(''); }
  };
  const deleteDocument = async () => {
    if (!selectedDoc || !window.confirm('Delete this document and its local reviews? This cannot be undone.')) return;
    setBusy('delete'); setError('');
    try { await api(`/documents/${selectedDoc}`, { method: 'DELETE' }); setDetail(null); setReview(null); await refresh(); setNotice('Document and associated review data deleted.'); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(''); }
  };
  const openReview = async (id: string) => {
    setBusy('review-load'); setError('');
    try { const next = await api<Review>(`/reviews/${id}`); setReview(next); setSelectedIssue(next.issues[0]?.id ?? ''); setActiveTab('issues'); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(''); }
  };
  const updateIssue = async (issue: Issue, update: Partial<Pick<Issue, 'status' | 'notes'>>) => {
    if (!review) return;
    try {
      const saved = await api<Issue>(`/reviews/${review.id}/issues/${issue.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: update.status ?? issue.status, notes: update.notes ?? issue.notes }) });
      setReview((current) => current ? { ...current, issues: current.issues.map((item) => item.id === saved.id ? saved : item) } : current);
      setNotice('Reviewer update saved locally.'); setError('');
    } catch (err) { setError((err as Error).message); }
  };
  const download = async (url: string, filename: string) => {
    try {
      const response = await fetch(`/api${url}`);
      if (!response.ok) throw new Error(`Download failed (${response.status})`);
      const blob = await response.blob(); const objectUrl = URL.createObjectURL(blob); const anchor = document.createElement('a');
      anchor.href = objectUrl; anchor.download = filename; document.body.append(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(objectUrl);
    } catch (err) { setError((err as Error).message); }
  };
  const runAi = async () => {
    if (!review || !consent || !model.trim()) { setError('Choose a model and confirm external transmission before starting AI assistance.'); return; }
    setBusy('ai'); setError(''); setNotice('');
    try { const next = await api<Review>(`/reviews/${review.id}/ai`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ consent, model: model.trim(), provider, max_output_tokens: Number(maxTokens), max_cost_usd: Number(maxCost) }) }); setReview(next); setNotice('AI-assisted interpretation returned. Verify every cited passage in the source panel.'); }
    catch (err) { setError((err as Error).message); try { setReview(await api<Review>(`/reviews/${review.id}`)); } catch { /* Keep original provider error visible. */ } }
    finally { setBusy(''); setConsent(false); }
  };
  const editPlaybook = async (id: string) => {
    setBusy('playbook-load'); setPlaybookError('');
    try { const book = await api<Playbook>(`/playbooks/${id}`); setEditingPlaybookId(id); setPlaybookText(book.yaml ?? ''); setPlaybookModal(true); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(''); }
  };
  const savePlaybook = async () => {
    setBusy('playbook-save'); setPlaybookError('');
    try {
      const saved = await api<Playbook>(editingPlaybookId ? `/playbooks/${editingPlaybookId}` : '/playbooks', { method: editingPlaybookId ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ yaml: playbookText }) });
      await refresh(); setSelectedPlaybook(saved.id); setPlaybookModal(false); setNotice(`Playbook “${saved.name}” saved.`);
    } catch (err) { setPlaybookError((err as Error).message); }
    finally { setBusy(''); }
  };
  const duplicatePlaybook = async () => {
    if (!selectedPlaybook) return;
    try { const created = await api<Playbook>(`/playbooks/${selectedPlaybook}/duplicate`, { method: 'POST' }); await refresh(); await editPlaybook(created.id); }
    catch (err) { setError((err as Error).message); }
  };
  const importPlaybook = async (file?: File) => {
    if (!file) return;
    try { setPlaybookText(await file.text()); setEditingPlaybookId(''); setPlaybookModal(true); setPlaybookError(''); }
    catch (err) { setPlaybookError((err as Error).message); }
  };

  const issues = review?.issues ?? [];
  const visibleIssues = useMemo(() => issues.filter((issue) => (severity === 'all' || issue.severity === severity) && (statusFilter === 'all' || issue.status === statusFilter) && `${issue.rule_id} ${issue.category} ${issue.explanation} ${issue.observed_language ?? ''}`.toLowerCase().includes(query.toLowerCase())), [issues, severity, statusFilter, query]);
  const focusedIssue = issues.find((issue) => issue.id === selectedIssue) ?? visibleIssues[0];
  const grouped = visibleIssues.reduce<Record<string, Issue[]>>((acc, issue) => { (acc[issue.severity] ??= []).push(issue); return acc; }, {});
  const format = (detail?.format ?? '').toUpperCase();
  const maxUpload = health ? formatBytes(health.max_upload_bytes) : '—';

  return <div className="app-shell">
    <header className="topbar">
      <a href="#main" className="brand" aria-label="Clause Review Workbench home"><span className="brand-icon"><FileCheck2 size={21} /></span><span><strong>Clause Review</strong><small>WORKBENCH</small></span></a>
      <div className="topbar-right"><span className="privacy-chip"><ShieldCheck size={15} /> Local by default</span><span className={`health-dot ${health ? 'online' : ''}`} aria-label={health ? 'Backend connected' : 'Checking connection'} /><span className="health-text">{health ? 'Workspace ready' : 'Connecting'}</span><button className="icon-button" onClick={() => void refresh()} aria-label="Refresh workspace" title="Refresh"><RefreshCw size={17} /></button></div>
    </header>
    <main id="main" className="workspace">
      <aside className="sidebar" aria-label="Document library">
        <div className="side-heading"><div><span className="eyebrow">WORKSPACE</span><h1>Document library</h1></div><span className="count-badge">{documents.length}</span></div>
        <label className={`upload-box ${busy === 'upload' ? 'is-busy' : ''}`}>
          <input type="file" accept=".docx,.pdf,.txt,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => { void upload(event.target.files?.[0]); event.currentTarget.value = ''; }} disabled={busy === 'upload'} />
          {busy === 'upload' ? <LoaderCircle className="spin" size={21} /> : <Upload size={21} />}<strong>{busy === 'upload' ? 'Processing document…' : 'Upload a contract'}</strong><span>DOCX, text PDF, or TXT · up to {maxUpload}</span>
        </label>
        <div className="library-label"><span>YOUR DOCUMENTS</span><span>{documents.length} total</span></div>
        <div className="doc-list">{documents.length ? documents.map((doc) => <button key={doc.id} className={`doc-row ${selectedDoc === doc.id ? 'selected' : ''}`} onClick={() => setSelectedDoc(doc.id)}>
          <span className={`file-icon ${doc.format}`}><FileText size={18} /></span><span className="doc-copy"><strong title={doc.name}>{doc.name}</strong><small><span className="state-mark" /> Ready <i>·</i> {doc.format.toUpperCase()}</small></span><ChevronDown className="doc-chevron" size={15} />
        </button>) : <div className="empty-library"><FolderOpen size={23} /><strong>No documents yet</strong><span>Upload a contract to begin a private review.</span></div>}</div>
        <div className="sidebar-bottom"><div className="local-card"><ShieldCheck size={17} /><div><strong>Private workspace</strong><span>Documents stay on this device unless you choose AI assistance.</span></div></div><div className="retention-note">Local retention: {health ? (health.retention_days > 0 ? `${health.retention_days} days` : "Until you delete") : '—'}</div></div>
      </aside>

      <section className="main-panel">
        <div className="page-head"><div><div className="breadcrumb"><span>Workspace</span><span>/</span><strong>{detail?.name ?? 'Review workbench'}</strong></div><h2>{detail?.name ?? 'Review workbench'}</h2><p>{detail ? `${format} document · added ${dateLabel(detail.created_at)}` : 'DOCX, text-based PDF, or UTF-8 text'}</p></div>
          {detail && <div className="head-actions"><a className="button button-quiet" href={`/api/documents/${detail.id}/original`} target="_blank" rel="noreferrer"><FileText size={16} /> Open original</a><button className="button button-danger-quiet" onClick={() => void deleteDocument()} disabled={!!busy}><Trash2 size={16} /> Delete</button></div>}
        </div>
        {error && <div className="alert alert-error" role="alert"><AlertCircle size={17} /><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><X size={15} /></button></div>}
        {detail && health && detail.extraction_revision !== health.extraction_revision && <div className="alert alert-error" role="alert">This upload predates the current extraction checks. Download and re-upload the original before reviewing.</div>}
        {review?.verification_warning && <div className="alert alert-error" role="alert">{review.verification_warning}</div>}
        {notice && <div className="alert alert-success" role="status"><Check size={17} /><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss notice"><X size={15} /></button></div>}
        {!detail ? <div className="empty-workspace"><h3>No document selected</h3><p>Upload a DOCX, text-based PDF, or UTF-8 text file.</p></div> : <>
          <div className="summary-strip"><div className="summary-item"><span className="summary-icon"><BookOpen size={17} /></span><div><small>ACTIVE PLAYBOOK</small><strong>{playbooks.find((book) => book.id === selectedPlaybook)?.name ?? 'Choose a playbook'}</strong></div></div><div className="playbook-picker"><label htmlFor="playbook-select">Review against</label><select id="playbook-select" value={selectedPlaybook} onChange={(e) => setSelectedPlaybook(e.target.value)}>{playbooks.map((book) => <option key={book.id} value={book.id}>{book.name} · v{book.version}</option>)}</select></div><button className="button button-primary run-button" onClick={() => void runReview()} disabled={!selectedPlaybook || !!busy || (!!health && detail.extraction_revision !== health.extraction_revision)}><Sparkles size={16} />{busy === 'review' ? 'Reviewing…' : 'Run review'}</button></div>
          <div className="tabbar" role="tablist" aria-label="Review views"><button role="tab" aria-selected={activeTab === 'issues'} className={activeTab === 'issues' ? 'active' : ''} onClick={() => setActiveTab('issues')}><AlertCircle size={16} /> Findings {review && <span>{review.issues.length}</span>}</button><button role="tab" aria-selected={activeTab === 'checks'} className={activeTab === 'checks' ? 'active' : ''} onClick={() => setActiveTab('checks')}><Activity size={16} /> Rule checks {review && <span>{review.checks.length}</span>}</button><button role="tab" aria-selected={activeTab === 'source'} className={activeTab === 'source' ? 'active' : ''} onClick={() => setActiveTab('source')}><FileText size={16} /> Extracted source <span>{detail.blocks.length}</span></button><div className="tab-spacer" />{review && <div className="export-menu"><label htmlFor="export-select" className="sr-only">Export review</label><select id="export-select" value="" onChange={(e) => { if (e.target.value && review) void download(`/reviews/${review.id}/export?format=${e.target.value}`, `review-${review.id}.${e.target.value === 'markdown' ? 'md' : e.target.value}`); e.target.value = ''; }}><option value="">Export report…</option><option value="markdown">Markdown</option><option value="docx">DOCX</option><option value="json">JSON</option></select><ArrowDownToLine size={15} /></div>}</div>
          {detail.warnings.length > 0 && <div className="warning-strip"><AlertCircle size={16} /><div><strong>Extraction notes</strong>{detail.warnings.map((warning, index) => <span key={index}>{warning}</span>)}</div></div>}
          {!review ? (activeTab === 'source' ? <SourcePanel detail={detail} /> : <div className="empty-review"><div className="empty-symbol"><SlidersHorizontal size={22} /></div><h3>No review yet</h3><p>Select a playbook and run review.</p><span><ShieldCheck size={15} /> Deterministic review works without external AI.</span></div>) : <>
            {activeTab === 'issues' && <div className="review-layout"><div className="issue-column"><div className="review-meta"><div><span className="eyebrow">REVIEW RESULTS</span><strong>{review.playbook_name}</strong><small>{dateLabel(review.created_at)} · {issues.length} findings</small></div><span className={`ai-badge ${review.ai_status.toLowerCase().includes('complete') || review.ai_status.toLowerCase().includes('success') ? 'ai-done' : ''}`}><span /> {review.ai_status || 'Offline review'}</span></div>
              <div className="filters"><label className="searchbox"><Search size={16} /><input placeholder="Search findings" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search findings" /></label><label className="filter-select"><span className="sr-only">Filter by severity</span><select value={severity} onChange={(e) => setSeverity(e.target.value)}><option value="all">All severity</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label><label className="filter-select"><span className="sr-only">Filter by reviewer status</span><select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="all">All status</option><option value="unresolved">Unresolved</option><option value="accepted">Accepted</option><option value="rejected">Rejected</option></select></label></div>
              <div className="issue-list">{visibleIssues.length ? (['high', 'medium', 'low'] as const).filter((level) => grouped[level]).map((level) => <section className="severity-group" key={level}><h3><span className={`severity-dot ${level}`} />{level} <span>{grouped[level].length}</span></h3>{grouped[level].map((issue) => <button key={issue.id} className={`issue-card ${selectedIssue === issue.id ? 'focused' : ''}`} onClick={() => { setSelectedIssue(issue.id); setActiveTab('issues'); }}><div className="issue-top"><span className={`severity-label ${issue.severity}`}>{issue.severity}</span><span className={`issue-status ${issue.status}`}>{issue.status}</span></div><strong>{issue.category}</strong><p>{issue.explanation}</p><div className="issue-footer"><span>{issue.rule_id}</span><span>{issue.confidence === 'NEEDS_REVIEW' ? 'Needs review' : 'Objective check'}</span></div></button>)}</section>) : <div className="no-results"><Search size={20} /><strong>No findings match</strong><span>Try a different search or filter.</span></div>}</div>
            </div><div className="detail-column">{focusedIssue ? <IssueDetail issue={focusedIssue} review={review} detail={detail} onUpdate={updateIssue} onOpenSource={() => setActiveTab('source')} /> : <div className="detail-empty"><CircleHelp size={21} /><span>Select a finding to inspect its evidence and reviewer details.</span></div>}<AiPanel health={health} review={review} consent={consent} setConsent={setConsent} provider={provider} setProvider={setProvider} model={model} setModel={setModel} maxTokens={maxTokens} setMaxTokens={setMaxTokens} maxCost={maxCost} setMaxCost={setMaxCost} runAi={runAi} busy={busy} /></div></div>}
            {activeTab === 'checks' && <div className="checks-panel"><div className="checks-heading"><div><span className="eyebrow">DETERMINISTIC ASSESSMENT</span><h3>Rule checks</h3></div><span className="check-count">{review.checks.length} checks</span></div>{review.checks.length ? <div className="check-table-wrap"><table className="check-table"><thead><tr><th>Clause category</th><th>Rule</th><th>Outcome</th><th>Observed properties</th></tr></thead><tbody>{review.checks.map((check, index) => <tr key={`${check.rule_id}-${index}`}><td><strong>{check.category}</strong></td><td><code>{check.rule_id}</code></td><td><span className={`outcome ${check.outcome.toLowerCase()}`}>{check.outcome.replace(/_/g, ' ')}</span></td><td><Properties data={check.properties} /></td></tr>)}</tbody></table></div> : <div className="no-results"><Activity size={20} /><strong>No rule checks returned</strong></div>}</div>}
            {activeTab === 'source' && <SourcePanel detail={detail} selectedIssue={focusedIssue} />}
            <div className="history-row"><div><span className="eyebrow">REVIEW HISTORY</span><span>{reviews.length ? `${reviews.length} saved ${reviews.length === 1 ? 'review' : 'reviews'}` : 'No saved reviews'}</span></div><div className="history-actions">{reviews.map((item) => <button key={item.id} className={`history-pill ${review.id === item.id ? 'current' : ''}`} onClick={() => void openReview(item.id)}>{dateLabel(item.created_at)} <small>{item.playbook_name}</small></button>)}</div></div>
            <div className="disclaimer"><ShieldCheck size={15} /><span>Clause Review Workbench supports contract review. It does not provide legal advice or replace attorney review.</span></div>
          </>}
          <div className="playbook-tools"><div><BookOpen size={16} /><span>Playbooks</span><button onClick={() => void editPlaybook(selectedPlaybook)} disabled={!selectedPlaybook}>Edit</button><button onClick={() => void duplicatePlaybook()} disabled={!selectedPlaybook}>Duplicate</button><button onClick={() => { void api<Playbook>(`/playbooks/${selectedPlaybook}`).then((book) => { setEditingPlaybookId(''); setPlaybookText((book.yaml ?? '').replace(/name:.*\n/, 'name: Custom playbook\n')); setPlaybookError(''); setPlaybookModal(true); }).catch((err: Error) => setError(err.message)); }}>New</button></div><div><label className="import-button"><Upload size={14} /> Import YAML<input type="file" accept=".yml,.yaml,text/yaml,text/plain" onChange={(event) => { void importPlaybook(event.target.files?.[0]); event.currentTarget.value = ''; }} /></label><button onClick={() => selectedPlaybook && void download(`/playbooks/${selectedPlaybook}/export`, `${playbooks.find((book) => book.id === selectedPlaybook)?.name ?? 'playbook'}.yaml`)} disabled={!selectedPlaybook}><ArrowDownToLine size={14} /> Export YAML</button></div></div>
        </>}
      </section>
    </main>
    <footer className="app-footer"><span>Clause Review Workbench 1.0.1</span><span>Review aid only. Not legal advice; attorney review required.</span></footer>
    {playbookModal && <div className="modal-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setPlaybookModal(false); }}><section className="playbook-modal" role="dialog" aria-modal="true" aria-labelledby="playbook-title"><header><div><span className="eyebrow">PLAYBOOK MANAGER</span><h2 id="playbook-title">{editingPlaybookId ? 'Edit playbook' : 'Create playbook'}</h2></div><button className="icon-button" onClick={() => setPlaybookModal(false)} aria-label="Close"><X size={18} /></button></header><p className="modal-help">Edit or import versioned YAML rules. Save to validate the playbook against the configured schema.</p><label className="field-label" htmlFor="playbook-yaml">Playbook YAML</label><textarea id="playbook-yaml" className="yaml-editor" value={playbookText} onChange={(e) => setPlaybookText(e.target.value)} spellCheck={false} placeholder={'version: "1.0"\nname: My commercial playbook\nrules:\n  - id: confidentiality.mutuality\n    category: Confidentiality\n    ...'} /><div className="editor-meta"><span>{playbookText.split('\n').length} lines</span><span>YAML · schema validated on save</span></div>{playbookError && <div className="alert alert-error"><AlertCircle size={16} /><span>{playbookError}</span></div>}<div className="modal-actions"><button className="button button-quiet" onClick={() => setPlaybookModal(false)}>Cancel</button><button className="button button-primary" onClick={() => void savePlaybook()} disabled={!!busy || !playbookText.trim()}>{busy === 'playbook-save' ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />} Save playbook</button></div></section></div>}
  </div>;
}

function Properties({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data ?? {});
  return entries.length ? <div className="property-list">{entries.map(([key, value]) => <span key={key}><b>{key.replace(/_/g, ' ')}:</b> {typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>)}</div> : <span className="muted">No measurable properties</span>;
}
function IssueDetail({ issue, review, detail, onUpdate, onOpenSource }: { issue: Issue; review: Review; detail: DocDetail; onUpdate: (issue: Issue, update: Partial<Pick<Issue, 'status' | 'notes'>>) => Promise<void>; onOpenSource: () => void }) {
  const [notes, setNotes] = useState(issue.notes);
  useEffect(() => { setNotes(issue.notes); }, [issue.id, issue.notes]);
  return <article className="finding-detail"><div className="detail-heading"><div><span className={`severity-label ${issue.severity}`}>{issue.severity} priority</span><span className={`confidence ${issue.confidence === 'NEEDS_REVIEW' ? 'uncertain' : ''}`}>{issue.confidence === 'NEEDS_REVIEW' ? 'Needs review' : 'Objective finding'}</span></div><span className="rule-code">{issue.rule_id}</span></div><h3>{issue.category}</h3><p className="finding-explanation">{issue.explanation}</p><div className="detail-section"><h4>Observed contract language</h4>{issue.absence ? <div className="absence-note"><AlertCircle size={16} /><span>No matching provision was found. This is an absence-based finding; no contract quotation is attributed.</span></div> : issue.observed_language ? <blockquote>{issue.observed_language}</blockquote> : <div className="absence-note"><CircleHelp size={16} /><span>No exact quote was returned. Review the source before relying on this finding.</span></div>}</div><div className="detail-section"><h4>Source evidence</h4>{issue.source_anchor ? <div className="source-card"><div className="source-loc"><span>{issue.source_anchor.kind === 'heading' ? 'Heading' : 'Paragraph'} · {issue.source_anchor.location}{issue.source_anchor.page ? ` · Page ${issue.source_anchor.page}` : ''}</span><button onClick={onOpenSource}>View in source <ChevronDown size={14} /></button></div><p>{issue.source_anchor.text}</p>{issue.source_anchor.page && <a href={`/api/documents/${detail.id}/original#page=${issue.source_anchor.page}`} target="_blank" rel="noreferrer">Open original at page {issue.source_anchor.page}</a>}</div> : <div className="absence-note"><FileText size={16} /><span>{issue.absence ? 'No source passage applies to an absence-based issue.' : 'No source anchor was returned. Treat this finding as unverified.'}</span></div>}</div><div className="detail-section position-grid"><div><h4>Preferred position</h4><p>{issue.preferred_position || 'No preferred position provided.'}</p></div><div><h4>Suggested response</h4><p>{issue.negotiating_response || 'No negotiating response provided.'}</p></div></div><details className="detail-section playbook-guidance"><summary>Saved playbook alternatives and fallback</summary><p className="muted">Playbook guidance only. This is not contract text or a verified legal standard.</p><h4>Acceptable alternatives</h4>{issue.playbook_guidance?.acceptable_alternatives.length ? <ul>{issue.playbook_guidance.acceptable_alternatives.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>None specified in this review’s saved playbook.</p>}<h4>Fallback wording</h4><p>{issue.playbook_guidance?.fallback_language || "None specified in this review’s saved playbook."}</p></details><div className="detail-section reviewer-section"><h4><MessageSquareText size={15} /> Reviewer notes</h4><textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Add a note for your review team…" aria-label="Reviewer notes" /><button className="button button-small" onClick={() => void onUpdate(issue, { notes })}>Save note</button></div><div className="reviewer-actions"><span>Reviewer decision</span><button className={`decision-button ${issue.status === 'accepted' ? 'accepted' : ''}`} onClick={() => void onUpdate(issue, { status: issue.status === 'accepted' ? 'unresolved' : 'accepted' })}><Check size={15} /> Accept</button><button className={`decision-button ${issue.status === 'rejected' ? 'rejected' : ''}`} onClick={() => void onUpdate(issue, { status: issue.status === 'rejected' ? 'unresolved' : 'rejected' })}><X size={15} /> Reject</button>{issue.status !== 'unresolved' && <button className="text-button" onClick={() => void onUpdate(issue, { status: 'unresolved' })}>Clear decision</button>}</div><span className="origin-note">Finding origin: {issue.origin === 'ai' ? 'AI-assisted' : 'deterministic'} · {review.ai_status}</span></article>;
}
function SourcePanel({ detail, selectedIssue }: { detail: DocDetail; selectedIssue?: Issue }) {
  useEffect(() => {
    const anchorId = selectedIssue?.source_anchor?.id;
    if (!anchorId) return;
    const target = document.getElementById(`block-${anchorId}`);
    target?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [selectedIssue?.source_anchor?.id]);
  return <div className="source-panel"><div className="source-panel-head"><div><span className="eyebrow">EXTRACTED DOCUMENT</span><h3>Source text</h3><p>Extracted blocks preserve their own text and location. Contract content is displayed as plain text.</p></div><a className="button button-quiet" href={`/api/documents/${detail.id}/original`} target="_blank" rel="noreferrer"><FileText size={15} /> Open original</a></div>{selectedIssue?.source_anchor && <div className="focused-source"><span>Selected finding evidence</span><strong>{selectedIssue.source_anchor.location}{selectedIssue.source_anchor.page ? ` · page ${selectedIssue.source_anchor.page}` : ''}</strong><p>{selectedIssue.source_anchor.text}</p></div>}<div className="source-block-list">{detail.blocks.map((block) => <article id={`block-${block.id}`} className={`source-block ${selectedIssue?.source_anchor?.id === block.id ? 'source-highlight' : ''}`} key={block.id}><div><span className={`block-kind ${block.kind}`}>{block.kind}</span><span>{block.location}{block.page ? ` · Page ${block.page}` : ''}</span><code>{block.id}</code></div>{block.kind === 'heading' ? <h4>{block.text}</h4> : <p>{block.text}</p>}</article>)}</div></div>;
}
function AiPanel({ health, review, consent, setConsent, provider, setProvider, model, setModel, maxTokens, setMaxTokens, maxCost, setMaxCost, runAi, busy }: { health: Health | null; review: Review; consent: boolean; setConsent: (value: boolean) => void; provider: string; setProvider: (value: string) => void; model: string; setModel: (value: string) => void; maxTokens: string; setMaxTokens: (value: string) => void; maxCost: string; setMaxCost: (value: string) => void; runAi: () => void; busy: string }) {
  return <section className="ai-panel"><div className="ai-title"><span className="ai-icon"><Sparkles size={16} /></span><div><strong>AI-assisted interpretation</strong><span>Optional · external provider</span></div><span className={`ai-config ${health?.ai_configured ? 'configured' : ''}`}>{health?.ai_configured ? 'Configured' : 'Not configured'}</span></div>{review.ai_error && <div className="ai-error" role="alert"><AlertCircle size={14} />{review.ai_error}</div>}<div className="ai-fields"><label>Provider<input value={provider} onChange={(e) => setProvider(e.target.value)} placeholder="Exact OpenRouter provider name" /></label><label>Model<input value={model} onChange={(e) => setModel(e.target.value)} placeholder="e.g. provider/model-name" /></label><div className="budget-fields"><label>Max output tokens<input type="number" min="128" max="4096" value={maxTokens} onChange={(e) => setMaxTokens(e.target.value)} /></label><label>Max cost (USD)<input type="number" min="0.001" step="0.001" value={maxCost} onChange={(e) => setMaxCost(e.target.value)} /></label></div></div><label className="consent-check"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /><span>I allow contract text and playbook guidance to be sent to the selected external provider for this review.</span></label><button className="ai-run" onClick={runAi} disabled={!health?.ai_configured || !consent || !model.trim() || !provider.trim() || !!busy}>{busy === 'ai' ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />}{busy === 'ai' ? 'Requesting interpretation…' : 'Run AI assistance'}</button><small className="ai-footnote">Your API key stays in server configuration. AI output may be uncertain; verify every citation against the source.</small></section>;
}
export default App;
