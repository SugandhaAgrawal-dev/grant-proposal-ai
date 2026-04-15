import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ClipboardList, PlusCircle, ChevronRight } from 'lucide-react';
import { proposalsApi } from '../utils/api';
import { formatDate, statusBadge, truncate, providerBadge } from '../utils/helpers';

export default function ProposalsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['proposals'],
    queryFn: () => proposalsApi.list().then(r => r.data.results || r.data),
    refetchInterval: (query) =>
      Array.isArray(query?.state?.data) && query.state.data.some(p => p.status === 'generating') ? 4000 : false,
  });

  if (isLoading) return <Spinner />;

  return (
    <div className="max-w-4xl space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">{(data || []).length} proposal(s)</p>
        <Link to="/proposals/new" className="btn-primary flex items-center gap-2">
          <PlusCircle className="w-4 h-4" /> New proposal
        </Link>
      </div>

      {!(data || []).length ? (
        <div className="card p-12 text-center">
          <ClipboardList className="w-10 h-10 text-gray-200 mx-auto mb-3" />
          <p className="text-sm text-gray-400">No proposals yet.</p>
          <Link to="/proposals/new" className="btn-primary mt-4 inline-flex items-center gap-2">
            <PlusCircle className="w-4 h-4" /> Create your first proposal
          </Link>
        </div>
      ) : (
        <div className="card divide-y divide-gray-50">
          {(data || []).map(p => {
            const { cls, label } = statusBadge(p.status);
            const { cls: pcls, label: plabel } = providerBadge(p.llm_provider);
            const isGenerating = p.status === 'generating';
            return (
              <Link key={p.id} to={`/proposals/${p.id}`}
                className="flex items-start gap-4 p-4 hover:bg-gray-50 transition-colors group">
                <div className="w-8 h-8 bg-health-50 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                  <ClipboardList className="w-4 h-4 text-health-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate group-hover:text-primary-600 transition-colors">
                    {truncate(p.title, 60)}
                  </p>
                  <div className="flex gap-2 mt-1 flex-wrap">
                    <span className={pcls}>{plabel}</span>
                    {p.total_words > 0 && <span className="badge-gray">{p.total_words.toLocaleString()} words</span>}
                    <span className="text-xs text-gray-400">{formatDate(p.created_at)}</span>
                  </div>
                  {isGenerating && (
                    <div className="mt-2 flex items-center gap-2">
                      <div className="h-1 w-32 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full bg-primary-400 rounded-full animate-pulse w-1/2" />
                      </div>
                      <span className="text-xs text-gray-400">Generating…</span>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={cls}>{label}</span>
                  <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500 transition-colors" />
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Spinner() {
  return <div className="flex justify-center py-16"><div className="w-6 h-6 border-2 border-primary-300 border-t-primary-600 rounded-full animate-spin" /></div>;
}
