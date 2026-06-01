# counselai

Project scaffold for CounselAI.

Structure:

- backend/
  - app/ (Flask application)
  - tests/ (unit tests)
  - alembic/ (DB migrations)
  - requirements.txt
  - Dockerfile
- frontend/ (frontend app)

Run the backend (development):

```bash
python -m pip install -r backend/requirements.txt
export FLASK_APP=backend.app:create_app
flask run
```
