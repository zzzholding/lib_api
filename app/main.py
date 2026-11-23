
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Library API")


def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="library_db",
        user="library_user",
        password="library_pass"
    )


class LoanRequest(BaseModel):
    book_id: int
    reader_id: int


# Получить все книги
@app.get("/books")
def get_books():
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, available FROM books ORDER BY id"
            )
            rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "title": row[1],
                "available": row[2]
            }
            for row in rows
        ]

    finally:
        conn.close()


# Получить книгу по ID
@app.get("/books/{book_id}")
def get_book(book_id: int):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, available FROM books WHERE id = %s",
                (book_id,)
            )
            row = cur.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Book not found"
            )

        return {
            "id": row[0],
            "title": row[1],
            "available": row[2]
        }

    finally:
        conn.close()


# Оформить выдачу книги
@app.post("/loans", status_code=201)
def create_loan(request: LoanRequest):
    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, available
                    FROM books
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (request.book_id,)
                )

                book = cur.fetchone()

                if book is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Book not found"
                    )

                if not book[1]:
                    raise HTTPException(
                        status_code=409,
                        detail="Book is not available"
                    )

                cur.execute(
                    """
                    INSERT INTO loans (book_id, reader_id)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (request.book_id, request.reader_id)
                )

                loan_id = cur.fetchone()[0]

                cur.execute(
                    """
                    UPDATE books
                    SET available = FALSE
                    WHERE id = %s
                    """,
                    (request.book_id,)
                )

        return {
            "message": "Book successfully loaned",
            "loan_id": loan_id,
            "book_id": request.book_id,
            "reader_id": request.reader_id
        }

    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Book already has an active loan"
        )

    finally:
        conn.close()