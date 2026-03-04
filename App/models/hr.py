from datetime import datetime, timedelta, timezone
from App.database import db

TRINIDAD_TZ = timezone(timedelta(hours=-4))

def _local_now():
    return datetime.now(TRINIDAD_TZ).replace(tzinfo=None)


class HRReport(db.Model):
    __tablename__ = "hr_reports"

    reportID     = db.Column(db.Integer, primary_key=True)
    filename     = db.Column(db.String(255), nullable=False)
    filepath     = db.Column(db.String(512), nullable=True)
    is_read      = db.Column(db.Boolean, default=False)
    generated_at = db.Column(db.DateTime, default=_local_now)

    generated_by = db.Column(
        db.Integer,
        db.ForeignKey("users.userID"),
        nullable=False
    )

    season = db.Column(db.String(20), nullable=True)

    user = db.relationship("User", backref=db.backref("hr_reports", lazy=True))

    def __init__(self, filename, generated_by, season=None, filepath=None):
        self.filename     = filename
        self.generated_by = generated_by
        self.season       = season
        self.filepath     = filepath

    def get_json(self):
        return {
            "reportID":     self.reportID,
            "filename":     self.filename,
            "filepath":     self.filepath,
            "is_read":      self.is_read,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "generated_by": self.generated_by,
            "season":       self.season,
        }