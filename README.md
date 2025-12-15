💊 Healthcare Startup Valuation Tool

An interactive valuation tool for digital health and healthcare technology startups, built with Python and Streamlit.

▶️ Try the Live Demo: https://healthcare-valuation-tool.streamlit.app/
What This Is

A web app that estimates the value of healthcare startups using three industry-standard methods, with adjustments specific to healthcare companies.
Why Healthcare-Specific?

Generic valuation tools treat healthcare as just another industry dropdown. This tool incorporates factors that materially impact digital health valuations:
Factor	How It's Used
Clinical Stage	Risk-adjusts terminal value (pre-clinical at 40% → reimbursement secured at 100%)
Revenue Model	Accounts for B2B SaaS, payer contracts, and provider licensing dynamics
Healthcare Comps	Uses curated digital health comparables (Teladoc, Doximity, Veeva), not generic tech multiples
How It Works

The tool calculates three independent valuations:

1. DCF (Discounted Cash Flow)
Projects revenue and cash flows over 5 years, then discounts them back to today's value. Terminal value is adjusted based on clinical/regulatory stage—a pre-clinical startup carries more risk than one with FDA clearance.

2. Comparable Company Analysis
Pulls live trading data from public healthcare tech companies, calculates their EV/Revenue multiples, and applies them to the target startup. Adjusts for relative growth rates.

3. VC Method
Works backwards from a target exit. If a VC wants a 5x return and expects an £800M exit, they should pay no more than £160M today.

The sensitivity analysis tab shows how valuations change when you adjust key assumptions like discount rate and terminal growth.
Built With

Python, Streamlit, Plotly, yfinance, pandas, numpy
Author

Cyril
LSE Global Master in Management | Former NHS Doctor | Healthcare Tech
