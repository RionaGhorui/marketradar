from fastapi import Request
from psycopg_pool import ConnectionPool


def get_pool(request: Request) -> ConnectionPool:
    return request.app.state.pool


def get_embedder(request: Request):
    return request.app.state.embedder


def get_llm(request: Request):
    return request.app.state.llm
