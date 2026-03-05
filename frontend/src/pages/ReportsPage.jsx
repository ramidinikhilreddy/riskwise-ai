export default function ReportsPage() {
  return (
    <div className="panel">
      <div className="title">Reports</div>
      <p className="sub">UI ready for export endpoints (PDF/HTML).</p>

      <div className="panel inner" style={{ maxWidth: 700 }}>
        <div className="row">
          <button className="btn btnPrimary" disabled>Export PDF (soon)</button>
          <button className="btn" disabled>Export HTML (soon)</button>
        </div>
      </div>
    </div>
  );
}