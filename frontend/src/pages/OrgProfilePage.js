import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Plus, Save, Trash2 } from 'lucide-react';
import { orgApi } from '../utils/api';

const BLANK = {
  name: '', short_name: '', service_area: '', patient_population: '',
  annual_patient_volume: '', certifications: '', specialties: '',
  mission_statement: '', capability_statement: '',
  primary_contact_name: '', primary_contact_email: '', uei_number: '',
};

export default function OrgProfilePage() {
  const qc = useQueryClient();
  const [form, setForm] = useState(BLANK);
  const [editing, setEditing] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const { data: orgs } = useQuery({
    queryKey: ['orgs'],
    queryFn: () => orgApi.list().then(r => r.data.results || r.data),
  });

  const saveMutation = useMutation({
    mutationFn: (data) => editing ? orgApi.update(editing, data) : orgApi.create(data),
    onSuccess: () => {
      toast.success(editing ? 'Profile updated' : 'Profile created');
      qc.invalidateQueries(['orgs']);
      setForm(BLANK); setEditing(null); setShowForm(false);
    },
    onError: () => toast.error('Save failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => orgApi.delete(id),
    onSuccess: () => { toast.success('Profile deleted'); qc.invalidateQueries(['orgs']); },
  });

  function handleEdit(org) {
    setForm({
      ...org,
      certifications: (org.certifications || []).join(', '),
      specialties:    (org.specialties || []).join(', '),
    });
    setEditing(org.id);
    setShowForm(true);
  }

  function handleSubmit(e) {
    e.preventDefault();
    saveMutation.mutate({
      ...form,
      certifications: form.certifications ? form.certifications.split(',').map(s => s.trim()).filter(Boolean) : [],
      specialties:    form.specialties    ? form.specialties.split(',').map(s => s.trim()).filter(Boolean) : [],
      annual_patient_volume: form.annual_patient_volume ? parseInt(form.annual_patient_volume) : null,
    });
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* Existing profiles */}
      {(orgs || []).map(org => (
        <div key={org.id} className="card p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="font-semibold text-gray-900">{org.name}</h3>
              {org.service_area && <p className="text-sm text-gray-500 mt-0.5">{org.service_area}</p>}
              <div className="flex flex-wrap gap-1 mt-2">
                {(org.certifications || []).map(c => <span key={c} className="badge-blue">{c}</span>)}
              </div>
            </div>
            <div className="flex gap-2 flex-shrink-0">
              <button onClick={() => handleEdit(org)} className="btn-secondary text-xs py-1.5 px-3">Edit</button>
              <button onClick={() => { if (window.confirm('Delete this profile?')) deleteMutation.mutate(org.id); }}
                className="p-1.5 hover:bg-red-50 rounded-lg text-gray-300 hover:text-red-500 transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      ))}

      {/* Add button */}
      {!showForm && (
        <button onClick={() => { setForm(BLANK); setEditing(null); setShowForm(true); }}
          className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> {(orgs || []).length ? 'Add another profile' : 'Create organisation profile'}
        </button>
      )}

      {/* Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="card p-5 space-y-4">
          <h2 className="text-base font-semibold text-gray-900">{editing ? 'Edit profile' : 'New organisation profile'}</h2>

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="label">Organisation name *</label>
              <input className="input" required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Valley Health System" />
            </div>
            <div>
              <label className="label">Short name</label>
              <input className="input" value={form.short_name} onChange={e => setForm(f => ({ ...f, short_name: e.target.value }))} placeholder="VHS" />
            </div>
            <div>
              <label className="label">Annual patient volume</label>
              <input className="input" type="number" value={form.annual_patient_volume} onChange={e => setForm(f => ({ ...f, annual_patient_volume: e.target.value }))} placeholder="120000" />
            </div>
            <div className="col-span-2">
              <label className="label">Service area</label>
              <input className="input" value={form.service_area} onChange={e => setForm(f => ({ ...f, service_area: e.target.value }))} placeholder="Santa Clara County, CA" />
            </div>
            <div className="col-span-2">
              <label className="label">Patient population</label>
              <textarea className="input min-h-16" value={form.patient_population} onChange={e => setForm(f => ({ ...f, patient_population: e.target.value }))} placeholder="Medi-Cal beneficiaries, uninsured, underserved communities" />
            </div>
            <div>
              <label className="label">Certifications (comma separated)</label>
              <input className="input" value={form.certifications} onChange={e => setForm(f => ({ ...f, certifications: e.target.value }))} placeholder="HIPAA, HITRUST, SOC 2, Joint Commission" />
            </div>
            <div>
              <label className="label">Specialties (comma separated)</label>
              <input className="input" value={form.specialties} onChange={e => setForm(f => ({ ...f, specialties: e.target.value }))} placeholder="Primary Care, Behavioral Health, Women's Health" />
            </div>
            <div className="col-span-2">
              <label className="label">Mission statement</label>
              <textarea className="input min-h-16" value={form.mission_statement} onChange={e => setForm(f => ({ ...f, mission_statement: e.target.value }))} placeholder="Providing quality healthcare to all community members…" />
            </div>
            <div>
              <label className="label">Primary contact name</label>
              <input className="input" value={form.primary_contact_name} onChange={e => setForm(f => ({ ...f, primary_contact_name: e.target.value }))} />
            </div>
            <div>
              <label className="label">Primary contact email</label>
              <input className="input" type="email" value={form.primary_contact_email} onChange={e => setForm(f => ({ ...f, primary_contact_email: e.target.value }))} />
            </div>
          </div>

          <div className="flex gap-3">
            <button type="submit" disabled={saveMutation.isPending} className="btn-primary flex items-center gap-2">
              <Save className="w-4 h-4" /> {saveMutation.isPending ? 'Saving…' : 'Save profile'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
          </div>
        </form>
      )}
    </div>
  );
}
