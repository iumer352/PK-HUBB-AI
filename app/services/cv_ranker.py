import logging
import json
import re
from typing import Dict, List
from together import Together
import json


logger = logging.getLogger(__name__)

class CVRankingAssistant:
    def __init__(self, api_key, model_name, temperature=0.7, top_p=0.7, top_k=50, repetition_penalty=1):
        self.client = Together(api_key=api_key)
        self.model_name = model_name
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.repetition_penalty = repetition_penalty

    def generate_prompt(self, job_description: Dict, cvs: List[Dict]) -> str:
         return f"""
        You are a CV scoring assistant. Analyze the resume against the job description and provide a scoring analysis in JSON format.

        Job Description:
        {json.dumps(job_description, indent=2)}

        Resume to Score:
        {json.dumps(cvs, indent=2)}

        Instructions:
        Calculate scores based on these criteria:
        * Skills (40%): Match with required skills
        * Experience (30%): Relevant work experience, evaluated as follows:

            Experience Evaluation Guidelines:
            1. Position-Based Experience Requirements:
               - Analyst: 0-5 years (ideal: 0-2, overqualified: >2)
               - Associate: 0-1 years (ideal: 0-1, overqualified: >5)
               - Senior Associate: 2-3 years (ideal: 2-3, overqualified: >6)
               - Assistant Manager: 3-4 years (ideal: 3-4, overqualified: >10)
               - Manager: 5-10 years (ideal: 5-8, overqualified: >20)
               - Manager1: 8-10 years (ideal: 8-10, overqualified: >20)
               - Senior Manager: 10+ years (ideal: 10-15)
               - Director: 15-20 years (ideal: 15-30, overqualified: >50)

            2. Experience Score Calculation:
               - Ideal Range Match: 100% of experience score
               - Within Acceptable Range: 80% of experience score
               - Slightly Outside Range (±1 year): 60% of experience score
               - Significantly Outside Range (±2 years): 40% of experience score
               - Overqualified/Underqualified: 0% of experience score

        * Education (20%): Relevant education
        * Certifications (10%): Relevant certifications

        Interview Questions Guidelines:
        Generate role-appropriate questions for each round based on these criteria:

        1. HR Round Questions should:
           - Verify resume claims and experience
           - Assess salary expectations and availability
           - Evaluate career progression and goals
           - Check cultural fit indicators
           - Focus on specific examples from past experiences
           Example: "Can you describe a specific project where you [relevant skill] and what was the measurable outcome?"

        2. Technical Round Questions should:
           - Test claimed technical skills
           - Include scenario-based problem-solving
           - Cover both theoretical knowledge and practical application
           - Address any skill gaps identified in the CV
           - Validate experience with specific tools/technologies
           Example: "How would you approach [specific technical challenge from job description]?"

        3. Cultural Round Questions should:
           - Assess teamwork and collaboration style
           - Evaluate communication skills
           - Check conflict resolution abilities
           - Understand leadership approach (if applicable)
           - Gauge adaptability and learning mindset
           Example: "Tell me about a time when you had to adapt to a major change at work."

        4. Final Round Questions should:
           - Focus on strategic thinking
           - Evaluate business acumen
           - Assess long-term potential
           - Validate key strengths
           - Address any concerns from previous rounds
           Example: "How do you see this role contributing to [company's current challenge or goal]?"

        Key Points for Question Generation:
        - Questions should be specific to the candidate's experience level
        - Include follow-up questions to dig deeper
        - Focus on gaps identified in the CV analysis
        - Consider industry-specific scenarios
        - Adapt complexity based on the role level
        - Include questions about specific achievements mentioned in CV

        Respond ONLY with a JSON object in this exact format:
        {{
            "Scores": [
                {{
                    "Name": "candidate_name",
                    "Overall_Score": 85.5,
                    "Score_Breakdown": {{
                        "Skills_Score": 34,
                        "Experience_Score": 25,
                        "Education_Score": 18,
                        "Certification_Score": 8.5
                    }},
                    "Evaluation": {{
                        "Pros": [
                            "Specific strength 1",
                            "Specific strength 2",
                            "Specific strength 3"
                        ],
                        "Cons": [
                            "Specific concern 1",
                            "Specific concern 2"
                        ],
                        "Job_Fit_Summary": "Clear explanation of why the candidate is/isn't suitable for the role"
                    }},
                    "Interview_Questions": {{
                        "HR_Round": [
                            "Specific question 1",
                            "Specific question 2"
                        ],
                        "Technical_Round": [
                            "Specific question 1",
                            "Specific question 2"
                        ],
                        "Cultural_Round": [
                            "Specific question 1",
                            "Specific question 2"
                        ],
                        "Final_Round": [
                            "Specific question 1",
                            "Specific question 2"
                        ]
                    }},
                    "Recommendation": "Proceed/Do Not Proceed"
                }}
            ]
        }}
        """

    def rank_cvs(self, job_description: Dict, cvs: List[Dict]) -> Dict:
        prompt = self.generate_prompt(job_description, cvs)
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                repetition_penalty=self.repetition_penalty,
                stop=["<|eot_id|>", "<|eom_id|>"],
                stream=True
            )

            parsed_response = ""
            for token in response:
                if hasattr(token, "choices") and token.choices:
                    if hasattr(token.choices[0].delta, 'content') and token.choices[0].delta.content is not None:
                        parsed_response += token.choices[0].delta.content

            # Clean and parse JSON response more robustly
            cleaned_response = parsed_response.strip()

            # Remove any markdown code block syntax
            cleaned_response = re.sub(r'^```json\s*', '', cleaned_response)
            cleaned_response = re.sub(r'\s*```$', '', cleaned_response)

            # Try to find JSON content within the response
            try:
                return json.loads(cleaned_response)
            except json.JSONDecodeError:
                # If direct parsing fails, try to find JSON-like content
                match = re.search(r'({[\s\S]*})', cleaned_response)
                if match:
                    return json.loads(match.group(1))
                else:
                    logger.error(f"Could not find valid JSON in response: {cleaned_response[:200]}")
                    raise HTTPException(
                        status_code=500, 
                        detail="Could not parse scoring response into valid JSON"
                    )

        except Exception as e:
            logger.error(f"Error in CV scoring: {str(e)}")
            logger.error(f"Full response content: {parsed_response[:500]}")
            raise HTTPException(status_code=500, detail=f"CV scoring failed: {str(e)}")