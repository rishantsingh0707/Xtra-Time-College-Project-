import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120))
    role = db.Column(db.String(20), nullable=False, default="player")  # organizer | player
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tournaments = db.relationship("Tournament", backref="organizer", cascade="all, delete-orphan")
    teams = db.relationship("Team", backref="captain", cascade="all, delete-orphan")


class Tournament(db.Model):
    __tablename__ = "tournaments"
    id = db.Column(db.Integer, primary_key=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    prize_pool = db.Column(db.Float, nullable=False, default=0)
    currency = db.Column(db.String(10), nullable=False, default="USD")
    location = db.Column(db.String(200), nullable=False)
    entry_fee = db.Column(db.Float, nullable=False, default=0)
    start_time = db.Column(db.DateTime, nullable=False)
    max_teams = db.Column(db.Integer, nullable=False, default=16)
    status = db.Column(db.String(20), nullable=False, default="open")  # open | closed | completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teams = db.relationship("Team", backref="tournament", cascade="all, delete-orphan")

    @property
    def team_count(self):
        return len(self.teams)

    @property
    def spots_left(self):
        return max(0, self.max_teams - len(self.teams))


class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    captain_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship("TeamMember", backref="team", cascade="all, delete-orphan")

    @property
    def member_count(self):
        return len(self.members)


class TeamMember(db.Model):
    __tablename__ = "team_members"
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    position = db.Column(db.String(50))
    jersey_number = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
