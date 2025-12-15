"""
Streamlit interface for Healthcare Startup Valuation Tool
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from valuation_tool import (
    StartupInputs, RevenueModel, ClinicalStage,
    DCFModel, ComparableCompanyAnalysis, VCMethod,
    wacc_growth_sensitivity, STAGE_RISK_FACTORS
)

st.set_page_config(
    page_title="Healthcare Startup Valuation Tool",
    page_icon="💊",
    layout="wide"
)

st.title("💊 Healthcare Startup Valuation Tool")
st.markdown("*DCF, Comparable Companies & VC Method for Digital Health Startups*")

# ============================================================================
# SIDEBAR INPUTS
# ============================================================================

st.sidebar.header("📊 Startup Parameters")

company_name = st.sidebar.text_input("Company Name", "HealthTech Co")
current_revenue = st.sidebar.number_input(
    "Current Revenue ($M)", min_value=0.1, value=15.0, step=1.0
)

st.sidebar.subheader("Growth Assumptions")
col1, col2 = st.sidebar.columns(2)
with col1:
    y1_growth = st.number_input("Year 1", value=0.80, format="%.2f")
    y2_growth = st.number_input("Year 2", value=0.60, format="%.2f")
    y3_growth = st.number_input("Year 3", value=0.45, format="%.2f")
with col2:
    y4_growth = st.number_input("Year 4", value=0.35, format="%.2f")
    y5_growth = st.number_input("Year 5", value=0.25, format="%.2f")
    terminal_growth = st.number_input("Terminal", value=0.03, format="%.2f")

growth_rates = [y1_growth, y2_growth, y3_growth, y4_growth, y5_growth]

st.sidebar.subheader("Financial Assumptions")
gross_margin = st.sidebar.slider("Gross Margin", 0.4, 0.9, 0.70)
op_margin_target = st.sidebar.slider("Target Operating Margin", 0.1, 0.4, 0.20)
wacc = st.sidebar.slider("WACC", 0.08, 0.25, 0.15)

st.sidebar.subheader("Healthcare-Specific")
revenue_model = st.sidebar.selectbox(
    "Revenue Model",
    options=[rm.value for rm in RevenueModel],
    index=0
)
clinical_stage = st.sidebar.selectbox(
    "Clinical/Regulatory Stage",
    options=[cs.value for cs in ClinicalStage],
    index=2
)

# Convert selections back to enums
revenue_model_enum = next(rm for rm in RevenueModel if rm.value == revenue_model)
clinical_stage_enum = next(cs for cs in ClinicalStage if cs.value == clinical_stage)

# Create inputs object
inputs = StartupInputs(
    name=company_name,
    current_revenue=current_revenue,
    revenue_growth_rates=growth_rates,
    terminal_growth_rate=terminal_growth,
    gross_margin=gross_margin,
    operating_margin_target=op_margin_target,
    wacc=wacc,
    revenue_model=revenue_model_enum,
    clinical_stage=clinical_stage_enum,
)

# ============================================================================
# MAIN CONTENT
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 DCF Analysis", 
    "🏢 Comparable Companies", 
    "🚀 VC Method",
    "🔬 Sensitivity Analysis"
])

# --- TAB 1: DCF ---
with tab1:
    st.header("Discounted Cash Flow Valuation")
    
    dcf = DCFModel(inputs)
    projections = dcf.project_financials()
    results = dcf.calculate_valuation()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Enterprise Value", f"${results['Enterprise Value ($M)']:.1f}M")
    col2.metric("EV/Revenue Multiple", f"{results['Implied EV/Revenue Multiple']:.1f}x")
    col3.metric("Risk Adjustment", f"{results['Risk Adjustment Applied']:.0%}")
    
    st.subheader("Projected Financials")
    st.dataframe(projections.style.format({
        "Revenue ($M)": "${:.1f}",
        "Operating Margin": "{:.1%}",
        "FCF ($M)": "${:.1f}",
        "Discount Factor": "{:.3f}",
        "PV of FCF ($M)": "${:.1f}",
    }), use_container_width=True)
    
    # Revenue projection chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=projections["Year"],
        y=projections["Revenue ($M)"],
        name="Revenue",
        marker_color="#2E86AB"
    ))
    fig.add_trace(go.Scatter(
        x=projections["Year"],
        y=projections["FCF ($M)"],
        name="Free Cash Flow",
        mode="lines+markers",
        marker_color="#A23B72",
        yaxis="y2"
    ))
    fig.update_layout(
        title="Revenue & FCF Projections",
        yaxis=dict(title="Revenue ($M)"),
        yaxis2=dict(title="FCF ($M)", overlaying="y", side="right"),
        legend=dict(x=0.01, y=0.99),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Valuation waterfall
    st.subheader("Valuation Bridge")
    waterfall_data = [
        ("PV of FCF", results["PV of Projected FCF ($M)"]),
        ("PV of Terminal Value", results["PV of Terminal Value ($M)"]),
        ("Enterprise Value", results["Enterprise Value ($M)"]),
    ]
    fig_waterfall = go.Figure(go.Waterfall(
        x=[x[0] for x in waterfall_data],
        y=[x[1] for x in waterfall_data],
        measure=["relative", "relative", "total"],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#2E86AB"}},
        totals={"marker": {"color": "#28A745"}}
    ))
    fig_waterfall.update_layout(title="DCF Valuation Components")
    st.plotly_chart(fig_waterfall, use_container_width=True)

# --- TAB 2: COMPS ---
with tab2:
    st.header("Comparable Company Analysis")
    
    comps = ComparableCompanyAnalysis(
        target_revenue=current_revenue,
        target_growth=growth_rates[0]
    )
    
    with st.spinner("Fetching live market data..."):
        comp_data = comps.fetch_comparables()
        comp_results = comps.calculate_valuation()
    
    if not comp_data.empty and "Error" not in comp_results:
        st.subheader("Public Healthcare Tech Comparables")
        st.dataframe(comp_data.style.format({
            "Market Cap ($M)": "${:,.0f}",
            "Revenue ($M)": "${:,.0f}",
            "EV ($M)": "${:,.0f}",
            "EV/Revenue": "{:.2f}x",
            "Revenue Growth": "{:.1%}",
        }), use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Low Estimate", f"${comp_results['Implied EV - Low ($M)']:.1f}M")
        col2.metric("Mid Estimate", f"${comp_results['Implied EV - Mid ($M)']:.1f}M")
        col3.metric("High Estimate", f"${comp_results['Implied EV - High ($M)']:.1f}M")
        
        # Multiples comparison chart
        fig = px.bar(
            comp_data,
            x="Company",
            y="EV/Revenue",
            title="EV/Revenue Multiples Comparison",
            color="EV/Revenue",
            color_continuous_scale="Blues"
        )
        fig.add_hline(
            y=comp_results["Median EV/Revenue Multiple"],
            line_dash="dash",
            annotation_text="Median"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Could not fetch comparable company data. Yahoo Finance may be temporarily unavailable.")

# --- TAB 3: VC METHOD ---
with tab3:
    st.header("VC Method Valuation")
    
    st.markdown("*Work backwards from expected exit to determine today's valuation*")
    
    col1, col2 = st.columns(2)
    with col1:
        exit_revenue = st.number_input("Projected Exit Revenue ($M)", value=100.0, step=10.0)
        years_to_exit = st.slider("Years to Exit", 3, 10, 5)
    with col2:
        exit_multiple = st.number_input("Exit EV/Revenue Multiple", value=8.0, step=0.5)
        target_return = st.number_input("Target Return Multiple", value=5.0, step=0.5)
    
    vc = VCMethod(
        current_revenue=current_revenue,
        projected_exit_revenue=exit_revenue,
        years_to_exit=years_to_exit,
        exit_multiple=exit_multiple,
        target_return=target_return,
    )
    vc_results = vc.calculate_valuation()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Exit Value", f"${vc_results['Exit Value ($M)']:.0f}M")
    col2.metric("Pre-Money Valuation", f"${vc_results['Pre-Money Valuation ($M)']:.1f}M")
    col3.metric("Required CAGR", vc_results["Required Revenue CAGR"])
    
    st.info(f"To achieve a **{target_return:.0f}x return** over **{years_to_exit} years**, "
            f"requires an implied IRR of **{vc_results['Implied IRR']}**")
    
    # VC scenario chart
    years = list(range(0, years_to_exit + 1))
    revenue_path = [current_revenue * (exit_revenue/current_revenue)**(y/years_to_exit) for y in years]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years, y=revenue_path,
        mode="lines+markers",
        name="Revenue Growth Path",
        fill="tozeroy"
    ))
    fig.update_layout(
        title="Revenue Path to Exit",
        xaxis_title="Years",
        yaxis_title="Revenue ($M)"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 4: SENSITIVITY ---
with tab4:
    st.header("Sensitivity Analysis")
    
    st.subheader("WACC vs Terminal Growth Rate")
    sensitivity_df = wacc_growth_sensitivity(inputs)
    
    # Heatmap
    fig = px.imshow(
        sensitivity_df.values,
        x=sensitivity_df.columns,
        y=sensitivity_df.index,
        color_continuous_scale="RdYlGn",
        aspect="auto",
        labels=dict(color="EV ($M)")
    )
    fig.update_layout(title="Enterprise Value Sensitivity ($M)")
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(sensitivity_df.style.format("${:.1f}M"), use_container_width=True)
    
    # Clinical stage impact
    st.subheader("Clinical Stage Risk Impact")
    stage_impact = []
    for stage in ClinicalStage:
        modified_inputs = StartupInputs(
            name=inputs.name,
            current_revenue=inputs.current_revenue,
            revenue_growth_rates=inputs.revenue_growth_rates,
            terminal_growth_rate=inputs.terminal_growth_rate,
            gross_margin=inputs.gross_margin,
            operating_margin_target=inputs.operating_margin_target,
            wacc=inputs.wacc,
            revenue_model=inputs.revenue_model,
            clinical_stage=stage,
        )
        dcf = DCFModel(modified_inputs)
        val = dcf.calculate_valuation()
        stage_impact.append({
            "Stage": stage.value,
            "Risk Factor": STAGE_RISK_FACTORS[stage],
            "Enterprise Value ($M)": val["Enterprise Value ($M)"]
        })
    
    stage_df = pd.DataFrame(stage_impact)
    fig = px.bar(
        stage_df,
        x="Stage",
        y="Enterprise Value ($M)",
        color="Risk Factor",
        color_continuous_scale="RdYlGn",
        title="Valuation by Clinical/Regulatory Stage"
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
**Methodology Notes:**
- DCF uses stage-adjusted terminal values to reflect healthcare-specific regulatory/clinical risk
- Comparable company multiples are fetched live and adjusted for relative growth
- VC Method assumes standard venture return expectations

*Built for healthcare technology valuation analysis*
""")
