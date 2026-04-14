import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Dashboard      from './pages/Dashboard';
import DocumentsPage  from './pages/DocumentsPage';
import UploadPage     from './pages/UploadPage';
import ProposalsPage  from './pages/ProposalsPage';
import ProposalDetail from './pages/ProposalDetail';
import NewProposal    from './pages/NewProposal';
import OrgProfilePage from './pages/OrgProfilePage';
import LLMSettingsPage from './pages/LLMSettingsPage';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/"                    element={<Dashboard />} />
        <Route path="/documents"           element={<DocumentsPage />} />
        <Route path="/documents/upload"    element={<UploadPage />} />
        <Route path="/proposals"           element={<ProposalsPage />} />
        <Route path="/proposals/new"       element={<NewProposal />} />
        <Route path="/proposals/:id"       element={<ProposalDetail />} />
        <Route path="/organisation"        element={<OrgProfilePage />} />
        <Route path="/settings/llm"        element={<LLMSettingsPage />} />
        <Route path="*"                    element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
