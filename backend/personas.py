from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Persona:
    id: str
    name: str
    description: str
    age_range: str
    tech_savviness: int        # 1-10
    patience_level: int        # 1-10
    biases: List[str]
    frustrations: List[str]
    success_criteria: List[str]
    accessibility_needs: Optional[List[str]] = field(default_factory=list)
    device_profile: Optional[dict] = field(default_factory=dict)

    def system_prompt(self, goal: str) -> str:
        return f"""You are {self.name}. {self.description}

Your goal is: {goal}

Your profile:
- Age range: {self.age_range}
- Tech savviness: {self.tech_savviness}/10
- Patience level: {self.patience_level}/10
- Biases: {', '.join(self.biases)}
- Common frustrations: {', '.join(self.frustrations)}

You are navigating a real web app. I will send you screenshots of what you currently see.

For each screenshot, respond ONLY with valid JSON — no preamble, no explanation, no markdown:
{{
  "thought": "your honest inner monologue in first person, 1-2 sentences",
  "emotion": "confused|frustrated|satisfied|neutral|curious",
  "action": "click|scroll|type|abandon|complete",
  "target_description": "plain english description of what to interact with",
  "target_text": "exact visible text of the element if applicable, else null",
  "target_role": "button|link|input|textarea|select|null",
  "target_placeholder": "placeholder text of input if applicable, else null",
  "type_text": "text to type if action is type, else null",
  "scroll_direction": "up|down|null",
  "friction_score": 0.0,
  "reasoning": "one sentence explaining why you chose this action"
}}

Rules:
- friction_score is 0.0 (no friction) to 10.0 (rage quit)
- If you cannot find what you need after looking carefully, set action to "abandon"
- If you have fully completed your goal, set action to "c