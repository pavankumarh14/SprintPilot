const BASE = process.env.REACT_APP_API_URL || "";
const LLM_KEY_STORAGE = "sprintsense_llm_key";

export function getLlmKey(): string {
  return localStorage.getItem(LLM_KEY_STORAGE) || "";
}

export function setLlmKey(key: string): void {
  if (key.trim()) {
    localStorage.setItem(LLM_KEY_STORAGE, key.trim());
  } else {
    localStorage.removeItem(LLM_KEY_STORAGE);
  }
}

function buildHeaders(): HeadersInit {
  const key = getLlmKey();
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (key) h["X-LLM-Key"] = key;
  return h;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: buildHeaders() });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export const api = {
  /* -- Read endpoints (all implemented) ----------------------------------- */

  // Backlog
  getBacklog:        () => get<any>("/api/backlog/"),
  getBacklogHistory: () => get<any>("/api/backlog/history"),
  getDependencies:   () => get<any>("/api/backlog/dependencies"),
  getAtRisk:         () => get<any>("/api/backlog/at-risk"),
  getTicket:         (id: string) => get<any>(`/api/backlog/${id}`),

  // Sprint
  getCurrentSprint: () => get<any>("/api/sprint/current"),
  getSprintHistory: () => get<any>("/api/sprint/history"),
  getBurndown:      () => get<any>("/api/sprint/burndown"),
  getDigest:        () => get<any>("/api/sprint/digest"),

  // Forecast
  getSlippage:  () => get<any>("/api/forecast/slippage"),
  getVelocity:  () => get<any>("/api/forecast/velocity"),

  // Team / Board
  getTeam:  () => get<any>("/api/team/"),
  getBoard: () => get<any>("/api/board/"),

  // LLM status
  getLlmStatus: () => get<any>("/api/llm-status"),

  /* -- Write endpoints ---------------------------------------------------- */

  updateTicketStatus: (ticketId: string, newStatus: string) =>
    post<any>("/api/board/move", { ticket_id: ticketId, status: newStatus }),

  /* -- Integration endpoints ---------------------------------------------- */
  getIntegrationStatus:  () => get<any>("/api/integrations/status"),
  saveIntegrationConfig: (cfg: Record<string, string>) => post<any>("/api/integrations/config", cfg),
  syncJira:   () => post<any>("/api/integrations/jira/sync", {}),
  syncGitHub: () => post<any>("/api/integrations/github/sync", {}),
  testSlack:  () => post<any>("/api/integrations/slack/test", {}),

  /* -- Scenario endpoints ------------------------------------------------- */
  getScenarioCompare:   () => get<any>("/api/scenarios/compare"),
  scenarioDrop:         (ticketIds: string[]) =>
    post<any>(`/api/scenarios/drop`, { ticket_ids: ticketIds }),  scenarioCapacity:     (hours: number) =>
    post<any>(`/api/scenarios/capacity`, { hours }),  scenarioScopeCreep:   (ticketIds: string[]) =>
    post<any>(`/api/scenarios/scope-creep`, { ticket_ids: ticketIds }),  scenarioPto:          (memberId: string, days: number) =>
    post<any>(`/api/scenarios/pto`, { member_id: memberId, days }),  scenarioOptimize:     (targetProbability: number) =>
    post<any>(`/api/scenarios/optimize`, { target_probability: targetProbability }),};
