import { useEffect, useMemo, useState } from "react";
import { api } from "../api";

function levelFromPercent(pct) {
  if (pct == null || Number.isNaN(Number(pct))) return "—";
  const p = Number(pct);
  if (p < 10) return "Low";
  if (p < 30) return "Medium";
  return "High";
}

function toFixedOrDash(v, digits) {
  if (v == null || Number.isNaN(Number(v))) return "—";
  return Number(v).toFixed(digits);
}

export default function DashboardPage({ selectedProjectId }) {
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  // New: store last prediction payload (from localStorage via api.getDashboard())
  const [last, setLast] = useState(null);

  // GitHub integration UI
  const [ghRepo, setGhRepo] = useState("");
  const [ghToken, setGhToken] = useState("");
  const [ghMetrics, setGhMetrics] = useState(null);
  const [ghBusy, setGhBusy] = useState(false);
  const [ghErr, setGhErr] = useState("");
  const [ghMsg, setGhMsg] = useState("");

  const derived = useMemo(() => {
    const summary = last?.summary || {};
    const buckets = summary?.risk_buckets || {};
    const percent = summary?.percent_defective;
    const sprint = summary?.sprint_risk || null;

    return {
      runId: last?.run_id || "—",
      rows: last?.rows ?? (Array.isArray(last?.results) ? last.results.length : "—"),
      countDefective: summary?.count_defective ?? "—",
      percentDefective: percent != null ? Number(percent) : null,
      avgProba: summary?.avg_probability_defect != null ? Number(summary.avg_probability_defect) : null,
      buckets: {
        low: buckets?.low ?? "—",
        medium: buckets?.medium ?? "—",
        high: buckets?.high ?? "—",
      },
      riskLevel: levelFromPercent(percent),
      sprintRiskScore: sprint?.score ?? null,
      sprintRiskLevel: sprint?.level ?? null,
    };
  }, [last]);

  async function refresh() {
    setErr("");
    setMsg("");

    if (!selectedProjectId) {
      setErr("No project selected. Go to Projects and click Select.");
      return;
    }

    setLoading(true);
    try {
      const d = await api.getDashboard(selectedProjectId);
      if (!d) {
        setErr("No prediction found yet. Upload a CSV first.");
        setLast(null);
      } else {
        setLast(d);
        setMsg("Dashboard refreshed ✅");
      }
    } catch (e) {
      setErr(e?.message || "Failed to refresh dashboard");
    } finally {
      setLoading(false);
    }
  }

  async function loadConnectedRepo() {
    if (!selectedProjectId) return;
    setGhErr("");
    try {
      const r = await api.getGithubRepo(selectedProjectId);
      setGhRepo(r?.repo_full_name || "");
    } catch {
      // No repo connected is OK; keep blank
    }
  }

  async function connectRepo() {
    if (!selectedProjectId) return;
    setGhErr("");
    setGhMsg("");
    setGhMetrics(null);
    setGhBusy(true);
    try {
      const r = await api.connectGithub(selectedProjectId, ghRepo, ghToken);
      setGhRepo(r?.repo_full_name || ghRepo);
      setGhMsg("GitHub repo connected ✅");
    } catch (e) {
      setGhErr(e?.message || "Failed to connect repo");
    } finally {
      setGhBusy(false);
    }
  }

  async function fetchMetrics() {
    if (!selectedProjectId) return;
    setGhErr("");
    setGhMsg("");
    setGhBusy(true);
    try {
      const m = await api.getGithubMetrics(selectedProjectId, ghToken, 30);
      setGhMetrics(m);
      setGhMsg("GitHub metrics refreshed ✅");
    } catch (e) {
      setGhErr(e?.message || "Failed to fetch metrics");
    } finally {
      setGhBusy(false);
    }
  }

  // Auto-refresh when project changes
  useEffect(() => {
    if (selectedProjectId) refresh();
    if (selectedProjectId) loadConnectedRepo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectId]);

  return (
    <div className="panel">
      <div className="title">Dashboard</div>
      <p className="sub">
        Shows the latest prediction for the selected project (from your most recent upload).
      </p>

      {err && <div className="notice bad">{err}</div>}
      {msg && <div className="notice ok">{msg}</div>}

      {!last ? (
        <div className="dashPlaceholder">
          No prediction loaded yet. Upload a CSV, then click “Refresh Dashboard”.
        </div>
      ) : (
        <>
          <div className="cardRow">
            <div className="smallCard">
              <div className="mutedSmall">Risk Score</div>
              <div className="bigNum">
                {derived.sprintRiskScore != null ? derived.sprintRiskScore : "—"}
              </div>
              <div className="muted">
                Level: <b>{derived.sprintRiskLevel || derived.riskLevel}</b>
              </div>
              <div className="muted">
                Percent defective:{" "}
                <b>{derived.percentDefective != null ? `${toFixedOrDash(derived.percentDefective, 2)}%` : "—"}</b>
              </div>
            </div>

            <div className="smallCard">
              <div className="mutedSmall">Predicted Defects</div>
              <div className="bigNum">{derived.countDefective}</div>
              <div className="muted">
                Rows analyzed: <b>{derived.rows}</b>
              </div>
              <div className="muted">
                Avg defect probability:{" "}
                <b>{toFixedOrDash(derived.avgProba, 3)}</b>
              </div>
            </div>

            <div className="smallCard">
              <div className="mutedSmall">Risk Buckets</div>
              <ol className="drivers">
                <li>Low: {derived.buckets.low}</li>
                <li>Medium: {derived.buckets.medium}</li>
                <li>High: {derived.buckets.high}</li>
              </ol>
              <div className="muted" style={{ marginTop: 8 }}>
                Run: <span className="mono" style={{ wordBreak: "break-all" }}>{derived.runId}</span>
              </div>
            </div>
          </div>

          <div className="panel inner" style={{ marginTop: 12 }}>
            <div className="mutedSmall" style={{ marginBottom: 8 }}>Top 10 highest-risk rows</div>
            {Array.isArray(last?.top_rows) && last.top_rows.length ? (
              <div className="table" style={{ marginTop: 10 }}>
                <div className="th">
                  <div>Row</div>
                  <div>Probability</div>
                  <div>Pred</div>
                  <div>Risk</div>
                </div>

                {last.top_rows.map((r) => (
                  <div className="tr" key={r.row_index}>
                    <div className="mono">{r.row_index}</div>
                    <div className="mono">{toFixedOrDash(r.probability_defect, 4)}</div>
                    <div className="mono">{r.predicted_class}</div>
                    <div className="strong">{r.risk_level}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="dashPlaceholder">No rows available yet.</div>
            )}
          </div>

          <div className="panel inner" style={{ marginTop: 12 }}>
            <div className="mutedSmall" style={{ marginBottom: 8 }}>Top 5 feature importance (global)</div>
            {Array.isArray(last?.feature_importance) && last.feature_importance.length ? (
              <div className="table" style={{ marginTop: 10 }}>
                <div className="th">
                  <div>Feature</div>
                  <div>Importance</div>
                  <div>Share</div>
                </div>
                {last.feature_importance.map((f) => (
                  <div className="tr" key={f.feature}>
                    <div className="mono" style={{ wordBreak: "break-all" }}>{f.feature}</div>
                    <div className="mono">{toFixedOrDash(f.importance, 6)}</div>
                    <div className="mono">{toFixedOrDash(f.importance_pct, 2)}%</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="dashPlaceholder">Feature importance not available for this model.</div>
            )}
          </div>

          <div className="panel inner" style={{ marginTop: 12 }}>
            <div className="mutedSmall" style={{ marginBottom: 8 }}>Latest model evaluation (optional)</div>
            {last?.latest_evaluation ? (
              <div className="cardRow">
                <div className="smallCard">
                  <div className="mutedSmall">Accuracy</div>
                  <div className="bigNum">{toFixedOrDash(last.latest_evaluation.accuracy, 3)}</div>
                </div>
                <div className="smallCard">
                  <div className="mutedSmall">Precision</div>
                  <div className="bigNum">{toFixedOrDash(last.latest_evaluation.precision, 3)}</div>
                </div>
                <div className="smallCard">
                  <div className="mutedSmall">Recall</div>
                  <div className="bigNum">{toFixedOrDash(last.latest_evaluation.recall, 3)}</div>
                </div>
                <div className="smallCard">
                  <div className="mutedSmall">F1</div>
                  <div className="bigNum">{toFixedOrDash(last.latest_evaluation.f1, 3)}</div>
                </div>
              </div>
            ) : (
              <div className="dashPlaceholder">
                No evaluation metrics saved yet. Go to Reports → Model Evaluation and upload a labeled CSV.
              </div>
            )}
          </div>
        </>
      )}

      <div className="panel inner" style={{ marginTop: 12 }}>
        <div className="mutedSmall" style={{ marginBottom: 8 }}>GitHub integration (repo metrics)</div>
        <div className="muted" style={{ marginBottom: 10 }}>
          Connect a GitHub repo to compute commits/issues/churn/velocity and a heuristic sprint risk.
          Use a GitHub Personal Access Token (recommended) to avoid rate limits.
        </div>

        {ghErr && <div className="notice bad">{ghErr}</div>}
        {ghMsg && <div className="notice ok">{ghMsg}</div>}

        <div className="cardRow" style={{ alignItems: "end" }}>
          <div className="smallCard" style={{ minWidth: 320 }}>
            <div className="mutedSmall">Repo (owner/repo)</div>
            <input
              className="input"
              value={ghRepo}
              onChange={(e) => setGhRepo(e.target.value)}
              placeholder="e.g. vercel/next.js"
            />
          </div>
          <div className="smallCard" style={{ minWidth: 320 }}>
            <div className="mutedSmall">Token (PAT) — optional but recommended</div>
            <input
              className="input"
              value={ghToken}
              onChange={(e) => setGhToken(e.target.value)}
              placeholder="ghp_..."
              type="password"
            />
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
          <button className="btn" onClick={connectRepo} disabled={ghBusy || !ghRepo.trim()}>
            {ghBusy ? "Working..." : "Connect Repo"}
          </button>
          <button className="btn secondary" onClick={fetchMetrics} disabled={ghBusy}>
            {ghBusy ? "Working..." : "Fetch Metrics"}
          </button>
        </div>

        {ghMetrics ? (
          <div className="panel inner" style={{ marginTop: 12 }}>
            <div className="cardRow">
              <div className="smallCard">
                <div className="mutedSmall">Sprint Risk (GitHub)</div>
                <div className="bigNum">{ghMetrics?.sprint_risk?.score ?? "—"}</div>
                <div className="muted">Level: <b>{ghMetrics?.sprint_risk?.level ?? "—"}</b></div>
                <div className="muted">Window: <b>{ghMetrics.window_days} days</b></div>
              </div>
              <div className="smallCard">
                <div className="mutedSmall">Activity</div>
                <ol className="drivers">
                  <li>Commits: {ghMetrics.commits}</li>
                  <li>Open issues: {ghMetrics.open_issues}</li>
                  <li>Closed issues: {ghMetrics.closed_issues}</li>
                  <li>Merged PRs: {ghMetrics.merged_prs}</li>
                </ol>
              </div>
              <div className="smallCard">
                <div className="mutedSmall">Engineering Signals</div>
                <ol className="drivers">
                  <li>Churn additions: {ghMetrics.churn_additions}</li>
                  <li>Churn deletions: {ghMetrics.churn_deletions}</li>
                  <li>Velocity (14d): {ghMetrics.velocity_14d}</li>
                </ol>
              </div>
            </div>
          </div>
        ) : (
          <div className="dashPlaceholder" style={{ marginTop: 10 }}>
            No GitHub metrics loaded yet.
          </div>
        )}
      </div>

      <button className="btn" onClick={refresh} disabled={loading} style={{ marginTop: 12 }}>
        {loading ? "Refreshing..." : "Refresh Dashboard"}
      </button>
    </div>
  );
}