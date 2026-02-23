from sqlite3 import IntegrityError
from App.models import Season
from App.database import db


# Create Season
def create_season(year):
    if year is None:
        raise ValueError("Year is required")

    try:
        year = int(year)
    except (TypeError, ValueError):
        raise ValueError("Year must be an integer")

    newSeason = Season(year=year)

    try:
        db.session.add(newSeason)
        db.session.commit()
        return newSeason
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Season year already exists")


# Read Seasons
def get_season(seasonID):
    return db.session.get(Season, seasonID)

def get_season_by_year(year):
    try:
        year = int(year)
    except (TypeError, ValueError):
        return None

    result = db.session.execute(db.select(Season).filter_by(year=year))
    return result.scalar_one_or_none()

def get_all_seasons():
    return db.session.scalars(db.select(Season)).all()

def get_all_seasons_json():
    seasons = get_all_seasons()
    if not seasons:
        return []
    return [s.get_json() for s in seasons]



# Update Season
def update_season_year(seasonID, newYear):
    season = get_season(seasonID)
    if not season:
        return False

    if newYear is None:
        raise ValueError("Year is required")

    try:
        newYear = int(newYear)
    except (TypeError, ValueError):
        raise ValueError("Year must be an integer")

    season.year = newYear

    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Season year already exists")


# Delete Season
def delete_season(seasonID):
    season = get_season(seasonID)
    if season:
        db.session.delete(season)
        db.session.commit()
        return True
    return False