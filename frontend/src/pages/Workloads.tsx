import { useEffect, useState } from 'react';
import { api } from '../lib/api';

type Workload = { id:number; name:string; workload_type:string; initial_load:number; growth_rate:number; duration_seconds:number; current_load:number; active:boolean };
const patterns=['Stable','Increasing','Decreasing','Sudden Spike','Periodic','Random','Anomaly'];
export default function Workloads(){
  const [rows,setRows]=useState<Workload[]>([]); const [form,setForm]=useState({name:'Sudden Spike Demo',workload_type:'Sudden Spike',initial_load:35,growth_rate:1,duration_seconds:60}); const [msg,setMsg]=useState('');
  async function load(){setRows((await api.get('/api/workloads')).data)} useEffect(()=>{load()},[]);
  async function create(){try{await api.post('/api/workloads',form);setMsg('Workload created');load()}catch(e:any){setMsg(e.response?.data?.detail||'Unable to create workload')}}
  async function toggle(w:Workload){try{await api.post(`/api/workloads/${w.id}/${w.active?'stop':'start'}`);load()}catch(e:any){setMsg(e.response?.data?.detail||'Request failed')}}
  return <main><h1 className="text-3xl font-bold">Workloads</h1><p className="text-slate-500 mt-1 mb-6">Create reproducible workload patterns for the closed-loop simulator.</p>
    <section className="bg-white border rounded-xl p-6 mb-6"><h2 className="font-semibold text-lg mb-4">Create Workload</h2><div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      <input className="border rounded-lg p-2" placeholder="Name" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/>
      <select className="border rounded-lg p-2" value={form.workload_type} onChange={e=>setForm({...form,workload_type:e.target.value})}>{patterns.map(x=><option key={x}>{x}</option>)}</select>
      <input className="border rounded-lg p-2" type="number" min="0" max="100" value={form.initial_load} onChange={e=>setForm({...form,initial_load:+e.target.value})}/>
      <input className="border rounded-lg p-2" type="number" value={form.growth_rate} onChange={e=>setForm({...form,growth_rate:+e.target.value})}/>
      <input className="border rounded-lg p-2" type="number" min="1" value={form.duration_seconds} onChange={e=>setForm({...form,duration_seconds:+e.target.value})}/>
    </div><div className="flex items-center gap-3 mt-4"><button onClick={create} className="bg-indigo-600 text-white px-4 py-2 rounded-lg">Create</button>{msg&&<span className="text-sm text-slate-600">{msg}</span>}</div></section>
    <section className="bg-white border rounded-xl p-6"><h2 className="font-semibold text-lg mb-4">Workload Library</h2><div className="overflow-x-auto"><table className="w-full"><thead><tr className="text-left border-b text-slate-500"><th className="py-2">Name</th><th>Pattern</th><th>Initial</th><th>Growth</th><th>Duration</th><th>Status</th><th></th></tr></thead><tbody>{rows.map(w=><tr key={w.id} className="border-b last:border-0"><td className="py-3 font-medium">{w.name}</td><td>{w.workload_type}</td><td>{w.initial_load}%</td><td>{w.growth_rate}</td><td>{w.duration_seconds}s</td><td><span className={`px-2 py-1 rounded-full text-xs ${w.active?'bg-emerald-100 text-emerald-700':'bg-slate-100 text-slate-600'}`}>{w.active?'RUNNING':'STOPPED'}</span></td><td><button onClick={()=>toggle(w)} className="border px-3 py-1 rounded-lg">{w.active?'Stop':'Start'}</button></td></tr>)}</tbody></table>{rows.length===0&&<p className="text-slate-500 py-6">No workloads yet.</p>}</div></section>
  </main>
}
