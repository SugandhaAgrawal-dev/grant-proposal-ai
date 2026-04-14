import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Upload, FileText, X, CheckCircle } from 'lucide-react';
import { documentsApi } from '../utils/api';
import { formatFileSize } from '../utils/helpers';

const ACCEPTED = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'image/png':  ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/tiff': ['.tif', '.tiff'],
};

export default function UploadPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [file, setFile]         = useState(null);
  const [name, setName]         = useState('');
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback((accepted) => {
    if (accepted[0]) {
      setFile(accepted[0]);
      setName(accepted[0].name.replace(/\.[^.]+$/, ''));
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: ACCEPTED, maxFiles: 1,
  });

  async function handleUpload() {
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    fd.append('name', name || file.name);
    setUploading(true);
    try {
      await documentsApi.upload(fd);
      toast.success('Document uploaded — parsing in background…');
      qc.invalidateQueries(['docs']);
      navigate('/documents');
    } catch (err) {
      toast.error(err.response?.data?.file?.[0] || 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-xl space-y-6">
      {/* Drop zone */}
      <div {...getRootProps()} className={`card p-10 text-center cursor-pointer transition-colors border-2 border-dashed ${isDragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'}`}>
        <input {...getInputProps()} />
        <Upload className="w-8 h-8 mx-auto text-gray-300 mb-3" />
        {isDragActive
          ? <p className="text-sm text-primary-600 font-medium">Drop the file here…</p>
          : <>
              <p className="text-sm text-gray-600">Drag & drop, or <span className="text-primary-600 font-medium">click to browse</span></p>
              <p className="text-xs text-gray-400 mt-1">PDF, DOCX, XLSX, PNG, JPEG, TIFF · Max 50 MB</p>
            </>
        }
      </div>

      {/* Selected file */}
      {file && (
        <div className="card p-4 space-y-4">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-primary-500 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
              <p className="text-xs text-gray-400">{formatFileSize(file.size)}</p>
            </div>
            <button onClick={() => { setFile(null); setName(''); }} className="p-1 hover:bg-gray-100 rounded">
              <X className="w-4 h-4 text-gray-400" />
            </button>
          </div>

          <div>
            <label className="label">Document name</label>
            <input className="input" value={name} onChange={e => setName(e.target.value)}
              placeholder="e.g. DHCS Medi-Cal RFP 2025" />
          </div>

          <button onClick={handleUpload} disabled={uploading || !name} className="btn-primary w-full">
            {uploading ? 'Uploading & processing…' : 'Upload document'}
          </button>
        </div>
      )}

      {/* Supported types */}
      <div className="card p-4">
        <p className="text-xs font-medium text-gray-500 mb-3">Supported document types</p>
        <div className="grid grid-cols-2 gap-2">
          {[
            ['📄', 'PDF', 'Grant solicitations, RFPs'],
            ['📝', 'DOCX', 'Proposal templates'],
            ['📊', 'Excel', 'Budget spreadsheets'],
            ['🖼️', 'Image', 'Scanned documents (OCR)'],
          ].map(([icon, type, desc]) => (
            <div key={type} className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg">
              <span className="text-base">{icon}</span>
              <div>
                <p className="text-xs font-medium text-gray-700">{type}</p>
                <p className="text-xs text-gray-400">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
