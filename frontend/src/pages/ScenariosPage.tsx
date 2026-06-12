import React, { useState } from "react";
import { useApi } from "../hooks/useApi";
import { api } from "../utils/api";
import { Zap, TrendingUp, TrendingDown } from "lucide-react";

export default function ScenariosPage() {
    const { data: comparison } = useApi(() => api.getScenarioCompare().catch(() => null));
    const [loading, setLoading] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState<any>(null);

  const baselineScenario = comparison?.scenarios?.find((sc: any) => sc.name === "Baseline (current)");
  const baselineProb = baselineScenario?.probability ?? 0.58;

  const runScenario = async (type: string, params: Record<string, any>) => {
    setLoading(true);
    try {
      let result;
      switch (type) {
        case "drop":
          result = await api.scenarioDrop(params.ticketIds);
          break;
        case "capacity":
          result = await api.scenarioCapacity(params.hours);
          break;
        case "scope-creep":
          result = await api.scenarioScopeCreep(params.ticketIds);
          break;
        case "pto":
          result = await api.scenarioPto(params.memberId, params.days);
          break;
        case "optimize":
          result = await api.scenarioOptimize(params.targetProbability);
          break;
        default:
          throw new Error("Unknown scenario type");
      }
      setSelectedScenario(result);
    } catch (err) {
      console.error("[Scenarios]", err);
      alert("Failed to run scenario");
    } finally {
      setLoading(false);
    }
  };

  const riskColor = (level: string) => level === "low" ? "var(--green)" : level === "medium" ? "var(--amber)" : "var(--red)";

  return (
    <div className="page-enter">
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em" }}>What-If Scenarios</h1>
        <p style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: 12 }}>
          AI-powered scenario planning &middot; Simulate changes without committing
        </p>
      </div>

      {/* Baseline */}
      <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 16, marginBottom: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", fontFamily: "var(--font-mono)", marginBottom: 12 }}>Baseline Sprint (Current)</div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <div style={{ fontSize: 48, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent)" }}>{Math.round(baselineProb * 100)}%</div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>Completion Probability</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>Sprint 9 &middot; 10 tickets &middot; 67 points</div>
          </div>
        </div>
      </div>

      {/* Scenario Actions */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 12 }}>
        <button
          onClick={() => runScenario("drop", { ticketIds: ["TKT-109", "TKT-105"] })}
          disabled={loading}
          style={{ ...btnStyles, background: "var(--bg-surface)", border: "1px solid var(--border)", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.5 : 1 }}
        >
          <TrendingDown size={16} color="var(--amber)" />
          <span>Drop 2 Tickets</span>
        </button>
        <button
          onClick={() => runScenario("capacity", { hours: 16 })}
          disabled={loading}
          style={{ ...btnStyles, background: "var(--bg-surface)", border: "1px solid var(--border)", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.5 : 1 }}
        >
          <TrendingUp size={16} color="var(--green)" />
          <span>Add 16h Capacity</span>
        </button>
        <button
          onClick={() => runScenario("scope-creep", { ticketIds: ["TKT-110"] })}
          disabled={loading}
          style={{ ...btnStyles, background: "var(--bg-surface)", border: "1px solid var(--border)", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.5 : 1 }}
        >
          <TrendingDown size={16} color="var(--red)" />
          <span>Add 1 Ticket (Creep)</span>
        </button>
        <button
          onClick={() => runScenario("pto", { memberId: "sarah", days: 3 })}
          disabled={loading}
          style={{ ...btnStyles, background: "var(--bg-surface)", border: "1px solid var(--border)", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.5 : 1 }}
        >
          <TrendingDown size={16} color="var(--amber)" />
          <span>Sarah Out 3 Days</span>
        </button>
        <button
          onClick={() => runScenario("optimize", { targetProbability: 0.8 })}
          disabled={loading}
          style={{ ...btnStyles, background: "var(--bg-surface)", border: "1px solid var(--border)", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.5 : 1 }}
        >
          <Zap size={16} color="var(--accent)" />
          <span>Optimize for 80%</span>
        </button>
      </div>

      {/* Result */}
      {selectedScenario && (
        <div style={{ background: "var(--bg-surface)", border: `2px solid ${riskColor(selectedScenario.risk_level)}`, borderRadius: 12, padding: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 40, fontWeight: 700, fontFamily: "var(--font-mono)", color: riskColor(selectedScenario.risk_level) }}>
              {Math.round(selectedScenario.completion_probability * 100)}%
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{selectedScenario.scenario_name}</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                {selectedScenario.completion_probability_change >= 0 ? "+" : ""}
                {Math.round(selectedScenario.completion_probability_change * 100)}% change &middot; {selectedScenario.days_to_complete?.toFixed(1)} days
              </div>
            </div>
            <span className={selectedScenario.risk_level === "low" ? "badge-green" : selectedScenario.risk_level === "medium" ? "badge-amber" : "badge-red"}>
              {selectedScenario.risk_level} risk
            </span>
          </div>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
            {selectedScenario.recommendation}
          </p>
          {selectedScenario.tickets_dropped && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", marginBottom: 4 }}>Tickets Dropped:</div>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {selectedScenario.tickets_dropped.map((id: string) => (
                  <span key={id} style={{ fontFamily: "var(--font-mono)", fontSize: 10, padding: "2px 6px", background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 4 }}>{id}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Comparison */}
      {comparison && comparison.scenarios && (
        <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 16, marginTop: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", fontFamily: "var(--font-mono)", marginBottom: 12 }}>Pre-computed Scenarios</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {comparison.scenarios.map((sc: any, i: number) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 12px", background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8 }}>
                <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "var(--font-mono)", color: riskColor(sc.risk_level), minWidth: 60 }}>
                  {Math.round(sc.completion_probability * 100)}%
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, fontWeight: 500 }}>{sc.scenario_name}</div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                    {sc.completion_probability_change >= 0 ? "+" : ""}
                    {Math.round(sc.completion_probability_change * 100)}% from baseline
                  </div>
                </div>
                <span className={sc.risk_level === "low" ? "badge-green" : sc.risk_level === "medium" ? "badge-amber" : "badge-red"}>
                  {sc.risk_level}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const btnStyles: React.CSSProperties = {
  display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
  padding: "12px 16px", borderRadius: 8, fontSize: 12, fontWeight: 500,
  transition: "all 0.15s",
};
