import os
import sys
from datetime import datetime

# Ensure local pylibs (flask, sqlalchemy, etc.) is importable regardless of
# how the process is launched (npm, node, direct python3, etc.)
_pylibs = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pylibs")
if os.path.isdir(_pylibs) and _pylibs not in sys.path:
    sys.path.insert(0, _pylibs)

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, User, Tournament, Team, TeamMember

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "xtra-time-dev-secret-key-change-in-prod")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///xtra_time.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# ---------------------------------------------------------------------------
# Helpers / decorators
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access that page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def organizer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access that page.", "error")
            return redirect(url_for("login"))
        if session.get("role") != "organizer":
            flash("Only organizers can access that page.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


def current_user():
    if "user_id" in session:
        return db.session.get(User, session["user_id"])
    return None


@app.context_processor
def inject_globals():
    return {"current_user": current_user()}


def fmt_currency(amount, currency="USD"):
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "PKR": "₨", "BRL": "R$", "NGN": "₦"}
    sym = symbols.get(currency, currency + " ")
    try:
        return f"{sym}{float(amount):,.0f}"
    except (ValueError, TypeError):
        return f"{sym}0"


def fmt_date(dt):
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return dt
    if dt is None:
        return "TBD"
    if dt.tzinfo:
        dt = dt.replace(tzinfo=None)
    return dt.strftime("%b %d, %Y · %I:%M %p")


