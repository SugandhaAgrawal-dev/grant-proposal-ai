import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { FileText, Trash2, RefreshCw, Upload, ChevronRight } from 'lucide-react';
import { documentsApi } from '../utils/api';
import { formatDate, formatFileSize, statusBadge, truncate } from '../utils/helpers';

const TYPE_ICONS = { pdf: '📄', docx: '📝', excel: '📊', image: '🖼️' };

export default function DocumentsPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['docs'],
    queryFn: () => documentsApi.list().then(r => r.data.results || r.data),
    refetchInterval: (data) =>
      (data || []).some(d => d.status === 'parsing') ? 3000 : false,
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => documentsApi.delete(id),
    onSuccess: () => { toast.success('Document deleted'); qc.invalidateQueries(['docs']); },
    onError:   () => toast.error('Delete failed'),
  });

  const reprocessMutation = useMutation({
    mutationFn: (id) => documentsApi.reprocess(id),
    onSuccess: () => { toast.success('Reprocessing started'); qc.invalidateQueries(['docs']); },
  });

  if (isLoading) return <Spinner />;

  return (
    <div className="max-w-4xl space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">{(data || []).length} document(s)</p>
        <Link to="/documents/upload" className="btn-primary flex items-center gap-2">
          <Upload className="w-4 h-4" /> Upload
        </Link>
      </div>

      {!(data || []).length ? (
        <div className="card p-12 text-center">
          <FileText className="w-10 h-10 text-gray-200 mx-auto mb-3" />
          <p className="text-sm text-gray-400">No documents yet.</p>
          <Link to="/documents/upload" className="btn-primary mt-4 inline-flex items-center gap-2">
            <Upload className="w-4 h-4" /> Upload your first document
          </Link>
        </div>
      ) : (
        <div className="card divide-y divide-gray-50">
          {(data || []).map(doc => {
            const { cls, label } = statusBadge(doc.status);
            return (
              <div key={doc.id} className="flex items-start gap-4 p-4 hover:bg-gray-50 transition-colors">
                <div className="text-2xl flex-shrink-0 mt-0.5">
                  {TYPE_ICONS[doc.document_type] || '📄'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{doc.name}</p>
                  <div className="flex gap-3 mt-0.5 text-xs text-gray-400">
                    <span>{doc.document_type?.toUpperCase()}</span>
                    <span>{formatFileSize(doc.file_size)}</span>
                    {doc.page_count > 0 && <span>{doc.page_count} pages</span>}
                    <span>{formatDate(doc.created_at)}</span>
                  </div>
                  {doc.status === 'parsing' && (
                    <div className="mt-2 h-1 w-32 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-primary-400 rounded-full animate-pulse w-2/3" />
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={cls}>{label}</span>
                  {doc.status === 'failed' && (
                    <button onClick={() => reprocessMutation.mutate(doc.id)}
                      className="p-1.5 hover:bg-blue-50 rounded-lg text-blue-400 hover:text-blue-600 transition-colors">
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  )}
                  <button onClick={() => {
                    if (window.confirm(`Delete "${doc.name}"?`)) deleteMutation.mutate(doc.id);
                  }} className="p-1.5 hover:bg-red-50 rounded-lg text-gray-300 hover:text-red-500 transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
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
