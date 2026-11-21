import sqlite3
from datetime import datetime

DB_NAME = "library.db"


class LibraryManagement:
    """Handles all database operations for the Library Management System."""

    def __init__(self, db_name=DB_NAME):
        self.connection = sqlite3.connect(db_name)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.connection.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                available INTEGER NOT NULL CHECK (
                    available >= 0 AND available <= quantity
                )
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS issued_books (
                issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                member_name TEXT NOT NULL,
                issue_date TEXT NOT NULL,
                FOREIGN KEY (book_id) REFERENCES books(book_id)
            )
        """)
        self.connection.commit()

    def add_book(self, title, author, quantity):
        title = title.strip()
        author = author.strip()

        if not title or not author:
            print("[ERROR] Title and author cannot be empty.")
            return

        if quantity <= 0:
            print("[ERROR] Quantity must be greater than zero.")
            return

        self.cursor.execute(
            """
            INSERT INTO books (title, author, quantity, available)
            VALUES (?, ?, ?, ?)
            """,
            (title, author, quantity, quantity)
        )
        self.connection.commit()
        print(
            f"[OK] Book '{title}' added successfully "
            f"with {quantity} copies."
        )

    def view_books(self):
        self.cursor.execute("""
            SELECT book_id, title, author, quantity, available
            FROM books
            ORDER BY book_id
        """)
        return self.cursor.fetchall()

    def search_book(self, keyword):
        like = f"%{keyword.strip()}%"
        self.cursor.execute("""
            SELECT book_id, title, author, quantity, available
            FROM books
            WHERE title LIKE ? OR author LIKE ?
            ORDER BY book_id
        """, (like, like))
        return self.cursor.fetchall()

    def issue_book(self, book_id, member_name):
        member_name = member_name.strip()

        if not member_name:
            print("[ERROR] Member name cannot be empty.")
            return False

        self.cursor.execute(
            "SELECT available FROM books WHERE book_id = ?",
            (book_id,)
        )
        result = self.cursor.fetchone()

        if result is None or result[0] <= 0:
            print("[ERROR] Book not available for issue.")
            return False

        issue_date = datetime.now().strftime("%Y-%m-%d")

        try:
            self.cursor.execute("""
                UPDATE books
                SET available = available - 1
                WHERE book_id = ? AND available > 0
            """, (book_id,))

            if self.cursor.rowcount != 1:
                self.connection.rollback()
                print("[ERROR] Book not available for issue.")
                return False

            self.cursor.execute("""
                INSERT INTO issued_books (book_id, member_name, issue_date)
                VALUES (?, ?, ?)
            """, (book_id, member_name, issue_date))

            self.connection.commit()
            print(f"[OK] Book issued to {member_name}.")
            return True

        except sqlite3.Error as error:
            self.connection.rollback()
            print(f"[ERROR] Could not issue book: {error}")
            return False

    def return_book(self, book_id):
        self.cursor.execute("""
            SELECT issue_id
            FROM issued_books
            WHERE book_id = ?
            ORDER BY issue_id
            LIMIT 1
        """, (book_id,))
        row = self.cursor.fetchone()

        if row is None:
            print("[ERROR] No issued record found for this book.")
            return False

        try:
            self.cursor.execute(
                "DELETE FROM issued_books WHERE issue_id = ?",
                (row[0],)
            )
            self.cursor.execute("""
                UPDATE books
                SET available = available + 1
                WHERE book_id = ?
            """, (book_id,))
            self.connection.commit()
            print("[OK] Book returned successfully.")
            return True

        except sqlite3.Error as error:
            self.connection.rollback()
            print(f"[ERROR] Could not return book: {error}")
            return False

    def delete_book(self, book_id):
        self.cursor.execute(
            "SELECT COUNT(*) FROM issued_books WHERE book_id = ?",
            (book_id,)
        )
        active_issues = self.cursor.fetchone()[0]

        if active_issues > 0:
            print(
                "[ERROR] This book has an active issue record. "
                "Return the book before deleting it."
            )
            return False

        self.cursor.execute(
            "DELETE FROM books WHERE book_id = ?",
            (book_id,)
        )
        self.connection.commit()

        if self.cursor.rowcount:
            print("[OK] Book record deleted.")
            return True

        print("[ERROR] Book ID not found.")
        return False

    def close(self):
        self.connection.close()


def print_books(rows):
    if not rows:
        print("No records found.")
        return

    print(
        f"\n{'ID':<5}{'Title':<35}{'Author':<25}"
        f"{'Qty':<7}{'Available'}"
    )
    print("-" * 82)

    for row in rows:
        book_id, title, author, quantity, available = row
        print(
            f"{book_id:<5}{title[:34]:<35}{author[:24]:<25}"
            f"{quantity:<7}{available}"
        )


def get_integer(prompt, minimum=None):
    while True:
        try:
            value = int(input(prompt))
            if minimum is not None and value < minimum:
                print(f"[ERROR] Please enter a number greater than or equal to {minimum}.")
                continue
            return value
        except ValueError:
            print("[ERROR] Invalid input. Please enter a whole number.")


def main_menu():
    library = LibraryManagement()

    try:
        while True:
            print("\n" + "=" * 46)
            print("          LIBRARY MANAGEMENT SYSTEM")
            print("=" * 46)
            print(" 1. Add New Book")
            print(" 2. View All Books")
            print(" 3. Search Book")
            print(" 4. Issue Book")
            print(" 5. Return Book")
            print(" 6. Delete Book")
            print(" 7. Exit")
            print("=" * 46)

            choice = get_integer("Enter your choice (1-7): ", 1)

            if choice == 1:
                title = input("Enter book title: ")
                author = input("Enter author name: ")
                quantity = get_integer("Enter quantity: ", 1)
                library.add_book(title, author, quantity)

            elif choice == 2:
                print_books(library.view_books())

            elif choice == 3:
                keyword = input("Enter title or author keyword: ")
                print_books(library.search_book(keyword))

            elif choice == 4:
                book_id = get_integer("Enter Book ID to issue: ", 1)
                member_name = input("Enter member name: ")
                library.issue_book(book_id, member_name)

            elif choice == 5:
                book_id = get_integer("Enter Book ID to return: ", 1)
                library.return_book(book_id)

            elif choice == 6:
                book_id = get_integer("Enter Book ID to delete: ", 1)
                library.delete_book(book_id)

            elif choice == 7:
                print("Thank you for using the Library Management System.")
                break

            else:
                print("[ERROR] Please choose a number between 1 and 7.")

    except (EOFError, KeyboardInterrupt):
        print("\nProgram stopped.")

    finally:
        library.close()


if __name__ == "__main__":
    main_menu()
