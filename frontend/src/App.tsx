import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity, AlertCircle, ArrowDownToLine, BookOpen, Check, ChevronDown, CircleHelp, FileCheck2,
  FileText, FolderOpen, LoaderCircle, MessageSquareText, RefreshCw, Search, ShieldCheck,
  SlidersHorizontal, Sparkles, Trash2, Upload, X,
} from 'lucide-react';
import { SYNTHETIC_SAMPLE } from './sample';
import { RevisionComparison } from './RevisionComparison';

type Doc = { id: string; name: string; format: string; created_at: string; state: string; sha256: string; source_document_id?: string | null; previous_document_id?: string };
type Block = { id: string; text: string; start: number; end: number; page: number | null; kind: 'paragraph' | 'heading'; location: string };
type DocDetail = Doc & { extraction_revision?: number; visual_check?: { status: string; manifest_sha256: string }; image_manifest?: Array<{ page: number; bbox: [number, number, number, number]; raw_bbox_points?: [number, number, number, number]; clipped?: boolean; width: number; height: number }>; text: string; blocks: Block[]; warnings: string[] };
type Interaction = { kind: string; explanation: string; evidence: Block[]; reference?: string; status?: string };
type Issue = { interactions?: Interaction[]; playbook_guidance?: { acceptable_alternatives: string[]; fallback_language: string | null }; id: string; rule_id: string; severity: 'high' | 'medium' | 'low'; category: string; observed_language: string | null; absence: boolean; source_anchor: Block | null; explanation: string; preferred_position: string; negotiating_response: string; status: 'unresolved' | 'accepted' | 'rejected'; notes: string; confidence: 'OBJECTIVE' | 'NEEDS_REVIEW'; origin: 'deterministic' | 'ai' };
type Check = { rule_id: string; category: string; outcome: 'COMPLIANT' | 'ISSUE' | 'NEEDS_REVIEW' | 'NOT_APPLICABLE'; properties: Record<string, unknown> };
type Review = { verification_warning?: string | null; id: string; document_id: string; playbook_id: string; playbook_name: string; created_at: string; issues: Issue[]; checks: Check[]; ai_status: string; ai_error: string | null; playbook_snapshot: object };
type ReviewSummary = Pick<Review, 'id' | 'document_id' | 'playbook_id' | 'playbook_name' | 'created_at' | 'ai_status'> & { extraction_revision?: number; review_revision?: number };
type Playbook = { id: string; name: string; version: string; description: string; yaml?: string };
type PlaybookSettings = { id: string; name: string; version: string; description: string; revision: string; rules: Array<{ id: string; category: string; description: string; severity: 'high' | 'medium' | 'low'; required: boolean; preferred_position: string; negotiation_guidance: string; fallback_language: string | null }> };
type Health = { extraction_revision: number; status: string; ai_configured: boolean; retention_days: number; max_upload_bytes: number };

const ONBOARDING_KEY = 'clause-workbench:onboarding:v1';

function readOnboardingDismissed() {
  try { return window.localStorage.getItem(ONBOARDING_KEY) === 'dismissed'; }
  catch { return false; }
}

function saveOnboardingDismissed(dismissed: boolean) {
  try {
    if (dismissed) window.localStorage.setItem(ONBOARDING_KEY, 'dismissed');
    else window.localStorage.removeItem(ONBOARDING_KEY);
  } catch { /* Onboarding still works when browser storage is unavailable. */ }
}

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

function aiStatusLabel(value: string) {
  return ({ NOT_REQUESTED: 'Local review', IN_PROGRESS: 'AI request in progress', ERROR: 'AI request failed', OUTCOME_UNKNOWN: 'AI outcome unknown', VERIFIED_CITATIONS_REQUIRES_REVIEW: 'AI citations checked; review required' } as Record<string, string>)[value] ?? 'AI status unavailable';
}

