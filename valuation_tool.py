"""
Healthcare Startup Valuation Tool
A Python tool for valuing digital health and healthcare technology startups
using DCF, Comparable Company Analysis, and VC Method approaches.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from dataclasses import dataclass
from enum import Enum
from typing import Optional

# ============================================================================
# CONFIGURATION & ENUMS
# ============================================================================

class RevenueModel(Enum):
    B2B_SAAS = "B2B SaaS"
    B2C_SUBSCRIPTION = "B2C Subscription"
    PAYER_CONTRACT = "Payer Contract"
    PROVIDER_LICENSE = "Provider License"
    HYBRID = "Hybrid"

class ClinicalStage(Enum):
    PRE_CLINICAL = "Pre-Clinical/Concept"
    PILOT = "Pilot Studies"
    VALIDATED = "Clinically Validated"
    FDA_CLEARED = "FDA Cleared/CE Marked"
    REIMBURSED = "Reimbursement Secured"

# Risk adjustments by stage (applied to terminal value)
STAGE_RISK_FACTORS = {
    ClinicalStage.PRE_CLINICAL: 0.4,
    ClinicalStage.PILOT: 0.55,
    ClinicalStage.VALIDATED: 0.7,
    ClinicalStage.FDA_CLEARED: 0.85,
    ClinicalStage.REIMBURSED: 1.0,
}

# Public healthcare tech comparables (tickers)
COMPARABLE_TICKERS = {
    "TDOC": "Teladoc Health",
    "DOCS": "Doximity",
    "VEEV": "Veeva Systems",
    "HIMS": "Hims & Hers",
    "AMWL": "Amwell",
    "OSCR": "Oscar Health",
}


@dataclass
class StartupInputs:
    """Input parameters for startup valuation."""
    name: str
    current_revenue: float  # in millions
    revenue_growth_rates: list[float]  # year-over-year growth for projection period
    terminal_growth_rate: float
    gross_margin: float
    operating_margin_target: float  # target margin at maturity
    wacc: float
    revenue_model: RevenueModel
    clinical_stage: ClinicalStage
    years_to_project: int = 5


# ============================================================================
# VALUATION MODELS
# ============================================================================

class DCFModel:
    """Discounted Cash Flow valuation model with healthcare adjustments."""
    
    def __init__(self, inputs: StartupInputs):
        self.inputs = inputs
        self.projections = None
    
    def project_financials(self) -> pd.DataFrame:
        """Project revenue and cash flows over the forecast period."""
        years = range(1, self.inputs.years_to_project + 1)
        revenue = [self.inputs.current_revenue]
        
        # Project revenue with declining growth rates
        for i, growth in enumerate(self.inputs.revenue_growth_rates):
            revenue.append(revenue[-1] * (1 + growth))
        revenue = revenue[1:]  # Remove base year
        
        # Margin expansion from current to target
        margin_ramp = np.linspace(
            self.inputs.gross_margin * 0.3,  # Start at ~30% of gross as operating
            self.inputs.operating_margin_target,
            self.inputs.years_to_project
        )
        
        fcf = [rev * margin for rev, margin in zip(revenue, margin_ramp)]
        discount_factors = [(1 + self.inputs.wacc) ** -y for y in years]
        pv_fcf = [f * d for f, d in zip(fcf, discount_factors)]
        
        self.projections = pd.DataFrame({
            "Year": list(years),
            "Revenue ($M)": revenue,
            "Operating Margin": margin_ramp,
            "FCF ($M)": fcf,
            "Discount Factor": discount_factors,
            "PV of FCF ($M)": pv_fcf,
        })
        return self.projections
    
    def calculate_terminal_value(self) -> float:
        """Calculate terminal value using perpetuity growth method."""
        if self.projections is None:
            self.project_financials()
        
        final_fcf = self.projections["FCF ($M)"].iloc[-1]
        tv = (final_fcf * (1 + self.inputs.terminal_growth_rate)) / \
             (self.inputs.wacc - self.inputs.terminal_growth_rate)
        
        # Apply clinical stage risk adjustment
        risk_factor = STAGE_RISK_FACTORS[self.inputs.clinical_stage]
        return tv * risk_factor
    
    def calculate_valuation(self) -> dict:
        """Calculate enterprise value via DCF."""
        if self.projections is None:
            self.project_financials()
        
        pv_fcf_sum = self.projections["PV of FCF ($M)"].sum()
        terminal_value = self.calculate_terminal_value()
        pv_terminal = terminal_value / (1 + self.inputs.wacc) ** self.inputs.years_to_project
        
        enterprise_value = pv_fcf_sum + pv_terminal
        
        return {
            "PV of Projected FCF ($M)": round(pv_fcf_sum, 2),
            "Terminal Value ($M)": round(terminal_value, 2),
            "PV of Terminal Value ($M)": round(pv_terminal, 2),
            "Enterprise Value ($M)": round(enterprise_value, 2),
            "Implied EV/Revenue Multiple": round(enterprise_value / self.inputs.current_revenue, 1),
            "Risk Adjustment Applied": STAGE_RISK_FACTORS[self.inputs.clinical_stage],
        }


class ComparableCompanyAnalysis:
    """Valuation using public healthcare tech company multiples."""
    
    def __init__(self, target_revenue: float, target_growth: float):
        self.target_revenue = target_revenue
        self.target_growth = target_growth
        self.comparables = None
    
    def fetch_comparables(self) -> pd.DataFrame:
        """Fetch current trading multiples for comparable companies."""
        data = []
        
        for ticker, name in COMPARABLE_TICKERS.items():
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                market_cap = info.get("marketCap", 0) / 1e6  # Convert to millions
                revenue = info.get("totalRevenue", 0) / 1e6
                ev = info.get("enterpriseValue", 0) / 1e6
                growth = info.get("revenueGrowth", 0)
                
                if revenue > 0:
                    data.append({
                        "Ticker": ticker,
                        "Company": name,
                        "Market Cap ($M)": round(market_cap, 1),
                        "Revenue ($M)": round(revenue, 1),
                        "EV ($M)": round(ev, 1),
                        "EV/Revenue": round(ev / revenue, 2) if revenue else None,
                        "Revenue Growth": growth,
                    })
            except Exception as e:
                print(f"Error fetching {ticker}: {e}")
        
        self.comparables = pd.DataFrame(data)
        return self.comparables
    
    def calculate_valuation(self, apply_growth_premium: bool = True) -> dict:
        """Calculate implied valuation based on comparable multiples."""
        if self.comparables is None:
            self.fetch_comparables()
        
        if self.comparables.empty or "EV/Revenue" not in self.comparables.columns:
            return {
                "Median EV/Revenue Multiple": None,
                "25th Percentile Multiple": None,
                "75th Percentile Multiple": None,
                "Growth Adjustment Factor": None,
                "Implied EV - Low ($M)": None,
                "Implied EV - Mid ($M)": None,
                "Implied EV - High ($M)": None,
                "Error": "Could not fetch comparable company data"
            }
        
        multiples = self.comparables["EV/Revenue"].dropna()
        
        median_multiple = multiples.median()
        p25_multiple = multiples.quantile(0.25)
        p75_multiple = multiples.quantile(0.75)
        
        # Growth premium/discount adjustment
        if apply_growth_premium:
            avg_comp_growth = self.comparables["Revenue Growth"].mean()
            growth_diff = self.target_growth - avg_comp_growth
            adjustment = 1 + (growth_diff * 2)  # 2x multiplier on growth differential
            adjustment = max(0.5, min(adjustment, 2.0))  # Cap between 0.5x and 2x
        else:
            adjustment = 1.0
        
        return {
            "Median EV/Revenue Multiple": round(median_multiple, 2),
            "25th Percentile Multiple": round(p25_multiple, 2),
            "75th Percentile Multiple": round(p75_multiple, 2),
            "Growth Adjustment Factor": round(adjustment, 2),
            "Implied EV - Low ($M)": round(self.target_revenue * p25_multiple * adjustment, 1),
            "Implied EV - Mid ($M)": round(self.target_revenue * median_multiple * adjustment, 1),
            "Implied EV - High ($M)": round(self.target_revenue * p75_multiple * adjustment, 1),
        }


class VCMethod:
    """VC Method valuation (work backwards from exit)."""
    
    def __init__(
        self,
        current_revenue: float,
        projected_exit_revenue: float,
        years_to_exit: int,
        exit_multiple: float,
        target_return: float,  # e.g., 10x = 10.0
    ):
        self.current_revenue = current_revenue
        self.exit_revenue = projected_exit_revenue
        self.years = years_to_exit
        self.exit_multiple = exit_multiple
        self.target_return = target_return
    
    def calculate_valuation(self) -> dict:
        """Calculate pre-money valuation using VC method."""
        exit_value = self.exit_revenue * self.exit_multiple
        
        # Work backwards: what's the current value to achieve target return?
        pre_money = exit_value / self.target_return
        
        # Calculate implied IRR if invested at this valuation
        implied_irr = (self.target_return ** (1 / self.years)) - 1
        
        # Revenue CAGR to exit
        revenue_cagr = (self.exit_revenue / self.current_revenue) ** (1 / self.years) - 1
        
        return {
            "Projected Exit Revenue ($M)": round(self.exit_revenue, 1),
            "Exit EV/Revenue Multiple": self.exit_multiple,
            "Exit Value ($M)": round(exit_value, 1),
            "Target Return Multiple": f"{self.target_return}x",
            "Pre-Money Valuation ($M)": round(pre_money, 1),
            "Implied IRR": f"{implied_irr:.1%}",
            "Required Revenue CAGR": f"{revenue_cagr:.1%}",
        }


# ============================================================================
# SENSITIVITY ANALYSIS
# ============================================================================

def wacc_growth_sensitivity(
    inputs: StartupInputs,
    wacc_range: tuple = (0.10, 0.20),
    growth_range: tuple = (0.02, 0.05),
    steps: int = 5
) -> pd.DataFrame:
    """Generate sensitivity table for WACC vs terminal growth rate."""
    waccs = np.linspace(wacc_range[0], wacc_range[1], steps)
    growths = np.linspace(growth_range[0], growth_range[1], steps)
    
    results = []
    for w in waccs:
        row = {"WACC": f"{w:.1%}"}
        for g in growths:
            modified = StartupInputs(
                name=inputs.name,
                current_revenue=inputs.current_revenue,
                revenue_growth_rates=inputs.revenue_growth_rates,
                terminal_growth_rate=g,
                gross_margin=inputs.gross_margin,
                operating_margin_target=inputs.operating_margin_target,
                wacc=w,
                revenue_model=inputs.revenue_model,
                clinical_stage=inputs.clinical_stage,
            )
            dcf = DCFModel(modified)
            val = dcf.calculate_valuation()
            row[f"g={g:.1%}"] = round(val["Enterprise Value ($M)"], 1)
        results.append(row)
    
    return pd.DataFrame(results).set_index("WACC")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example: Digital health startup focused on remote patient monitoring
    startup = StartupInputs(
        name="HealthTech Example Co",
        current_revenue=15.0,  # $15M ARR
        revenue_growth_rates=[0.80, 0.60, 0.45, 0.35, 0.25],  # Declining growth
        terminal_growth_rate=0.03,
        gross_margin=0.70,
        operating_margin_target=0.20,
        wacc=0.15,
        revenue_model=RevenueModel.B2B_SAAS,
        clinical_stage=ClinicalStage.VALIDATED,
    )
    
    print(f"\n{'='*60}")
    print(f"VALUATION ANALYSIS: {startup.name}")
    print(f"{'='*60}")
    
    # DCF Valuation
    print("\n1. DCF VALUATION")
    print("-" * 40)
    dcf = DCFModel(startup)
    projections = dcf.project_financials()
    print("\nProjected Financials:")
    print(projections.to_string(index=False))
    
    dcf_result = dcf.calculate_valuation()
    print("\nDCF Results:")
    for k, v in dcf_result.items():
        print(f"  {k}: {v}")
    
    # Comparable Company Analysis
    print("\n2. COMPARABLE COMPANY ANALYSIS")
    print("-" * 40)
    comps = ComparableCompanyAnalysis(
        target_revenue=startup.current_revenue,
        target_growth=startup.revenue_growth_rates[0]
    )
    print("\nFetching comparable company data...")
    comp_data = comps.fetch_comparables()
    print(comp_data.to_string(index=False))
    
    comp_result = comps.calculate_valuation()
    print("\nComps Valuation:")
    for k, v in comp_result.items():
        print(f"  {k}: {v}")
    
    # VC Method
    print("\n3. VC METHOD")
    print("-" * 40)
    vc = VCMethod(
        current_revenue=startup.current_revenue,
        projected_exit_revenue=100.0,  # $100M at exit
        years_to_exit=5,
        exit_multiple=8.0,
        target_return=5.0,  # 5x return target
    )
    vc_result = vc.calculate_valuation()
    print("\nVC Method Results:")
    for k, v in vc_result.items():
        print(f"  {k}: {v}")
    
    # Sensitivity Analysis
    print("\n4. SENSITIVITY ANALYSIS (WACC vs Terminal Growth)")
    print("-" * 40)
    sensitivity = wacc_growth_sensitivity(startup)
    print(sensitivity)
