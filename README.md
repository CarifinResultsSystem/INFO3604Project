# 🏆 INFO3604 Project – CLI Testing Guide

This project provides CLI commands for testing controllers using Flask's built-in CLI system.

All commands are run using:

```bash
flask <command-name> [arguments]
```

---

# ⚙️ Setup

### 1️⃣ Activate Virtual Environment (Windows Git Bash)

```bash
source .venv/Scripts/activate
```

### 2️⃣ Set up Flask
#### Initialize Database:
```bash
flask init
```

#### Run Application:
```bash
flask run
```

Verify commands:

```bash
flask --help
```

---

# 👤 USER COMMANDS

```bash
flask create-user <username> <role> <email> <password>
flask get-user <user_id>
flask get-user-by-username <username>
flask get-all-users
flask update-username <user_id> <new_username>
flask update-email <user_id> <new_email>
flask update-password <user_id> <new_password>
flask update-role <user_id> <new_role>
flask delete-user <user_id>
flask authenticate-user <username> <password>
```

---

# 👨‍⚖️ ADMIN COMMANDS

```bash
flask assign-role <user_id> <role>
```

---

# 🧑‍⚖️ JUDGE COMMANDS

```bash
flask get-judge <user_id>
```

---

# 📝 SCORETAKER COMMANDS

```bash
flask scoretaker-get <user_id>
flask score-doc-upload <user_id> <file_path>
flask score-docs-list <user_id>
flask score-docs-list-json <user_id>
flask score-doc-get <document_id>
flask score-doc-delete <user_id> <document_id>
```

---

# 📅 EVENT COMMANDS

```bash
flask create-event <event_name> <event_date> <event_time> <event_location>
```

Example:

```bash
flask create-event "Sports Day" "2026-05-01 00:00:00" "2026-05-01 09:00:00" "Main Stadium"
```

---

# 🏁 SEASON COMMANDS

```bash
flask season-create <year>
flask season-get <season_id>
flask season-get-year <year>
flask season-list
flask season-list-json
flask season-update-year <season_id> <new_year>
flask season-delete <season_id>
```

---

# 🏫 INSTITUTION COMMANDS

```bash
flask create-institution <institution_name>
flask get-institution <institution_id>
flask get-institution-name <institution_name>
flask get-all-institutions
```

---

# 🏆 LEADERBOARD COMMANDS

```bash
flask create-leaderboard <year>
flask get-leaderboard <year>
```

---

# 🎯 POINTS RULES COMMANDS

```bash
flask points-rule-create <eventType> <conditionType> <conditionValue> <upperLimit> <lowerLimit> <seasonID>
flask points-rule-get <pointsID>
flask points-rules-by-season <seasonID>
flask points-rules-list
flask points-rules-list-json
flask points-rule-update <pointsID> --eventType "Track" --conditionType "place" --conditionValue 1 --upperLimit 10 --lowerLimit 1 --seasonID 2
flask points-rule-delete <pointsID>
```

Example:

```bash
flask points-rule-create "100m" "place" 1 10 1 1
```

---

# ✅ View All Commands

```bash
flask --help
```

---

# 📌 Notes

- Activate the virtual environment before running commands.
- Ensure the database is initialized.
- Some commands depend on existing records (e.g., `seasonID` must exist before creating points rules).
