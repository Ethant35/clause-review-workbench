import { useEffect, useState } from 'react';

type Doc = { id: string; name: string };
type Anchor = { id: string; text: string; location: string; page: number | null };
type Finding = { id: string; category: string; explanation: string; source_anchor: Anchor | null; status: string; notes: string; interactions?: { kind: string; explanation: string; evidence: Anchor[] }[] };
type RuleDelta = { rule_id: string; category: string; status: string; before_check: { outcome: string } | null; after_check: { outcome: string } | null; before_issues: Finding[]; after_issues: Finding[]; prior_decisions: { issue_id: string; status: string; notes: string }[]; revisit_prior_decisions: boolean };
type Comparison = { before_document: Doc; after_document: Doc; same_extracted_text: boolean; same_original: boolean; warnings: string[]; rules: RuleDelta[]; text_changes: { kind: string; before: Anchor[]; after: Anchor[] }[] };
type SavedReview = { id: string; created_at: string; playbook_name: string };

async function read<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(`/api${path}`, { signal });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Comparison could not be loaded.');
  return data as T;
}

const labels: Record<string, string> = { ADDED: 'New finding', NO_LONGER_FLAGGED: 'No longer flagged', CHANGED: 'Changed finding or check', UNCHANGED: 'Same findings and check', NOT_COMPARABLE: 'Policy or checks differ' };
function outcomeLabel(outcome?: string) {
  return ({ COMPLIANT: 'Configured conditions matched', NEEDS_REVIEW: 'Interpretation unresolved', ISSUE: 'Finding returned', NOT_APPLICABLE: 'No check applied' } as Record<string, string>)[outcome ?? ''] ?? 'No check';
}