function dateLabel(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}
function documentReference(id: string, documents: Doc[]) {
  let length = 8;
  while (length < id.length && documents.some(doc => doc.id !== id && doc.id.startsWith(id.slice(0, length)))) length++;
  return id.slice(0, length);
}
function formatBytes(value: number) { return value < 1024 * 1024 ? `${Math.round(value / 1024)} KB` : `${(value / (1024 * 1024)).toFixed(1)} MB`; }
function initialIssueId(issues: Issue[]) {
  const priority: Record<Issue['severity'], number> = { high: 0, medium: 1, low: 2 };
  return [...issues].sort((a, b) => priority[a.severity] - priority[b.severity])[0]?.id ?? '';
}
function issueKind(issue: Issue) {
  if (issue.absence) return 'Provision not located';
  if (issue.confidence === 'NEEDS_REVIEW') return 'Interpretation unresolved';
  if (issue.origin === 'deterministic') return 'Configured adverse wording matched';
  return 'Language identified for review';
}
function issueKindToken(issue: Issue) {
  if (issue.absence) return 'not-located';
  if (issue.confidence === 'NEEDS_REVIEW') return 'unresolved';
  if (issue.origin === 'deterministic') return 'adverse';
  return 'review';
}
function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string>('');
  const [detail, setDetail] = useState<DocDetail | null>(null);
  const [reviews, setReviews] = useState<ReviewSummary[]>([]);
  const [hasMoreDocuments, setHasMoreDocuments] = useState(false);
  const [hasMoreReviews, setHasMoreReviews] = useState(false);
  const documentLoadSequence = useRef(0);
  const reviewLoadSequence = useRef(0);
  const [review, setReview] = useState<Review | null>(null);
  const [selectedPlaybook, setSelectedPlaybook] = useState('');
  const [activeTab, setActiveTab] = useState<'issues' | 'checks' | 'source' | 'revisions'>('issues');
  const [query, setQuery] = useState('');
  const [severity, setSeverity] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [selectedIssue, setSelectedIssue] = useState('');
  const [sourceBlock, setSourceBlock] = useState('');
  const [onboardingMode, setOnboardingMode] = useState<'first-run' | 'dismissed' | 'replaying'>(() => readOnboardingDismissed() ? 'dismissed' : 'first-run');
  const uploadInput = useRef<HTMLInputElement>(null);
  const revisionInput = useRef<HTMLInputElement>(null);
  useEffect(() => { setSourceBlock(''); }, [selectedIssue, review?.id]);
  useEffect(() => {
    if (onboardingMode === 'replaying') document.getElementById('getting-started')?.scrollIntoView({ block: 'center', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }, [onboardingMode]);
  const [playbookModal, setPlaybookModal] = useState(false);
  const playbookDialog = useRef<HTMLElement>(null);
  useEffect(() => {
    const dialog = playbookDialog.current;
    if (!playbookModal || !dialog) return;
    const previousFocus = document.activeElement;
    const background = Array.from(document.querySelectorAll<HTMLElement>('.app-shell > :not(.modal-backdrop)'));
    const previousInert = background.map((element) => element.inert);
    background.forEach((element) => { element.inert = true; });
    (dialog.querySelector<HTMLElement>('.settings-form input, .settings-form select, textarea') ?? dialog.querySelector<HTMLElement>('button'))?.focus({ preventScroll: true });
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); setPlaybookModal(false); }
      if (event.key !== 'Tab') return;
      const controls = Array.from(dialog.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex="0"]'));
      const first = controls[0], last = controls[controls.length - 1];
      if (!dialog.contains(document.activeElement)) { event.preventDefault(); first?.focus(); }
      else if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    };
    // Disabling the focused Save control can move focus to the body. Keep
    // Escape/Tab handling active for that failure state as well.
    document.addEventListener('keydown', keydown);
    return () => {
      document.removeEventListener('keydown', keydown);
      background.forEach((element, index) => { element.inert = previousInert[index]; });
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus({ preventScroll: true });
    };
  }, [playbookModal]);
  const [editingPlaybookId, setEditingPlaybookId] = useState('');
  const [playbookText, setPlaybookText] = useState('');
  const [playbookSettings, setPlaybookSettings] = useState<PlaybookSettings | null>(null);
  const [selectedRuleId, setSelectedRuleId] = useState('');
  const [advancedPlaybook, setAdvancedPlaybook] = useState(false);
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
      const [h, docs, books] = await Promise.all([api<Health>('/health'), api<Doc[]>('/documents?limit=50&offset=0'), api<Playbook[]>('/playbooks')]);
      setHealth(h); setDocuments(docs); setHasMoreDocuments(docs.length === 50); setPlaybooks(books);
      setSelectedPlaybook((current) => books.some((book) => book.id === current) ? current : books[0]?.id ?? '');
      setSelectedDoc((current) => current || (docs[0]?.id ?? ''));
    } catch (err) { setError((err as Error).message); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  const loadDocument = useCallback(async (id: string) => {
    const sequence = ++documentLoadSequence.current;
    const reviewSequence = ++reviewLoadSequence.current;
    if (!id) { setDetail(null); setReviews([]); setReview(null); setHasMoreReviews(false); setBusy(''); return; }
    setBusy('document'); setError('');
    try {
      const [doc, history] = await Promise.all([api<DocDetail>(`/documents/${id}`), api<ReviewSummary[]>(`/documents/${id}/reviews?summary=true&limit=50&offset=0`)]);
      if (sequence !== documentLoadSequence.current) return;
      setDetail(doc); setReviews(history); setHasMoreReviews(history.length === 50);
      if (history.length) {
        const latest = await api<Review>(`/reviews/${history[0].id}`);
        if (sequence !== documentLoadSequence.current || reviewSequence !== reviewLoadSequence.current) return;
        setReview(latest); setSelectedIssue(initialIssueId(latest.issues)); setSelectedPlaybook(latest.playbook_id);
      } else { setReview(null); setSelectedIssue(''); }
    } catch (err) { if (sequence === documentLoadSequence.current) { setError((err as Error).message); setDetail(null); } }
    finally { if (sequence === documentLoadSequence.current && reviewSequence === reviewLoadSequence.current) setBusy(''); }
  }, []);
  useEffect(() => { void loadDocument(selectedDoc); }, [selectedDoc, loadDocument]);

  const upload = async (file?: File, previousDocumentId?: string) => {
    if (!file) return;
    setBusy('upload'); setError(''); setNotice('');
    try {
      const form = new FormData(); form.append('file', file);
      const created = await api<DocDetail>(`/documents${previousDocumentId ? `?revision_of=${encodeURIComponent(previousDocumentId)}` : ''}`, { method: 'POST', body: form });
      await refresh(); setSelectedDoc(created.id); setActiveTab(previousDocumentId ? 'revisions' : 'issues'); setNotice(created.visual_check?.status === 'NEEDS_VISUAL_CHECK' ? `${created.name} uploaded. Compare the original with extracted text before review.` : `${created.name} is ready for review.`);
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(''); }
  };
  const trySyntheticSample = () => {
    const commercial = playbooks.find((book) => book.name === 'Commercial contracts');
    if (commercial) setSelectedPlaybook(commercial.id);
    const sample = new File([SYNTHETIC_SAMPLE], 'synthetic-sample.txt', { type: 'text/plain' });
    void upload(sample);
  };
  const runReview = async () => {
    if (!selectedDoc || !selectedPlaybook || detail?.visual_check?.status === 'NEEDS_VISUAL_CHECK') return;
    const sequence = documentLoadSequence.current;
    const reviewSequence = ++reviewLoadSequence.current;
    setBusy('review'); setError(''); setNotice('');
    try {
      const next = await api<Review>(`/documents/${selectedDoc}/reviews`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ playbook_id: selectedPlaybook }) });
      if (sequence !== documentLoadSequence.current || reviewSequence !== reviewLoadSequence.current) return;
      setReview(next); setSelectedIssue(initialIssueId(next.issues)); setReviews((current) => [next, ...current]); setNotice('Review complete.');
      setOnboardingMode('dismissed'); saveOnboardingDismissed(true);
    } catch (err) { if (sequence === documentLoadSequence.current && reviewSequence === reviewLoadSequence.current) setError((err as Error).message); }
    finally { if (sequence === documentLoadSequence.current && reviewSequence === reviewLoadSequence.current) setBusy(''); }
  };
  const confirmVisualCheck = async () => {
    if (!detail?.visual_check || detail.visual_check.status !== 'NEEDS_VISUAL_CHECK' || !detail.extraction_revision) return;
    setBusy('visual-check'); setError(''); setNotice('');
    try {
      const updated = await api<DocDetail>(`/documents/${detail.id}/visual-check`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm_no_missing_text: true, original_sha256: detail.sha256, extraction_revision: detail.extraction_revision, manifest_sha256: detail.visual_check.manifest_sha256 }) });
      setDetail(updated); setNotice('Visual comparison recorded. This does not add text from images.');
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(''); }
  };
  const reprocessOriginal = async () => {
    if (!detail || busy) return;
    setBusy('reprocess'); setError(''); setNotice('');
    try {
      const created = await api<DocDetail>(`/documents/${detail.id}/reprocess`, { method: 'POST' });
      await refresh(); setSelectedDoc(created.id); setNotice(`A new extraction was created from ${detail.name}. The earlier document and its review history remain available.`);
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(''); }
  };
  const deleteDocument = async () => {
    if (!selectedDoc || !window.confirm('Delete this document and its local reviews? This cannot be undone.')) return;
    setBusy('delete'); setError('');
    try { await api(`/documents/${selectedDoc}`, { method: 'DELETE' }); setDetail(null); setReview(null); setSelectedDoc(''); await refresh(); setNotice('Document and associated review data deleted.'); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(''); }
  };
  const openReview = async (id: string) => {
    const sequence = documentLoadSequence.current;
    const reviewSequence = ++reviewLoadSequence.current;
    setBusy('review-load'); setError('');
    try { const next = await api<Review>(`/reviews/${id}`); if (sequence !== documentLoadSequence.current || reviewSequence !== reviewLoadSequence.current) return; setReview(next); setSelectedIssue(initialIssueId(next.issues)); setSelectedPlaybook(next.playbook_id); setActiveTab('issues'); }
    catch (err) { if (sequence === documentLoadSequence.current && reviewSequence === reviewLoadSequence.current) setError((err as Error).message); }
    finally { if (sequence === documentLoadSequence.current && reviewSequence === reviewLoadSequence.current) setBusy(''); }
  };
  const updateIssue = async (issue: Issue, update: Partial<Pick<Issue, 'status' | 'notes'>>) => {
    if (!review) return;
    try {
      const saved = await api<Issue>(`/reviews/${review.id}/issues/${issue.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(update) });
      setReview((current) => current?.id === review.id ? { ...current, issues: current.issues.map((item) => item.id === saved.id ? saved : item) } : current);
      setNotice('Reviewer update saved locally.'); setError('');
    } catch (err) { setError((err as Error).message); }
  };
  const loadMoreDocuments = async () => {
    if (busy || !hasMoreDocuments) return;
    setBusy('documents-more'); setError('');
    try {
      const next = await api<Doc[]>(`/documents?limit=50&offset=${documents.length}`);
      setDocuments((current) => [...current, ...next]); setHasMoreDocuments(next.length === 50);
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(''); }
  };
  const loadMoreReviews = async () => {
    if (!selectedDoc || busy || !hasMoreReviews) return;
    const sequence = documentLoadSequence.current;
    setBusy('reviews-more'); setError('');
    try {
      const next = await api<ReviewSummary[]>(`/documents/${selectedDoc}/reviews?summary=true&limit=50&offset=${reviews.length}`);
      if (sequence !== documentLoadSequence.current) return;
      setReviews((current) => [...current, ...next]); setHasMoreReviews(next.length === 50);
    } catch (err) { if (sequence === documentLoadSequence.current) setError((err as Error).message); }
    finally { if (sequence === documentLoadSequence.current) setBusy(''); }
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
    const sequence = documentLoadSequence.current;
    const reviewSequence = ++reviewLoadSequence.current;
    const isCurrent = () => sequence === documentLoadSequence.current && reviewSequence === reviewLoadSequence.current;
    setBusy('ai'); setError(''); setNotice('');
    try {
      const next = await api<Review>(`/reviews/${review.id}/ai`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ consent, model: model.trim(), provider, max_output_tokens: Number(maxTokens), max_cost_usd: Number(maxCost) }) });
      if (isCurrent()) { setReview(next); setNotice('AI-assisted interpretation returned. Verify every cited passage in the source panel.'); }
    } catch (err) {
      if (isCurrent()) {
        setError((err as Error).message);
        try { const latest = await api<Review>(`/reviews/${review.id}`); if (isCurrent()) setReview(latest); }
        catch { /* Keep original provider error visible. */ }
      }
    } finally { if (isCurrent()) { setBusy(''); setConsent(false); } }
  };
  const editPlaybook = async (id: string) => {
    setBusy('playbook-load'); setPlaybookError('');
    try {
      const [book, settings] = await Promise.all([api<Playbook>(`/playbooks/${id}`), api<PlaybookSettings>(`/playbooks/${id}/settings`)]);
      setSelectedPlaybook(id); setEditingPlaybookId(id); setPlaybookText(book.yaml ?? ''); setPlaybookSettings(settings); setSelectedRuleId(settings.rules[0]?.id ?? ''); setAdvancedPlaybook(false); setPlaybookModal(true);
    }
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
  const savePlaybookSettings = async () => {
    if (!playbookSettings) return;
    setBusy('playbook-save'); setPlaybookError('');
    try {
      const saved = await api<PlaybookSettings>(`/playbooks/${playbookSettings.id}/settings`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ revision: playbookSettings.revision, name: playbookSettings.name, version: playbookSettings.version, description: playbookSettings.description, rules: playbookSettings.rules.map(({ id, severity, required, preferred_position, negotiation_guidance, fallback_language }) => ({ id, severity, required, preferred_position, negotiation_guidance, fallback_language })) }) });
      setPlaybookSettings(saved); await refresh(); setPlaybookModal(false); setNotice(`Playbook “${saved.name}” settings saved.`);
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
    try { setPlaybookText(await file.text()); setEditingPlaybookId(''); setPlaybookSettings(null); setAdvancedPlaybook(false); setPlaybookModal(true); setPlaybookError(''); }
    catch (err) { setPlaybookError((err as Error).message); }
  };

  const issues = review?.issues ?? [];
  const visibleIssues = useMemo(() => issues.filter((issue) => (severity === 'all' || issue.severity === severity) && (statusFilter === 'all' || issue.status === statusFilter) && `${issue.rule_id} ${issue.category} ${issue.explanation} ${issue.observed_language ?? ''}`.toLowerCase().includes(query.toLowerCase())), [issues, severity, statusFilter, query]);
  const focusedIssue = issues.find((issue) => issue.id === selectedIssue) ?? visibleIssues[0];
  const grouped = visibleIssues.reduce<Record<string, Issue[]>>((acc, issue) => { (acc[issue.severity] ??= []).push(issue); return acc; }, {});
  const format = (detail?.format ?? '').toUpperCase();
  const visualCheckPending = detail?.visual_check?.status === 'NEEDS_VISUAL_CHECK';
  const maxUpload = health ? formatBytes(health.max_upload_bytes) : '—';
  const showOnboarding = (onboardingMode === 'first-run' && !review) || onboardingMode === 'replaying';

  const replayOnboarding = () => {
    setOnboardingMode('replaying'); saveOnboardingDismissed(false);
  };

  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to main content</a>
    <header className="topbar">
      <a href="#main" className="brand" aria-label="Clause Review Workbench home"><span className="brand-icon"><FileCheck2 size={21} /></span><span><strong>Clause Review</strong><small>WORKBENCH</small></span></a>
      <div className="topbar-right"><span className="privacy-chip"><ShieldCheck size={15} /> Local by default</span><span className={`health-dot ${health ? 'online' : ''}`} aria-hidden="true" /><span className="health-text" role="status">{health ? 'Workspace ready' : 'Connecting'}</span><button className="icon-button" onClick={() => void refresh()} aria-label="Refresh workspace" title="Refresh"><RefreshCw size={17} /></button></div>
    </header>
    <main id="main" className="workspace" tabIndex={-1} aria-busy={['upload', 'document', 'review', 'review-load', 'documents-more', 'reviews-more'].includes(busy)}>
      <aside className="sidebar" aria-label="Document library">
        <div className="side-heading"><div><span className="eyebrow">WORKSPACE</span><h1>Document library</h1></div><span className="count-badge">{documents.length}</span></div>
        <label className={`upload-box ${busy === 'upload' ? 'is-busy' : ''}`}>
          <input ref={uploadInput} type="file" accept=".docx,.pdf,.txt,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" aria-label="Choose a contract to upload" onChange={(event) => { void upload(event.target.files?.[0]); event.currentTarget.value = ''; }} disabled={busy === 'upload'} />
          {busy === 'upload' ? <LoaderCircle className="spin" size={21} /> : <Upload size={21} />}<strong>{busy === 'upload' ? 'Processing document…' : 'Upload a contract'}</strong><span>DOCX, searchable PDF, or TXT · up to {maxUpload}</span>
        </label>
        <div className="library-label"><span>YOUR DOCUMENTS</span><span>{hasMoreDocuments ? `${documents.length} loaded` : `${documents.length} total`}</span></div>
        <div className="doc-list">{documents.length ? documents.map((doc) => <button key={doc.id} data-document-id={doc.id} className={`doc-row ${selectedDoc === doc.id ? 'selected' : ''}`} onClick={() => setSelectedDoc(doc.id)}>
          <span className={`file-icon ${doc.format}`}><FileText size={18} /></span><span className="doc-copy"><strong title={doc.name}>{doc.name}</strong><small><span className="state-mark" /> {doc.state === 'needs_visual_check' ? 'Visual check needed' : 'Ready'} <i>·</i> {doc.format.toUpperCase()}</small><small className="doc-origin">{doc.source_document_id ? 'Reprocessed' : doc.previous_document_id ? 'Revision' : 'Uploaded'} · <time dateTime={doc.created_at}>{dateLabel(doc.created_at)}</time></small>{documents.some(other => other.id !== doc.id && other.name === doc.name) && <small className="doc-reference" title={doc.id}>Record {documentReference(doc.id, documents)}</small>}</span><ChevronDown className="doc-chevron" size={15} />
        </button>) : <div className="empty-library"><FolderOpen size={23} /><strong>No documents yet</strong><span>Upload a contract to begin a private review.</span></div>}</div>
        {hasMoreDocuments && <button className="load-more" onClick={() => void loadMoreDocuments()} disabled={!!busy}>{busy === 'documents-more' ? 'Loading documents…' : 'Load more documents'}</button>}
        <div className="sidebar-bottom"><div className="local-card"><ShieldCheck size={17} /><div><strong>Private workspace</strong><span>Documents stay on this device unless you choose AI assistance.</span></div></div><div className="retention-note">Local retention: {health ? (health.retention_days > 0 ? `${health.retention_days} ${health.retention_days === 1 ? 'day' : 'days'}` : "Until you delete") : '—'}</div></div>
      </aside>

      <section className="main-panel">
        <div className="page-head"><div><div className="breadcrumb"><span>Workspace</span><span>/</span><strong>{detail?.name ?? 'Review workbench'}</strong></div><h2>{detail?.name ?? 'Review workbench'}</h2><p>{detail ? `${format} document · added ${dateLabel(detail.created_at)}${detail.source_document_id ? ` · reprocessed from ${documents.find((doc) => doc.id === detail.source_document_id)?.name ?? 'an earlier document'}` : ''}` : 'DOCX, searchable PDF, or UTF-8 text'}</p></div>
          {detail && <div className="head-actions"><input className="sr-only" type="file" ref={revisionInput} aria-label="Choose a revised contract" accept=".txt,.pdf,.docx" disabled={!!busy} onChange={event => { void upload(event.target.files?.[0], detail.id); event.target.value = ''; }} /><button className="button button-quiet" disabled={!!busy} onClick={() => revisionInput.current?.click()}><Upload size={15} /> Upload revision</button><a className="button button-quiet" href={`/api/documents/${detail.id}/original`} target="_blank" rel="noreferrer"><FileText size={16} /> Open original</a><button className="button button-quiet" onClick={() => void reprocessOriginal()} disabled={!!busy}><RefreshCw size={15} /> Reprocess original</button><button className="button button-danger-quiet" onClick={() => void deleteDocument()} disabled={!!busy}><Trash2 size={16} /> Delete</button></div>}
        </div>
        {error && <div className="alert alert-error" role="alert"><AlertCircle size={17} /><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><X size={15} /></button></div>}
        {detail && health && detail.extraction_revision !== health.extraction_revision && <div className="alert alert-error" role="alert">This upload predates the current extraction checks. Download and re-upload the original before reviewing.</div>}
        {review?.verification_warning && <div className="alert alert-error" role="alert">{review.verification_warning}</div>}
        {notice && <div className="alert alert-success" role="status"><Check size={17} /><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss notice"><X size={15} /></button></div>}
        <span className="sr-only" role="status" aria-live="polite">{busy === 'upload' ? 'Uploading and processing contract…' : busy === 'document' ? 'Loading selected document…' : busy === 'review' ? 'Running local contract review…' : busy === 'review-load' ? 'Loading saved review…' : busy === 'documents-more' ? 'Loading more documents…' : busy === 'reviews-more' ? 'Loading more reviews…' : ''}</span>
        {showOnboarding && <GettingStarted documentName={detail?.name} hasReview={!!review} sourceCheck={visualCheckPending ? 'visual' : detail && health && detail.extraction_revision !== health.extraction_revision ? 'reprocess' : undefined} action={detail ? <><button className="button button-primary" onClick={() => void runReview()} disabled={!selectedPlaybook || !!busy || !!visualCheckPending || (!!health && detail.extraction_revision !== health.extraction_revision)}><Sparkles size={16} />{busy === 'review' ? 'Reviewing…' : review ? 'Run a new review' : 'Run local review'}</button><button className="button button-quiet" onClick={trySyntheticSample} disabled={!!busy}>Use synthetic sample</button></> : <><button className="button button-primary" onClick={() => uploadInput.current?.click()} disabled={busy === 'upload'}><Upload size={16} /> Choose a contract</button><button className="button button-quiet" onClick={trySyntheticSample} disabled={!!busy}>Use synthetic sample</button></>} onDismiss={() => { setOnboardingMode('dismissed'); saveOnboardingDismissed(true); }} />}
        {!detail ? <div className="empty-workspace"><h3>No document selected</h3><p>Upload a DOCX, searchable PDF, or UTF-8 text file. Scanned image-only PDFs need OCR and are not supported.</p></div> : <>
          <div className="summary-strip"><div className="summary-item"><span className="summary-icon"><BookOpen size={17} /></span><div><small>{review ? 'SAVED REVIEW POLICY' : 'REVIEW POLICY'}</small><strong>{review?.playbook_name ?? playbooks.find((book) => book.id === selectedPlaybook)?.name ?? 'Choose a playbook'}</strong></div></div><div className="playbook-picker"><label htmlFor="playbook-select">Review against</label><select id="playbook-select" value={selectedPlaybook} onChange={(e) => setSelectedPlaybook(e.target.value)}><option value="">Choose a playbook</option>{review && !playbooks.some((book) => book.id === review.playbook_id) && <option value={review.playbook_id} disabled>{review.playbook_name} · unavailable</option>}{playbooks.map((book) => <option key={book.id} value={book.id}>{book.name} · v{book.version}</option>)}</select>{review && <small className="policy-scope">New review only</small>}</div><button className="button button-primary run-button" onClick={() => void runReview()} disabled={!playbooks.some((book) => book.id === selectedPlaybook) || !!busy || !!visualCheckPending || (!!health && detail.extraction_revision !== health.extraction_revision)}><Sparkles size={16} />{busy === 'review' ? 'Reviewing…' : 'Run review'}</button></div>
          <div className="tabbar"><div className="tab-controls" role="tablist" aria-label="Review views" onKeyDown={(event) => { if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return; event.preventDefault(); const tabs = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]')); const current = tabs.indexOf(document.activeElement as HTMLButtonElement); const next = tabs[(current + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length]; next.focus(); next.click(); }}><button role="tab" aria-selected={activeTab === 'issues'} tabIndex={activeTab === 'issues' ? 0 : -1} className={activeTab === 'issues' ? 'active' : ''} onClick={() => setActiveTab('issues')}><AlertCircle size={16} /> Findings {review && <span>{review.issues.length}</span>}</button><button role="tab" aria-selected={activeTab === 'checks'} tabIndex={activeTab === 'checks' ? 0 : -1} className={activeTab === 'checks' ? 'active' : ''} onClick={() => setActiveTab('checks')}><Activity size={16} /> Rule checks {review && <span>{review.checks.length}</span>}</button><button role="tab" aria-selected={activeTab === 'source'} tabIndex={activeTab === 'source' ? 0 : -1} className={activeTab === 'source' ? 'active' : ''} onClick={() => setActiveTab('source')}><FileText size={16} /> Extracted source <span>{detail.blocks.length}</span></button><button role="tab" aria-selected={activeTab === 'revisions'} tabIndex={activeTab === 'revisions' ? 0 : -1} className={activeTab === 'revisions' ? 'active' : ''} onClick={() => setActiveTab('revisions')}>Revisions</button></div><div className="tab-spacer" />{review && <div className="export-menu"><label htmlFor="export-select" className="sr-only">Export review</label><select id="export-select" value="" onChange={(e) => { if (e.target.value && review) void download(`/reviews/${review.id}/export?format=${e.target.value}`, `review-${review.id}.${e.target.value === 'markdown' ? 'md' : e.target.value}`); e.target.value = ''; }}><option value="">Export report…</option><option value="markdown">Markdown</option><option value="docx">DOCX</option><option value="json">JSON</option></select><ArrowDownToLine size={15} /></div>}</div>
          {detail.warnings.filter((warning) => !visualCheckPending || !warning.startsWith('PDF contains raster images. OCR and image text checks are unsupported.')).length > 0 && <div className="warning-strip"><AlertCircle size={16} /><div><strong>Extraction notes</strong>{detail.warnings.filter((warning) => !visualCheckPending || !warning.startsWith('PDF contains raster images. OCR and image text checks are unsupported.')).map((warning, index) => <span key={index}>{warning}</span>)}</div></div>}
          {visualCheckPending && <div className="visual-check-panel" role="region" aria-labelledby="visual-check-title"><div><h3 id="visual-check-title">Compare this PDF with the extracted text</h3><p>Check every page, image region, annotation or form, and reading order against extracted text. Images are not read or OCR’d. If terms are missing or out of order, upload a corrected text-based copy. Confirm only if all contract text is present in the correct order.</p><div className="image-map-list" aria-label="Raster image locations">{Array.from(new Set(detail.image_manifest?.map((image) => image.page) ?? [])).map((page) => <div className="image-map-item" key={page}><span className="image-map-label">Page {page}</span><div className="page-map" role="img" aria-label={`Page ${page} image locations`}><span className="page-map-margin" aria-hidden="true" />{detail.image_manifest?.filter((image) => image.page === page).map((image, index) => { const [x0, y0, x1, y1] = image.bbox; return <span key={`${page}-${index}`} className={`page-map-image${image.clipped ? ' clipped' : ''}`} aria-hidden="true" style={{ left: `${Math.max(0, Math.min(1, x0)) * 100}%`, top: `${Math.max(0, Math.min(1, y0)) * 100}%`, width: `${Math.max(0, Math.min(1, x1) - Math.max(0, x0)) * 100}%`, height: `${Math.max(0, Math.min(1, y1) - Math.max(0, y0)) * 100}%` }} />; })}</div></div>)}</div>{detail.image_manifest?.some((image) => image.clipped) && <p className="crop-warning" role="note">A PDF crop cuts off part of an image. Only the visible area is marked; content outside the crop was not assessed.</p>}</div><div className="visual-check-actions"><a className="button button-quiet" href={`/api/documents/${detail.id}/original`} target="_blank" rel="noreferrer"><FileText size={15} /> Open original</a><button className="button button-primary" onClick={() => void confirmVisualCheck()} disabled={!!busy}>I checked all pages; no text is missing</button></div></div>}
          {!review ? (activeTab === 'source' ? <SourcePanel detail={detail} /> : <div className="empty-review"><div className="empty-symbol"><SlidersHorizontal size={22} /></div><h3>No review yet</h3><p>{visualCheckPending ? 'Complete the source check above before running a review.' : 'Select a playbook and run review.'}</p></div>) : <>
            {activeTab === 'issues' && <div className="review-layout"><div className="issue-column"><div className="review-meta"><div><span className="eyebrow">REVIEW RESULTS</span><strong>{review.playbook_name}</strong><small>{dateLabel(review.created_at)} · {issues.length} findings</small></div><span className={`ai-badge ${review.ai_status.toLowerCase().includes('complete') || review.ai_status.toLowerCase().includes('success') ? 'ai-done' : ''}`}><span /> {aiStatusLabel(review.ai_status)}</span></div>
              <div className="filters"><label className="searchbox"><Search size={16} /><input placeholder="Search findings" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search findings" /></label><label className="filter-select"><span className="sr-only">Filter by severity</span><select value={severity} onChange={(e) => setSeverity(e.target.value)}><option value="all">All severity</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label><label className="filter-select"><span className="sr-only">Filter by reviewer decision</span><select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="all">All review states</option><option value="unresolved">Needs decision</option><option value="accepted">Confirmed finding</option><option value="rejected">Dismissed finding</option></select></label></div>
              <div className="issue-list">{visibleIssues.length ? (['high', 'medium', 'low'] as const).filter((level) => grouped[level]).map((level) => <section className="severity-group" key={level}><h3><span className={`severity-dot ${level}`} />{level} <span>{grouped[level].length}</span></h3>{grouped[level].map((issue) => <button key={issue.id} data-issue-id={issue.id} data-finding-kind={issueKindToken(issue)} className={`issue-card ${selectedIssue === issue.id ? 'focused' : ''}`} onClick={() => { setSelectedIssue(issue.id); setActiveTab('issues'); }}><div className="issue-top"><span className={`severity-label ${issue.severity}`}>{issue.severity}</span><span className={`issue-status ${issue.status}`}>{issue.status === 'accepted' ? 'Confirmed' : issue.status === 'rejected' ? 'Dismissed' : 'Needs decision'}</span></div><strong>{issue.category}</strong><p>{issue.explanation}</p><div className="issue-footer"><span>{issue.rule_id}</span><span className={`finding-kind ${issueKindToken(issue)}`}>{issueKind(issue)}</span></div></button>)}</section>) : <div className="no-results"><Search size={20} /><strong>No findings match</strong><span>Try a different search or filter.</span></div>}</div>
            </div><div className="detail-column">{focusedIssue ? <IssueDetail issue={focusedIssue} review={review} detail={detail} onUpdate={updateIssue} onOpenSource={(anchor) => { setSourceBlock(anchor.id); setActiveTab('source'); }} /> : <div className="detail-empty"><CircleHelp size={21} /><span>Select a finding to inspect its evidence and reviewer details.</span></div>}<AiPanel health={health} review={review} consent={consent} setConsent={setConsent} provider={provider} setProvider={setProvider} model={model} setModel={setModel} maxTokens={maxTokens} setMaxTokens={setMaxTokens} maxCost={maxCost} setMaxCost={setMaxCost} runAi={runAi} busy={busy} /></div></div>}
            {activeTab === 'checks' && <div className="checks-panel"><div className="checks-heading"><div><span className="eyebrow">DETERMINISTIC ASSESSMENT</span><h3>Rule checks</h3></div><span className="check-count">{review.checks.length} checks</span></div>{review.checks.length ? <div className="check-table-wrap"><table className="check-table"><thead><tr><th>Clause category</th><th>Rule</th><th>Outcome</th><th>Observed properties</th></tr></thead><tbody>{review.checks.map((check, index) => <tr key={`${check.rule_id}-${index}`}><td><strong>{check.category}</strong></td><td><code>{check.rule_id}</code></td><td><span className={`outcome ${check.outcome.toLowerCase()}`}>{check.outcome === 'COMPLIANT' ? 'Configured conditions matched' : check.outcome.replace(/_/g, ' ')}</span></td><td><Properties data={check.properties} /></td></tr>)}</tbody></table></div> : <div className="no-results"><Activity size={20} /><strong>No rule checks returned</strong></div>}</div>}
            {activeTab === 'revisions' && <RevisionComparison key={review.id} reviewId={review.id} documentId={detail.id} previousDocumentId={detail.previous_document_id ?? detail.source_document_id ?? undefined} documents={documents} onOpenFinding={id => { setSelectedIssue(id); setActiveTab('issues'); }} />}
            {activeTab === 'source' && <SourcePanel detail={detail} selectedIssue={focusedIssue} anchorId={sourceBlock} />}
            <div className="history-row"><div><span className="eyebrow">REVIEW HISTORY</span><span>{hasMoreReviews ? `${reviews.length}+ reviews loaded` : reviews.length ? `${reviews.length} saved ${reviews.length === 1 ? 'review' : 'reviews'}` : 'No saved reviews'}</span></div><div className="history-actions">{reviews.map((item) => <button key={item.id} className={`history-pill ${review.id === item.id ? 'current' : ''}`} onClick={() => void openReview(item.id)}>{dateLabel(item.created_at)} <small>{item.playbook_name}</small></button>)}{hasMoreReviews && <button className="load-more" onClick={() => void loadMoreReviews()} disabled={!!busy}>{busy === 'reviews-more' ? 'Loading reviews…' : 'Load more reviews'}</button>}</div></div>
            <div className="disclaimer"><ShieldCheck size={15} /><span>Clause Review Workbench supports contract review. It does not provide legal advice or replace attorney review.</span></div>
          </>}
          <div className="playbook-tools"><div><BookOpen size={16} /><span>Playbooks</span><button onClick={() => void editPlaybook(selectedPlaybook)} disabled={!selectedPlaybook}>Edit settings</button><button onClick={() => void duplicatePlaybook()} disabled={!selectedPlaybook}>Duplicate</button><button onClick={() => { void api<Playbook>(`/playbooks/${selectedPlaybook}`).then((book) => { setEditingPlaybookId(''); setPlaybookSettings(null); setAdvancedPlaybook(false); setPlaybookText((book.yaml ?? '').replace(/name:.*\n/, 'name: Custom playbook\n')); setPlaybookError(''); setPlaybookModal(true); }).catch((err: Error) => setError(err.message)); }}>New</button></div><div><label className="import-button"><Upload size={14} /> Import YAML<input type="file" accept=".yml,.yaml,text/yaml,text/plain" onChange={(event) => { void importPlaybook(event.target.files?.[0]); event.currentTarget.value = ''; }} /></label><button onClick={() => selectedPlaybook && void download(`/playbooks/${selectedPlaybook}/export`, `${playbooks.find((book) => book.id === selectedPlaybook)?.name ?? 'playbook'}.yaml`)} disabled={!selectedPlaybook}><ArrowDownToLine size={14} /> Export YAML</button></div></div>
        </>}
      </section>
    </main>
    <footer className="app-footer"><span>Clause Review Workbench 1.5.0</span><span>Review aid only. Not legal advice; attorney review required.</span><button className="text-button onboarding-replay" onClick={replayOnboarding}>Getting started</button></footer>
    {playbookModal && <div className="modal-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setPlaybookModal(false); }}><section ref={playbookDialog} className="playbook-modal" role="dialog" aria-modal="true" aria-labelledby="playbook-title"><PlaybookEditor editing={!!editingPlaybookId} settings={playbookSettings} setSettings={setPlaybookSettings} selectedRuleId={selectedRuleId} setSelectedRuleId={setSelectedRuleId} advanced={advancedPlaybook} setAdvanced={setAdvancedPlaybook} yaml={playbookText} setYaml={setPlaybookText} error={playbookError} busy={busy} onClose={() => setPlaybookModal(false)} onSave={() => void (playbookSettings && !advancedPlaybook ? savePlaybookSettings() : savePlaybook())} /></section></div>}
  </div>;
}

function GettingStarted({ documentName, hasReview, sourceCheck, action, onDismiss }: { documentName?: string; hasReview: boolean; sourceCheck?: 'visual' | 'reprocess'; action: ReactNode; onDismiss: () => void }) {
  return <section id="getting-started" className="getting-started" aria-labelledby="getting-started-title">
    <div className="getting-started-copy">
      <h3 id="getting-started-title">{sourceCheck ? (sourceCheck === 'visual' ? 'Check the original before review' : 'Reprocess the original before a new review') : hasReview ? 'Review a finding and record your decision' : documentName ? 'Your contract is ready' : 'Start a contract review'}</h3>
      <p>{sourceCheck ? (sourceCheck === 'visual' ? 'Compare the original with all extracted text using the source check below. Review stays blocked until you confirm that no contract text is missing or out of order.' : 'This upload predates the current extraction checks. Use Reprocess original to create a separate record; earlier reviews and decisions remain available.') : hasReview ? 'Confirm the flagged issue or dismiss it for this review. Neither choice approves or changes contract terms.' : 'The local review compares extracted text with the selected playbook. Check the source passage before recording a decision.'}</p>
      <ol>{sourceCheck ? <><li><strong>Check the source</strong><span>{sourceCheck === 'visual' ? 'Use the visual comparison below. If text is missing or out of order, upload a corrected text-based copy.' : 'Inspect the new extraction against the original.'}</span></li><li><strong>Run a local review</strong><span>Continue only after the source checks are complete.</span></li></> : documentName ? <><li><strong>Find</strong><span>Select a flagged issue.</span></li><li><strong>Verify</strong><span>Open its passage in the source.</span></li><li><strong>Record</strong><span>Confirm or dismiss the finding.</span></li><li><strong>Export</strong><span>Download the review report.</span></li></> : <><li><strong>Choose a contract</strong><span>DOCX, searchable PDF, or UTF-8 text.</span></li><li><strong>Run a local review</strong><span>Select a playbook to check its text patterns.</span></li></>}</ol>
      <div className="getting-started-actions">{action}<button className="text-button" onClick={onDismiss}>Skip for now</button></div>
    </div>
    <span className="getting-started-mark" aria-hidden="true"><FileCheck2 size={22} /></span>
  </section>;
}

function Properties({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data ?? {});
  return entries.length ? <div className="property-list">{entries.map(([key, value]) => <span key={key}><b>{key.replace(/_/g, ' ')}:</b> {typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>)}</div> : <span className="muted">No measurable properties</span>;
}
function PlaybookEditor({ editing, settings, setSettings, selectedRuleId, setSelectedRuleId, advanced, setAdvanced, yaml, setYaml, error, busy, onClose, onSave }: { editing: boolean; settings: PlaybookSettings | null; setSettings: (value: PlaybookSettings | null) => void; selectedRuleId: string; setSelectedRuleId: (value: string) => void; advanced: boolean; setAdvanced: (value: boolean) => void; yaml: string; setYaml: (value: string) => void; error: string; busy: string; onClose: () => void; onSave: () => void }) {
  const initialSettings = useRef(settings ? JSON.stringify(settings) : '');
  const initialYaml = useRef(yaml);
  const [pendingAdvanced, setPendingAdvanced] = useState<boolean | null>(null);
  const commonDirty = !!settings && JSON.stringify(settings) !== initialSettings.current;
  const yamlDirty = yaml !== initialYaml.current;
  const requestMode = (next: boolean) => {
    if ((advanced && yamlDirty) || (!advanced && commonDirty)) setPendingAdvanced(next);
    else setAdvanced(next);
  };
  const discardAndSwitch = () => {
    if (advanced) setYaml(initialYaml.current);
    else if (settings) setSettings(JSON.parse(initialSettings.current) as PlaybookSettings);
    if (pendingAdvanced !== null) setAdvanced(pendingAdvanced);
    setPendingAdvanced(null);
  };
  const rule = settings?.rules.find((item) => item.id === selectedRuleId);
  const updateRule = (changes: Partial<PlaybookSettings['rules'][number]>) => {
    if (!settings) return;
    setSettings({ ...settings, rules: settings.rules.map((item) => item.id === selectedRuleId ? { ...item, ...changes } : item) });
  };
  return <><header><div><span className="eyebrow">PLAYBOOK SETTINGS</span><h2 id="playbook-title">{editing ? 'Edit playbook' : 'Create playbook'}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close"><X size={18} /></button></header>{settings && !advanced ? <><p className="modal-help">These settings apply to future reviews. Existing reviews keep their saved playbook.</p><div className="settings-form"><label>Playbook name<input value={settings.name} onChange={(event) => setSettings({ ...settings, name: event.target.value })} /></label><label>Version<input value={settings.version} onChange={(event) => setSettings({ ...settings, version: event.target.value })} /></label><label>Description<textarea value={settings.description} onChange={(event) => setSettings({ ...settings, description: event.target.value })} /></label><label>Clause category<select value={selectedRuleId} onChange={(event) => setSelectedRuleId(event.target.value)}>{settings.rules.map((item) => <option key={item.id} value={item.id}>{item.category}</option>)}</select></label>{rule && <><label>Finding priority<select value={rule.severity} onChange={(event) => updateRule({ severity: event.target.value as PlaybookSettings['rules'][number]['severity'] })}><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select><small>Changes the priority shown when this rule finds an issue.</small></label><label className="required-rule"><input type="checkbox" checked={rule.required} onChange={(event) => updateRule({ required: event.target.checked })} /><span><strong>Required clause</strong><small>When on, a missing clause can create a finding.</small></span></label><label>Preferred position<textarea value={rule.preferred_position} onChange={(event) => updateRule({ preferred_position: event.target.value })} /></label><label>Negotiation guidance<textarea value={rule.negotiation_guidance} onChange={(event) => updateRule({ negotiation_guidance: event.target.value })} /></label><label>Fallback wording<textarea value={rule.fallback_language ?? ''} onChange={(event) => updateRule({ fallback_language: event.target.value || null })} /></label></>}</div><p className="settings-note">Text guidance changes reviewer guidance only. It does not change which contract wording the rule recognizes.</p></> : <><p className="modal-help">Advanced YAML controls rule patterns and detailed matching conditions. Invalid playbooks stay unsaved.</p><label className="field-label" htmlFor="playbook-yaml">Playbook YAML</label><textarea id="playbook-yaml" aria-invalid={!!error} aria-describedby={error ? 'playbook-error' : undefined} className="yaml-editor" value={yaml} onChange={(event) => setYaml(event.target.value)} spellCheck={false} placeholder={'schema_version: 1\nname: My commercial playbook\nrules:\n  - id: confidentiality-mutual\n    category: Confidentiality\n    ...'} /><div className="editor-meta"><span>{yaml.split('\n').length} lines</span><span>Schema checked on save</span></div></>}{error && <div id="playbook-error" role="alert" className="alert alert-error"><AlertCircle size={16} /><span>{error}</span></div>}{pendingAdvanced !== null && <div className="unsaved-switch" role="alert"><strong>Unsaved {advanced ? 'YAML' : 'common settings'} changes</strong><span>Switching views will discard these edits.</span><div><button type="button" className="button button-quiet" onClick={() => setPendingAdvanced(null)}>Stay here</button><button type="button" className="button button-danger-quiet" onClick={discardAndSwitch}>Discard edits and switch</button></div></div>}<div className="playbook-editor-links">{settings && <button type="button" className="text-button" onClick={() => requestMode(!advanced)} aria-expanded={advanced}>{advanced ? 'Back to common settings' : 'Advanced YAML'}</button>}</div><div className="modal-actions"><button className="button button-quiet" onClick={onClose}>Cancel</button><button className="button button-primary" onClick={onSave} disabled={!!busy || (settings && !advanced ? !settings.name.trim() || !settings.version.trim() : !yaml.trim())}>{busy === 'playbook-save' ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />} Save {editing ? 'settings' : 'playbook'}</button></div></>;
}
function IssueDetail({ issue, review, detail, onUpdate, onOpenSource }: { issue: Issue; review: Review; detail: DocDetail; onUpdate: (issue: Issue, update: Partial<Pick<Issue, 'status' | 'notes'>>) => Promise<void>; onOpenSource: (anchor: Block) => void }) {
  const [notes, setNotes] = useState(issue.notes);
  useEffect(() => { setNotes(issue.notes); }, [issue.id, issue.notes]);
  return <article className="finding-detail"><div className="detail-heading"><div><span className={`severity-label ${issue.severity}`}>{issue.severity} priority</span><span data-finding-kind={issueKindToken(issue)} className={`finding-kind ${issueKindToken(issue)}`}>{issueKind(issue)}</span></div><span className="rule-code">{issue.rule_id}</span></div><h3>{issue.category}</h3><p className="finding-explanation">{issue.explanation}</p><div className="detail-section"><h4>Observed contract language</h4>{issue.absence ? <div className="absence-note"><AlertCircle size={16} /><span>No matching provision was found in the extracted text. No quotation is attributed.</span></div> : issue.observed_language ? <blockquote>{issue.observed_language}</blockquote> : <div className="absence-note"><CircleHelp size={16} /><span>No exact quote was returned. Check the source passage before relying on this finding.</span></div>}</div><div className="detail-section"><h4>Source evidence</h4>{issue.source_anchor ? <div className="source-card"><div className="source-loc"><span>{issue.source_anchor.kind === 'heading' ? 'Heading' : 'Paragraph'} · {issue.source_anchor.location}{issue.source_anchor.page ? ` · Page ${issue.source_anchor.page}` : ''}</span><button onClick={() => onOpenSource(issue.source_anchor!)}>View in source <ChevronDown size={14} /></button></div><p>{issue.source_anchor.text}</p>{issue.source_anchor.page && <a href={`/api/documents/${detail.id}/original#page=${issue.source_anchor.page}`} target="_blank" rel="noreferrer">Open original at page {issue.source_anchor.page}</a>}</div> : <div className="absence-note"><FileText size={16} /><span>{issue.absence ? 'No source passage applies to this absence-based finding.' : 'No source passage was linked. Treat this finding as unverified.'}</span></div>}</div>{!!issue.interactions?.length && <section className="detail-section interactions"><h4>Related clauses and effect</h4>{issue.interactions.map((relation, index) => <article className="interaction-card" key={index}><h5>{({ 'cap-exception': 'Cap scope and exceptions', 'fee-definition': 'Defined fee basis', 'termination-cost': 'Cost of exercising termination', 'qualified-reference': 'Qualified cross-reference' } as Record<string, string>)[relation.kind] ?? relation.kind}</h5>{relation.reference && <span className="reference-status">{relation.reference} · {relation.status}</span>}<p>{relation.explanation}</p>{relation.evidence.map((anchor) => <div className="source-card" key={anchor.id}><div className="source-loc"><span>{anchor.location}{anchor.page ? ` · Page ${anchor.page}` : ''}</span><button onClick={() => onOpenSource(anchor)}>View in source <ChevronDown size={14} /></button></div><p>{anchor.text}</p></div>)}</article>)}</section>}<div className="detail-section position-grid"><div><h4>Preferred position</h4><p>{issue.preferred_position || 'No preferred position provided.'}</p></div><div><h4>Suggested response</h4><p>{issue.negotiating_response || 'No negotiating response provided.'}</p></div></div><details className="detail-section playbook-guidance"><summary>Saved playbook alternatives and fallback</summary><p className="muted">These are playbook guidance, not contract text or verified legal standards.</p><h4>Alternatives</h4>{issue.playbook_guidance?.acceptable_alternatives.length ? <ul>{issue.playbook_guidance.acceptable_alternatives.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>None specified in this review’s saved playbook.</p>}<h4>Fallback wording</h4><p>{issue.playbook_guidance?.fallback_language || "None specified in this review’s saved playbook."}</p></details><div className="detail-section reviewer-section"><h4><MessageSquareText size={15} /> Reviewer notes</h4><textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Add a note for your review team…" aria-label="Reviewer notes" /><button className="button button-small" onClick={() => void onUpdate(issue, { notes })}>Save note</button></div><div className="reviewer-actions"><div><strong>Decision on this finding</strong><small>These choices track the flagged issue for this review. They do not approve or change contract terms.</small></div><button className={`decision-button ${issue.status === 'accepted' ? 'accepted' : ''}`} aria-pressed={issue.status === 'accepted'} onClick={() => void onUpdate(issue, { status: 'accepted' })}><Check size={15} /> Confirm finding</button><button className={`decision-button ${issue.status === 'rejected' ? 'rejected' : ''}`} aria-pressed={issue.status === 'rejected'} onClick={() => void onUpdate(issue, { status: 'rejected' })}><X size={15} /> Dismiss finding</button>{issue.status !== 'unresolved' && <button className="text-button" onClick={() => void onUpdate(issue, { status: 'unresolved' })}>Clear decision</button>}</div><span className="origin-note">Finding source: {issue.origin === 'ai' ? 'AI-assisted' : 'local rule'} · {aiStatusLabel(review.ai_status)}</span></article>;
}
function SourcePanel({ detail, selectedIssue, anchorId }: { detail: DocDetail; selectedIssue?: Issue; anchorId?: string }) {
  const anchor = detail.blocks.find((block) => block.id === anchorId) ?? selectedIssue?.source_anchor;
  useEffect(() => {
    if (!anchor) return;
    const target = document.getElementById(`block-${anchor.id}`);
    target?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [anchor?.id]);
  return <div className="source-panel"><div className="source-panel-head"><div><span className="eyebrow">EXTRACTED DOCUMENT</span><h3>Source text</h3><p>Extracted blocks preserve their own text and location. Contract content is displayed as plain text.</p></div><a className="button button-quiet" href={`/api/documents/${detail.id}/original`} target="_blank" rel="noreferrer"><FileText size={15} /> Open original</a></div>{anchor && <div className="focused-source"><span>Selected clause evidence</span><strong>{anchor.location}{anchor.page ? ` · page ${anchor.page}` : ''}</strong><p>{anchor.text}</p></div>}<div className="source-block-list">{detail.blocks.map((block) => <article id={`block-${block.id}`} className={`source-block ${anchor?.id === block.id ? 'source-highlight' : ''}`} key={block.id}><div><span className={`block-kind ${block.kind}`}>{block.kind}</span><span>{block.location}{block.page ? ` · Page ${block.page}` : ''}</span><code>{block.id}</code></div>{block.kind === 'heading' ? <h4>{block.text}</h4> : <p>{block.text}</p>}</article>)}</div></div>;
}
function AiPanel({ health, review, consent, setConsent, provider, setProvider, model, setModel, maxTokens, setMaxTokens, maxCost, setMaxCost, runAi, busy }: { health: Health | null; review: Review; consent: boolean; setConsent: (value: boolean) => void; provider: string; setProvider: (value: string) => void; model: string; setModel: (value: string) => void; maxTokens: string; setMaxTokens: (value: string) => void; maxCost: string; setMaxCost: (value: string) => void; runAi: () => void; busy: string }) {
  return <details className="ai-panel"><summary className="ai-title"><span className="ai-icon"><Sparkles size={16} /></span><span><strong>Optional AI assistance</strong><small>External provider · {health?.ai_configured ? 'configured' : 'not configured'}</small></span><ChevronDown size={16} aria-hidden="true" /></summary>{review.ai_error && <div className="ai-error" role="alert"><AlertCircle size={14} />{review.ai_error}</div>}<p className="ai-panel-intro">Local findings are available without AI. If you continue, the contract text and playbook guidance are sent to the selected provider.</p><div className="ai-fields"><label>Provider<input value={provider} onChange={(e) => setProvider(e.target.value)} placeholder="Exact OpenRouter provider name" /></label><label>Model<input value={model} onChange={(e) => setModel(e.target.value)} placeholder="e.g. provider/model-name" /></label><div className="budget-fields"><label>Max output tokens<input type="number" min="128" max="4096" value={maxTokens} onChange={(e) => setMaxTokens(e.target.value)} /></label><label>Max cost (USD)<input type="number" min="0.001" step="0.001" value={maxCost} onChange={(e) => setMaxCost(e.target.value)} /></label></div></div><label className="consent-check"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /><span>Send this review to the external provider</span></label><button className="ai-run" onClick={runAi} disabled={!health?.ai_configured || !consent || !model.trim() || !provider.trim() || !!busy}>{busy === 'ai' ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />}{busy === 'ai' ? 'Requesting interpretation…' : 'Run AI assistance'}</button><small className="ai-footnote">AI output can be wrong. Check each citation in the source.</small></details>;
}
export default App;
