import React from "react";
import { useApi } from "../hooks/useApi";
import { api } from "../utils/api";
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, BarChart, Bar
} from "recharts";
import { AlertTriangle, TrendingDown, Zap } from "lucide-react";

function StatPill({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, padding: "10px 14px", flex: 1 }}>
      <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--font-mono)", color }}>{value}</div>
    </div>
  );
}

export default function ForecastPage() {
  const { data: slippage, loading: sl } = useApi(() => api.getSlippage());
  const { data: velocity, loading: vl } = useApi(() => api.getVelocity());
  const { data: burndown } = useApi(() => api.getBurndown());

  if (sl || vl) return <div className="loading-spinner"><div className="pulse" />Loading forecast...</div>;

  const currentProb  = slippage?.current_probability ?? 0.63;
  const probPct      = Math.round(currentProb * 100);
  const probColor    = currentProb >= 0.8 ? "var(--green)" : currentProb >= 0.6 ? "var(--amber)" : "var(--red)";

  const forecastData = (slippage?.forecast ?? []).map((f: any) => ({
    day: `D${f.day}`, prob: Math.round(f.completion_probability * 100),
    remaining: f.remaining_points, date: f.date,
  }));

  const velHistory = (velocity?.history ?? []).map((v: number, i: number) => ({
    sprint: `S${i + 1}`, velocity: v, avg: velocity?.average,
  }));

  const burndownChart = burndown
    ? burndown.days.map((d: string, i: number) => ({
        day: d, ideal: burndown.ideal[i], actual: burndown.actual[i] ?? undefined,
      }))
    : [];

  const riskColors: Record<string, string> = {
    high: "var(--red)", medium: "var(--amber)", low: "var(--accent)"
  };

  return (
    <div className="page-enter">
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Slippage Forecast</h1>
          <p style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: 12 }}>
            Monte-Carlo simulation &middot; Sprint 9 &middot; 10 000 runs/day
          </p>
        </div>
        <div style={{ ...styles.probCard, borderColor: probColor }}>
          <TrendingDown size={20} color={probColor} />
          <div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-mono)", color: probColor, lineHeight: 1 }}>{probPct}%</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>Day {slippage?.current_day} &middot; {slippage?.trend}</div>
          </div>
        </div>
      </div>

      {/* TODO 1 — Completion Probability + Remaining Points */}
      <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
        <div style={{ flex: 2, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 16 }}>
          <div style={styles.cardTitle}>Completion Probability — Daily</div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={forecastData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="pGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--amber)" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="var(--amber)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: "var(--text-muted)" }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "var(--text-muted)" }} tickFormatter={(v) => `${v}%`} />
              <Tooltip formatter={(v: any) => `${v}%`} contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
              <ReferenceLine y={80} stroke="var(--green)" strokeDasharray="4 2" label={{ value: "80%", fontSize: 9, fill: "var(--green)" }} />
              <ReferenceLine y={60} stroke="var(--amber)" strokeDasharray="4 2" label={{ value: "60%", fontSize: 9, fill: "var(--amber)" }} />
              <Area type="monotone" dataKey="prob" stroke="var(--amber)" fill="url(#pGrad)" strokeWidth={2} dot={{ r: 3, fill: "var(--amber)" }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div style={{ flex: 1.5, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 16 }}>
          <div style={styles.cardTitle}>Remaining Points</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={forecastData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: "var(--text-muted)" }} />
              <YAxis tick={{ fontSize: 10, fill: "var(--text-muted)" }} />
              <Tooltip contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="remaining" fill="var(--accent)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* TODO 2 — Burndown + Velocity */}
      <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
        <div style={{ flex: 1.5, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 16 }}>
          <div style={styles.cardTitle}>Burndown — Actual vs Ideal</div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={burndownChart} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: "var(--text-muted)" }} />
              <YAxis tick={{ fontSize: 10, fill: "var(--text-muted)" }} />
              <Tooltip contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
              <Line type="monotone" dataKey="ideal" stroke="var(--border)" strokeDasharray="5 3" strokeWidth={1.5} dot={false} name="Ideal" />
              <Line type="monotone" dataKey="actual" stroke="var(--accent)" strokeWidth={2} connectNulls={false} dot={{ r: 3, fill: "var(--accent)" }} name="Actual" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div style={{ flex: 1, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 16 }}>
          <div style={styles.cardTitle}>Velocity History</div>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <StatPill label="Avg" value={String(velocity?.average ?? "—")} color="var(--accent)" />
            <StatPill label="Min" value={String(velocity?.min ?? "—")} color="var(--red)" />
            <StatPill label="Max" value={String(velocity?.max ?? "—")} color="var(--green)" />
            <StatPill label="Last" value={String(velocity?.last_sprint ?? "—")} color="var(--amber)" />
          </div>
          <ResponsiveContainer width="100%" height={130}>
            <BarChart data={velHistory} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="sprint" tick={{ fontSize: 10, fill: "var(--text-muted)" }} />
              <YAxis tick={{ fontSize: 10, fill: "var(--text-muted)" }} />
              <Tooltip contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
              <ReferenceLine y={velocity?.average} stroke="var(--accent)" strokeDasharray="4 2" />
              <Bar dataKey="velocity" fill="var(--purple)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* TODO 3 — At-Risk Items */}
      <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 16 }}>
        <div style={styles.cardTitle}>At-Risk Items — Sprint 9</div>
        {(slippage?.at_risk ?? []).length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: 13, textAlign: "center", padding: "24px 0" }}>No at-risk items</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 12 }}>
            {(slippage?.at_risk ?? []).map((item: any) => {
              const Icon = item.risk_level === "high" ? AlertTriangle : item.risk_level === "medium" ? TrendingDown : Zap;
              const badgeCls = item.risk_level === "high" ? "badge-red" : item.risk_level === "medium" ? "badge-amber" : "badge-blue";
              return (
                <div key={item.ticket_id} style={{ display: "flex", flexDirection: "column", gap: 4, padding: "10px 14px", background: "var(--bg-elevated)", border: "1px solid var(--border)", borderLeft: `3px solid ${riskColors[item.risk_level] ?? "var(--border)"}`, borderRadius: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Icon size={14} color={riskColors[item.risk_level]} />
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--accent)" }}>{item.ticket_id}</span>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{item.title}</span>
                    <span className={badgeCls} style={{ marginLeft: "auto" }}>{item.risk_level} risk</span>
                  </div>
                  <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, paddingLeft: 22 }}>{item.reason}</p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  header:   { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 },
  title:    { fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em" },
  probCard: { display: "flex", alignItems: "center", gap: 14, padding: "14px 20px", border: "2px solid", borderRadius: 12, background: "var(--bg-surface)" },
  cardTitle: { fontSize: 12, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" as const, letterSpacing: "0.06em", fontFamily: "var(--font-mono)", marginBottom: 12 },
};
