import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, FileText, Upload, ClipboardList,
  PlusCircle, Building2, Settings, Menu, X, Activity,
} from 'lucide-react';

const nav = [
  { to: '/',                icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/documents',       icon: FileText,        label: 'Documents' },
  { to: '/documents/upload',icon: Upload,          label: 'Upload Document' },
  { to: '/proposals',       icon: ClipboardList,   label: 'Proposals' },
  { to: '/proposals/new',   icon: PlusCircle,      label: 'New Proposal' },
  { to: '/organisation',    icon: Building2,       label: 'Organisation' },
  { to: '/settings/llm',    icon: Settings,        label: 'LLM Settings' },
];

export default function Layout({ children }) {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const pageTitle = nav.find(n =>
    n.to === '/' ? location.pathname === '/' : location.pathname.startsWith(n.to)
  )?.label || 'Grant Proposal AI';

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-40 w-56 bg-white border-r border-gray-100 flex flex-col transform transition-transform duration-200 ${open ? 'translate-x-0' : '-translate-x-full'} md:relative md:translate-x-0`}>
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 py-4 border-b border-gray-100">
          <div className="w-7 h-7 bg-primary-600 rounded-lg flex items-center justify-center">
            <Activity className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="font-semibold text-gray-900 text-sm leading-none">Grant Proposal</p>
            <p className="text-xs text-gray-400 mt-0.5">Healthcare AI</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {nav.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} end={to === '/'} onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive ? 'bg-primary-50 text-primary-700 font-medium' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}>
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* LLM status */}
        <LLMStatus />
      </aside>

      {/* Mobile overlay */}
      {open && <div className="fixed inset-0 z-30 bg-black/20 md:hidden" onClick={() => setOpen(false)} />}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="bg-white border-b border-gray-100 px-4 md:px-6 py-3 flex items-center gap-3 flex-shrink-0">
          <button className="md:hidden p-1.5 rounded-lg hover:bg-gray-100" onClick={() => setOpen(!open)}>
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          <h1 className="text-base font-semibold text-gray-900">{pageTitle}</h1>
        </header>
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}

function LLMStatus() {
  const [status, setStatus] = React.useState('checking');
  const [provider, setProvider] = React.useState('');

  React.useEffect(() => {
    fetch('/api/llm/health/')
      .then(r => r.json())
      .then(data => {
        const ollama = data.ollama;
        setStatus(ollama?.status === 'healthy' ? 'ok' : 'error');
        setProvider(ollama?.llm_model || '');
      })
      .catch(() => setStatus('error'));
  }, []);

  return (
    <div className="px-4 py-3 border-t border-gray-100">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
          status === 'ok' ? 'bg-health-500' : status === 'error' ? 'bg-red-500' : 'bg-amber-400 animate-pulse'
        }`} />
        <div className="min-w-0">
          <p className="text-xs text-gray-500 truncate">
            {status === 'ok' ? `Ollama · ${provider}` : status === 'error' ? 'Ollama offline' : 'Checking…'}
          </p>
        </div>
      </div>
    </div>
  );
}
