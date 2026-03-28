import os
from groq import Groq

class BookCompoundAI:
    def __init__(self):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        # Using the Groq Compound model that handles native research
        self.model = "groq/compound" 

    def generate_with_research(self, system_role: str, user_prompt: str) -> str:
        """
        Single call for Research + Generation.
        The Compound model handles web retrieval internally.
        """
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": f"{system_role}. Use your research capabilities to verify all facts."},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.6 # Lower temperature for better factual consistency
        )
        return completion.choices[0].message.content