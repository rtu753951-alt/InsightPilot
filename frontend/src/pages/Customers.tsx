import { useMemo, useState, useEffect, useRef } from "react";
import { MessageCircle, Smartphone, Phone } from "lucide-react";
import { getFollowupSuggestion, importCustomersCSV, listCustomers, loadDemoData, type CustomerOut } from "../services/customersApi";

function formatMoney(n: number) {
  return n.toLocaleString();
}

function getMembershipLabel(type: string) {
  const t = (type || "").toUpperCase();
  if (t === "VIP") return "VIP會員";
  if (t === "STANDARD") return "標準會員";
  if (t === "BASIC") return "一般會員";
  return type || "-";
}

function pillStyle(level: "low" | "medium" | "high"): React.CSSProperties {
  const base: React.CSSProperties = {
    display: "inline-block",
    padding: "4px 10px",
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 600,
    border: "1px solid #e5e7eb",
  };

  if (level === "high") return { ...base, background: "#fee2e2", borderColor: "#fecaca" };
  if (level === "medium") return { ...base, background: "#fef9c3", borderColor: "#fde68a" };
  return { ...base, background: "#dcfce7", borderColor: "#bbf7d0" };
}

const cardStyle: React.CSSProperties = {
  border: "1px solid #e5e7eb",
  borderRadius: 12,
  padding: 12,
  background: "#fff",
  boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
};

const cardLabel: React.CSSProperties = { fontSize: 12, color: "#6b7280" };
const cardValue: React.CSSProperties = { fontSize: 28, fontWeight: 700, marginTop: 6 };
const cardHint: React.CSSProperties = { fontSize: 12, color: "#9ca3af", marginTop: 4 };

const modalBackdrop: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.4)",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  zIndex: 999,
};

const modalBox: React.CSSProperties = {
  background: "#fff",
  padding: 20,
  width: 600,
  maxHeight: "80vh",
  overflow: "auto",
  borderRadius: 12,
};

