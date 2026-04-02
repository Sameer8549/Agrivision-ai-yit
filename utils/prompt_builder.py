"""
CropSentinel AI  -  utils/prompt_builder.py
Builds structured prompts for the three LLM tiers.
Avoids nested quotes inside f-strings by pre-extracting geo values.
"""

import logging

logger = logging.getLogger("PromptBuilder")


class PromptBuilder:
    """
    Assembles disease-specific prompts for each LLM tier.

    Tier 1 (Groq)     -  Standard advisory
    Tier 2 (Mixtral)  -  Differential diagnosis + extended fields
    Tier 3 (Ollama)   -  Compact offline fallback
    """

    def build_tier1(
        self,
        crop: str,
        disease: str,
        confidence: float,
        severity: str,
        geo: dict,
    ) -> str:
        region       = geo["region_name"]
        ts           = geo["timestamp_str"]
        season       = geo["season"]
        humidity     = geo["humidity_estimate"]
        rainfall     = geo["rainfall_context"]
        seas_risk    = geo["seasonal_risk"]
        risk_note    = geo["risk_note"]

        return (
            "You are CropSentinel, an elite agricultural expert and plant pathologist "
            "with 20+ years of experience in South Asian farming  -  especially Karnataka, "
            "Andhra Pradesh, Tamil Nadu, and Maharashtra.\n\n"
            "CROP DISEASE DETECTION:\n"
            f"  Crop       : {crop}\n"
            f"  Disease    : {disease}\n"
            f"  Confidence : {confidence:.1f}%\n"
            f"  Severity   : {severity}\n\n"
            "ENVIRONMENTAL CONTEXT:\n"
            f"  Location      : {region}\n"
            f"  Date and Time : {ts}\n"
            f"  Season        : {season}\n"
            f"  Humidity      : {humidity}%\n"
            f"  Rainfall      : {rainfall}\n"
            f"  Seasonal Risk : {seas_risk}\n"
            f"  Risk Note     : {risk_note}\n\n"
            "Respond ONLY with valid JSON. No markdown. No text before or after the JSON.\n"
            "{\n"
            '  "action_plan": [\n'
            '    "Action step 1",\n'
            '    "Action step 2",\n'
            '    "Action step 3",\n'
            '    "Action step 4",\n'
            '    "Action step 5"\n'
            '  ],\n'
            '  "est_recovery": "Estimated recovery time in days (e.g. 14-21 days)",\n'
            f'  "preventive_note": "Specific preventive note factoring in {season} conditions and {humidity}% humidity for {region}"\n'
            "}"
        )

    def build_tier2(
        self,
        crop: str,
        disease: str,
        confidence: float,
        severity: str,
        geo: dict,
        top3: list,
    ) -> str:
        while len(top3) < 3:
            top3.append({"disease": "Unknown", "confidence": 0.0})

        region    = geo["region_name"]
        ts        = geo["timestamp_str"]
        season    = geo["season"]
        humidity  = geo["humidity_estimate"]
        rainfall  = geo["rainfall_context"]
        seas_risk = geo["seasonal_risk"]
        risk_note = geo["risk_note"]

        d1 = top3[0]["disease"]
        c1 = top3[0]["confidence"]
        d2 = top3[1]["disease"]
        c2 = top3[1]["confidence"]
        d3 = top3[2]["disease"]
        c3 = top3[2]["confidence"]

        return (
            "You are CropSentinel, an elite agricultural expert and plant pathologist "
            "with 20+ years of experience in South Asian farming  -  especially Karnataka, "
            "Andhra Pradesh, Tamil Nadu, and Maharashtra.\n\n"
            "CROP DISEASE DETECTION:\n"
            f"  Crop       : {crop}\n"
            f"  Disease    : {disease}\n"
            f"  Confidence : {confidence:.1f}%\n"
            f"  Severity   : {severity}\n\n"
            "ENVIRONMENTAL CONTEXT:\n"
            f"  Location      : {region}\n"
            f"  Date and Time : {ts}\n"
            f"  Season        : {season}\n"
            f"  Humidity      : {humidity}%\n"
            f"  Rainfall      : {rainfall}\n"
            f"  Seasonal Risk : {seas_risk}\n"
            f"  Risk Note     : {risk_note}\n\n"
            "TOP 3 PREDICTIONS FOR DIFFERENTIAL DIAGNOSIS:\n"
            f"  1. {d1} ({c1}%)\n"
            f"  2. {d2} ({c2}%)\n"
            f"  3. {d3} ({c3}%)\n\n"
            "Respond ONLY with valid JSON. No markdown. No text before or after the JSON.\n"
            "{\n"
            '  "action_plan": [\n'
            '    "Action step 1",\n'
            '    "Action step 2",\n'
            '    "Action step 3",\n'
            '    "Action step 4",\n'
            '    "Action step 5"\n'
            '  ],\n'
            '  "est_recovery": "Estimated recovery time in days (e.g. 14-21 days)",\n'
            f'  "preventive_note": "Specific preventive note factoring in {season} conditions and {humidity}% humidity for {region}",\n'
            f'  "differential_diagnosis": "Why this is {disease} and not {d2}",\n'
            '  "yield_impact": "Estimated yield loss if untreated (percentage)",\n'
            '  "escalate_to_expert": false\n'
            "}"
        )

    def build_tier3(
        self,
        crop: str,
        disease: str,
        severity: str,
    ) -> str:
        return (
            f"Crop: {crop} | Disease: {disease} | Severity: {severity}\n"
            "You are a plant pathologist. Provide concise farmer advice as JSON only.\n"
            "{\n"
            '  "action_plan": ["step 1", "step 2", "step 3", "step 4", "step 5"],\n'
            '  "est_recovery": "...",\n'
            '  "preventive_note": "..."\n'
            "}\n"
            "Keep response under 200 words. JSON only. No markdown."
        )
