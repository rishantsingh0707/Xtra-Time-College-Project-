# Xtra Time

Xtra Time is a football tournament management application. Organizers can publish and manage tournaments, while players can register teams and maintain their team rosters.

## Features

- Player and organizer accounts
- Session-based authentication
- Browse and filter tournaments by name, status, and location
- Organizer dashboard with tournament creation, editing, and deletion
- Tournament details with capacity, entry fee, prize pool, and schedule
- Player team registration for open tournaments
- Team member management, including positions and jersey numbers
- SQLite database with SQLAlchemy models
- Flask-rendered pages with Vite development tooling

## Tech Stack

- Python and Flask
- Flask-SQLAlchemy
- SQLite by default
- Vite, React, and TypeScript tooling
- Tailwind CSS and Lucide React dependencies

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer
- npm

## Installation

Clone or open the project, then install the Python and JavaScript dependencies:

```bash
python -m pip install -r requirements.txt
npm install
```

## Running the Application

### Windows

The bundled `npm run dev` launcher uses `python3` and `pkill`, which are commonly unavailable in native Windows shells. Start the services in two terminals instead.

Terminal 1 - Flask backend:

```powershell
python app.py
```

Terminal 2 - Vite development server:

```powershell
npm run dev -- --host 127.0.0.1
```

Open [http://localhost:5173](http://localhost:5173). The Vite server proxies application routes to Flask on port 5000.

You can also open the backend directly at [http://127.0.0.1:5000](http://127.0.0.1:5000).

### macOS or Linux

The combined launcher starts Flask and Vite together:

```bash
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173).

## Configuration

The application uses these environment variables:

- `SECRET_KEY`: Flask session signing key. Set a strong value outside local development.
- `DATABASE_URL`: SQLAlchemy database URL. Defaults to SQLite at `xtra_time.db`.

PowerShell example:

```powershell
$env:SECRET_KEY = "replace-with-a-long-random-value"
$env:DATABASE_URL = "sqlite:///xtra_time.db"
python app.py
```

The database tables are created automatically when the Flask application starts. The local SQLite database file is created in the project directory unless `DATABASE_URL` points elsewhere.

## Typical Workflow

1. Register an account as an organizer or player.
2. Organizers create a tournament from the organizer dashboard.
3. Players browse open tournaments and register a team.
4. Team captains add or remove team members from the team details page.
5. Organizers update tournament status or details as the event progresses.

## Project Structure

```text
.
├── app.py              Flask routes, authentication, and application setup
├── models.py           SQLAlchemy database models
├── requirements.txt    Python dependencies
├── start-dev.mjs       Combined development launcher
├── vite.config.ts      Vite configuration and Flask proxy
├── templates/          Jinja HTML templates
├── static/             CSS and other static assets
└── src/                Vite/React frontend scaffold
```

## Development Checks

Run the available frontend checks with:

```bash
npm run lint
npm run typecheck
npm run build
```

There is currently no dedicated automated test suite in the repository.

## Notes

- Flask runs on port `5000`.
- Vite runs on port `5173`.
- The default development secret key should not be used in production.
- Debug mode is enabled by the current local Flask entry point; configure a production WSGI server before deployment.
