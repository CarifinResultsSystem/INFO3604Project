from uuid import uuid4

from App.database import db
from .user import create_user
from .participant import create_participant
from .institution import create_institution
from .pointsRules import create_individual_rule, create_team_rule
from .event import create_event
from .season import create_season

def initialize():
    db.drop_all()
    db.create_all()
    create_user('bob', 'admin', 'bob@mail.com', 'bobpass')
    create_user('alice', 'judge', 'alice@mail.com', 'alicepass')
    create_user('john', 'scoretaker', 'john@mail.com', 'johnpass')
    create_user('eve', 'hr', 'eve@mail.com', 'evepass')
    season = create_season(2026)
    institution1 = create_institution("Scotiabank", "Port of Spain")
    institution2 = create_institution("Republic Bank", "Port of Spain")
    event = create_event("1 Lap Savannah", "2026-06-15", "09:00","Queens Park Savannah", season.seasonID)
    create_participant(str(uuid4()), "Dave", "Darren", "Male", "2000-01-01", "San Fernando", institution1.institutionID, [event[0].eventID])
    create_participant(str(uuid4()), "Frank", "Frederick", "Male", "2000-01-01", "San Fernando", institution2.institutionID, [event[0].eventID])
    create_individual_rule(event[0].eventID, season.seasonID, 1, "Gold", 15)
    create_individual_rule(event[0].eventID, season.seasonID, 2, "Silver", 10)
    create_individual_rule(event[0].eventID, season.seasonID, 3, "Silver", 5)
    create_team_rule(event[0].eventID, season.seasonID, "Participation/Attendance", "Mr. Carifin Representative", 10)
    create_team_rule(event[0].eventID, season.seasonID, "Participation/Attendance", "Mrs. Carifin Representative", 10)
    create_team_rule(event[0].eventID, season.seasonID, "Participation/Attendance", "Team Uniformity", 10)