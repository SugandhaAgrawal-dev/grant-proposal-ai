import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FileText, ClipboardList, PlusCircle, Upload, ChevronRight, Zap } from 'lucide-react';
import { documentsApi, proposalsApi } from '../utils/api';
import { formatDate, statusBadge, truncate } from '../utils/helpers';

export default function Dashboard() {
  const { data: docs }      = useQuery({ queryKey: ['docs'],      queryFn: () => documentsApi.list().then(r => r.data.results || r.data) });
  const { data: proposals } = useQuery({ queryKey: ['proposals'], queryFn: () => proposalsApi.list().then(r => r.data.results || r.data) });

  const recentDocs      = (docs || []).slice(0, 5);
  const recentProposals = (proposals || []).slice(0, 5);

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={<FileText className="w-5 h-5 text-primary-600" />} label="Documents"  value={docs?.length ?? '—'}      bg="bg-primary-50" />
        <StatCard icon={<ClipboardList className="w-5 h-5 text-health-600" />} label="Proposals" value={proposals?.length ?? '—'} bg="bg-health-50" />
        <StatCard icon={<Zap className="w-5 h-5 text-amber-600" />} label="Generating" bg="bg-amber-50"
          value={(proposals || []).filter(p => p.status === 'generating').length} />
        <StatCard icon={<ClipboardList className="w-5 h-5 text-green-600" />} label="Approved" bg="bg-green-50"
          value={(proposals || []).filter(p => p.status === 'approved').length} />
      </div>

      {/* Quick actions */}
      <div className="card p-5">
        <h2 className="text-base font-semibold text-gray-900 mb-4">Quick actions</h2>
        <div className="flex flex-wrap gap-3">
          <Link to="/documents/upload" className="btn-primary flex items-center gap-2"><Upload className="w-4 h-4" /> Upload Document</Link>
          <Link to="/proposals/new"    className="btn-success flex items-center gap-2"><PlusCircle className="w-4 h-4" /> New Proposal</Link>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Recent Documents */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-gray-900">Recent documents</h2>
            <Link to="/documents" className="text-xs text-primary-600 hover:underline flex items-center gap-1">View all <ChevronRight className="w-3 h-3" /></Link>
          </div>
          <div className="space-y-2">
            {!recentDocs.length && <Empty msg="No documents yet. Upload your first RFP." />}
            {recentDocs.map(doc => {
              const { cls, label } = statusBadge(doc.status);
              return (
                <div key={doc.id} className="flex items-center justify-between gap-2 py-2 border-b border-gray-50 last:border-0">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{truncate(doc.name, 45)}</p>
                    <p className="text-xs text-gray-400">{doc.document_type?.toUpperCase()} · {formatDate(doc.created_at)}</p>
                  </div>
                  <span className={cls}>{label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent Proposals */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-gray-900">Recent proposals</h2>
            <Link to="/proposals" className="text-xs text-primary-600 hover:underline flex items-center gap-1">View all <ChevronRight className="w-3 h-3" /></Link>
          </div>
          <div className="space-y-2">
            {!recentProposals.length && <Empty msg="No proposals yet. Create one from an uploaded RFP." />}
            {recentProposals.map(p => {
              const { cls, label } = statusBadge(p.status);
              return (
                <Link key={p.id} to={`/proposals/${p.id}`}
                  className="flex items-center justify-between gap-2 py-2 border-b border-gray-50 last:border-0 hover:bg-gray-50 -mx-2 px-2 rounded-lg transition-colors">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{truncate(p.title, 45)}</p>
                    <p className="text-xs text-gray-400">{formatDate(p.created_at)}</p>
                  </div>
                  <span className={cls}>{label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, bg }) {
  return (
    <div className="card p-4">
      <div className={`w-9 h-9 ${bg} rounded-lg flex items-center justify-center mb-3`}>{icon}</div>
      <p className="text-2xl font-semibold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
    </div>
  );
}

function Empty({ msg }) {
  return <p className="text-sm text-gray-400 py-4 text-center">{msg}</p>;
}