app.jinja_env.filters["currency"] = fmt_currency
app.jinja_env.filters["fmt_date"] = fmt_date


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    tournaments = Tournament.query.filter_by(status="open").order_by(Tournament.start_time.asc()).limit(6).all()
    return render_template("index.html", tournaments=tournaments)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "player")

        if role not in ("organizer", "player"):
            role = "player"

        if not username or not email or not password:
            flash("Username, email and password are required.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("That username is taken.", "error")
            return render_template("register.html")

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            full_name=full_name or username,
            role=role,
        )
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        session["role"] = user.role
        session["username"] = user.username
        flash(f"Welcome to Xtra Time, {user.username}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["role"] = user.role
            session["username"] = user.username
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been signed out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    if user.role == "organizer":
        tournaments = Tournament.query.filter_by(organizer_id=user.id).order_by(Tournament.created_at.desc()).all()
        return render_template("dashboard_organizer.html", tournaments=tournaments)
    else:
        teams = Team.query.filter_by(captain_id=user.id).order_by(Team.created_at.desc()).all()
        return render_template("dashboard_player.html", teams=teams)


# ---------------------------------------------------------------------------
# Tournaments (browse + organizer CRUD)
# ---------------------------------------------------------------------------
@app.route("/tournaments")
def tournaments():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    location = request.args.get("location", "").strip()

    query = Tournament.query
    if q:
        query = query.filter(Tournament.name.ilike(f"%{q}%"))
    if status:
        query = query.filter_by(status=status)
    if location:
        query = query.filter(Tournament.location.ilike(f"%{location}%"))

    all_tournaments = query.order_by(Tournament.start_time.asc()).all()
    locations = [r[0] for r in db.session.query(Tournament.location).distinct().all() if r[0]]
    return render_template(
        "tournaments.html",
        tournaments=all_tournaments,
        q=q,
        status=status,
        location=location,
        locations=locations,
    )


@app.route("/tournaments/<int:tournament_id>")
def tournament_detail(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        abort(404)
    teams = Team.query.filter_by(tournament_id=tournament_id).all()
    team_count = len(teams)
    return render_template(
        "tournament_detail.html",
        tournament=tournament,
        teams=teams,
        team_count=team_count,
        spots_left=max(0, tournament.max_teams - team_count),
        is_organizer=(session.get("user_id") == tournament.organizer_id),
    )


@app.route("/tournaments/new", methods=["GET", "POST"])
@organizer_required
def create_tournament():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        prize_pool = request.form.get("prize_pool", "0") or "0"
        currency = request.form.get("currency", "USD")
        location = request.form.get("location", "").strip()
        entry_fee = request.form.get("entry_fee", "0") or "0"
        start_time = request.form.get("start_time", "")
        max_teams = request.form.get("max_teams", "16") or "16"

        if not name or not location or not start_time:
            flash("Tournament name, location and start time are required.", "error")
            return render_template("tournament_form.html", form=request.form)

        try:
            prize = float(prize_pool)
            fee = float(entry_fee)
            teams = int(max_teams)
            if teams < 2:
                raise ValueError
        except ValueError:
            flash("Prize pool, entry fee must be numbers and max teams must be at least 2.", "error")
            return render_template("tournament_form.html", form=request.form)

        dt = datetime.fromisoformat(start_time)

        tournament = Tournament(
            organizer_id=session["user_id"],
            name=name,
            description=description,
            prize_pool=prize,
            currency=currency,
            location=location,
            entry_fee=fee,
            start_time=dt,
            max_teams=teams,
        )
        db.session.add(tournament)
        db.session.commit()
        flash("Tournament created!", "success")
        return redirect(url_for("tournament_detail", tournament_id=tournament.id))

    return render_template("tournament_form.html", form={})


@app.route("/tournaments/<int:tournament_id>/edit", methods=["GET", "POST"])
@organizer_required
def edit_tournament(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        abort(404)
    if tournament.organizer_id != session["user_id"]:
        flash("You can only edit your own tournaments.", "error")
        return redirect(url_for("tournament_detail", tournament_id=tournament_id))

    if request.method == "POST":
        tournament.name = request.form.get("name", "").strip() or tournament.name
        tournament.description = request.form.get("description", "").strip()
        tournament.currency = request.form.get("currency", "USD")
        tournament.location = request.form.get("location", "").strip() or tournament.location
        tournament.status = request.form.get("status", tournament.status)

        try:
            tournament.prize_pool = float(request.form.get("prize_pool", 0) or 0)
            tournament.entry_fee = float(request.form.get("entry_fee", 0) or 0)
            tournament.max_teams = int(request.form.get("max_teams", 16) or 16)
        except ValueError:
            flash("Invalid numeric values.", "error")
            return render_template("tournament_form.html", form=tournament, edit=True, tournament_id=tournament_id)

        start_time = request.form.get("start_time", "")
        if start_time:
            tournament.start_time = datetime.fromisoformat(start_time)

        db.session.commit()
        flash("Tournament updated.", "success")
        return redirect(url_for("tournament_detail", tournament_id=tournament.id))

    return render_template("tournament_form.html", form=tournament, edit=True, tournament_id=tournament_id)


@app.route("/tournaments/<int:tournament_id>/delete", methods=["POST"])
@organizer_required
def delete_tournament(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        abort(404)
    if tournament.organizer_id != session["user_id"]:
        flash("You can only delete your own tournaments.", "error")
        return redirect(url_for("tournament_detail", tournament_id=tournament_id))

    db.session.delete(tournament)
    db.session.commit()
    flash("Tournament deleted.", "info")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Teams (player CRUD + registration into a tournament)
# ---------------------------------------------------------------------------
@app.route("/tournaments/<int:tournament_id>/register", methods=["GET", "POST"])
@login_required
def register_team(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        abort(404)

    if tournament.status != "open":
        flash("Registration is closed for this tournament.", "error")
        return redirect(url_for("tournament_detail", tournament_id=tournament_id))

    existing = Team.query.filter_by(tournament_id=tournament_id, captain_id=session["user_id"]).first()
    if existing:
        flash("You already have a team registered in this tournament.", "info")
        return redirect(url_for("team_detail", team_id=existing.id))

    team_count = Team.query.filter_by(tournament_id=tournament_id).count()
    if team_count >= tournament.max_teams:
        flash("This tournament is full.", "error")
        return redirect(url_for("tournament_detail", tournament_id=tournament_id))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        members_raw = request.form.getlist("members")
        positions_raw = request.form.getlist("positions")
        jerseys_raw = request.form.getlist("jerseys")

        if not name:
            flash("Team name is required.", "error")
            return render_template("team_form.html", tournament=tournament, form=request.form)

        team = Team(name=name, captain_id=session["user_id"], tournament_id=tournament_id)
        db.session.add(team)
        db.session.flush()

        for i, member_name in enumerate(members_raw):
            member_name = member_name.strip()
            if not member_name:
                continue
            pos = positions_raw[i].strip() if i < len(positions_raw) else ""
            jersey = None
            if i < len(jerseys_raw) and jerseys_raw[i].strip():
                try:
                    jersey = int(jerseys_raw[i])
                except ValueError:
                    jersey = None
            db.session.add(TeamMember(
                team_id=team.id, name=member_name, position=pos or None, jersey_number=jersey
            ))

        db.session.commit()
        flash("Team registered successfully!", "success")
        return redirect(url_for("team_detail", team_id=team.id))

    return render_template("team_form.html", tournament=tournament, form={})


@app.route("/teams/<int:team_id>")
def team_detail(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        abort(404)
    tournament = db.session.get(Tournament, team.tournament_id)
    members = TeamMember.query.filter_by(team_id=team_id).order_by(TeamMember.id).all()
    is_captain = session.get("user_id") == team.captain_id
    return render_template("team_detail.html", team=team, tournament=tournament, members=members, is_captain=is_captain)


@app.route("/teams/<int:team_id>/members/add", methods=["POST"])
@login_required
def add_member(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        abort(404)
    if team.captain_id != session["user_id"]:
        flash("Only the captain can add members.", "error")
        return redirect(url_for("team_detail", team_id=team_id))

    name = request.form.get("name", "").strip()
    position = request.form.get("position", "").strip()
    jersey = request.form.get("jersey", "").strip()

    if not name:
        flash("Member name is required.", "error")
        return redirect(url_for("team_detail", team_id=team_id))

    jersey_num = None
    if jersey:
        try:
            jersey_num = int(jersey)
        except ValueError:
            pass

    db.session.add(TeamMember(team_id=team_id, name=name, position=position or None, jersey_number=jersey_num))
    db.session.commit()
    flash("Team member added.", "success")
    return redirect(url_for("team_detail", team_id=team_id))


@app.route("/teams/<int:team_id>/members/<int:member_id>/delete", methods=["POST"])
@login_required
def delete_member(team_id, member_id):
    team = db.session.get(Team, team_id)
    if not team:
        abort(404)
    if team.captain_id != session["user_id"]:
        flash("Only the captain can remove members.", "error")
        return redirect(url_for("team_detail", team_id=team_id))

    member = TeamMember.query.filter_by(id=member_id, team_id=team_id).first()
    if member:
        db.session.delete(member)
        db.session.commit()
        flash("Member removed.", "info")
    return redirect(url_for("team_detail", team_id=team_id))


@app.route("/teams/<int:team_id>/withdraw", methods=["POST"])
@login_required
def withdraw_team(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        abort(404)
    if team.captain_id != session["user_id"]:
        flash("Only the captain can withdraw the team.", "error")
        return redirect(url_for("team_detail", team_id=team_id))

    tournament_id = team.tournament_id
    db.session.delete(team)
    db.session.commit()
    flash("Your team has been withdrawn from the tournament.", "info")
    return redirect(url_for("tournament_detail", tournament_id=tournament_id))


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page not found"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="Something went wrong on our end."), 500


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    # Always use port 5000 for Flask — the harness uses PORT env var for Vite.
    # use_reloader=False so the process doesn't fork in background mode.
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
