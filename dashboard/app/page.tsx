"use client";

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { Shield, Database, RefreshCw, Layers } from 'lucide-react';

interface Card {
  id: string;
  card_data: string;
  extracted_at: string;
}

export default function Home() {
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCards();
    // Real-time subscription
    const channel = supabase
      .channel('schema-db-changes')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'cards' },
        (payload) => {
          setCards((prev) => [payload.new as Card, ...prev]);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  async function fetchCards() {
    setLoading(true);
    const { data, error } = await supabase
      .from('cards')
      .select('*')
      .order('extracted_at', { ascending: false });

    if (!error && data) setCards(data);
    setLoading(false);
  }

  return (
    <main className="min-h-screen bg-[#020617] text-slate-200 selection:bg-cyan-500/30">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_-20%,#0ea5e915,transparent)]" />
      
      <div className="max-w-7xl mx-auto px-6 py-12 relative z-10">
        {/* Header */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-12 gap-6 bg-slate-900/40 border border-slate-800/50 p-8 rounded-3xl backdrop-blur-xl">
          <div>
            <h1 className="text-4xl font-black tracking-tighter bg-gradient-to-r from-white via-slate-400 to-slate-600 bg-clip-text text-transparent flex items-center gap-3">
              <Shield className="w-10 h-10 text-cyan-400" />
              PROJECT SCYTHE
            </h1>
            <p className="text-slate-400 mt-2 font-medium tracking-wide">SHADOW CLOUD DOMINANCE: VERCEL CORE</p>
          </div>
          
          <div className="flex gap-4">
            <div className="bg-slate-950/50 border border-slate-800/50 p-4 rounded-2xl flex flex-col items-center min-w-[120px]">
              <span className="text-2xl font-bold text-cyan-400">{cards.length}</span>
              <span className="text-xs text-slate-500 uppercase font-black">Assets Stored</span>
            </div>
            <button 
              onClick={fetchCards}
              className="bg-cyan-600 hover:bg-cyan-500 transition-all p-4 rounded-2xl border border-cyan-400/30 shadow-[0_0_20px_rgba(6,182,212,0.2)] group"
            >
              <RefreshCw className={`w-6 h-6 group-hover:rotate-180 transition-transform duration-500 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </header>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Status Column */}
          <section className="lg:col-span-4 space-y-6">
            <div className="bg-slate-900/30 border border-slate-800/50 p-6 rounded-3xl backdrop-blur-md">
              <h3 className="text-sm font-black uppercase text-slate-500 flex items-center gap-2 mb-4">
                <Database className="w-4 h-4 text-cyan-500" />
                Cloud Status
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center p-3 bg-slate-950/40 rounded-xl border border-slate-800/30">
                  <span className="text-xs font-bold text-slate-400">GH Runner</span>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
                    <span className="text-xs font-black text-cyan-400 uppercase">Synchronized</span>
                  </div>
                </div>
                <div className="flex justify-between items-center p-3 bg-slate-950/40 rounded-xl border border-slate-800/30">
                  <span className="text-xs font-bold text-slate-400">Database</span>
                  <span className="text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2 py-0.5 rounded font-black italic">NOMINAL</span>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-cyan-600/20 to-blue-600/5 border border-cyan-500/10 p-6 rounded-3xl">
              <h3 className="text-sm font-black uppercase text-cyan-400 flex items-center gap-2 mb-2">
                <Layers className="w-4 h-4" />
                Mission Protocol
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed italic">
                Scythe Engine V2 is currently monitoring 50+ channels. All unread vectors are being synchronized and filtered via Scythe Regex Core.
              </p>
            </div>
          </section>

          {/* Cards List Column */}
          <section className="lg:col-span-8">
            <div className="bg-slate-900/20 border border-slate-800/40 rounded-3xl overflow-hidden backdrop-blur-sm">
              <div className="p-6 border-b border-slate-800/50 bg-slate-900/40 flex justify-between items-center">
                <h2 className="font-black text-xs uppercase tracking-[0.2em] text-slate-500 italic">Extracted Vectors</h2>
                <div className="text-[10px] text-slate-600 font-mono">ENCRYPTED STREAM // AES-256</div>
              </div>
              
              <div className="max-h-[600px] overflow-y-auto custom-scrollbar">
                {cards.length === 0 && !loading && (
                  <div className="p-20 text-center text-slate-600 italic">The void is empty. Waiting for next extraction...</div>
                )}
                
                {cards.map((card, idx) => (
                  <div key={card.id} className="p-6 border-b border-slate-800/30 hover:bg-slate-800/20 transition-colors group">
                    <div className="flex justify-between items-center">
                      <div className="font-mono text-lg font-bold group-hover:text-cyan-400 transition-colors tracking-widest bg-slate-950/50 px-4 py-2 rounded-xl border border-slate-800/50">
                        {card.card_data}
                      </div>
                      <div className="text-right">
                        <div className="text-[10px] text-slate-500 font-bold uppercase tracking-tighter">Synchronized At</div>
                        <div className="text-xs font-black text-slate-300 italic">{new Date(card.extracted_at).toLocaleString()}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