export function RevisionComparison({ reviewId, documentId, previousDocumentId, documents, onOpenFinding }: { reviewId: string; documentId: string; previousDocumentId?: string; documents: Doc[]; onOpenFinding: (id: string) => void }) {
  const [baselineDoc, setBaselineDoc] = useState(previousDocumentId ?? documentId);
  const [baselineReview, setBaselineReview] = useState('');
  const [history, setHistory] = useState<SavedReview[]>([]);
  const [offset, setOffset] = useState(0);
  const [more, setMore] = useState(false);
  const [result, setResult] = useState<Comparison | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showUnchanged, setShowUnchanged] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    if (offset === 0) { setHistory([]); setBaselineReview(''); setResult(null); }
    read<SavedReview[]>(`/documents/${baselineDoc}/reviews?summary=true&limit=50&offset=${offset}`, controller.signal)
      .then(rows => {
        const candidates = rows.filter(row => row.id !== reviewId);
        setHistory(old => offset === 0 ? candidates : [...old, ...candidates]); setMore(rows.length === 50);
        if (offset === 0) setBaselineReview(candidates[0]?.id ?? '');
      }).catch(err => { if (!controller.signal.aborted) setError((err as Error).message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [baselineDoc, reviewId, offset]);
  useEffect(() => {
    setResult(null);
    if (!baselineReview) return;
    const controller = new AbortController();
    setLoading(true); setError('');
    read<Comparison>(`/reviews/${reviewId}/comparison?baseline_review_id=${baselineReview}`, controller.signal)
      .then(setResult).catch(err => { if (!controller.signal.aborted) setError((err as Error).message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [baselineReview, reviewId]);
  const shown = result?.rules.filter(row => showUnchanged || row.status !== 'UNCHANGED' || row.revisit_prior_decisions) ?? [];
  return <section className="revision-panel" aria-labelledby="revision-title">
    <h3 id="revision-title">Compare saved reviews</h3>
    <div className="revision-selectors">
      <label>Earlier document<select aria-label="Earlier document" value={baselineDoc} onChange={e => { setBaselineDoc(e.target.value); setBaselineReview(''); setResult(null); setOffset(0); }}>
        {!documents.some(doc => doc.id === baselineDoc) && <option value={baselineDoc}>Earlier linked document</option>}
        {documents.map(doc => <option key={doc.id} value={doc.id}>{doc.name}</option>)}
      </select></label>
      <label>Baseline review<select aria-label="Baseline review" value={baselineReview} onChange={e => { setBaselineReview(e.target.value); setResult(null); }} disabled={!history.length}>
        <option value="">Choose a saved review</option>
        {history.map(row => <option key={row.id} value={row.id}>{new Date(row.created_at).toLocaleString()} · {row.playbook_name} · {row.id.slice(0, 8)}</option>)}
      </select></label>
      {more && <button className="button button-quiet" disabled={loading} onClick={() => setOffset(value => value + 50)}>Load earlier reviews</button>}
    </div>
    <p className="muted">Use the document library’s “Load more documents” to include older uploads. Baseline is the before version; the selected review is the after version.</p>
    {loading && <p role="status">Loading comparison…</p>}
    {error && <p className="alert alert-error" role="alert">{error}</p>}
    {!loading && !error && !history.length && <p>No other review for this document. Choose an earlier document or run a review of that version first.</p>}
    {result && <>
      <div className="revision-actions"><a className="button button-quiet" href={`/api/reviews/${reviewId}/comparison?baseline_review_id=${baselineReview}&download=true`} download="review-comparison.json">Export comparison JSON</a>
        <a href={`/api/documents/${result.before_document.id}/original`} target="_blank" rel="noreferrer">Open before original</a>
        <a href={`/api/documents/${result.after_document.id}/original`} target="_blank" rel="noreferrer">Open after original</a></div>
      <ul className="revision-notes">{result.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul>
      <h4>Findings and decisions</h4>
      <label className="revision-toggle"><input type="checkbox" checked={showUnchanged} onChange={e => setShowUnchanged(e.target.checked)} /> Show unchanged checks</label>
      {!shown.length && <p>No changed findings or prior decisions to revisit. Check the text changes below.</p>}
      {shown.map(row => <details key={row.rule_id} className="revision-rule" open={row.revisit_prior_decisions || undefined}>
        <summary>{row.category} · {labels[row.status]}{row.revisit_prior_decisions ? ' · Revisit prior decisions' : ''}</summary>
        <p>Before: {outcomeLabel(row.before_check?.outcome)} → After: {outcomeLabel(row.after_check?.outcome)}</p>
        {!!row.prior_decisions.length && <div className="prior-decisions"><strong>Earlier review only</strong>{row.prior_decisions.map(item => <p key={item.issue_id}>{item.status === 'accepted' ? 'Finding confirmed' : item.status === 'rejected' ? 'Finding dismissed' : 'Unresolved'}{item.notes ? ` — ${item.notes}` : ''}</p>)}</div>}
        <div className="revision-columns">{([['Before', row.before_issues], ['After', row.after_issues]] as const).map(([title, issues]) => <div key={title}><h5>{title}</h5>{issues.length ? issues.map(issue => <article key={issue.id}>{title === 'After' && <button className="button button-quiet" onClick={() => onOpenFinding(issue.id)}>Review this finding</button>}<p>{issue.explanation}</p>{issue.source_anchor && <blockquote><small>{issue.source_anchor.location}</small>{issue.source_anchor.text}</blockquote>}{!!issue.interactions?.length && <details className="revision-evidence"><summary>Related clauses and effect</summary>{issue.interactions.map((relation, index) => <div key={index}><p>{relation.explanation}</p>{relation.evidence.filter(anchor => anchor.id !== issue.source_anchor?.id).map(anchor => <blockquote key={anchor.id}><small>{anchor.location}</small>{anchor.text}</blockquote>)}</div>)}</details>}</article>) : <p>No finding returned.</p>}</div>)}</div>
      </details>)}
      <h4>Extracted text changes</h4>
      <p>{result.same_extracted_text ? (result.same_original ? 'Original bytes and extracted text match.' : 'Extracted text matches; original bytes differ.') : `${result.text_changes.length} changed paragraph groups. Moved text may appear as a deletion and an addition.`}</p>
      {result.text_changes.map((change, index) => <details className="revision-text" key={index}><summary>Change {index + 1} · {({ insert: 'Added', delete: 'Deleted', replace: 'Replaced' } as Record<string, string>)[change.kind]}</summary><div className="revision-columns">{(['before', 'after'] as const).map(side => <div key={side}><h5>{side === 'before' ? 'Before' : 'After'}</h5>{change[side].length ? change[side].map(block => <blockquote key={block.id}><small>{block.location}</small>{block.text}</blockquote>) : <p>No text.</p>}</div>)}</div></details>)}
    </>}
  </section>;
}
