// import React, { useState, useEffect, useRef } from 'react';
import React, { useState, useEffect } from 'react';
import {
  Plus,
  Upload,
  DollarSign,
  AlertCircle,
  ArrowRight,
  Sparkles,
  Clock,
  ArrowLeftRight,
  CheckCircle,
  RefreshCw,
  Users,
  FileSpreadsheet,
  Eye
} from 'lucide-react';

const API_BASE = 'https://expense-o64l.onrender.com'; // Django API base

interface GroupMember {
  id: number;
  username: string;
  joined_at: string;
  left_at: string | null;
}

interface Group {
  id: number;
  name: string;
}

interface Split {
  username: string;
  amount: number;
}

interface Expense {
  id: number;
  description: string;
  amount: number;
  paid_by: string;
  date: string;
  original_currency: string;
  original_amount: number;
  exchange_rate: number;
  splits: Split[];
}

interface Payment {
  id: number;
  from_user: string;
  to_user: string;
  amount: number;
  date: string;
}

interface Anomaly {
  type: string;
  severity: string;
  message: string;
  column: string;
  suggested: string;
}

interface CSVRow {
  row_index: number;
  exclude?: boolean;
  original_row: {
    Date: string;
    Description: string;
    Amount: string;
    "Paid By": string;
    Currency: string;
    splits: Record<string, string>;
  };
  anomalies: Anomaly[];
  suggested_row: {
    Date: string;
    Description: string;
    Amount: string;
    "Paid By": string;
    Currency: string;
    original_currency: string;
    original_amount: string;
    exchange_rate: string;
    splits: Record<string, string>;
    split_type: string;
    is_settlement: boolean;
    is_personal: boolean;
  };
}

interface LedgerItem {
  type: string;
  date: string;
  description: string;
  total_amount: number;
  your_share: number;
  owed_by_others?: number;
  paid_by: string;
  details: string;
}

interface LedgerDetails {
  username: string;
  ledger_items: LedgerItem[];
  calculated_balance: number;
}

