# -*- coding: utf-8 -*-
"""
AML Compliance Dashboard — Enhanced
=====================================
Streamlit UI with:
  - PDF upload → auto-ingest → gap analysis (no pre-known UUID needed)
  - Coverage score + risk-banded gap display
  - Obligation graph visualization (networkx spring layout)
  - Markdown report export button
"""
import streamlit as st
import requests
import pandas as pd
import json
import io
import os

# ── Config ────────────────────────────────────────────────────────────────────
API_URL = os.getenv("SIA_RAG_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AML Compliance Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.score-box { border-radius: 8px; padding: 12px 20px; text-align: center; font-size: 2rem; font-weight: 700; }
.critical  { background: #3d0000; border: 1px solid #ff4444; }
.moderate  { background: #2d1f00; border: 1px solid #ff9900; }
.safe      { background: #002200; border: 1px solid #44ff44; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=60)
st.sidebar.title("🛡️ AML Compliance")
st.sidebar.markdown("*Gap Analysis & Traceability*")
st.sidebar.divider()

# ── Upload mode switch ────────────────────────────────────────────────────────
input_mode = st.sidebar.radio(
    "Input Method",
    ["📤 Upload PDF", "🔑 Enter Document ID"],
    index=0,
)

uploaded_file = None
policy_doc_id = ""

if input_mode == "📤 Upload PDF":
    uploaded_file = st.sidebar.file_uploader(
        "Upload AML Policy PDF",
        type=["pdf"],
        help="Upload your bank's internal AML/KYC policy document"
    )
else:
    policy_doc_id = st.sidebar.text_input(
        "Ingested Document UUID",
        value="",
        placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    )

st.sidebar.divider()
st.sidebar.subheader("Analysis Parameters")

as_of_date = st.sidebar.date_input(
    "Regulation Snapshot Date",
    value=None,
    help="Only regulations effective on or before this date will be checked"
)

jurisdiction_filter = st.sidebar.selectbox(
    "Jurisdiction Filter",
    options=["All", "RBI", "FATF", "FIU-IND", "PMLA", "SEBI"],
    index=0,
)

regulation_type_filter = st.sidebar.selectbox(
    "Regulation Type",
    options=["All", "KYC", "CDD", "EDD", "STR", "CTR", "PEP", "RecordKeeping", "BeneficialOwnership"],
    index=0,
)

max_obligations = st.sidebar.slider(
    "Max Obligations to Analyze",
    min_value=10, max_value=150, value=75, step=5,
    help="Caps Stage 2 LLM calls. Higher = more thorough but slower."
)

run_btn = st.sidebar.button("🔍 Run Gap Analysis", type="primary", use_container_width=True)

st.sidebar.divider()
st.sidebar.caption("Two-stage pipeline: hybrid search pre-filter → LLM judge → evidence guard")

# ── Main Panel ─────────────────────────────────────────────────────────────────
st.title("⚖️ AML Compliance Gap Analysis")

if not run_btn:
    st.markdown("""
    ### Welcome
    This dashboard analyses your internal AML/KYC policy against indexed regulatory frameworks:
    **FATF 40 Recommendations · RBI KYC Master Direction · PMLA · FIU-IND Guidelines · SEBI AML Circular**

    **How to use:**
    1. Upload your policy PDF (or paste a Document ID if already ingested)
    2. Optionally set a regulation snapshot date for temporal filtering
    3. Click **Run Gap Analysis**
    4. Review gaps, download the Markdown report, and explore the traceability graph

    **Research Metrics:** Coverage Score = (0.7·S_sim + 0.3·S_cite) × W_reg
    """)

    with st.expander("📐 Coverage Score Formula"):
        st.code("""
CoverageScore_i = (0.7 × S_sim + 0.3 × S_cite) × W_reg

  S_sim  = cosine_similarity(obligation_embedding, best_policy_chunk_embedding)
  S_cite = 1.0 if evidence quote verified in policy text, else 0.0
  W_reg  = 1.5 (Mandatory) | 1.0 (Recommended) | 0.5 (Optional)

OverallCoverage = Σ(CoverageScore_i) / Σ(W_reg_i) × 100
        """, language="text")
else:
    # ── Step 1: Ingest PDF if needed ──────────────────────────────────────────
    if uploaded_file is not None:
        with st.spinner(f"Uploading & ingesting '{uploaded_file.name}'..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                params = {"document_tier": "internal_policy"}
                ingest_resp = requests.post(
                    f"{API_URL}/upload/",
                    files=files,
                    params=params,
                    timeout=120
                )
                if ingest_resp.status_code == 200:
                    ingest_data = ingest_resp.json()
                    policy_doc_id = ingest_data.get("doc_id") or ingest_data.get("document_id", "")
                    if not policy_doc_id:
                        st.error("Ingestion succeeded but no doc_id returned. Check your upload API.")
                        st.stop()
                    st.success(f"✅ Ingested: `{uploaded_file.name}` → `{policy_doc_id}`")
                else:
                    st.error(f"Upload failed ({ingest_resp.status_code}): {ingest_resp.text}")
                    st.stop()
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend. Is `uvicorn backend.app:app --reload` running?")
                st.stop()

    if not policy_doc_id or policy_doc_id.strip() == "":
        st.warning("Please upload a PDF or enter a Document ID.")
        st.stop()

    # ── Step 2: Run gap analysis ──────────────────────────────────────────────
    with st.spinner("Running two-stage gap analysis... (Stage 1: hybrid search | Stage 2: LLM judge)"):
        payload = {
            "policy_doc_id":   policy_doc_id.strip(),
            "max_obligations": max_obligations,
        }
        if as_of_date:
            payload["as_of_date"] = as_of_date.isoformat()
        if jurisdiction_filter != "All":
            payload["jurisdiction_filter"] = jurisdiction_filter
        if regulation_type_filter != "All":
            payload["regulation_type_filter"] = regulation_type_filter

        try:
            resp = requests.post(f"{API_URL}/gap-analysis/", json=payload, timeout=300)
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend. Is `uvicorn backend.app:app --reload` running?")
            st.stop()

    if resp.status_code != 200:
        st.error(f"API Error ({resp.status_code}): {resp.text}")
        st.stop()

    data     = resp.json()
    report   = data.get("report", {})
    markdown = data.get("markdown", "")
    report_id = report.get("report_id", "unknown")

    # ── Headline metrics ──────────────────────────────────────────────────────
    score   = report.get("overall_coverage_score", 0)
    summary = report.get("summary", {})
    latency = report.get("latency_seconds", 0)

    st.success(f"Analysis complete in **{latency}s** — Report ID: `{report_id}`")

    # Score color
    score_color = "#44ff44" if score >= 80 else "#ff9900" if score >= 60 else "#ff4444"
    risk_label  = "LOW RISK" if score >= 80 else "MODERATE RISK" if score >= 60 else "HIGH RISK 🚨"

    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
    with col1:
        st.markdown(
            f'<div class="score-box" style="background:#1a1a2e; border:2px solid {score_color};">'
            f'<div style="font-size:0.85rem;color:{score_color};">{risk_label}</div>'
            f'<div style="color:{score_color};">{score:.1f}%</div>'
            f'<div style="font-size:0.7rem;color:#888;">Coverage Score</div></div>',
            unsafe_allow_html=True
        )
    col2.metric("🟢 Covered",  summary.get("covered", 0))
    col3.metric("🟡 Partial",  summary.get("partial", 0))
    col4.metric("🔴 Missing",  summary.get("missing", 0))
    col5.metric("🛡️ Stage 1",  report.get("stage1_obligations_retrieved", 0))

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔴 Critical Gaps",
        "🟡 Partial Coverage",
        "🟢 Covered",
        "🕸️ Traceability Graph",
        "📄 Markdown Report",
    ])

    # ── Tab 1: Missing ────────────────────────────────────────────────────────
    with tab1:
        st.subheader("Missing Obligations (Compliance Gaps)")
        missing_gaps = report.get("missing", [])
        if not missing_gaps:
            st.info("🎉 No missing obligations found.")
        else:
            for gap in missing_gaps:
                sev_icon = "🚨" if gap.get("severity") == "critical" else "⚠️"
                with st.expander(
                    f"{sev_icon} {gap.get('regulation_type','General')} | "
                    f"{gap.get('jurisdiction','?')} | "
                    f"{gap.get('obligation_level','Mandatory')} | "
                    f"Score: {gap.get('coverage_score', 0):.3f}"
                ):
                    cols = st.columns([2, 1])
                    with cols[0]:
                        st.markdown(f"**Source:** {gap.get('regulation_source')} — Page {gap.get('regulation_page')}")
                        if gap.get("effective_date"):
                            st.markdown(f"**Effective:** {gap.get('effective_date')}")
                        st.markdown(f"**Obligation:**\n> {gap.get('obligation_text', '')[:500]}")
                        st.error(f"**Gap Reason:** {gap.get('gap_reason', '—')}")
                        if gap.get("remediation"):
                            st.warning(f"**Suggested Remediation:**\n{gap.get('remediation')}")
                    with cols[1]:
                        st.metric("S_sim", f"{gap.get('s_sim', 0):.3f}")
                        st.metric("S_cite", f"{gap.get('s_cite', 0):.1f}")
                        st.metric("W_reg", f"{gap.get('w_reg', 0):.1f}")
                    if gap.get("graph_path"):
                        st.caption(f"Traceability: `{gap.get('graph_path')}`")

    # ── Tab 2: Partial ────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Partially Covered Obligations")
        partial_gaps = report.get("partial", [])
        if not partial_gaps:
            st.info("No partially covered obligations.")
        else:
            for gap in partial_gaps:
                with st.expander(
                    f"🟡 {gap.get('regulation_type','General')} | "
                    f"{gap.get('jurisdiction','?')} | "
                    f"Score: {gap.get('coverage_score', 0):.3f}"
                ):
                    st.markdown(f"**Source:** {gap.get('regulation_source')}")
                    st.markdown(f"**Obligation:**\n> {gap.get('obligation_text', '')[:400]}")
                    if gap.get("evidence"):
                        st.markdown(f"**Closest Policy Match:**\n> _{gap.get('evidence')[:300]}_")
                    st.warning(f"**Gap:** {gap.get('gap_reason','—')}")
                    if gap.get("remediation"):
                        st.info(f"**Remediation:**\n{gap.get('remediation')}")
                    if gap.get("graph_path"):
                        st.caption(f"Traceability: `{gap.get('graph_path')}`")

    # ── Tab 3: Covered ────────────────────────────────────────────────────────
    with tab3:
        st.subheader("Fully Covered Obligations")
        covered_gaps = report.get("covered", [])
        if not covered_gaps:
            st.info("No covered obligations found.")
        else:
            df_data = [{
                "Type":         g.get("regulation_type", "—"),
                "Jurisdiction": g.get("jurisdiction", "—"),
                "Level":        g.get("obligation_level", "—"),
                "Source":       g.get("regulation_source", "—"),
                "Score":        g.get("coverage_score", 0),
                "S_sim":        g.get("s_sim", 0),
                "S_cite":       g.get("s_cite", 0),
            } for g in covered_gaps]
            df = pd.DataFrame(df_data)
            st.dataframe(df.style.format({"Score": "{:.3f}", "S_sim": "{:.3f}", "S_cite": "{:.1f}"}),
                         use_container_width=True)

    # ── Tab 4: Graph Visualization ────────────────────────────────────────────
    with tab4:
        st.subheader("🕸️ Regulatory Obligation Traceability Graph")
        st.markdown("Shows the chain: FATF → PMLA → RBI → Internal Policy Clause")

        try:
            import networkx as nx
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            from io import BytesIO

            # Load the saved graph JSON
            graph_json_path = "./data/aml_obligation_graph.json"
            if os.path.exists(graph_json_path):
                with open(graph_json_path) as f:
                    graph_data = json.load(f)

                G_plot = nx.readwrite.json_graph.adjacency_graph(graph_data)

                # Colour nodes by type
                COLOR_MAP = {
                    "FATF_Recommendation": "#e74c3c",
                    "PMLA_Section":        "#e67e22",
                    "RBI_Direction":       "#3498db",
                    "FIU_Guideline":       "#9b59b6",
                    "SEBI_Guideline":      "#1abc9c",
                    "Policy_Clause":       "#2ecc71",
                    "Generic_Obligation":  "#95a5a6",
                }
                node_colors = [
                    COLOR_MAP.get(G_plot.nodes[n].get("node_type", ""), "#aaaaaa")
                    for n in G_plot.nodes
                ]

                fig, ax = plt.subplots(figsize=(14, 9), facecolor="#0e0e1a")
                ax.set_facecolor("#0e0e1a")

                pos = nx.spring_layout(G_plot, k=2.5, seed=42)
                nx.draw_networkx(
                    G_plot, pos, ax=ax,
                    node_color=node_colors,
                    node_size=400,
                    font_size=6,
                    font_color="white",
                    edge_color="#555577",
                    arrows=True,
                    arrowsize=8,
                    width=0.8,
                )

                # Legend
                patches = [mpatches.Patch(color=c, label=t) for t, c in COLOR_MAP.items()]
                ax.legend(handles=patches, loc="lower left", fontsize=7,
                          facecolor="#1a1a2e", edgecolor="#555", labelcolor="white")

                buf = BytesIO()
                fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                            facecolor="#0e0e1a")
                buf.seek(0)
                st.image(buf, caption="AML Obligation Traceability Graph", use_container_width=True)
                plt.close(fig)

                # GEXF download
                gexf_path = "./data/aml_obligation_graph.gexf"
                if os.path.exists(gexf_path):
                    with open(gexf_path, "rb") as gf:
                        st.download_button(
                            "📥 Download GEXF (open in Gephi)",
                            data=gf.read(),
                            file_name="aml_obligation_graph.gexf",
                            mime="application/gexf+xml",
                        )

                # Stats
                n_nodes = G_plot.number_of_nodes()
                n_edges = G_plot.number_of_edges()
                missing_edges = sum(1 for _, _, d in G_plot.edges(data=True)
                                    if d.get("relation") == "MISSING")
                c1, c2, c3 = st.columns(3)
                c1.metric("Graph Nodes", n_nodes)
                c2.metric("Graph Edges", n_edges)
                c3.metric("Missing Edges", missing_edges)
            else:
                st.info("Graph file not found. Run a gap analysis first — it will be generated automatically.")

        except ImportError as imp_err:
            st.warning(f"networkx or matplotlib not installed: {imp_err}")
        except Exception as graph_err:
            st.warning(f"Could not render graph: {graph_err}")

    # ── Tab 5: Markdown Export ────────────────────────────────────────────────
    with tab5:
        st.subheader("📄 Markdown Narrative Report")
        if markdown:
            st.markdown(markdown[:4000] + ("\n\n_...truncated — download for full report_"
                                           if len(markdown) > 4000 else ""))
            st.download_button(
                "📥 Download Full Report (.md)",
                data=markdown.encode("utf-8"),
                file_name=f"aml_gap_report_{report_id[:8]}.md",
                mime="text/markdown",
            )
        else:
            # Fallback: fetch from the markdown endpoint
            try:
                md_resp = requests.get(f"{API_URL}/gap-analysis/{report_id}/markdown", timeout=30)
                if md_resp.status_code == 200:
                    st.download_button(
                        "📥 Download Report (.md)",
                        data=md_resp.text.encode("utf-8"),
                        file_name=f"aml_gap_report_{report_id[:8]}.md",
                        mime="text/markdown",
                    )
                else:
                    st.warning("Markdown report not available. Re-run analysis to regenerate.")
            except Exception:
                st.warning("Could not fetch Markdown report from backend.")

    # ── Footer stats ──────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        f"Stage 1: {report.get('stage1_obligations_retrieved', 0)} obligations retrieved via hybrid search  ·  "
        f"Stage 2: {report.get('stage2_obligations_analyzed', 0)} LLM judgments  ·  "
        f"Evidence guard: {report.get('hallucination_rejections', 0)} hallucinations rejected  ·  "
        f"Avg confidence: {report.get('avg_confidence', 0):.1%}  ·  "
        f"Frameworks: {', '.join(report.get('regulatory_frameworks', [])) or 'All indexed'}"
    )
