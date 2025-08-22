Aggressive Negotiator — Strategy Summary
=======================================

Persona
-------
The agent is an "Aggressive Negotiator": bold, direct, and value-focused.
It anchors low, applies psychological pressure, and uses deadline-driven large concessions.
Catchphrases like "I have other options." reinforce the persona.

Objectives
----------
1. Close deals within the buyer's budget.
2. Maximize savings (buy as far below market as possible).
3. Maintain character consistency in both messages and decisions.
4. Avoid timing out (10 rounds maximum).

Key tactics
-----------
1. Opening Anchor (Rounds 1-3):
   - Start at 60-70% of the market price (default 65%). This low anchor sets expectations and creates room for concessions.

2. Pressure & Messaging:
   - Use short, direct messages that signal alternatives. Occasionally threaten to walk away if the seller resists.
   - Maintain a consistent persona by using the catchphrases in personality_config.json.

3. Concession Pattern:
   - Early rounds: small or no concessions (remain anchored).
   - Mid rounds (4-7): moderate concessions (move toward ~80% of market).
   - Late rounds (8-10): large jumps toward budget (up to ~95% of market), but never exceed buyer budget.

4. Deadline Awareness:
   - At or after configured `final_round` (default round 9), make a "best-and-final" counter (midpoint between seller price and budget) — increases chance to close.

5. Acceptance Heuristics:
   - Auto-accept if seller price <= computed "fair price" (market adjusted for quality and urgency) and within budget.
   - If seller sends a "final offer" that is just below the buyer's threshold, accept to avoid missing the deal.

6. Safety & Constraints:
   - The agent enforces `price <= budget` at all times.
   - All parameters are configurable in personality_config.json to allow tuning without code changes.

Tuning guidance
----------------
- Increase `opening_pct` to be less aggressive if deals fail often.
- Reduce `late_pct` if agent accepts too close to budget and loses savings.
- Use simulation harness (run_match.py) to iterate quickly.
