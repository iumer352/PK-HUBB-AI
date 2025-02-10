from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import List
from pydantic import BaseModel
from dotenv import load_dotenv
import logging
from app.services.cv_parser import ResumeParser
from app.services.cv_ranker import CVRankingAssistant
from app.config import get_settings
import json

import os
# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

load_dotenv()

parser = ResumeParser(api_key=os.getenv("TOGETHER_API_KEY"))
ranker = CVRankingAssistant(api_key=os.getenv("TOGETHER_API_KEY"), model_name=os.getenv("MODEL_NAME"))

class ScoreBreakdown(BaseModel):

    Skills_Score: float
    Experience_Score: float
    Education_Score: float
    Certification_Score: float

class Evaluation(BaseModel):
    Pros: List[str]
    Cons: List[str]
    Job_Fit_Summary: str

class InterviewQuestions(BaseModel):
    HR_Round: List[str]
    Technical_Round: List[str]
    Cultural_Round: List[str]
    Final_Round: List[str]

class CandidateScore(BaseModel):
    Overall_Score: float
    Score_Breakdown: ScoreBreakdown
    Evaluation: Evaluation
    Interview_Questions: InterviewQuestions
    Recommendation: str

class ParsedDocument(BaseModel):
    filename: str
    content: dict
    score: CandidateScore = None

class MultipleParseResponse(BaseModel):
    successful_parses: List[ParsedDocument]
    failed_files: List[dict]

@router.post("/parse-and-rank", response_model=MultipleParseResponse)
async def parse_and_rank_documents(
    files: List[UploadFile] = File(...),
    job_description: str = Form(...) 
):
    logger.info(f"Received {len(files)} files for processing")
    logger.info(f"Received job description: {job_description}")
    
    successful_parses = []
    failed_files = []
    
    # Process all CVs first
    for file in files:
        if not file.filename.endswith('.pdf'):
            failed_files.append({
                "filename": file.filename,
                "error": "Only PDF files are supported"
            })
            continue
            
        temp_path = f"temp_{file.filename}"
        try:
            # Save and process file
            with open(temp_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            text = parser.extract_text_from_pdf(temp_path)
            parse_type = "resume"
            result = parser.parse_text(text, parse_type, os.getenv("MODEL_NAME"))
            

            # Calculate score if job description is provided
            score = None
            if job_description:
                try:
                    job_desc_parsed = {
                        "description": job_description
                    }
                    cv_for_scoring = {
                        "id": file.filename,
                        "content": result
                    }
                    score_result = ranker.rank_cvs(job_desc_parsed, [cv_for_scoring])
                    
                    if score_result and "Scores" in score_result and len(score_result["Scores"]) > 0:
                        score_data = score_result["Scores"][0]
                        score = CandidateScore(
                            Overall_Score=score_data["Overall_Score"],
                            Score_Breakdown=ScoreBreakdown(
                                Skills_Score=score_data["Score_Breakdown"]["Skills_Score"],
                                Experience_Score=score_data["Score_Breakdown"]["Experience_Score"],
                                Education_Score=score_data["Score_Breakdown"]["Education_Score"],
                                Certification_Score=score_data["Score_Breakdown"]["Certification_Score"]
                            ),
                            Evaluation=Evaluation(
                                Pros=score_data["Evaluation"]["Pros"],
                                Cons=score_data["Evaluation"]["Cons"],
                                Job_Fit_Summary=score_data["Evaluation"]["Job_Fit_Summary"]
                            ),
                            Interview_Questions=InterviewQuestions(
                                HR_Round=score_data["Interview_Questions"]["HR_Round"],
                                Technical_Round=score_data["Interview_Questions"]["Technical_Round"],
                                Cultural_Round=score_data["Interview_Questions"]["Cultural_Round"],
                                Final_Round=score_data["Interview_Questions"]["Final_Round"]
                            ),
                            Recommendation=score_data["Recommendation"]
                        )
                except Exception as e:
                    logger.error(f"Error calculating score: {str(e)}")
                    logger.exception("Detailed scoring error")
            
            successful_parses.append(ParsedDocument(
                filename=file.filename,
                content=result,
                score=score
            ))
            
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")
            logger.exception("Detailed processing error")
            failed_files.append({
                "filename": file.filename,
                "error": str(e)
            })
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    if not successful_parses:
        raise HTTPException(
            status_code=500, 
            detail="No files were successfully processed"
        )
    
    return MultipleParseResponse(
        successful_parses=successful_parses,
        failed_files=failed_files
    )