export default function CustomersPage() {
  const [file, setFile] = useState<File | null>(null);
  const [rows, setRows] = useState<CustomerOut[]>([]);
  const [total, setTotal] = useState(0); // New state for total count
  const [status, setStatus] = useState<string>("請先選擇 CSV 檔並匯入，或按 重新整理 載入資料庫中的資料。");
  const [loading, setLoading] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [suggestion, setSuggestion] = useState<any | null>(null);
  const [suggestionStatus, setSuggestionStatus] = useState<Record<string, "loading" | "done">>({});

  // Pagination input state
  const [jumpPage, setJumpPage] = useState("1");

  // Filters
  const [filterMembership, setFilterMembership] = useState("all");
  const [filterRisk, setFilterRisk] = useState("all");


  useEffect(() => {
    console.log("CustomersPage MOUNTED");
    return () => console.log("CustomersPage UNMOUNTED");
  }, []);

  const lastDoneTimeRef = useRef<Record<string, number>>({});

  console.log("Render CustomersPage. suggestionStatus:", suggestionStatus);


  const [limit, setLimit] = useState(100);
  const [offset, setOffset] = useState(0);

  const page = useMemo(() => Math.floor(offset / limit) + 1, [offset, limit]);
  const totalPages = useMemo(() => Math.ceil(total / limit) || 1, [total, limit]);

  // Sync jumpPage with current page when page changes via buttons
  useEffect(() => {
    setJumpPage(String(page));
  }, [page]);

  const kpi = useMemo(() => {
    const loadedCount = rows.length; // items on this page
    const vip = rows.filter(r => r.membership_type?.toUpperCase() === "VIP").length;
    const high = rows.filter(r => r.risk_level === "high").length;
    const avgDays = loadedCount ? Math.round(rows.reduce((s, r) => s + (r.days_since_last_visit ?? 0), 0) / loadedCount) : 0;
    return { total: loadedCount, vip, high, avgDays };
  }, [rows]);


  async function refresh(target?: { limit?: number; offset?: number }) {
    const nextLimit = target?.limit ?? limit;
    const nextOffset = target?.offset ?? offset;

    // Use current state unless overridden (careful with closures, but for simple refresh button is fine)
    // Actually best to use the state values directly.
    // If called from an effect when filter changes, we might want to reset offset to 0.

    setLoading(true);
    setStatus("Loading customers...");
    try {
      const data = await listCustomers({ 
        limit: nextLimit, 
        offset: nextOffset,
        membership_type: filterMembership,
        risk_level: filterRisk
      });
      setRows(data.items);
      setTotal(data.total);
      setHasLoaded(true);
      setStatus(`Loaded ${data.items.length} customers (Total ${data.total}).`);
    } catch (e) {
      setStatus(`❌ ${String(e)}`);
    } finally {
      setLoading(false);
    }
  }

  // Trigger refresh when filters change (reset to page 1)
  useEffect(() => {
     if (!hasLoaded && !file) return; // Don't auto load heavily on mount if empty? Or maybe yes.
     // Let's assume user wants to see data.
     if (hasLoaded) { // Only auto-refresh if we already have data loaded once implies Intent
        setOffset(0);
        refresh({ offset: 0 });
     }
  }, [filterMembership, filterRisk]);

  async function onImport() {
    if (!file) {
      setStatus("Please choose a CSV file first.");
      return;
    }
    setLoading(true);
    setStatus("Importing CSV...");
    try {
      const r = await importCustomersCSV(file);
      setStatus(`✅ Imported. inserted=${r.inserted}, updated=${r.updated}, total_rows=${r.total_rows}`);

      // 匯入後回到第一頁，並拉回第一頁資料
      setOffset(0);
      await refresh({ offset: 0 });
    } catch (e) {
      setStatus(`❌ ${String(e)}`);
    } finally {
      setLoading(false);
    }
  }



  return (
    <div style={{ padding: 24, fontFamily: "system-ui" }}>
      <style>{`
        button, a, input[type="button"], input[type="submit"] {
          cursor: pointer;
        }
        button:disabled {
          cursor: not-allowed;
        }
      `}</style>
      <h1 style={{ marginBottom: 8 }}>顧客洞悉</h1>

      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button onClick={onImport} disabled={loading}>
          匯入 CSV
        </button>
        
        {/* Filters */}
        <select value={filterMembership} onChange={(e) => setFilterMembership(e.target.value)} disabled={loading}>
            <option value="all">會員等級: 全部</option>
            <option value="VIP">VIP會員</option>
            <option value="Standard">標準會員</option>
            <option value="Basic">一般會員</option>
        </select>

        <select value={filterRisk} onChange={(e) => setFilterRisk(e.target.value)} disabled={loading}>
            <option value="all">流失風險: 全部</option>
            <option value="high">High (需跟進)</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
        </select>


        <a href="/demo_customers.csv" download style={{ textDecoration: "none" }}>
          <button type="button">下載範例 CSV</button>
        </a>

        <button
          onClick={async () => {
            if (!confirm("確定要清除現有資料並載入範例資料嗎？")) return;
            setLoading(true);
            setStatus("載入範例資料中...");
            try {
              const res = await loadDemoData();
              setStatus(`✅ 已載入範例資料，共 ${res.rows} 筆`);
              setOffset(0);
              await refresh({ offset: 0 });
            } catch (e) {
              setStatus(`❌ ${String(e)}`);
            } finally {
              setLoading(false);
            }
          }}
          disabled={loading}
        >
          🚀 載入範例資料
        </button>

        <button onClick={() => refresh()} disabled={loading}>
          重新整理
        </button>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <label>
            限制{" "}
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              disabled={loading || !hasLoaded}
            >
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
            </select>
          </label>

          <button
            onClick={async () => {
              const next = Math.max(0, offset - limit);
              setOffset(next);
              await refresh({ offset: next });
            }}
            disabled={!hasLoaded || loading || offset === 0}
          >
            上一頁
          </button>

          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
           第
           <input 
             type="number"
             min={1}
             max={totalPages}
             value={jumpPage} 
             onChange={(e) => setJumpPage(e.target.value)}
             onBlur={() => {
                let p = parseInt(jumpPage);
                if (isNaN(p) || p < 1) p = 1;
                if (p > totalPages) p = totalPages;
                if (p !== page) {
                   const nextOffset = (p - 1) * limit;
                   setOffset(nextOffset);
                   refresh({ offset: nextOffset });
                } else {
                   setJumpPage(String(page));
                }
             }}
             onKeyDown={(e) => {
               if (e.key === "Enter") {
                  e.currentTarget.blur();
               }
             }}
             style={{ width: 50, textAlign: "center" }}
             disabled={!hasLoaded || loading}
           />
           頁 / 共 {totalPages} 頁
          </span>

          <button
            onClick={async () => {
              const next = offset + limit;
              setOffset(next);
              await refresh({ offset: next });
            }}
            disabled={!hasLoaded || loading || page >= totalPages}
          >
            下一頁
          </button>

        </div>
      </div>

{hasLoaded && (
  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(160px, 1fr))", gap: 12, marginBottom: 12 }}>
    <div style={cardStyle}>
      <div style={cardLabel}>本頁顧客</div>
      <div style={cardValue}>{kpi.total}</div>
      <div style={cardHint}>位顧客</div>
    </div>
    <div style={cardStyle}>
      <div style={cardLabel}>VIP</div>
      <div style={cardValue}>{kpi.vip}</div>
      <div style={cardHint}>位於本頁</div>
    </div>
    <div style={cardStyle}>
      <div style={cardLabel}>高風險</div>
      <div style={cardValue}>{kpi.high}</div>
      <div style={cardHint}>需立即跟進</div>
    </div>
    <div style={cardStyle}>
      <div style={cardLabel}>平均未訪天數</div>
      <div style={cardValue}>{kpi.avgDays}</div>
      <div style={cardHint}>排除今日</div>
    </div>
  </div>
)}

      <p style={{ marginTop: 0 }}>{status}</p>

      <div style={{ overflowX: "auto" }}>
        <table cellPadding={8} style={{ borderCollapse: "collapse", minWidth: 900 }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>
              <th>顧客代碼</th>
              <th>會員等級</th>
              <th>總消費額</th>
              <th>來訪次數</th>
              <th>最近來訪</th>
              <th>未訪天數</th>
              <th>流失風險</th>
              <th>風險原因</th>
              <th>AI 建議</th>

            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id} style={{ borderBottom: "1px solid #f0f0f0" }}>
                <td>{c.customer_code}</td>
                <td>{getMembershipLabel(c.membership_type)}</td>
                <td>{formatMoney(c.total_spent)}</td>
                <td>{c.visit_count}</td>
                <td>{c.last_visit_date}</td>
                <td>{c.days_since_last_visit}</td>
                <td>
                 <span style={pillStyle(c.risk_level)}>
                  {c.risk_level.toUpperCase()}
                   </span>
                </td>
                <td style={{ maxWidth: 360, color: "#6b7280" }}>{c.risk_reason}</td>
                <td>
                  <button
                    type="button"
                    onClick={async () => {
                      const idStr = String(c.id);
                      const current = suggestionStatus[idStr] || "idle";

                      if (current === "done") {
                        // Debounce reset: ignore if done within last 2 seconds
                        const lastDone = lastDoneTimeRef.current[idStr] || 0;
                        if (Date.now() - lastDone < 2000) {
                           console.log("Ignoring click (debounce) for:", idStr);
                           return;
                        }

                        // Reset to idle
                        console.log("Resetting to idle:", idStr);
                        setSuggestionStatus((prev) => {
                          const next = { ...prev };
                          delete next[idStr];
                          return next;
                        });
                        return;
                      }

                      if (current === "loading") return;

                      // Start loading
                      setSuggestionStatus((prev) => ({ ...prev, [idStr]: "loading" }));
                      
                      try {
                        const data = await getFollowupSuggestion(c.id);
                        console.log("API Success for ID:", idStr, data);
                        setSuggestion(data);
                        // Mark as done
                        setSuggestionStatus((prev) => {
                           console.log("Updating status to DONE for:", idStr);
                           lastDoneTimeRef.current[idStr] = Date.now(); // Update timestamp
                           return { ...prev, [idStr]: "done" };
                        });
                      } catch (e) {
                        console.error("Error loading suggestion:", e);
                        alert(String(e));
                        // Error -> reset to idle
                        setSuggestionStatus((prev) => {
                          const next = { ...prev };
                          delete next[idStr];
                          return next;
                        });
                      }
                    }}
                    style={{ 
                      cursor: "pointer", 
                      minWidth: 80 
                    }}
                    disabled={suggestionStatus[String(c.id)] === "loading"}
                  >
                    {suggestionStatus[String(c.id)] === "loading" || suggestionStatus[String(c.id)] === "done" ? "✅ 已產生" : "🤖 建議"}
                  </button>
                </td>
              </tr>
            ))}

            {!hasLoaded && (
              <tr>
                <td colSpan={9} style={{ padding: 16 }}>
                  尚未載入資料。請匯入 CSV 或按 <b>重新整理</b>。
                </td>
              </tr>
            )}

            {hasLoaded && rows.length === 0 && (
              <tr>
                <td colSpan={9} style={{ padding: 16 }}>
                  已載入，但目前沒有資料（DB 可能是空的）。
                </td>
              </tr>
            )}

            {hasLoaded && rows.length > 0 && page === totalPages && (
               <tr>
                 <td colSpan={9} style={{ padding: 16, textAlign: "center", fontStyle: "italic", color: "#666" }}>
                   這是最後一筆~
                 </td>
               </tr>
            )}


          </tbody>
        </table>
      </div>

      {suggestion && (
        <div style={modalBackdrop} onClick={() => setSuggestion(null)}>
          <div style={modalBox} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
              <h2 style={{ margin: 0 }}>🤖 AI 跟進建議</h2>
              <button onClick={() => setSuggestion(null)} style={{ border: "none", background: "transparent", cursor: "pointer", fontSize: 20 }}>
                ✕
              </button>
            </div>

            <div style={{ padding: "12px", background: "#f3f4f6", borderRadius: 8, marginBottom: 16 }}>
              <strong>總結：</strong> {suggestion.summary}
            </div>

            <h3 style={{ fontSize: 16, marginBottom: 8 }}>📋 建議行動 (Next Actions)</h3>
            <ul style={{ marginBottom: 16, paddingLeft: 24 }}>
              {suggestion.next_actions?.map((action: string, idx: number) => (
                <li key={idx} style={{ marginBottom: 4 }}>{action}</li>
              ))}
            </ul>

            <h3 style={{ fontSize: 16, marginBottom: 8 }}>💬 溝通腳本 (Scripts)</h3>
            <div style={{ display: "grid", gap: 12 }}>
              {Object.entries(suggestion.scripts || {}).map(([channel, content]) => {
                let icon = <MessageCircle size={18} />;
                let label = "Line";
                const c = channel.toLowerCase();
                if (c === "sms") {
                   icon = <Smartphone size={18} />;
                   label = "簡訊 (SMS)";
                } else if (c === "call") {
                   icon = <Phone size={18} />;
                   label = "電話 (Call)";
                }

                return (
                  <div key={channel} style={{ border: "1px solid #eee", padding: 12, borderRadius: 8 }}>
                    <div style={{ fontWeight: 600, marginBottom: 4, display: "flex", alignItems: "center", gap: 6, color: "#4b5563" }}>
                      {icon} {label}
                    </div>
                    <div style={{ whiteSpace: "pre-wrap", color: "#374151" }}>{content as string}</div>
                  </div>
                );
              })}
            </div>
            
            <div style={{ marginTop: 20, textAlign: "right" }}>
              <button onClick={() => setSuggestion(null)}>關閉</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
