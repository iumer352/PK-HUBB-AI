class ResumeParser:
    def __init__(self, api_key, temperature=0.7, top_p=0.7, top_k=50, repetition_penalty=1):
        logger.info("Initializing ResumeParser...")
        try:
            self.client = Together(api_key=api_key)
            logger.info("Together client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Together client: {str(e)}")
            raise
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.repetition_penalty = repetition_penalty

    @staticmethod
    def extract_text_from_file(file_path: str):
        logger.info(f"Starting text extraction from: {file_path}")
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        try:
            if ext == ".pdf":
                return ResumeParser._extract_text_from_pdf(file_path)
            elif ext == ".docx":
                return ResumeParser._extract_text_from_docx(file_path)
            elif ext == ".doc":
                return ResumeParser._extract_text_from_doc(file_path)
            else:
                logger.error(f"Unsupported file type: {ext}")
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error extracting text: {str(e)}")

    @staticmethod
    def _extract_text_from_pdf(pdf_path):
        logger.info(f"Starting PDF text extraction from: {pdf_path}")
        try:
            reader = PdfReader(pdf_path)
            logger.debug(f"PDF loaded successfully, number of pages: {len(reader.pages)}")
            
            text = ""
            for i, page in enumerate(reader.pages):
                logger.debug(f"Processing page {i+1}/{len(reader.pages)}")
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            if not text.strip():
                logger.error("No text content found in PDF")
                raise ValueError("No text found in the PDF.")
            
            logger.info(f"Successfully extracted {len(text)} characters from PDF")
            logger.debug(f"First 100 characters of extracted text: {text[:100]}")
            return text.strip()
        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error extracting text from PDF: {str(e)}")

    @staticmethod
    def _extract_text_from_docx(docx_path):
        logger.info(f"Starting DOCX text extraction from: {docx_path}")
        try:
            doc = docx.Document(docx_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            if not text.strip():
                logger.error("No text content found in DOCX")
                raise ValueError("No text found in the DOCX file.")
            logger.info(f"Successfully extracted text from DOCX")
            return text.strip()
        except Exception as e:
            logger.error(f"DOCX extraction failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error extracting text from DOCX: {str(e)}")

    @staticmethod
    def create_prompt(text, parse_type):
        logger.info(f"Creating prompt for parse_type: {parse_type}")
        logger.debug(f"Input text length: {len(text)} characters")
        
        if parse_type == "resume":
            prompt = f'''
            You are a highly accurate and concise resume parser. Parse the following resume text and return the structured information in **JSON format only**.
            Do not include any additional explanations, echoed text, or anything other than the JSON response.

            ### Resume Text:
            {text}

            ### Fields to Extract:
            - Name: Full name of the person.
            - Email: Email address.
            - Phone: Phone number.
            - LinkedIn: LinkedIn profile link (or "Not available" if missing).
            - Education: Extract degree, university, year, and details.
            - Skills: List all skills.
            - Work Experience: Include role, company, duration, and key responsibilities.
            - Certifications/Courses: List certifications with titles and organizations.
            - Projects: Include title and description.
            - Languages: List languages and proficiency levels.

            ### Response Format:
            {{
                "Name": "John Doe",
                "Email": "john.doe@example.com",
                "Phone": "123-456-7890",
                "LinkedIn": "linkedin.com/in/johndoe",
                "Education": [
                    {{
                        "Degree": "B.Sc. Computer Science",
                        "University": "XYZ University",
                        "Year": "2015-2019",
                        "Details": "Graduated with honors"
                    }}
                ],
                "Skills": ["Python", "Machine Learning", "Data Analysis"],
                "Work Experience": [
                    {{
                        "Role": "Data Scientist",
                        "Company": "ABC Corp",
                        "Duration": "2019-2022",
                        "Responsibilities": ["Developed ML models", "Improved data pipelines"]
                    }}
                ],
                "Certifications": [
                    {{
                        "Title": "AI for Everyone",
                        "Organization": "Coursera"
                    }}
                ],
                "Projects": [
                    {{
                        "Title": "Resume Parser",
                        "Description": "A project to parse resumes using AI"
                    }}
                ],
                "Languages": ["English", "Spanish"]
            }}

            ### Response:
            '''
        elif parse_type == "job_description":
            prompt = f'''
            You are a highly accurate and concise text parser. Parse the following text from the given job description and return the structured information in **JSON format only**.

            ### Fields to Extract:
            - **Role Overview**: Summarize the role's responsibilities and focus areas.
            - **Key Responsibilities**: List the primary responsibilities of the role.
            - **Key Skills and Competencies**: Highlight required skills, subject matter expertise, and competencies.
            - **Experience**: Identify the experience requirements and areas of expertise.
            - **What We're Looking For**: Specify the personal qualities and attributes desired for the role.

            ### Job Description:
            {text}

            ### Response:
            '''
        else:
            logger.error(f"Invalid parse_type received: {parse_type}")
            raise HTTPException(status_code=400, detail="Invalid parse type. Must be 'resume' or 'job_description'")
        
        logger.debug(f"Generated prompt length: {len(prompt)} characters")
        return prompt

    def generate_response(self, model_name, prompt, max_tokens):
        try:
            logger.info("Starting API call to Together")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                repetition_penalty=self.repetition_penalty,
                stop=["<|eot_id|>", "<|eom_id|>"],
                stream=True
            )

            logger.info("API call successful, processing stream response")
            parsed_response = ""
            for token in response:
                if hasattr(token, "choices") and token.choices:
                    if hasattr(token.choices[0].delta, 'content') and token.choices[0].delta.content is not None:
                        parsed_response += token.choices[0].delta.content

            try:
                cleaned_response = parsed_response.replace("```json", "").replace("```", "").strip()
                return cleaned_response
            except Exception as e:
                logger.error(f"Response processing failed: {str(e)}")
                logger.debug(f"Raw response content: {parsed_response[:500]}")
                raise HTTPException(status_code=500, detail=f"Error processing response: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in generate_response: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

    def parse_text(self, text, parse_type, model_name):
        logger.info(f"Starting text parsing for type: {parse_type}")
        prompt = self.create_prompt(text, parse_type)
        max_tokens = 4096 if parse_type == "resume" else 1024
        
        try:
            logger.info("Calling generate_response")
            response_text = self.generate_response(model_name, prompt, max_tokens)
            
            if response_text:
                logger.info("Attempting to parse response as JSON")
                try:
                    parsed_json = json.loads(response_text)
                    logger.info("Successfully parsed JSON response")
                    return parsed_json
                except json.JSONDecodeError as je:
                    logger.error(f"JSON parsing failed: {str(je)}")
                    logger.debug(f"Failed JSON content: {response_text[:500]}")
                    raise HTTPException(status_code=500, detail=f"Invalid JSON response: {str(je)}")
            else:
                logger.error("Empty response received from generate_response")
                raise HTTPException(status_code=500, detail="No response generated")
                
        except Exception as e:
            logger.error(f"Error in parse_text: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))