export default function App() {
  // Authentication & Group Context
  const [currentUser, setCurrentUser] = useState<string | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [groupDetails, setGroupDetails] = useState<{ name: string; members: GroupMember[] } | null>(null);
  
  // App Tabs: 'dashboard' | 'timeline' | 'importer' | 'history'
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  
  // Dashboard & Balances State
  const [balances, setBalances] = useState<Record<string, number>>({});
  const [simplifiedPayments, setSimplifiedPayments] = useState<Array<{ from_user: string; to_user: string; amount: number }>>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  
  // Rohan's Ledger Modal State
  const [viewLedgerUser, setViewLedgerUser] = useState<string | null>(null);
  const [ledgerDetails, setLedgerDetails] = useState<LedgerDetails | null>(null);
  
  // CSV Importer State
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [dryRunRows, setDryRunRows] = useState<CSVRow[]>([]);
  const [importReport, setImportReport] = useState<any | null>(null);
  const [isDryRunLoading, setIsDryRunLoading] = useState<boolean>(false);
  const [isImportConfirmLoading, setIsImportConfirmLoading] = useState<boolean>(false);
  
  // Forms & Modal State
  const [showExpenseModal, setShowExpenseModal] = useState<boolean>(false);
  const [showPaymentModal, setShowPaymentModal] = useState<boolean>(false);
  const [showGroupModal, setShowGroupModal] = useState<boolean>(false);
  
  // New Expense form state
  const [expDesc, setExpDesc] = useState<string>('');
  const [expAmount, setExpAmount] = useState<string>('');
  const [expPayer, setExpPayer] = useState<string>('');
  const [expDate, setExpDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [expCurrency, setExpCurrency] = useState<string>('INR');
  const [expSplitType, setExpSplitType] = useState<string>('EQUAL');
  const [expSplitValues, setExpSplitValues] = useState<Record<string, string>>({}); // user -> value (percent/share/exact)
  
  // New Payment form state
  const [payFrom, setPayFrom] = useState<string>('');
  const [payTo, setPayTo] = useState<string>('');
  const [payAmount, setPayAmount] = useState<string>('');
  const [payDate, setPayDate] = useState<string>(new Date().toISOString().split('T')[0]);
  
  // New Group form state
  const [groupName, setGroupName] = useState<string>('');

  // Auto-login standard user initially
  useEffect(() => {
    const saved = localStorage.getItem('expenses_current_user');
    if (saved) {
      setCurrentUser(saved);
    } else {
      setCurrentUser('aisha'); // Default to Aisha
    }
  }, []);

  // Fetch groups
  useEffect(() => {
    fetch(`${API_BASE}/groups/`)
      .then(res => res.json())
      .then(data => {
        setGroups(data);
        if (data.length > 0) {
          setSelectedGroupId(data[0].id);
        }
      });
  }, []);

  // Fetch group details and data when active group changes
  useEffect(() => {
    if (selectedGroupId) {
      fetchGroupData(selectedGroupId);
    }
  }, [selectedGroupId]);

  // Fetch Rohan's Ledger Details when requested
  useEffect(() => {
    if (selectedGroupId && viewLedgerUser) {
      fetch(`${API_BASE}/groups/${selectedGroupId}/ledger/${viewLedgerUser}/`)
        .then(res => res.json())
        .then(data => setLedgerDetails(data));
    } else {
      setLedgerDetails(null);
    }
  }, [selectedGroupId, viewLedgerUser, expenses, payments]);

  const fetchGroupData = (groupId: number) => {
    // 1. Group Details
    fetch(`${API_BASE}/groups/${groupId}/`)
      .then(res => res.json())
      .then(data => setGroupDetails(data));

    // 2. Balances & simplified paths
    fetch(`${API_BASE}/groups/${groupId}/balances/`)
      .then(res => res.json())
      .then(data => {
        setBalances(data.balances);
        setSimplifiedPayments(data.simplified_payments);
      });

    // 3. Expenses log
    fetch(`${API_BASE}/groups/${groupId}/expenses/`)
      .then(res => res.json())
      .then(data => setExpenses(data));

    // 4. Payments log
    fetch(`${API_BASE}/groups/${groupId}/payments/`)
      .then(res => res.json())
      .then(data => setPayments(data));
  };

  const handleUserSwitch = (username: string) => {
    setCurrentUser(username);
    localStorage.setItem('expenses_current_user', username);
  };

  const handleCreateGroup = (e: React.FormEvent) => {
    e.preventDefault();
    if (!groupName.trim()) return;

    fetch(`${API_BASE}/groups/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: groupName })
    })
      .then(res => res.json())
      .then(data => {
        setGroups(prev => [...prev, { id: data.id, name: data.name }]);
        setSelectedGroupId(data.id);
        setShowGroupModal(false);
        setGroupName('');
      });
  };

  const handleCreateExpense = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGroupId || !expDesc || !expAmount || !expPayer || !expDate) return;

    // Build splits based on active group members on that date
    const amountNum = parseFloat(expAmount);
    const activeMembers = getActiveMembersOnDate(expDate);
    
    let splits: any[] = [];
    
    if (expSplitType === 'EQUAL') {
      const share = amountNum / activeMembers.length;
      splits = activeMembers.map(m => ({ username: m.username, amount: share, value: 1 }));
    } else {
      // EXACT, PERCENT, or SHARE mapping
      let totalValue = 0;
      activeMembers.forEach(m => {
        totalValue += parseFloat(expSplitValues[m.username] || '0');
      });

      splits = activeMembers.map(m => {
        const val = parseFloat(expSplitValues[m.username] || '0');
        let amt = 0;
        if (expSplitType === 'PERCENT') {
          amt = amountNum * (val / 100);
        } else if (expSplitType === 'SHARE') {
          amt = amountNum * (val / totalValue);
        } else { // EXACT
          amt = val;
        }
        return {
          username: m.username,
          amount: amt,
          value: val
        };
      });
    }

    const payload = {
      description: expDesc,
      amount: amountNum,
      paid_by: expPayer,
      date: expDate,
      original_currency: expCurrency,
      original_amount: amountNum,
      exchange_rate: 1.0,
      split_type: expSplitType,
      splits: splits
    };

    fetch(`${API_BASE}/groups/${selectedGroupId}/expenses/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(res => {
        if (!res.ok) {
          return res.json().then(d => { throw new Error(d.error); });
        }
        return res.json();
      })
      .then(() => {
        fetchGroupData(selectedGroupId);
        setShowExpenseModal(false);
        // Reset form
        setExpDesc('');
        setExpAmount('');
        setExpPayer('');
        setExpSplitValues({});
      })
      .catch(err => alert(err.message));
  };

  const handleCreatePayment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGroupId || !payFrom || !payTo || !payAmount || !payDate) return;

    fetch(`${API_BASE}/groups/${selectedGroupId}/payments/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from_user: payFrom,
        to_user: payTo,
        amount: parseFloat(payAmount),
        date: payDate
      })
    })
      .then(() => {
        fetchGroupData(selectedGroupId);
        setShowPaymentModal(false);
        setPayAmount('');
      });
  };

  // CSV Parsing Flow
  const handleCSVUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    setCsvFile(e.target.files[0]);
    setDryRunRows([]);
    setImportReport(null);
  };

  const handleDryRun = () => {
    if (!selectedGroupId || !csvFile) return;
    setIsDryRunLoading(true);

    const formData = new FormData();
    formData.append('file', csvFile);

    fetch(`${API_BASE}/groups/${selectedGroupId}/import/dry-run/`, {
      method: 'POST',
      body: formData
    })
      .then(res => res.json())
      .then(data => {
        // Map rows and add editable toggles
        const rows = data.map((r: any) => ({
          ...r,
          exclude: r.exclude_by_default || false
        }));
        setDryRunRows(rows);
        setIsDryRunLoading(false);
      })
      .catch(err => {
        alert(err.message);
        setIsDryRunLoading(false);
      });
  };

  const toggleRowExclude = (idx: number) => {
    setDryRunRows(prev => prev.map(r => r.row_index === idx ? { ...r, exclude: !r.exclude } : r));
  };

  const handleModifySuggestedRow = (idx: number, field: string, value: any) => {
    setDryRunRows(prev => prev.map(r => {
      if (r.row_index === idx) {
        return {
          ...r,
          suggested_row: {
            ...r.suggested_row,
            [field]: value
          }
        };
      }
      return r;
    }));
  };

  const handleModifySuggestedSplits = (idx: number, member: string, val: string) => {
    setDryRunRows(prev => prev.map(r => {
      if (r.row_index === idx) {
        return {
          ...r,
          suggested_row: {
            ...r.suggested_row,
            splits: {
              ...r.suggested_row.splits,
              [member]: val
            }
          }
        };
      }
      return r;
    }));
  };

  const handleConfirmImport = () => {
    if (!selectedGroupId || dryRunRows.length === 0) return;
    setIsImportConfirmLoading(true);

    fetch(`${API_BASE}/groups/${selectedGroupId}/import/confirm/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: csvFile?.name || 'expenses_export.csv',
        rows: dryRunRows
      })
    })
      .then(res => res.json())
      .then(data => {
        setImportReport(data);
        setIsImportConfirmLoading(false);
        fetchGroupData(selectedGroupId);
        setDryRunRows([]);
        setCsvFile(null);
      })
      .catch(err => {
        alert(err.message);
        setIsImportConfirmLoading(false);
      });
  };

  const getActiveMembersOnDate = (dateStr: string) => {
    if (!groupDetails) return [];
    const dateObj = new Date(dateStr);
    return groupDetails.members.filter(m => {
      const join = new Date(m.joined_at);
      const leave = m.left_at ? new Date(m.left_at) : null;
      return dateObj >= join && (!leave || dateObj <= leave);
    });
  };

  const getInactiveMembersOnDate = (dateStr: string) => {
    if (!groupDetails) return [];
    const dateObj = new Date(dateStr);
    return groupDetails.members.filter(m => {
      const join = new Date(m.joined_at);
      const leave = m.left_at ? new Date(m.left_at) : null;
      return dateObj < join || (leave !== null && dateObj > leave);
    });
  };

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="flex-between glass-card animate-fade-in" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            background: 'linear-gradient(135deg, var(--primary), var(--primary-dark))',
            borderRadius: '12px', width: '40px', height: '40px'
          }} className="flex-center">
            <DollarSign size={22} color="#000" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.4rem', color: '#fff' }}>Settled.io</h1>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Premium Shared Expenses App</p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          {/* Group Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Users size={16} color="var(--text-muted)" />
            <select 
              value={selectedGroupId || ''} 
              onChange={e => setSelectedGroupId(parseInt(e.target.value))}
              style={{ width: '180px', padding: '0.5rem' }}
            >
              {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
            <button className="btn btn-secondary" style={{ padding: '0.5rem 0.75rem' }} onClick={() => setShowGroupModal(true)}>
              <Plus size={16} />
            </button>
          </div>

          {/* User Selector Persona switcher */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Viewing as:</span>
            <div style={{ display: 'flex', gap: '0.25rem' }}>
              {['aisha', 'rohan', 'priya', 'meera', 'sam', 'dev'].map(name => (
                <button
                  key={name}
                  onClick={() => handleUserSwitch(name)}
                  className={`btn ${currentUser === name ? 'btn-primary' : 'btn-secondary'}`}
                  style={{
                    padding: '0.35rem 0.65rem', fontSize: '0.8rem', textTransform: 'capitalize',
                    border: currentUser === name ? 'none' : '1px solid var(--border-color)'
                  }}
                >
                  {name}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <div className="grid-2" style={{ gridTemplateColumns: '1fr 3fr', alignItems: 'start' }}>
        {/* Left Sidebar Menu */}
        <aside className="glass-card flex-between animate-fade-in" style={{ flexDirection: 'column', gap: '1.5rem', alignItems: 'stretch' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <button 
              onClick={() => setActiveTab('dashboard')} 
              className={`btn ${activeTab === 'dashboard' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ justifyContent: 'flex-start', width: '100%' }}
            >
              <Sparkles size={16} /> Dashboard & Ledgers
            </button>
            
            <button 
              onClick={() => setActiveTab('timeline')} 
              className={`btn ${activeTab === 'timeline' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ justifyContent: 'flex-start', width: '100%' }}
            >
              <Clock size={16} /> Group Timeline
            </button>
            
            <button 
              onClick={() => setActiveTab('importer')} 
              className={`btn ${activeTab === 'importer' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ justifyContent: 'flex-start', width: '100%' }}
            >
              <FileSpreadsheet size={16} /> CSV Clean Importer
            </button>
          </div>

          <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
            <h3 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Quick Actions</h3>
            <button 
              onClick={() => {
                // Pre-fill payer if not empty
                setExpPayer(currentUser || '');
                setShowExpenseModal(true);
              }} 
              className="btn btn-primary" 
              style={{ width: '100%', marginBottom: '0.5rem' }}
            >
              <Plus size={16} /> Add Expense
            </button>
            <button 
              onClick={() => {
                setPayFrom(currentUser || '');
                setShowPaymentModal(true);
              }} 
              className="btn btn-secondary" 
              style={{ width: '100%' }}
            >
              <ArrowLeftRight size={16} /> Settle Debt
            </button>
          </div>
        </aside>

        {/* Right Dashboard Window */}
        <main style={{ minHeight: '60vh' }}>
          {/* TAB 1: DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              
              {/* Aisha's Section: Simplified debts */}
              <section className="glass-card" style={{ borderLeft: '4px solid var(--primary)' }}>
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Sparkles size={18} color="var(--primary)" />
                    <h2 style={{ fontSize: '1.2rem', color: '#fff' }}>Aisha's Simplified Debt Settlements</h2>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Minimal transaction pathways to completely settle the group's debts.</p>
                </div>
                
                {simplifiedPayments.length === 0 ? (
                  <div className="flex-center" style={{ gap: '0.5rem', padding: '1rem 0' }}>
                    <CheckCircle size={18} color="var(--success)" />
                    <span style={{ color: 'var(--text-muted)' }}>All debts settled! Everyone is even.</span>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                    {simplifiedPayments.map((p, idx) => (
                      <div 
                        key={idx} 
                        style={{
                          background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)',
                          borderRadius: '12px', padding: '1rem', display: 'flex', alignItems: 'center', gap: '1rem',
                          minWidth: '280px'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{ textTransform: 'capitalize', fontWeight: 600 }}>{p.from_user}</span>
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>pays</span>
                          <ArrowRight size={14} color="var(--text-muted)" />
                          <span style={{ textTransform: 'capitalize', fontWeight: 600 }}>{p.to_user}</span>
                        </div>
                        <div style={{ marginLeft: 'auto', fontWeight: 700, color: 'var(--primary)', fontSize: '1.1rem' }}>
                          ₹{p.amount.toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Grid for balances */}
              <section className="grid-3">
                {groupDetails?.members.map(member => {
                  const bal = balances[member.username] || 0;
                  const isCreditor = bal > 0;
                  const isDebtor = bal < 0;
                  return (
                    <div 
                      key={member.username} 
                      className="glass-card" 
                      style={{ 
                        display: 'flex', flexDirection: 'column', gap: '0.75rem',
                        borderBottom: isCreditor ? '3px solid var(--success)' : isDebtor ? '3px solid var(--danger)' : 'none',
                        position: 'relative'
                      }}
                    >
                      <div className="flex-between">
                        <span style={{ textTransform: 'capitalize', fontWeight: 700, fontSize: '1.1rem' }}>{member.username}</span>
                        {isCreditor && <span className="badge badge-success">Owed</span>}
                        {isDebtor && <span className="badge badge-danger">Owes</span>}
                        {bal === 0 && <span className="badge badge-info">Settle</span>}
                      </div>

                      <div style={{ fontSize: '1.8rem', fontWeight: 800, color: isCreditor ? 'var(--success)' : isDebtor ? 'var(--danger)' : '#fff' }}>
                        ₹{Math.abs(bal).toLocaleString()}
                      </div>

                      <button 
                        onClick={() => setViewLedgerUser(member.username)} 
                        className="btn btn-secondary" 
                        style={{ padding: '0.35rem 0.5rem', fontSize: '0.75rem', marginTop: '0.5rem', gap: '0.25rem' }}
                      >
                        <Eye size={12} /> Rohan's Breakdown (Ledger)
                      </button>
                    </div>
                  );
                })}
              </section>

              {/* Transactions Ledger Log */}
              <section className="glass-card">
                <h2 style={{ fontSize: '1.2rem', color: '#fff', marginBottom: '1rem' }}>Expenses & Payments Ledger</h2>
                
                {expenses.length === 0 && payments.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)' }}>No transactions recorded yet in this group.</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {/* Combine and sort by date */}
                    {[
                      ...expenses.map(e => ({ ...e, type: 'EXPENSE' })),
                      ...payments.map(p => ({ ...p, type: 'PAYMENT' }))
                    ]
                      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
                      .map((t: any) => {
                        const isExpense = t.type === 'EXPENSE';
                        return (
                          <div 
                            key={t.id + t.type} 
                            style={{
                              background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-light)',
                              borderRadius: '12px', padding: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between'
                            }}
                          >
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{t.date}</span>
                                {isExpense ? (
                                  <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>Expense</span>
                                ) : (
                                  <span className="badge badge-success" style={{ fontSize: '0.65rem' }}>Settlement</span>
                                )}
                              </div>
                              <h3 style={{ fontSize: '1rem', color: '#fff', marginTop: '0.25rem' }}>
                                {isExpense ? t.description : `${t.from_user} paid ${t.to_user}`}
                              </h3>
                              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                {isExpense ? (
                                  `Paid by ${t.paid_by}. Split amongst: ${t.splits.map((s: any) => s.username).join(', ')}`
                                ) : (
                                  `Direct transfer to settle debt`
                                )}
                              </p>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <div style={{ fontSize: '1.2rem', fontWeight: 700, color: isExpense ? '#fff' : 'var(--success)' }}>
                                {isExpense ? `₹${t.amount}` : `₹${t.amount}`}
                              </div>
                              {isExpense && t.original_currency === 'USD' && (
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                  Original: ${t.original_amount} USD (1 USD = ₹{t.exchange_rate})
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })
                    }
                  </div>
                )}
              </section>
            </div>
          )}

          {/* TAB 2: TIMELINE */}
          {activeTab === 'timeline' && (
            <div className="glass-card animate-fade-in">
              <h2 style={{ fontSize: '1.3rem', color: '#fff', marginBottom: '1.5rem' }}>Flatmates Membership Timeline</h2>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', position: 'relative', paddingLeft: '1.5rem' }}>
                <div style={{
                  position: 'absolute', left: '7px', top: '10px', bottom: '10px',
                  width: '2px', background: 'var(--border-color)'
                }}></div>

                <div style={{ position: 'relative' }}>
                  <div style={{
                    position: 'absolute', left: '-22px', top: '4px',
                    width: '12px', height: '12px', borderRadius: '50%', background: 'var(--success)'
                  }}></div>
                  <h3 style={{ fontSize: '1.1rem', color: '#fff' }}>February 1, 2026</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                    Group created. <strong>Aisha, Rohan, Priya, Meera, and Dev</strong> move in/start tracking expenses in INR and USD.
                  </p>
                </div>

                <div style={{ position: 'relative' }}>
                  <div style={{
                    position: 'absolute', left: '-22px', top: '4px',
                    width: '12px', height: '12px', borderRadius: '50%', background: 'var(--danger)'
                  }}></div>
                  <h3 style={{ fontSize: '1.1rem', color: '#fff' }}>March 31, 2026</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                    <strong>Meera</strong> moves out of the flat. 
                    <span style={{ display: 'block', color: 'var(--warning)', marginTop: '0.25rem' }}>
                      ⚠️ App rule: March electricity affects her, but any expenses dated April 1 or later cannot be split with her.
                    </span>
                  </p>
                </div>

                <div style={{ position: 'relative' }}>
                  <div style={{
                    position: 'absolute', left: '-22px', top: '4px',
                    width: '12px', height: '12px', borderRadius: '50%', background: 'var(--primary)'
                  }}></div>
                  <h3 style={{ fontSize: '1.1rem', color: '#fff' }}>April 15, 2026</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                    <strong>Sam</strong> moves in. 
                    <span style={{ display: 'block', color: 'var(--warning)', marginTop: '0.25rem' }}>
                      ⚠️ App rule: March electricity or early April expenses cannot affect Sam's balance. Only splits on or after April 15 apply.
                    </span>
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: CSV IMPORTER (Meera's Screen) */}
          {activeTab === 'importer' && (
            <div className="glass-card animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.3rem', color: '#fff', marginBottom: '0.25rem' }}>CSV Ingestion Hub (Meera's Review Screen)</h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  Upload the exported CSV. The app automatically detects at least 12 anomalies and proposes clean fixes. Meera's policy: approve anything changes or deletes before importing.
                </p>
              </div>

              {/* Upload Form */}
              <div 
                style={{
                  border: '2px dashed var(--border-color)', borderRadius: '12px', padding: '2rem',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem',
                  background: 'rgba(255,255,255,0.01)'
                }}
              >
                <Upload size={32} color="var(--primary)" />
                <div>
                  <input 
                    type="file" 
                    accept=".csv" 
                    onChange={handleCSVUpload} 
                    style={{ display: 'none' }} 
                    id="csv-file-input" 
                  />
                  <label htmlFor="csv-file-input" className="btn btn-secondary" style={{ cursor: 'pointer' }}>
                    Select CSV File
                  </label>
                  {csvFile && <span style={{ marginLeft: '1rem', color: '#fff' }}>{csvFile.name}</span>}
                </div>
                {csvFile && (
                  <button onClick={handleDryRun} className="btn btn-primary" disabled={isDryRunLoading}>
                    {isDryRunLoading ? <RefreshCw className="animate-spin" size={16} /> : 'Analyze & Detect Anomalies'}
                  </button>
                )}
              </div>

              {/* Import report results */}
              {importReport && (
                <div style={{ background: 'rgba(74, 222, 128, 0.05)', border: '1px solid var(--success)', borderRadius: '12px', padding: '1.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                    <CheckCircle color="var(--success)" size={24} />
                    <h3 style={{ fontSize: '1.2rem', color: '#fff' }}>Import Finished Successfully!</h3>
                  </div>
                  <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
                    <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Expenses Imported</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>{importReport.summary.inserted_expenses}</div>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Direct Payments Imported</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>{importReport.summary.inserted_payments}</div>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Skipped/Excluded Rows</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>{importReport.summary.skipped_rows}</div>
                    </div>
                  </div>

                  <h4 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>Import Report Anomaly Log:</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '200px', overflowY: 'auto' }}>
                    {importReport.anomalies.map((anom: any, idx: number) => (
                      <div key={idx} style={{ background: 'rgba(0,0,0,0.15)', padding: '0.75rem', borderRadius: '8px', fontSize: '0.8rem' }}>
                        <strong>Row {anom.row_index} [{anom.type}]</strong>: {anom.message} <br />
                        <span style={{ color: 'var(--primary)' }}>Action Taken: {anom.action_taken}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Dry Run Interactive Review Grid */}
              {dryRunRows.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  <div className="flex-between">
                    <h3 style={{ fontSize: '1.1rem' }}>Review & Approve Corrections ({dryRunRows.length} Rows Detected)</h3>
                    <button onClick={handleConfirmImport} className="btn btn-primary" disabled={isImportConfirmLoading}>
                      {isImportConfirmLoading ? <RefreshCw className="spin" size={16} /> : 'Approve & Import to Database'}
                    </button>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    {dryRunRows.map((row) => (
                      <div 
                        key={row.row_index} 
                        style={{
                          border: '1px solid var(--border-color)', borderRadius: '12px', padding: '1.25rem',
                          background: row.exclude ? 'rgba(230, 20, 50, 0.02)' : 'rgba(255,255,255,0.02)',
                          opacity: row.exclude ? 0.6 : 1
                        }}
                      >
                        <div className="flex-between" style={{ marginBottom: '1rem', borderBottom: '1px solid var(--border-light)', paddingBottom: '0.5rem' }}>
                          <div>
                            <span style={{ fontWeight: 800, color: 'var(--primary)' }}>Row #{row.row_index}</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginLeft: '0.5rem' }}>
                              Original: {row.original_row.Description} (₹{row.original_row.Amount})
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button 
                              onClick={() => toggleRowExclude(row.row_index)}
                              className={`btn ${row.exclude ? 'btn-danger' : 'btn-secondary'}`}
                              style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
                            >
                              {row.exclude ? 'Excluded' : 'Exclude Row'}
                            </button>
                          </div>
                        </div>

                        {/* Anomalies Box */}
                        {row.anomalies.length > 0 && (
                          <div style={{ background: 'rgba(245, 158, 11, 0.05)', border: '1px solid var(--warning)', borderRadius: '8px', padding: '0.75rem', marginBottom: '1rem' }}>
                            <h4 style={{ fontSize: '0.85rem', color: 'var(--warning)', display: 'flex', alignItems: 'center', gap: '0.25rem', marginBottom: '0.25rem' }}>
                              <AlertCircle size={14} /> Anomaly Detected:
                            </h4>
                            {row.anomalies.map((anom, aIdx) => (
                              <div key={aIdx} style={{ fontSize: '0.8rem', color: 'var(--text-main)' }}>
                                • <strong>[{anom.type}]</strong> {anom.message} <br />
                                <span style={{ color: 'var(--text-muted)', marginLeft: '10px' }}>Fix Policy Applied: {anom.suggested}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Interactive Edit Suggested Row Fields */}
                        <div className="grid-3" style={{ gap: '1rem', marginBottom: '1rem' }}>
                          <div>
                            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Date</label>
                            <input 
                              type="text" 
                              value={row.suggested_row.Date} 
                              onChange={e => handleModifySuggestedRow(row.row_index, 'Date', e.target.value)}
                              disabled={row.exclude}
                              style={{ padding: '0.4rem' }}
                            />
                          </div>
                          <div>
                            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Description</label>
                            <input 
                              type="text" 
                              value={row.suggested_row.Description} 
                              onChange={e => handleModifySuggestedRow(row.row_index, 'Description', e.target.value)}
                              disabled={row.exclude}
                              style={{ padding: '0.4rem' }}
                            />
                          </div>
                          <div>
                            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Payer</label>
                            <input 
                              type="text" 
                              value={row.suggested_row['Paid By']} 
                              onChange={e => handleModifySuggestedRow(row.row_index, 'Paid By', e.target.value)}
                              disabled={row.exclude}
                              style={{ padding: '0.4rem' }}
                            />
                          </div>
                          <div>
                            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Normalized Amount (INR)</label>
                            <input 
                              type="text" 
                              value={row.suggested_row.Amount} 
                              onChange={e => handleModifySuggestedRow(row.row_index, 'Amount', e.target.value)}
                              disabled={row.exclude}
                              style={{ padding: '0.4rem' }}
                            />
                          </div>
                          <div>
                            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Convert USD?</label>
                            <select 
                              value={row.suggested_row.original_currency} 
                              onChange={e => {
                                const curr = e.target.value;
                                const origAmt = parseFloat(row.suggested_row.original_amount);
                                let finalAmt = origAmt;
                                if (curr === 'USD') {
                                  finalAmt = origAmt * 83.0;
                                }
                                handleModifySuggestedRow(row.row_index, 'original_currency', curr);
                                handleModifySuggestedRow(row.row_index, 'Amount', finalAmt.toString());
                              }}
                              disabled={row.exclude}
                              style={{ padding: '0.4rem' }}
                            >
                              <option value="INR">No (INR)</option>
                              <option value="USD">Yes (USD * 83.0)</option>
                            </select>
                          </div>
                          <div>
                            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Record Type</label>
                            <select 
                              value={row.suggested_row.is_settlement ? 'settlement' : 'expense'} 
                              onChange={e => handleModifySuggestedRow(row.row_index, 'is_settlement', e.target.value === 'settlement')}
                              disabled={row.exclude}
                              style={{ padding: '0.4rem' }}
                            >
                              <option value="expense">Expense</option>
                              <option value="settlement">Direct Settlement Payment</option>
                            </select>
                          </div>
                        </div>

                        {/* Interactive Edit Suggested Splits */}
                        {!row.suggested_row.is_settlement && (
                          <div>
                            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>Split Shares</label>
                            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                              {['Aisha', 'Rohan', 'Priya', 'Meera', 'Sam', 'Dev'].map(m => {
                                const val = row.suggested_row.splits[m] || '0';
                                // Determine active timing warning flags for UI
                                const dateStr = row.suggested_row.Date;
                                const isSamInactive = m === 'Sam' && dateStr && new Date(dateStr) < new Date('2026-04-15');
                                const isMeeraInactive = m === 'Meera' && dateStr && new Date(dateStr) > new Date('2026-03-31');
                                return (
                                  <div 
                                    key={m} 
                                    style={{
                                      background: 'rgba(0,0,0,0.2)', padding: '0.35rem 0.5rem', borderRadius: '8px',
                                      display: 'flex', alignItems: 'center', gap: '0.25rem',
                                      border: (isSamInactive || isMeeraInactive) ? '1px solid var(--danger)' : '1px solid transparent'
                                    }}
                                  >
                                    <span style={{ fontSize: '0.75rem', textTransform: 'capitalize', color: (isSamInactive || isMeeraInactive) ? 'var(--danger)' : 'var(--text-main)' }}>{m}:</span>
                                    <input 
                                      type="text" 
                                      value={val} 
                                      onChange={e => handleModifySuggestedSplits(row.row_index, m, e.target.value)}
                                      disabled={row.exclude}
                                      style={{ width: '40px', padding: '0.1rem', background: 'transparent', border: 'none', borderBottom: '1px solid var(--text-dark)', textAlign: 'center' }}
                                    />
                                    {(isSamInactive || isMeeraInactive) && (
                                      <span style={{ fontSize: '0.6rem', color: 'var(--danger)', fontWeight: 'bold' }}>Inactive</span>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Rohan's Ledger Detail Modal */}
      {viewLedgerUser && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.75)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem'
        }}>
          <div className="glass-card animate-fade-in" style={{ width: '100%', maxWidth: '750px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="flex-between" style={{ borderBottom: '1px solid var(--border-light)', paddingBottom: '0.75rem', marginBottom: '1.25rem' }}>
              <div>
                <h2 style={{ fontSize: '1.3rem', textTransform: 'capitalize', color: '#fff' }}>{viewLedgerUser}'s Reconciliation Ledger</h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Rohan's Request: Full transparency. Every expense breakdown displayed here.</p>
              </div>
              <button className="btn btn-secondary" onClick={() => setViewLedgerUser(null)} style={{ padding: '0.35rem 0.75rem' }}>
                Close
              </button>
            </div>

            {ledgerDetails ? (
              <div>
                <div 
                  style={{
                    display: 'flex', justifyContent: 'space-between', background: 'rgba(255,255,255,0.02)',
                    padding: '1rem', borderRadius: '12px', border: '1px solid var(--border-color)', marginBottom: '1.5rem'
                  }}
                >
                  <span style={{ fontWeight: 600 }}>Reconciled Net Balance:</span>
                  <span style={{ fontWeight: 800, color: ledgerDetails.calculated_balance >= 0 ? 'var(--success)' : 'var(--danger)', fontSize: '1.2rem' }}>
                    {ledgerDetails.calculated_balance >= 0 ? '+' : ''}₹{ledgerDetails.calculated_balance.toLocaleString()}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {ledgerDetails.ledger_items.length === 0 ? (
                    <p style={{ color: 'var(--text-muted)' }}>No items found in this ledger.</p>
                  ) : (
                    ledgerDetails.ledger_items.map((item, idx) => {
                      const isOwed = item.type === 'EXPENSE_OWED';
                      const isPaid = item.type === 'EXPENSE_PAID';
                      const isSent = item.type === 'PAYMENT_SENT';
                      const isReceived = item.type === 'PAYMENT_RECEIVED';

                      let color = '#fff';
                      let amountSign = '';
                      if (isOwed) { color = 'var(--danger)'; amountSign = '-'; }
                      if (isPaid) { color = 'var(--success)'; amountSign = '+'; }
                      if (isSent) { color = 'var(--success)'; amountSign = '+'; } // Payment sent increases balance (debt reduction)
                      if (isReceived) { color = 'var(--danger)'; amountSign = '-'; } // Payment received decreases balance (credit reduction)

                      return (
                        <div 
                          key={idx} 
                          style={{
                            background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-light)',
                            borderRadius: '8px', padding: '0.75rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                          }}
                        >
                          <div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              {item.date} • <span style={{ textTransform: 'capitalize' }}>{item.type.replace('_', ' ').toLowerCase()}</span>
                            </div>
                            <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#fff', margin: '0.15rem 0' }}>{item.description}</div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{item.details}</div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: color }}>
                              {amountSign}₹{isPaid ? item.owed_by_others?.toLocaleString() : item.your_share.toLocaleString()}
                            </div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-dark)' }}>
                              Total amount: ₹{item.total_amount.toLocaleString()}
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            ) : (
              <div className="flex-center" style={{ padding: '2rem 0' }}>
                <RefreshCw className="animate-spin" />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal: Create Group */}
      {showGroupModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.75)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <form onSubmit={handleCreateGroup} className="glass-card animate-fade-in" style={{ width: '100%', maxWidth: '400px' }}>
            <h2 style={{ fontSize: '1.2rem', color: '#fff', marginBottom: '1rem' }}>Create Shared Expenses Group</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>Group Name</label>
                <input 
                  type="text" 
                  value={groupName} 
                  onChange={e => setGroupName(e.target.value)} 
                  placeholder="e.g. Flatmates 2026, Trip to USA"
                  required
                />
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowGroupModal(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary">Create Group</button>
            </div>
          </form>
        </div>
      )}

      {/* Modal: Add Expense */}
      {showExpenseModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.75)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem'
        }}>
          <form onSubmit={handleCreateExpense} className="glass-card animate-fade-in" style={{ width: '100%', maxWidth: '500px', maxHeight: '95vh', overflowY: 'auto' }}>
            <h2 style={{ fontSize: '1.2rem', color: '#fff', marginBottom: '1rem' }}>Log Shared Expense</h2>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
              <div className="grid-2">
                <div>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Date</label>
                  <input type="date" value={expDate} onChange={e => setExpDate(e.target.value)} required />
                </div>
                <div>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Payer</label>
                  <select value={expPayer} onChange={e => setExpPayer(e.target.value)} required>
                    <option value="">Select payer</option>
                    {groupDetails?.members.map(m => (
                      <option key={m.username} value={m.username}>{m.username}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Description</label>
                <input type="text" value={expDesc} onChange={e => setExpDesc(e.target.value)} placeholder="e.g. Electricity, Dinner" required />
              </div>

              <div className="grid-2">
                <div>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Amount</label>
                  <input type="number" step="0.01" value={expAmount} onChange={e => setExpAmount(e.target.value)} placeholder="0.00" required />
                </div>
                <div>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Currency</label>
                  <select value={expCurrency} onChange={e => setExpCurrency(e.target.value)}>
                    <option value="INR">INR (₹)</option>
                    <option value="USD">USD ($)</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>Split Type</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {['EQUAL', 'EXACT', 'PERCENT', 'SHARE'].map(t => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setExpSplitType(t)}
                      className={`btn ${expSplitType === t ? 'btn-primary' : 'btn-secondary'}`}
                      style={{ flex: 1, padding: '0.4rem', fontSize: '0.75rem' }}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* Show splits allocations input boxes for active group members on date */}
              {expSplitType !== 'EQUAL' && (
                <div>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>
                    Enter split values ({expSplitType}):
                  </label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {getActiveMembersOnDate(expDate).map(m => (
                      <div key={m.username} className="flex-between" style={{ background: 'rgba(0,0,0,0.15)', padding: '0.4rem 0.8rem', borderRadius: '8px' }}>
                        <span style={{ textTransform: 'capitalize' }}>{m.username}</span>
                        <input
                          type="number"
                          step="0.01"
                          value={expSplitValues[m.username] || ''}
                          onChange={e => setExpSplitValues({ ...expSplitValues, [m.username]: e.target.value })}
                          placeholder={expSplitType === 'PERCENT' ? '%' : expSplitType === 'SHARE' ? 'share' : 'Amount'}
                          style={{ width: '100px', padding: '0.3rem' }}
                          required
                        />
                      </div>
                    ))}
                    {/* Display inactive members on that date */}
                    {getInactiveMembersOnDate(expDate).map(m => (
                      <div key={m.username} className="flex-between" style={{ background: 'rgba(230,20,50,0.05)', padding: '0.4rem 0.8rem', borderRadius: '8px', opacity: 0.5 }}>
                        <span style={{ textTransform: 'capitalize' }}>{m.username}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--danger)' }}>Inactive on this date</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowExpenseModal(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary">Save Expense</button>
            </div>
          </form>
        </div>
      )}

      {/* Modal: Add Settlement Payment */}
      {showPaymentModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.75)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <form onSubmit={handleCreatePayment} className="glass-card animate-fade-in" style={{ width: '100%', maxWidth: '400px' }}>
            <h2 style={{ fontSize: '1.2rem', color: '#fff', marginBottom: '1rem' }}>Record Direct Settlement</h2>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Date</label>
                <input type="date" value={payDate} onChange={e => setPayDate(e.target.value)} required />
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>From User (Payer)</label>
                <select value={payFrom} onChange={e => setPayFrom(e.target.value)} required>
                  <option value="">Select sender</option>
                  {groupDetails?.members.map(m => (
                    <option key={m.username} value={m.username}>{m.username}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>To User (Recipient)</label>
                <select value={payTo} onChange={e => setPayTo(e.target.value)} required>
                  <option value="">Select recipient</option>
                  {groupDetails?.members.map(m => (
                    <option key={m.username} value={m.username}>{m.username}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Settlement Amount (INR)</label>
                <input type="number" step="0.01" value={payAmount} onChange={e => setPayAmount(e.target.value)} placeholder="0.00" required />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowPaymentModal(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary">Record Payment</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
