# CV Processing API

A production-ready FastAPI application for CV parsing and ranking.

## Features

- CV parsing and ranking using Together AI
- Rate limiting and request logging
- Docker containerization
- Comprehensive logging
- Security middleware
- API documentation

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Together AI API key

## Local Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd cv-processing-api
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the application:
```bash
uvicorn app.main:app --reload
```

## Docker Deployment

1. Build and run with Docker Compose:
```bash
docker-compose up -d
```

2. Access the services:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/api/docs

## API Documentation

The API documentation is available at `/api/docs` (Swagger) and `/api/redoc` (ReDoc).

### Main Endpoints

- `POST /api/v1/parse-and-rank`: Parse and rank CVs against a job description
- `GET /api/health`: Health check endpoint

## Monitoring

The application includes:
- Request logging
- Health checks

## Security

- Rate limiting per IP
- CORS middleware
- Trusted hosts middleware
- Environment variable management
- Non-root Docker user

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 