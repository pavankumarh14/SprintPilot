import React, { useEffect, useRef } from "react";
import { useApi } from "../hooks/useApi";
import { api } from "../utils/api";
import * as d3 from "d3";

const TICKET_POINTS: Record<string, number> = {
  "TKT-101": 8, "TKT-102": 3, "TKT-103": 5, "TKT-104": 5,
  "TKT-105": 8, "TKT-106": 8, "TKT-107": 13, "TKT-108": 8,
  "TKT-109": 8, "TKT-110": 3,
};

const STATUS_COLOR: Record<string, string> = {
  in_progress: "#3d7eff",
  review:      "#a78bfa",
  done:        "#22d58a",
  todo:        "#4a5468",
  backlog:     "#4a5468",
};

export default function DependenciesPage() {
  const { data: deps }    = useApi(() => api.getDependencies());
  const { data: backlog } = useApi(() => api.getBacklog());
  const { data: board }   = useApi(() => api.getBoard());
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!deps || !backlog || !svgRef.current) return;

    const edges: { from: string; to: string; reason: string }[] = deps.edges ?? [];
    const tickets = backlog.tickets ?? [];
    const boardState = board;

    const statusMap: Record<string, string> = {};
    if (boardState) {
      ["todo", "in_progress", "review", "done"].forEach((col: string) => {
        (boardState[col] ?? []).forEach((t: any) => { statusMap[t.id] = col; });
      });
    }
    tickets.forEach((t: any) => { if (!statusMap[t.id]) statusMap[t.id] = "backlog"; });

    const nodeIds = Array.from(new Set([...edges.map(e => e.from), ...edges.map(e => e.to)]));
    const nodes = nodeIds.map(id => {
      const t = tickets.find((tk: any) => tk.id === id);
      return { id, label: id, title: t?.title ?? id, pts: TICKET_POINTS[id] ?? 5, status: statusMap[id] ?? "backlog" };
    });
    const links = edges.map(e => ({ source: e.from, target: e.to, reason: e.reason }));

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const W = svgRef.current.clientWidth || 700;
    const H = 480;
    svg.attr("viewBox", `0 0 ${W} ${H}`);

    // 1. Arrow marker
    svg.append("defs").append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 28).attr("refY", 0)
      .attr("markerWidth", 6).attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path").attr("d", "M0,-5L10,0L0,5").attr("fill", "#3d7eff");

    // 2. Force simulation
    const sim = d3.forceSimulation(nodes as any)
      .force("link", d3.forceLink(links).id((d: any) => d.id).distance(120))
      .force("charge", d3.forceManyBody().strength(-350))
      .force("center", d3.forceCenter(W / 2, H / 2))
      .force("collision", d3.forceCollide(50));

    // 3. Link lines
    const link = svg.append("g").selectAll("line").data(links).join("line")
      .attr("stroke", "#3d7eff").attr("stroke-opacity", 0.55)
      .attr("stroke-width", 1.5).attr("marker-end", "url(#arrow)");

    // 4. Link labels
    const linkLabel = svg.append("g").selectAll("text").data(links).join("text")
      .attr("font-size", 9).attr("fill", "#4a5468")
      .attr("font-family", "Space Mono, monospace")
      .text((d: any) => (d.reason ?? "").substring(0, 28) + (d.reason?.length > 28 ? "\u2026" : ""));

    // 5. Tooltip
    const tooltip = d3.select("body").append("div")
      .style("position", "fixed")
      .style("background", "#1a1f2e")
      .style("border", "1px solid #2a3147")
      .style("border-radius", "8px")
      .style("padding", "8px 12px")
      .style("font-size", "12px")
      .style("color", "#e2e8f0")
      .style("pointer-events", "none")
      .style("opacity", 0)
      .style("z-index", 9999);

    // 6. Node groups with drag
    const node = svg.append("g").selectAll("g").data(nodes).join("g")
      .attr("cursor", "pointer")
      .call((d3.drag() as any)
        .on("start", (event: any, d: any) => { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on("drag",  (event: any, d: any) => { d.fx = event.x; d.fy = event.y; })
        .on("end",   (event: any, d: any) => { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
      );

    node.append("circle")
      .attr("r", (d: any) => 14 + d.pts)
      .attr("fill", (d: any) => STATUS_COLOR[d.status] + "2e")
      .attr("stroke", (d: any) => STATUS_COLOR[d.status])
      .attr("stroke-width", 2);

    node.append("text")
      .attr("dy", "-4px")
      .attr("font-size", 10).attr("font-weight", 700)
      .attr("fill", "#3d7eff").attr("text-anchor", "middle")
      .text((d: any) => d.label);

    node.append("text")
      .attr("dy", "12px")
      .attr("font-size", 9).attr("fill", "#8b95a8").attr("text-anchor", "middle")
      .text((d: any) => `${d.pts}p`);

    node
      .on("mouseover", (event: any, d: any) => {
        tooltip.style("opacity", 1)
          .html(`<strong style="color:#3d7eff">${d.id}</strong><br/>${d.title}<br/><span style="color:#8b95a8">${d.status}</span>`);
      })
      .on("mousemove", (event: any) => {
        tooltip.style("left", (event.clientX + 14) + "px").style("top", (event.clientY - 28) + "px");
      })
      .on("mouseout", () => { tooltip.style("opacity", 0); });

    // 8. Tick handler
    sim.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x).attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x).attr("y2", (d: any) => d.target.y);
      linkLabel
        .attr("x", (d: any) => (d.source.x + d.target.x) / 2)
        .attr("y", (d: any) => (d.source.y + d.target.y) / 2);
      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    // 9. Cleanup
    return () => { tooltip.remove(); sim.stop(); };
  }, [deps, backlog, board]);

  return (
    <div className="page-enter">
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Dependency Graph</h1>
          <p style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: 12 }}>
            LLM-inferred implicit + explicit ticket dependencies &middot; drag nodes to rearrange
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {[
            { color: "#3d7eff", label: "In Progress" },
            { color: "#a78bfa", label: "Review" },
            { color: "#22d58a", label: "Done" },
            { color: "#4a5468", label: "Not started" },
          ].map(l => (
            <div key={l.label} style={styles.legendItem}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: l.color }} />
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{l.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 16, marginBottom: 12 }}>
        <div style={styles.cardTitle}>Ticket Dependency Map</div>
        <svg ref={svgRef} style={{ width: "100%", height: 480, display: "block" }} />
      </div>

      <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 16 }}>
        <div style={styles.cardTitle}>Dependency Edges</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 10 }}>
          {(deps?.edges ?? []).map((e: any, i: number) => (
            <div key={i} style={styles.edgeRow}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "#3d7eff" }}>{e.from}</span>
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>&nbsp;&rarr; blocks &rarr;&nbsp;</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "#a78bfa" }}>{e.to}</span>
              <span style={{ fontSize: 11, color: "var(--text-secondary)", marginLeft: "auto" }}>{e.reason}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  header:     { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 },
  title:      { fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em" },
  cardTitle:  { fontSize: 12, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" as const, letterSpacing: "0.06em", fontFamily: "var(--font-mono)", marginBottom: 8 },
  legendItem: { display: "flex", alignItems: "center", gap: 6, padding: "6px 10px", background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 6 },
  edgeRow:    { display: "flex", alignItems: "center", gap: 12, padding: "8px 12px", background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 6 },
};
