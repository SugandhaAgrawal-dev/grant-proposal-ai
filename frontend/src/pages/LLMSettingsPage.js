import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { CheckCircle, XCircle, Loader, Zap } from 'lucide-react';
import { llmApi } from '../utils/api';

export default function LLMSettingsPage() {
  const [testProvider, setTestProvider] = useState('ollama');
  const [testPrompt,   setTestPrompt]   = useState('In one sentence, what is HIPAA?');
  const [testResult,   setTestResult]   = useState('');

  const { data: health, isLoading, refetch } = useQuery({
    queryKey: ['llm-health'],
    queryFn: () => llmApi.health().then(r => r.data),
  });

  const { data: providers } = useQuery({
    queryKey: ['llm-providers'],
    queryFn: () => llmApi.providers().then(r => r.data),
  });

  const testMutation = useMutation({
    mutationFn: () => llmApi.test({ provider: testProvider, prompt: testPrompt }),
    onSuccess:  (r) => setTestResult(r.data.response),
    onError:    (e) => toast.error(e.response?.data?.error || 'Test failed'),
  });

  return (
    <div className="max-w-2xl space-y-6">

      {/* Provider health */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-900">Provider status</h2>
          <button onClick={() => refetch()} className="btn-secondary text-xs py-1.5 px-3">Refresh</button>
        </div>

        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-gray-400"><Loader className="w-4 h-4 animate-spin" /> Checking…</div>
        ) : (
          <div className="space-y-3">
            {['ollama', 'vertex', 'openai', 'claude'].map(provider => {
              const info   = health?.[provider] || {};
              const isOk   = info.status === 'healthy';
              const isErr  = info.status === 'unavailable' || info.status === 'error';
              return (
                <div key={provider} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                  <div className="flex-shrink-0 mt-0.5">
                    {isOk  ? <CheckCircle className="w-5 h-5 text-health-500" /> :
                     isErr ? <XCircle className="w-5 h-5 text-red-400" /> :
                     <Loader className="w-5 h-5 text-amber-400 animate-spin" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 capitalize">
                      {provider === 'ollama' ? 'Ollama (local)' :
                       provider === 'openai' ? 'OpenAI GPT-4o' :
                       provider === 'vertex' ? 'Vertex AI / Gemini' :
                       'Anthropic Claude'}
                    </p>
                    {isOk && provider === 'ollama' && (
                      <div className="text-xs text-gray-500 space-y-0.5 mt-1">
                        <p>LLM: {info.llm_model} {info.llm_available ? '✓' : '✗ not pulled'}</p>
                        <p>Embed: {info.embed_model} {info.embed_available ? '✓' : '✗ not pulled'}</p>
                      </div>
                    )}
                    {isErr && <p className="text-xs text-red-400 mt-1">{info.error || 'Unavailable'}</p>}
                    {!isOk && !isErr && provider !== 'ollama' && (
                      <p className="text-xs text-gray-400 mt-1">Add API key to .env file</p>
                    )}
                  </div>
                  <span className={`badge flex-shrink-0 ${isOk ? 'badge-green' : isErr ? 'badge-red' : 'badge-yellow'}`}>
                    {isOk ? 'Online' : isErr ? 'Offline' : 'Unknown'}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Ollama setup guide */}
      {health?.ollama?.status !== 'healthy' && (
        <div className="card p-5 border border-amber-200">
          <h3 className="text-sm font-semibold text-amber-800 mb-3">Set up Ollama</h3>
          <div className="space-y-1 text-xs text-gray-600 font-mono bg-gray-50 rounded-lg p-3">
            <p className="text-gray-400"># Install Ollama</p>
            <p>curl -fsSL https://ollama.com/install.sh | sh</p>
            <p className="text-gray-400 mt-2"># Pull required models</p>
            <p>ollama pull llama3.1:8b</p>
            <p>ollama pull nomic-embed-text</p>
          </div>
        </div>
      )}

      {/* Vertex AI setup guide */}
      {health?.vertex?.status !== 'healthy' && (
        <div className="card p-5 border border-blue-200">
          <h3 className="text-sm font-semibold text-blue-800 mb-3">Set up Vertex AI / Gemini</h3>
          <div className="space-y-1 text-xs text-gray-600 font-mono bg-gray-50 rounded-lg p-3">
            <p className="text-gray-400"># Option 1 — Application Default Credentials</p>
            <p>gcloud auth application-default login</p>
            <p className="text-gray-400 mt-2"># Option 2 — Service account key (.env)</p>
            <p>GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json</p>
            <p className="text-gray-400 mt-2"># Required .env settings</p>
            <p>GOOGLE_CLOUD_PROJECT=your-gcp-project-id</p>
            <p>VERTEX_LLM_MODEL=gemini-1.5-pro-002</p>
            <p>VERTEX_EMBED_MODEL=text-embedding-004</p>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Vertex AI is HIPAA-eligible and VPC-SC compatible — recommended for production health data.
          </p>
        </div>
      )}

      {/* Test generation */}
      <div className="card p-5 space-y-4">
        <h2 className="text-base font-semibold text-gray-900">Test generation</h2>
        <div>
          <label className="label">Provider</label>
          <select className="input" value={testProvider} onChange={e => setTestProvider(e.target.value)}>
            <option value="ollama">Ollama (local)</option>
            <option value="vertex">Vertex AI / Gemini</option>
            <option value="openai">OpenAI GPT-4o</option>
            <option value="claude">Anthropic Claude</option>
          </select>
        </div>
        <div>
          <label className="label">Test prompt</label>
          <textarea className="input min-h-16" value={testPrompt} onChange={e => setTestPrompt(e.target.value)} />
        </div>
        <button onClick={() => testMutation.mutate()} disabled={testMutation.isPending}
          className="btn-primary flex items-center gap-2">
          <Zap className="w-4 h-4" />
          {testMutation.isPending ? 'Generating…' : 'Run test'}
        </button>

        {testResult && (
          <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
            <p className="text-xs font-medium text-gray-500 mb-2">Response from {testProvider}:</p>
            <p className="text-sm text-gray-700">{testResult}</p>
          </div>
        )}
      </div>

      {/* Default provider info */}
      <div className="card p-5">
        <h2 className="text-base font-semibold text-gray-900 mb-2">Default provider</h2>
        <p className="text-sm text-gray-600">
          Current default: <span className="font-medium">{providers?.default || 'ollama'}</span>
        </p>
        <p className="text-xs text-gray-400 mt-1">Change via <code className="bg-gray-100 px-1 rounded">DEFAULT_LLM_PROVIDER</code> in your <code className="bg-gray-100 px-1 rounded">.env</code> file.</p>
      </div>
    </div>
  );
}
