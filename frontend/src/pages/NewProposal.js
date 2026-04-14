import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { PlusCircle, Trash2 } from 'lucide-react';
import { documentsApi, proposalsApi, orgApi } from '../utils/api';

const DEFAULT_SECTIONS = [
  { name: 'Executive Summary',  requirements: 'Provide a concise overview of the proposed programme, organisation qualifications, and expected outcomes.', page_limit: 3,  order: 1 },
  { name: 'Technical Approach', requirements: 'Describe your methodology, care model, technology infrastructure, and implementation timeline.', page_limit: 10, order: 2 },
  { name: 'Management Plan',    requirements: 'Describe your project management approach, key personnel, and organisational structure.',             page_limit: 6,  order: 3 },
  { name: 'Past Performance',   requirements: 'Provide three examples of similar contracts from the past 5 years with measurable outcomes.',          page_limit: 6,  order: 4 },
  { name: 'Staffing Plan',      requirements: 'List all key personnel with qualifications, FTE commitments, and relevant experience.',               page_limit: 5,  order: 5 },
  { name: 'Data Security',      requirements: 'Describe your HIPAA compliance programme, technical safeguards, and certifications.',                  page_limit: 4,  order: 6 },
  { name: 'Budget',             requirements: 'Provide a detailed line-item budget with narrative justification for each cost category.',            page_limit: 5,  order: 7 },
];

export default function NewProposal() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [title,       setTitle]       = useState('');
  const [rfpId,       setRfpId]       = useState('');
  const [orgId,       setOrgId]       = useState('');
  const [provider,    setProvider]    = useState('ollama');
  const [sections,    setSections]    = useState(DEFAULT_SECTIONS);
  const [submitting,  setSubmitting]  = useState(false);

  const { data: docs } = useQuery({
    queryKey: ['docs'],
    queryFn: () => documentsApi.list().then(r => (r.data.results || r.data).filter(d => d.status === 'parsed')),
  });
  const { data: orgs } = useQuery({
    queryKey: ['orgs'],
    queryFn: () => orgApi.list().then(r => r.data.results || r.data),
  });

  function addSection() {
    setSections(s => [...s, { name: '', requirements: '', page_limit: null, order: s.length + 1 }]);
  }

  function removeSection(i) {
    setSections(s => s.filter((_, idx) => idx !== i));
  }

  function updateSection(i, field, value) {
    setSections(s => s.map((sec, idx) => idx === i ? { ...sec, [field]: value } : sec));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!orgId) { toast.error('Please select an organisation profile.'); return; }
    if (!sections.length) { toast.error('Add at least one section.'); return; }

    setSubmitting(true);
    try {
      const { data } = await proposalsApi.generate({
        title,
        rfp_document_id: rfpId || null,
        org_profile_id:  orgId,
        llm_provider:    provider,
        sections:        sections.filter(s => s.name),
      });
      toast.success('Proposal generation started!');
      qc.invalidateQueries(['proposals']);
      navigate(`/proposals/${data.id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create proposal');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl space-y-6">

      {/* Basic info */}
      <div className="card p-5 space-y-4">
        <h2 className="text-base font-semibold text-gray-900">Proposal details</h2>

        <div>
          <label className="label">Proposal title *</label>
          <input className="input" required value={title} onChange={e => setTitle(e.target.value)}
            placeholder="e.g. Response to DHCS Medi-Cal Population Health RFP 2025" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">RFP document (optional)</label>
            <select className="input" value={rfpId} onChange={e => setRfpId(e.target.value)}>
              <option value="">— Select parsed document —</option>
              {(docs || []).map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
            <p className="text-xs text-gray-400 mt-1">Only parsed documents shown</p>
          </div>
          <div>
            <label className="label">Organisation profile *</label>
            <select className="input" required value={orgId} onChange={e => setOrgId(e.target.value)}>
              <option value="">— Select organisation —</option>
              {(orgs || []).map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
            {!(orgs || []).length && (
              <p className="text-xs text-amber-600 mt-1">No profiles yet. <a href="/organisation" className="underline">Create one first.</a></p>
            )}
          </div>
        </div>

        <div>
          <label className="label">LLM provider</label>
          <select className="input" value={provider} onChange={e => setProvider(e.target.value)}>
            <option value="ollama">Ollama (local — free, private)</option>
            <option value="vertex">Vertex AI / Gemini (HIPAA-eligible)</option>
            <option value="openai">OpenAI GPT-4o</option>
            <option value="claude">Anthropic Claude</option>
          </select>
        </div>
      </div>

      {/* Sections */}
      <div className="card p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">Proposal sections ({sections.length})</h2>
          <button type="button" onClick={addSection} className="btn-secondary flex items-center gap-1.5 text-xs py-1.5 px-3">
            <PlusCircle className="w-3.5 h-3.5" /> Add section
          </button>
        </div>

        <div className="space-y-3">
          {sections.map((sec, i) => (
            <div key={i} className="p-4 bg-gray-50 rounded-lg space-y-3">
              <div className="flex items-start gap-3">
                <div className="flex-1 grid grid-cols-3 gap-3">
                  <div>
                    <label className="label text-xs">Section name</label>
                    <input className="input text-xs" value={sec.name} onChange={e => updateSection(i, 'name', e.target.value)} placeholder="e.g. Technical Approach" />
                  </div>
                  <div className="col-span-2">
                    <label className="label text-xs">Requirements</label>
                    <input className="input text-xs" value={sec.requirements} onChange={e => updateSection(i, 'requirements', e.target.value)} placeholder="What must this section address?" />
                  </div>
                </div>
                <div className="w-20 flex-shrink-0">
                  <label className="label text-xs">Pages</label>
                  <input className="input text-xs" type="number" min="1" value={sec.page_limit || ''} onChange={e => updateSection(i, 'page_limit', e.target.value ? parseInt(e.target.value) : null)} placeholder="—" />
                </div>
                <button type="button" onClick={() => removeSection(i)} className="p-1.5 hover:bg-red-50 rounded text-gray-300 hover:text-red-500 mt-5 flex-shrink-0">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <button type="submit" disabled={submitting || !title || !orgId} className="btn-primary w-full flex items-center justify-center gap-2">
        {submitting ? 'Starting generation…' : 'Generate proposal'}
      </button>
    </form>
  );
}
