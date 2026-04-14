export const formatDate = (iso) =>
  iso ? new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : '—';

export const formatFileSize = (bytes) => {
  if (!bytes) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
};

export const statusBadge = (status) => ({
  draft:             { cls: 'badge-gray',   label: 'Draft' },
  generating:        { cls: 'badge-yellow', label: 'Generating…' },
  compliance_review: { cls: 'badge-yellow', label: 'Compliance Review' },
  human_review:      { cls: 'badge-blue',   label: 'Human Review' },
  approved:          { cls: 'badge-green',  label: 'Approved' },
  submitted:         { cls: 'badge-green',  label: 'Submitted' },
  error:             { cls: 'badge-red',    label: 'Error' },
  uploaded:          { cls: 'badge-gray',   label: 'Uploaded' },
  parsing:           { cls: 'badge-yellow', label: 'Parsing…' },
  parsed:            { cls: 'badge-green',  label: 'Parsed' },
  failed:            { cls: 'badge-red',    label: 'Failed' },
}[status] || { cls: 'badge-gray', label: status });

export const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const a   = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
};

export const truncate = (str, max = 60) =>
  str && str.length > max ? str.slice(0, max) + '…' : (str || '—');

export const providerBadge = (provider) => ({
  ollama: { cls: 'badge-green',  label: 'Ollama (local)' },
  openai: { cls: 'badge-blue',   label: 'GPT-4o' },
  claude: { cls: 'badge-yellow', label: 'Claude' },
  vertex: { cls: 'badge-blue',   label: 'Vertex AI / Gemini' },
}[provider] || { cls: 'badge-gray', label: provider });
