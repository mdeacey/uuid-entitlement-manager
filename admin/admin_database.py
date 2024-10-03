import sqlite3
from shared.shared_database import get_database_connection, DATABASE_FILE
from shared.utils.logging import logger

def clear_all_balances():
    """
    Clears all balances to zero for all users.
    """
    try:
        with get_database_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET balance = 0')
            logger.info("All user balances have been cleared to zero.")
    except sqlite3.Error as e:
        logger.exception("Admin database error while clearing all balances: {}", e)

def delete_all_user_records():
    """
    Deletes all user records from the shared database.
    """
    try:
        with get_database_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM users')
            logger.info("All user records have been successfully deleted from the shared database.")
    except sqlite3.Error as e:
        logger.exception("Admin database error while deleting all user records: {}", e)
