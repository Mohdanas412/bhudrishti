# Matching Engine — owner M5

Implements the weighted score (playbook Section 7):

match_score = 0.30*geometry_similarity + 0.25*spatial_proximity + 0.20*area_similarity
            + 0.15*attribute_similarity + 0.10*source_reliability

Thresholds (from .env / config, not hardcoded): >=90 high, 70-89 review, <70 unmatched.

Known open item from audit: matches are pairwise (feature_a/feature_b). Define the
clustering rule that groups pairwise matches across all 3 datasets into one
harmonized group before wiring up `harmonized_features` population.
