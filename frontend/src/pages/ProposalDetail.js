import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Download, RefreshCw, CheckCircle, AlertCircle, AlertTriangle, ChevronDown, ChevronUp, Loader, Shield } from 'lucide-react';
import { proposalsApi, complianceApi } from '../utils/api';
import { formatDate, statusBadge, providerBadge, downloadBlob } from '../utils/helpers';

export default function ProposalDetail() {
  const { id } = useParams();
  const qc = useQueryClient();
  const [expanded, setExpanded]         = useState(null);
  const [feedback, setFeedback]         = useState('');
  const [reviewNotes, setReviewNotes]   = useState('');
  const [regenerating, setRegenerating] = useState(null);
  const [running, setRunning]           = useState(false);

  const { data: proposal, isLoading } = useQuery({
    queryKey: ['proposal', id],
    queryFn: () => proposalsApi.get(id).then(r => r.data),
    refetchInterval: (data) => data?.status === 'generating' ? 4000 : false,
  });

  async function handleDownload() {
    try {
      await proposalsApi.export(id);
      toast('Export started — downloading in a moment…');
      await new Promise(r => setTimeout(r, 3000));
      const { data } = await proposalsApi.download(id);
      downloadBlob(data, `proposal_${id}.docx`);
    } catch { toast.error('Download failed'); }
  }

  async function handleCompliance() {
    setRunning(true);
    try {
      const { data } = await complianceApi.check(id);
      toast(data.passed ? '✅ Compliance passed!' : `⚠️ ${data.errors} error(s) found`);
      qc.invalidateQueries(['proposal', id]);
    } catch { toast.error('Compliance check failed'); }
    finally { setRunning(false); }
  }

  async function handleRegenerate(sectionId, sectionName) {
    if (!feedback.trim()) { toast.error('Add reviewer feedback first.'); return; }
    setRegenerating(sectionId);
    try {
      await proposalsApi.regenerateSection(sectionId, {
        reviewer_feedback: feedback,
        llm_provider: proposal.llm_provider,
      });
      toast.success(`${sectionName} regeneration started`);
      qc.invalidateQueries(['proposal', id]);
    } catch { toast.error('Regeneration failed'); }
    finally { setRegenerating(null); }
  }

  async function handleApprove() {
    try {
      await proposalsApi.review(id, { status: 'approved', reviewer_notes: reviewNotes });
      toast.success('Proposal approved!');
      qc.invalidateQueries(['proposal', id]);
    } catch { toast.error('Failed'); }
  }

  if (isLoading) return <Spinner />;
  if (!proposal)  return <p className="text-sm text-gray-400">Proposal not found.</p>;

  const { cls, label }       = statusBadge(proposal.status);
  const { cls: pcls, label: plabel } = providerBadge(proposal.llm_provider);
  const isGenerating         = proposal.status === 'generating';
  const compliance           = proposal.rfp_metadata?.compliance_report;

  return (
    <div className="max-w-4xl space-y-6">

      {/* Header */}
      <div className="card p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-gray-900">{proposal.title}</h2>
            <div className="flex gap-2 mt-2 flex-wrap">
              <span className={cls}>{label}</span>
              <span className={pcls}>{plabel}</span>
              {proposal.total_words > 0 && <span className="badge-gray">{proposal.total_words.toLocaleString()} words</span>}
              <span className="text-xs text-gray-400">{formatDate(proposal.created_at)}</span>
            </div>
          </div>
          {!isGenerating && proposal.sections?.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              <button onClick={handleCompliance} disabled={running} className="btn-secondary flex items-center gap-2">
                <Shield className="w-4 h-4" />
                {running ? 'Checking…' : 'Compliance check'}
              </button>
              <button onClick={handleDownload} className="btn-primary flex items-center gap-2">
                <Download className="w-4 h-4" /> Download DOCX
              </button>
            </div>
          )}
        </div>

        {isGenerating && (
          <div className="mt-4 p-4 bg-amber-50 rounded-lg border border-amber-100 flex items-start gap-3">
            <Loader className="w-4 h-4 text-amber-500 animate-spin flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-800">Generating proposal sections…</p>
              <p className="text-xs text-amber-600 mt-0.5">This takes 2–10 minutes depending on model. Page auto-refreshes.</p>
              <div className="mt-2 h-1.5 bg-amber-100 rounded-full overflow-hidden">
                <div className="h-full bg-amber-400 rounded-full animate-pulse w-1/2" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Compliance report */}
      {compliance && (
        <div className={`card p-5 border ${compliance.passed ? 'border-health-200' : 'border-red-200'}`}>
          <div className="flex items-center gap-2 mb-3">
            {compliance.passed
              ? <CheckCircle className="w-5 h-5 text-health-500" />
              : <AlertCircle className="w-5 h-5 text-red-500" />}
            <h3 className="text-sm font-semibold text-gray-900">
              Compliance — {compliance.passed ? 'Passed' : `${compliance.errors} error(s)`}
            </h3>
            <div className="ml-auto flex gap-2">
              {compliance.errors   > 0 && <span className="badge-red">{compliance.errors} error{compliance.errors   !== 1 ? 's' : ''}</span>}
              {compliance.warnings > 0 && <span className="badge-yellow">{compliance.warnings} warning{compliance.warnings !== 1 ? 's' : ''}</span>}
            </div>
          </div>
          <p className="text-xs text-gray-500 mb-3">{compliance.summary}</p>
          {compliance.issues?.length > 0 && (
            <div className="space-y-2">
              {compliance.issues.map((issue, i) => (
                <div key={i} className={`flex items-start gap-2 p-2.5 rounded-lg text-xs ${issue.severity === 'error' ? 'bg-red-50' : 'bg-amber-50'}`}>
                  <AlertTriangle className={`w-3.5 h-3.5 flex-shrink-0 mt-0.5 ${issue.severity === 'error' ? 'text-red-500' : 'text-amber-500'}`} />
                  <div>
                    <span className="font-medium">{issue.section}: </span>{issue.message}
                    {issue.suggestion && <p className="text-gray-500 mt-0.5">Suggestion: {issue.suggestion}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Reviewer feedback input */}
      {!isGenerating && proposal.sections?.length > 0 && (
        <div className="card p-5 space-y-3">
          <h3 className="text-sm font-semibold text-gray-900">Reviewer feedback</h3>
          <textarea className="input min-h-20 resize-y text-sm" value={feedback} onChange={e => setFeedback(e.target.value)}
            placeholder="e.g. 'Strengthen past performance with contract values. Add HIPAA subsection to Technical Approach.'" />
          <p className="text-xs text-gray-400">This feedback is used when regenerating individual sections below.</p>
        </div>
      )}

      {/* Sections */}
      {proposal.sections?.length > 0 && !isGenerating && (
        <div className="card divide-y divide-gray-50">
          <div className="p-4">
            <h3 className="text-sm font-semibold text-gray-900">Sections ({proposal.sections.length})</h3>
          </div>
          {proposal.sections.map(sec => {
            const { cls: scls, label: slabel } = statusBadge(sec.status);
            const isOpen = expanded === sec.id;
            return (
              <div key={sec.id}>
                <div className="flex items-center gap-3 p-4 hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => setExpanded(isOpen ? null : sec.id)}>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{sec.name}</p>
                    <div className="flex gap-2 mt-0.5">
                      <span className={scls}>{slabel}</span>
                      {sec.word_count > 0 && <span className="text-xs text-gray-400">{sec.word_count} words</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button onClick={(e) => { e.stopPropagation(); handleRegenerate(sec.id, sec.name); }}
                      disabled={regenerating === sec.id}
                      className="btn-secondary py-1 px-2.5 text-xs flex items-center gap-1">
                      <RefreshCw className={`w-3 h-3 ${regenerating === sec.id ? 'animate-spin' : ''}`} />
                      Regenerate
                    </button>
                    {isOpen ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                  </div>
                </div>
                {isOpen && (
                  <div className="px-4 pb-5 bg-gray-50 border-t border-gray-100">
                    <div className="pt-4 text-sm text-gray-700 leading-relaxed whitespace-pre-wrap font-mono text-xs">
                      {sec.content || 'No content generated yet.'}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Human review */}
      {proposal.status === 'human_review' && (
        <div className="card p-5 space-y-4">
          <h3 className="text-sm font-semibold text-gray-900">Human review</h3>
          <textarea className="input min-h-20 resize-y" value={reviewNotes} onChange={e => setReviewNotes(e.target.value)}
            placeholder="Final reviewer notes…" />
          <button onClick={handleApprove} className="btn-success flex items-center gap-2">
            <CheckCircle className="w-4 h-4" /> Approve proposal
          </button>
        </div>
      )}
    </div>
  );
}

function Spinner() {
  return <div className="flex justify-center py-16"><div className="w-6 h-6 border-2 border-primary-300 border-t-primary-600 rounded-full animate-spin" /></div>;
}
