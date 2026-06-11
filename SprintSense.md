
## **SprintPilot** 

## _Turn a messy backlog into a realistic, risk-aware sprint plan_ 

Idea 02 — AI-Augmented Project Management  ·  Theme: 06 — Production  ·  Function: AI-Powered Production Suggested stack: LLM (any) · Embeddings · Lightweight regression · React  ·  Optional MS: Azure OpenAI · Azure DevOps Boards / GitHub Issues · Power BI 

## **Problem Statement** 

## **Problem Background** 

Sprint planning is largely guesswork. Estimates are inconsistent between people, implicit dependencies between tickets are missed, and teams routinely over-commit. Slippage is discovered at the end of the sprint during the retro — not predicted at the start when something could still be done about it. Project-management tools track work but do not reason about it. 

## **Why It Matters** 

Missed sprints erode trust with stakeholders, break roadmaps, and force crunch. Even modest gains in estimate accuracy and an early warning when a sprint is going off track compound into far more predictable delivery — one of the clearest wins available to the production function. 

## **Solution Summary** 

## **Why This Problem Was Chosen** 

AI-augmented project management is called out directly in the theme. Estimation, dependency reasoning, and slippage forecasting are exactly the kind of pattern-over-history tasks an LLM plus a team’s own data can do well, and the result is immediately useful to every team. 

## **Proposed Solution** 

SprintPilot ingests the backlog (tickets, descriptions, labels) together with the team’s historical velocity and cycle-time data. It estimates each item from its text and similar past items, detects implicit dependencies between tickets, and proposes a capacity-aware sprint plan that actually fits the team. Once the sprint starts, it produces a daily slippage forecast that updates as work moves — flagging the specific at-risk items, with reasons, while there is still time to react. 

## **Expected Impact** 

- More accurate, consistent estimates grounded in the team’s own delivery history. 

- Fewer over-commitments through capacity-aware planning. 

- Slippage flagged mid-sprint with the specific items at risk — not at the retro. 

- Less crunch and more predictable roadmaps for stakeholders. 

## **Technical Approach & Implementation** 

## **Solution Workflow** 

1. Pull the backlog from the issue tracker (descriptions, labels, links). 

2. An LLM estimates each item using its text plus the most similar previously-completed items. 

3. Dependency detection infers implicit ordering between tickets from their content and explicit links. 

4. A capacity-aware scheduler assembles a candidate sprint that respects team capacity and dependency order. 

5. During the sprint, actual progress is compared against the forecast each day. 

6. A slippage alert fires with the at-risk items and the reason, while there is still room to rebalance. 

## **Key Features** 

**History-Grounded Estimation.** Estimates each ticket from its text and the team’s own similar past items, not a generic model. 

**Dependency Graph Detection.** Surfaces implicit dependencies between tickets so the plan is sequenced correctly. 

**Capacity-Aware Auto-Plan.** Builds a candidate sprint that fits real team capacity and dependency order. 

**Live Slippage Forecast.** Daily probability the sprint completes, with the specific items dragging it off track. 

## **Technology Stack** 

## **Frontend** 

- React + TypeScript 

- Gantt + burndown charts 

- Drag-to-adjust sprint board 

## **Backend** 

- Python 3.11 + FastAPI 

- Scheduler service (capacity bin-packing) 

- Nightly forecast job 

## **AI / ML** 

- LLM for estimation + dependency reasoning 

- Embeddings for nearest-neighbour over past tickets 

- Lightweight regression on cycle time 

## **Data & Integrations** 

- Issue tracker API (Azure DevOps Boards / GitHub Issues / Jira) 

- Historical velocity store 

- Monte-Carlo forecast engine 

## **Models & Algorithms** 

**Estimation.** Embedding nearest-neighbour over completed tickets gives a baseline; an LLM adjusts for specifics in the description. 

**Dependency Detection.** LLM classifies whether ticket A blocks ticket B, combined with explicit tracker links, to build a DAG. 

**Scheduler.** Capacity bin-packing that respects the dependency DAG and per-member availability. 

**Slippage Forecast.** Monte-Carlo simulation over remaining work versus the team’s velocity distribution, run daily. 

## **Innovation** 

**Estimates from your own history.** The model learns this team’s pace from completed work, instead of imposing a one-size-fits-all velocity. 

**Predictive, not retrospective.** Slippage is forecast on day two, not explained at the retro — turning planning into a live control loop. 

**Plan + forecast in one loop.** The same engine that builds the plan continuously checks whether reality is keeping up with it. 

## **Future Scope** 

**Near-term** 

- Cross-team dependency view for shared roadmaps 

- Daily standup digest auto-generated from board movement 

- What-if scope simulator (“if we drop X, do we finish?”) 

**Medium-term** 

   - Automatic mid-sprint rebalancing suggestions 

   - Risk-aware roadmap planning across multiple sprints 

   - Estimate-accuracy feedback loop per team and per author 

- **Long-term** 

   - Portfolio-level delivery forecasting across many teams 

   - Capacity planning tied to hiring and leave calendars 

   - Predictive staffing recommendations for upcoming epics 

## **Scalability & Larger Vision** 

## **How It Scales** 

SprintPilot is designed to scale from a single team’s board to portfolio-level delivery forecasting on the same engine. 

**Technically** , ingestion runs through pluggable adapters, so adding a new issue tracker (Azure DevOps Boards, GitHub Issues, Jira) is a connector, not a redesign. Estimation relies on embedding nearest-neighbour search over completed tickets, which scales to large backlog 

histories, and the Monte-Carlo slippage forecast is embarrassingly parallel — more teams simply mean more independent simulation jobs. 

**Across teams** , each team gets its own history-grounded model, so accuracy improves with the team’s own data instead of being diluted by a one-size-fits-all velocity. Because every team is modelled independently, the system scales horizontally: a hundred teams are a hundred parallel forecasts, not a single bottlenecked model. 

**Organisationally** , the same primitives — estimate, dependency graph, capacity-aware plan, live forecast — roll up from a single sprint to cross-team roadmaps to a portfolio view, giving leadership an aggregated delivery forecast built from the same trusted signals each team already sees. 

## **How It Expands** 

Expansion turns planning into an increasingly autonomous control loop. Near term, a cross-team dependency view and a what-if scope simulator help teams reason about trade-offs live. In the medium term, the system suggests automatic mid-sprint rebalancing and supports risk-aware planning across multiple sprints. Long term, capacity planning ties directly into hiring and leave calendars, and SprintPilot produces predictive staffing recommendations for upcoming epics — connecting delivery forecasting to the resourcing decisions that drive it. 

## **The Larger Vision** 

Project management shifts from tracking work to reasoning about it. Slippage is forecast on day two and corrected mid-flight, not explained at the retro. At full scale, an organisation gains a continuously updating, bottom-up forecast of whether its roadmap is achievable — turning planning from an annual act of optimism into a live, data-grounded control system. 

## **Potential Impact** 

For a single team, SprintPilot delivers more accurate estimates, fewer over-commitments, and early warnings while there is still time to react. Aggregated across an organisation, modest per-team gains in estimate accuracy compound into materially more predictable delivery: rebuilt stakeholder trust, roadmaps that hold, and far less crunch. It is one of the clearest, most repeatable wins available to the production function — and it gets more valuable the more teams adopt it, because every completed sprint sharpens the model. 

